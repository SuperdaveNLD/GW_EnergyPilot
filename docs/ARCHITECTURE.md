# GW EnergyPilot architecture

This document describes the current runtime architecture of GW EnergyPilot v0.17 Beta.

## High-level data flow

```text
GoodWe ETA-G20 inverter
        |
        | Modbus TCP
        v
GWModbusClient (client.py)
        |
        v
GWEnergyPilotCoordinator (coordinator.py)
        |
        +--> sensor entities
        +--> controller
        +--> EMHASS orchestrator
        +--> diagnostics/dashboard

EMHASS
  ^  |
  |  +-- optimization + publish --> P_batt / optim status entities
  |
  +----- EnergyPilot runtime configuration and SOC settings

Controller
   |
   +--> GoodWe EMS mode + power writes

Frontend panel
   |
   +--> reads Home Assistant entities/services
   +--> admin settings WebSocket API
                |
                v
          existing ConfigEntry
```

## Config-entry startup

`custom_components/gw_energypilot/__init__.py` creates one runtime object per config entry containing:

- `GWModbusClient`
- `GWEnergyPilotCoordinator`
- `GWEnergyPilotController`
- `GWEnergyPilotOrchestrator`

The integration forwards these Home Assistant platforms:

- sensor
- switch
- number
- select
- button

Before platform setup, v0.17 migrates the legacy mutable Home Assistant device identifier `(DOMAIN, host:slave)` to `(DOMAIN, config_entry_id)` when the legacy device exists for that entry. Entity unique IDs already use the config-entry ID.

The first Modbus refresh is started as a background config-entry task after entities are forwarded. This is intentional: a sleeping or unavailable inverter must not unnecessarily block Home Assistant startup.

## Integration-wide settings API

`async_setup()` registers the admin-only WebSocket settings API from `settings_api.py`:

```text
gw_energypilot/settings/get
gw_energypilot/settings/update
```

The dashboard and the normal Home Assistant config/options flows share the same `ConfigEntry`; there is no second configuration store.

The settings API owns three sections:

- **EP** — controller, telemetry cadence and EV coordination options;
- **EMHASS** — EnergyPilot-owned EMHASS connection/orchestration/output/price options;
- **GOODWE** — host, Modbus port and unit ID.

GoodWe connection settings are validated with a temporary Modbus client before the existing entry is updated. A successful write reloads the entry. The stable config-entry device identifier prevents connection changes from intentionally creating a second Home Assistant device.

See `docs/SETTINGS.md`.

## Modbus layer

`client.py` owns the asynchronous Modbus TCP connection.

Responsibilities:

- connect/reconnect to the configured inverter;
- read contiguous required and optional holding-register blocks;
- decode values using `registers.py`;
- serialize Modbus I/O through an async lock;
- write EMS power and mode registers;
- close the connection on transport/protocol errors;
- reconnect between optional reads when an unsupported optional range closes the socket.

Default connection assumptions are currently:

```text
port:    502
unit id: 247
```

These defaults are configuration values, not a guarantee for every GoodWe device.

## Telemetry coordinator

`GWEnergyPilotCoordinator` is a Home Assistant `DataUpdateCoordinator`.

It polls the inverter at the configured scan interval (default 10 seconds) and exposes a `GWETAData` snapshot to coordinator-backed entities.

A Modbus failure becomes `UpdateFailed`, allowing normal Home Assistant availability/update behaviour rather than crashing setup.

## Register definitions

`registers.py` is the canonical source for:

- register key;
- address;
- data type/width;
- scale;
- precision;
- required and optional read blocks.

`client.py` imports the read blocks; telemetry ranges are not duplicated locally.

v0.16+ includes read-only optional Beta candidates for G20 field validation. Static code/CI coverage does not promote their hardware semantics to confirmed status.

## Entity layer

### Sensors

`sensor.py` exposes:

- PV telemetry;
- inverter-side diagnostics;
- GoodWe load telemetry;
- battery/BMS telemetry;
- smart-meter/grid telemetry;
- cumulative grid import/export energy;
- EMS/controller diagnostic state.

Most raw/diagnostic entities are disabled by default where they are primarily useful for troubleshooting.

v0.17 intentionally exposes these three read-only Beta values as enabled Diagnostic entities for active field correlation:

```text
45356  Beta on-grid discharge depth (%)
45358  Beta off-grid discharge depth (%)
47500  Beta battery SOC protection (raw)
```

The extended `36104/36120` meter counters remain backend/dashboard Beta diagnostics and do not replace the canonical Recorder-facing grid-energy entities.

### Switch

`switch.py` contains the master **Automatic Control** ownership switch.

Important behaviour:

- ON enables controller evaluation;
- OFF writes GoodWe Auto / AI (`mode 1`, `0 W`);
- state is restored after Home Assistant restart;
- restoring control is done in a background task so slow Modbus I/O does not block platform setup.

### Number entities

`number.py` exposes:

- manual EMS power;
- EMHASS minimum battery SOC;
- EMHASS maximum battery SOC.

SOC changes write the complete EMHASS configuration and then trigger one debounced re-optimization after the control settles.

### Select

`select.py` exposes manual GoodWe EMS mode selection. Selecting a mode transfers ownership to manual control before writing the requested mode.

### Buttons

`button.py` exposes actions including:

- Optimize now;
- EMHASS Profit / Cost / Self-consumption;
- maximum export;
- battery pause/hold;
- maximum charge;
- resume automatic control.

The Optimize button also exposes a compact diagnostics snapshot through state attributes, including Beta field-validation values when available.

## Controller ownership model

`controller.py` translates Home Assistant/EMHASS state into GoodWe EMS commands.

Automatic mapping:

```text
P_batt > deadband    -> mode 12 -> battery discharge
P_batt < -deadband  -> mode 11 -> battery charge
inside deadband     -> mode 8  -> battery hold
```

Power is clamped to the configured maximum.

### Safety/readiness gates

Automatic evaluation does not write a new EMS command until:

- Automatic Control is enabled;
- `P_batt` is finite/numeric;
- optimization status matches the configured required state (when configured);
- EV coordination does not require battery hold.

Beta register values do not participate in these gates or control decisions.

### Manual ownership

Manual quick actions intentionally set controller ownership to manual before writing an EMS command. This prevents a later `P_batt` state change from immediately overwriting the user's command.

## EMHASS architecture

GW EnergyPilot does not install EMHASS. EMHASS is an external prerequisite.

The orchestration path is:

```text
live SOC + load history/forecast + optional runtime prices
        |
        v
POST /action/dayahead-optim
        |
        v
validate optimizer result
        |
        v
POST /action/publish-data
        |
        v
validate fresh numeric P_batt
        |
        v
controller may apply target
```

### Active orchestrator inheritance chain

The current runtime does **not** instantiate `orchestrator.py` directly.

```text
orchestrator_v013.GWEnergyPilotOrchestrator
  -> orchestrator_v012.GWEnergyPilotOrchestrator
       -> orchestrator.GWEnergyPilotOrchestrator
```

All three files remain part of current runtime behaviour.

### Load semantics

For the tested GW15K-ETA-G20, register `35172` is the primary Home/load value and basis for the load forecast.

The calculated balance:

```text
PV - grid + battery
```

is retained as a system-balance diagnostic and is not treated as a second household-load sensor.

### EMHASS configuration API

`emhass_config.py` uses:

- `GET /get-config`
- `POST /set-config`

Selected changes are applied to the full currently active configuration so unrelated EMHASS settings are preserved.

Cost-function buttons use this path for `profit`, `cost` and `self-consumption`. They change the optimizer objective, not the GoodWe actuator strategy.

## Event-driven optimization

Optimization can be triggered by:

- configured periodic interval;
- Optimize now;
- Resume AUTO;
- EMHASS cost-function changes;
- publication of tomorrow prices;
- EV charging stopping;
- SOC limit changes after a short debounce.

Home Assistant startup itself deliberately does not force an optimization run.

## EV coordination

If enabled, EV activity can force battery hold.

When charging stops, EnergyPilot can trigger a fresh EMHASS optimization. The controller avoids briefly reusing the stale pre-EV battery target while waiting for the new plan.

## Frontend panel

`__init__.py` registers a Home Assistant sidebar panel and serves files from:

```text
custom_components/gw_energypilot/frontend/
```

The active v0.17 entry module is:

```text
gw-energy-pilot-v017.js
```

It layers:

```text
gw-energy-pilot-v016.js              read-only G20 Beta diagnostics
  -> gw-energy-pilot-v015.js         EMHASS strategy layer
  -> earlier dashboard layers

gw-energy-pilot-settings-v016.js     dedicated EP/EMHASS/GOODWE settings UI
```

The final v0.17 wrapper owns the visible version badge/status. Versioned frontend files may therefore still be active runtime dependencies even when their filename is older.

## Power semantics used by EnergyPilot

For the tested GW15K-ETA-G20:

```text
grid power
  negative = import
  positive = export

battery power
  negative = charging
  positive = discharging
```

Primary confirmed values currently used by the dashboard/control model include:

```text
35301  PV total power
35172  GoodWe load power
35182  battery power
37007  battery SOC
36008  fast grid power
36015  canonical cumulative grid export energy
36017  canonical cumulative grid import energy
47511  EMS mode
47512  EMS power setpoint
```

See `docs/MODBUS.md` and `registers.py` for confirmed versus Beta register details.

## Design principles

1. Local operation first.
2. Home Assistant startup must tolerate sleeping/unavailable external devices.
3. Control ownership must be explicit.
4. Optimizer output must pass readiness checks before controlling the inverter.
5. Register semantics must be evidence-based; Beta means not extensively field-tested.
6. Recorder/history should be used efficiently rather than repeatedly scanning large histories from the dashboard.
7. Entity unique IDs and device identity should remain stable across releases; intentional changes require migration.
8. The existing Home Assistant config entry is the single settings source.
