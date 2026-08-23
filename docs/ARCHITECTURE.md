# GW EnergyPilot architecture

This document describes the current runtime architecture of GW EnergyPilot **v0.23 Beta**.

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
        +--> GWEnergyPilotAccounting
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

Persistent EnergyPilot-owned runtime state is split by purpose:

```text
ConfigEntry data/options       user/integration configuration
GoodWe registers               inverter-stored settings + hardware state
EMHASS config/output           optimizer configuration + current plan
runtime Store                  small EnergyPilot runtime history
accounting Store               derived persistent daily grid accounting
```

## Runtime objects

`custom_components/gw_energypilot/__init__.py` creates one runtime object per Home Assistant config entry:

- `GWModbusClient`;
- `GWEnergyPilotCoordinator`;
- `GWEnergyPilotController`;
- `GWEnergyPilotOrchestrator`;
- `GWEnergyPilotAccounting`.

Platforms:

- sensor;
- switch;
- number;
- select;
- button.

The initial Modbus refresh runs as a background config-entry task so an unavailable/sleeping inverter does not unnecessarily block Home Assistant startup. After that fresh refresh, accounting may perform its optional one-time Recorder bootstrap.

## Stable device identity

Current Home Assistant device identity is:

```text
(DOMAIN, config_entry_id)
```

v0.17 migrates the former mutable `(DOMAIN, host:slave)` identifier before entity setup when necessary. Entity unique IDs already use the config-entry ID.

Changing GoodWe connection data must not intentionally create a second EnergyPilot device.

## Configuration and APIs

EnergyPilot uses the existing Home Assistant `ConfigEntry`; there is no parallel settings database.

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
- `ConfigEntry.data` — GoodWe connection plus **GoodWe smart meter active**;
- EMHASS `/get-config` and `/set-config` — live EMHASS configuration such as SOC bounds and `costfun`;
- GoodWe registers `45356/45358` — inverter-stored manual Beta SOC-floor settings;
- Home Assistant Store — persistent EnergyPilot runtime/accounting state, never user configuration.

See `docs/SETTINGS.md` and `docs/RUNTIME_STATE.md`.

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

`registers.py` is the canonical definition/read-block source. `client.py` must not duplicate telemetry block lists.

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

## Persistent grid accounting

v0.23 adds `GWEnergyPilotAccounting` as the single native daily grid-accounting runtime.

Canonical physical sources remain:

```text
36017 = lifetime grid import
36015 = lifetime grid export
```

The accounting runtime:

- establishes a baseline from the physical lifetime counters;
- accumulates only positive counter deltas;
- re-baselines on a counter decrease instead of inventing negative energy/reset semantics;
- rolls current-day totals at local midnight;
- persists current/previous-day state through Home Assistant storage;
- exposes native daily import/export entities through `accounting_sensor.py`;
- may use Recorder once during upgrade bootstrap to recover previous/current local-midnight boundaries.

Recorder is **not** part of the live accounting loop. The 24-hour Grid power graph remains Recorder-backed because it is historical visualization.

The extended `36104/36120` candidates remain Beta diagnostics and are not canonical accounting inputs.

See `docs/ACCOUNTING.md`.

## Automatic controller ownership

`switch.automatic_control` is the master automatic EMS ownership switch.

When OFF:

```text
mode 1 · GoodWe Auto / AI
setpoint 0 W
```

When ON, the selected GoodWe strategy determines which optimizer output is the actuator plan unless a documented safety override is active.

### Strategy A — GoodWe smart meter active = ON

Default:

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

Modes 9/10 close the fast loop inside GoodWe against its own smart meter/PCC. EnergyPilot does **not** run the former 30-second mode-11 trim controller in parallel.

### Strategy B — GoodWe smart meter active = OFF

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt inside deadband -> mode 8 Battery Hold
```

This fallback requires finite `P_batt` but deliberately does **not** require `P_grid`.

### EV anti-discharge override

EV anti-discharge protection is directional and is not an EV charging controller.

During active EV charging:

```text
P_batt > +deadband -> mode 8  Battery Hold
P_batt near 0 W    -> mode 8  Battery Hold
P_batt < -deadband -> mode 11 Battery charge power
```

The direct mode-11 charge override is intentional even when normal automatic operation uses PCC modes 9/10/1. A changing EV load must not cause the home battery to become the EV's source merely to maintain a site-level PCC target.

When native orchestration is enabled, EV stop waits for a fresh EMHASS optimization before normal automatic execution resumes.

The stored key `enable_ev_coordination` is retained for backwards compatibility; user-facing terminology is **EV anti-discharge protection**.

See `docs/EV_ANTI_DISCHARGE.md`.

### Common safety gates

Automatic evaluation also respects:

- optimizer required state;
- configured maximum setpoint magnitude;
- finite numeric plan values;
- explicit Automatic Control ownership;
- EV anti-discharge protection when configured.

Beta diagnostic registers do not choose EMS modes or targets.

## Manual ownership

Manual mode selection and quick actions disable Automatic Control ownership before issuing a command.

The Controller test pad is only a frontend over the existing entities:

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

The active orchestrator remains layered:

```text
orchestrator_v013.GWEnergyPilotOrchestrator
  -> orchestrator_v012.GWEnergyPilotOrchestrator
       -> orchestrator.GWEnergyPilotOrchestrator
```

All three remain runtime dependencies until intentionally consolidated.

`emhass_config.py` uses complete-config reads/writes so selected changes preserve unrelated EMHASS configuration.

### Persistent orchestrator runtime evidence

v0.23 gives the active v0.13 orchestrator a `GWEnergyPilotRuntimeStore`.

The per-entry Store key is:

```text
gw_energypilot.runtime.<config_entry_id>
```

`last_success` is restored before the inherited orchestrator setup begins and is persisted only after a complete EnergyPilot-owned optimize + publish cycle succeeds. A later failure preserves the previous successful timestamp. Invalid/timezone-less stored timestamps are ignored.

This Store is runtime history only; configuration remains in `ConfigEntry.data/options` and EMHASS config.

See `docs/RUNTIME_STATE.md`.

## Load semantics

On the reference GW15K-ETA-G20, register `35172` is the primary GoodWe load value and normally matches the phase-load sum.

```text
PV - grid + battery
```

is a **system power balance diagnostic**, not a replacement load sensor.

External AC-coupled PV can complicate inverter-local load/forecast semantics. PCC modes 9/10 remain useful because the GoodWe smart meter observes the external generation in the live net-site balance.

## Event-driven optimization

Optimization can be triggered by:

- configured periodic interval;
- Optimize now;
- Resume AUTO;
- EMHASS strategy change;
- tomorrow prices becoming available;
- EV charging stopping;
- SOC limit changes after debounce.

Home Assistant startup deliberately does not start a new optimization.

## Frontend

The sidebar entry module selected by `__init__.py` is:

```text
gw-energy-pilot-v023.js
```

Current upper chain:

```text
gw-energy-pilot-v023.js
  -> gw-energy-pilot-v022-flow-direction.js
       -> gw-energy-pilot-v022.js
            -> gw-energy-pilot-v021.js
                 -> earlier layered dashboard/settings files
```

Responsibilities of the upper layers:

- v0.23 — persistent Today/Yesterday accounting UI and current release badge;
- flow-direction overlay — removes the layered particle double reversal;
- v0.22 — Smart Meter strategy UI and PCC/battery target relabelling;
- v0.21 — manual 12-mode EMS test pad.

Older versioned files remain active dependencies and must not be deleted based on filename alone.

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

The geometry-correct Forward/Reverse keyframe selected from live state is authoritative. The v0.23 overlay forces particle `animation-direction` to normal so an older layer cannot reverse that result a second time.

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
9. Keep a reversible fallback for Beta automatic control strategies.
10. External EV charging schedules remain external; EV anti-discharge may constrain battery direction but never owns the charger.
11. Derived accounting must consume canonical physical counters rather than replace them.
12. Persistent runtime history must remain separate from user configuration.
