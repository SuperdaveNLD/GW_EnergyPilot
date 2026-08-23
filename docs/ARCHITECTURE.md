# GW EnergyPilot architecture

This document describes the current runtime architecture of GW EnergyPilot **v0.22 Beta** plus staged next-update behavior where explicitly noted.

## High-level data flow

```text
GoodWe ETA-G20 inverter
        |
        | Modbus TCP
        v
GWModbusClient
        |
        v
GWEnergyPilotCoordinator
        |
        +--> Home Assistant telemetry/entities
        +--> GWEnergyPilotController
        +--> EMHASS orchestrator
        +--> diagnostics/dashboard

EMHASS
  |
  +-- publish --> P_batt / P_grid / optimization status
                      |
                      v
               Automatic Control
                      |
          +-----------+-----------+
          |                       |
GoodWe smart meter ON      GoodWe smart meter OFF
P_grid actuator plan       P_batt actuator plan
modes 9 / 10 / 1          modes 11 / 12 / 8
          |                       |
          +-----------+-----------+
                      |
                      v
              EMS 47511 / 47512
```

## Runtime objects

`custom_components/gw_energypilot/__init__.py` creates one runtime object per Home Assistant config entry:

- `GWModbusClient`;
- `GWEnergyPilotCoordinator`;
- `GWEnergyPilotController`;
- `GWEnergyPilotOrchestrator`.

Platforms:

- sensor;
- switch;
- number;
- select;
- button.

The initial Modbus refresh is a background config-entry task so a sleeping/unavailable inverter does not unnecessarily block Home Assistant startup.

## Stable device identity

Current Home Assistant device identity is:

```text
(DOMAIN, config_entry_id)
```

v0.17 migrates the former mutable `(DOMAIN, host:slave)` identifier before entity setup when necessary. Entity unique IDs already use the config-entry ID.

Changing GoodWe connection data must not intentionally create a second EnergyPilot device.

## Configuration and APIs

EnergyPilot uses the existing Home Assistant `ConfigEntry`; there is no separate configuration database.

Administrator dashboard APIs include:

```text
gw_energypilot/settings/get
gw_energypilot/settings/update

gw_energypilot/smart_meter/get
gw_energypilot/smart_meter/set

gw_energypilot/beta_soc/get
gw_energypilot/beta_soc/set
```

Ownership:

- `ConfigEntry.options` — EP/EMHASS integration options;
- `ConfigEntry.data` — GoodWe connection plus the v0.22 **GoodWe smart meter active** strategy choice;
- EMHASS `/get-config` and `/set-config` — live EMHASS configuration such as SOC bounds and `costfun`;
- GoodWe registers `45356/45358` — inverter-stored manual Beta SOC-floor settings.

See `docs/SETTINGS.md`.

## Modbus layer

`client.py` owns the asynchronous Modbus TCP connection.

Responsibilities:

- connect/reconnect;
- serialize I/O through an async lock;
- read required and optional register blocks from `registers.py`;
- decode typed/scaled telemetry;
- write the GoodWe EMS command;
- close/recover after transport/protocol errors.

Canonical EMS write order remains:

```text
write 47512 power/setpoint magnitude
wait briefly
write 47511 mode
```

Do not reorder these writes without hardware validation.

`registers.py` remains the canonical definition/read-block source. `client.py` must not duplicate telemetry block lists.

## Telemetry coordinator

`GWEnergyPilotCoordinator` is a Home Assistant `DataUpdateCoordinator` and publishes a `GWETAData` snapshot at the configured scan interval.

Important signs on the tested ETA-G20:

```text
GoodWe meter 36008
  negative = import
  positive = export

battery power
  negative = charging
  positive = discharging
```

EMHASS `P_grid` deliberately uses the opposite grid sign:

```text
P_grid > 0 = planned import
P_grid < 0 = planned export
```

## Automatic controller ownership

`switch.automatic_control` is the master automatic EMS ownership switch.

When OFF:

```text
mode 1 · GoodWe Auto / AI
setpoint 0 W
```

When ON, the selected GoodWe strategy determines which optimizer output is the actuator plan unless a documented safety override such as EV anti-discharge protection is active.

### Strategy A — GoodWe smart meter active = ON

This is the v0.22 default.

```text
P_grid > +deadband
    -> mode 9  Grid import target
    -> 47512 = planned import magnitude

P_grid < -deadband
    -> mode 10 Grid export target
    -> 47512 = planned export magnitude

P_grid inside deadband
    -> mode 1 GoodWe Auto / self-use
    -> 47512 = 0 W
```

Both `P_batt` and `P_grid` must be finite and optimizer readiness must pass. `P_batt` remains a plan-validity/diagnostic output; `P_grid` is the actuator request.

Modes 9/10 close the fast loop inside GoodWe against its own smart meter/PCC. EnergyPilot therefore does **not** run the former v0.18-v0.21 30-second mode-11 charge-trimming controller in parallel.

Hardware validation on the reference GW15K-ETA-G20 established that mode-9/mode-10 setpoints are grid targets, not direct battery targets.

### Strategy B — GoodWe smart meter active = OFF

```text
P_batt < -deadband
    -> mode 11 Battery charge power

P_batt > +deadband
    -> mode 12 Battery discharge power

P_batt inside deadband
    -> mode 8 Battery Hold
```

This fallback requires finite `P_batt` but deliberately does **not** require `P_grid`.

### Common safety gates

Automatic evaluation also respects:

- optimizer required state;
- configured maximum setpoint magnitude;
- EV anti-discharge protection when configured and EV charging is active;
- finite numeric plan values;
- explicit Automatic Control ownership.

Beta diagnostic registers do not choose EMS modes or targets.

## Manual ownership

Manual mode selection and quick actions disable Automatic Control ownership before issuing a command.

The v0.21+ Controller test pad is only a frontend over the existing entities:

```text
number.manual_power
      |
select.manual_mode
      |
controller.async_manual_command()
      |
GWModbusClient.async_set_mode()
```

The automatic Smart Meter setting never remaps a manual operator command.

## EMHASS architecture

EMHASS is an external prerequisite; EnergyPilot does not install it.

Native orchestration performs:

```text
live SOC + load forecast + optional runtime prices
        |
        v
POST /action/dayahead-optim
        |
        v
validate result
        |
        v
POST /action/publish-data
        |
        v
validate fresh numeric outputs/status
        |
        v
controller executes selected actuator strategy
```

The active orchestrator class remains layered:

```text
orchestrator_v013.GWEnergyPilotOrchestrator
  -> orchestrator_v012.GWEnergyPilotOrchestrator
       -> orchestrator.GWEnergyPilotOrchestrator
```

All three remain runtime dependencies until intentionally consolidated.

`emhass_config.py` uses complete-config reads/writes so selected changes preserve unrelated EMHASS configuration.

## Load semantics

On the reference GW15K-ETA-G20, register `35172` is the primary GoodWe load value and normally matches the phase-load sum.

```text
PV - grid + battery
```

is a **system power balance diagnostic**, not a replacement load sensor.

External AC-coupled PV can complicate `35172`/forecast semantics. PCC modes 9/10 are valuable in that topology because the GoodWe smart meter still observes the external generation in the live net-site balance.

## Event-driven optimization

Optimization can be triggered by:

- configured periodic interval;
- Optimize now;
- Resume AUTO;
- EMHASS strategy change;
- tomorrow prices becoming available;
- EV charging stopping;
- SOC limit changes after debounce.

Home Assistant startup itself deliberately does not start an optimization.

## EV anti-discharge protection

The staged next-update EV behavior is a **directional battery protection**, not an EV charging controller.

Ownership is deliberately separated:

```text
EV charger / external charging service
    -> owns EV charging start/stop/power

EMHASS
    -> owns the desired home-battery plan

EnergyPilot
    -> prevents home-battery discharge while the EV is charging
    -> allows an explicit home-battery charge plan

GoodWe / BMS / smart meter
    -> remain authoritative for inverter and hardware limits
```

During active EV charging, `P_batt` is the direction guard regardless of the normal automatic actuator strategy:

```text
P_batt > +deadband  -> mode 8 Battery Hold
P_batt near 0 W     -> mode 8 Battery Hold
P_batt < -deadband  -> mode 11 Battery charge power
```

The direct mode-11 charge override is intentional even when normal automatic operation uses PCC modes 9/10/1. A PCC target can result in either battery direction when the EV load changes; the EV safety contract instead requires a hard guarantee that the home battery cannot become the EV's source.

This architecture is useful when the EV charger is scheduled by an external service rather than simply following the lowest spot price. **Tibber Grid Rewards** is a concrete example: Tibber can start or pause connected EV charging to support grid conditions and reward the customer for that flexibility. EnergyPilot must not counteract such an external EV schedule by discharging the home battery into the car, and it must not unnecessarily block a separate EMHASS home-battery charge request.

EnergyPilot does not integrate with Tibber Grid Rewards and does not control the charger. Tibber Grid Rewards is only an explicit real-world ownership example.

The existing stored option name `enable_ev_coordination` is retained for backwards compatibility. User-facing terminology becomes **EV anti-discharge protection**.

After EV charging stops, EnergyPilot keeps the existing fresh-plan protection: when native orchestration is enabled it holds the battery while waiting for a new EMHASS optimization instead of executing the stale pre-stop plan.

See `docs/EV_ANTI_DISCHARGE.md` for the complete behavior contract and non-goals.

## Frontend

The sidebar entry module selected by `__init__.py` is now:

```text
gw-energy-pilot-v022.js
```

Current upper chain:

```text
gw-energy-pilot-v022.js
  -> gw-energy-pilot-v021.js       12-mode manual test pad
       -> gw-energy-pilot-v020.js  SOC diagnostics validity
            -> earlier layered dashboard/settings files
```

Older versioned files are therefore active dependencies and must not be deleted based on filename alone.

v0.22 adds at the top layer:

- Smart Meter automatic-strategy control in GOODWE settings;
- controller target relabelling for PCC versus battery targets;
- authoritative energy-flow particle direction from current signed telemetry.

## Live-flow direction contract

The current frontend must display energy movement as:

```text
PV production         -> hub
Grid import           -> hub
Grid export           hub -> grid
Battery charging      hub -> battery
Battery discharging   battery -> hub
House consumption     hub -> house
```

This direction is derived from live telemetry signs, not from the selected EMS mode.

## Primary confirmed control/telemetry registers

```text
35172  GoodWe load power
35301  PV total power
35182  battery power
37007  battery SOC
36008  fast grid power
36015  canonical cumulative grid export
36017  canonical cumulative grid import
47511  EMS mode
47512  EMS power/setpoint magnitude
```

See `docs/MODBUS.md` and `docs/EMS_MODES.md` for the full evidence/status contract.

## Design principles

1. Local operation first.
2. Home Assistant startup tolerates unavailable external devices.
3. Automatic/manual ownership is explicit.
4. Optimizer outputs pass readiness/numeric checks before control.
5. GoodWe register/mode semantics are evidence-based.
6. Do not run competing feedback controllers over the same EMS actuator.
7. Preserve entity unique IDs and stable device identity.
8. Keep one Home Assistant config entry as the integration configuration source.
9. Keep a reversible fallback for new Beta automatic control strategies.
10. External EV charging schedules remain external; EV anti-discharge protection may constrain battery direction but never takes ownership of the charger.
