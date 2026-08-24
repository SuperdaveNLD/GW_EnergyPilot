# GW EnergyPilot architecture

This document describes the current runtime architecture of **GW EnergyPilot v0.25 Beta**.

## High-level data flow

```text
GoodWe ETA-G20
    |
    | Modbus TCP
    v
GWModbusClient
    |
    v
GWEnergyPilotCoordinator
    |---------------------> Home Assistant telemetry/entities
    |---------------------> GWEnergyPilotAccounting
    |---------------------> GWEnergyPilotController
    `---------------------> EMHASS orchestrator
                                  |
                                  | publish
                                  v
                         P_batt / P_grid / status
                                  |
                                  v
                         Automatic Control
```

Persistent EnergyPilot-owned data is deliberately separated by purpose:

```text
ConfigEntry data/options                   user/integration configuration
GoodWe registers                           hardware state + inverter settings
EMHASS configuration/output                optimizer configuration + current plan
gw_energypilot.runtime.<entry_id>          small runtime evidence / last_success
gw_energypilot.accounting.<entry_id>       derived daily grid accounting
gw_energypilot.optimization_log.<entry_id> newest 50 optimization attempts
```

None of the Home Assistant Stores is a second configuration database.

## Runtime objects

`custom_components/gw_energypilot/__init__.py` creates one runtime set per config entry:

- `GWModbusClient`;
- `GWEnergyPilotCoordinator`;
- `GWEnergyPilotController`;
- `GWEnergyPilotOrchestrator`;
- `GWEnergyPilotAccounting`.

Entity platforms are sensor, switch, number, select and button.

The first Modbus refresh is a background config-entry task so an unavailable/sleeping inverter does not block Home Assistant startup. After that fresh poll, accounting may perform its optional one-time Recorder bootstrap.

## Device identity

The Home Assistant device identifier is stable:

```text
(DOMAIN, config_entry_id)
```

Connection changes must not create a second EnergyPilot device. Entity unique IDs remain config-entry based.

## APIs

Administrator dashboard APIs include:

```text
gw_energypilot/settings/get
gw_energypilot/settings/update
gw_energypilot/smart_meter/get
gw_energypilot/smart_meter/set
gw_energypilot/beta_soc/get
gw_energypilot/beta_soc/set
gw_energypilot/optimization_log/get
```

The historical `smart_meter` API name is retained for compatibility, but v0.25 uses it to expose/store the three-value automatic `control_strategy`.

## Modbus layer

`client.py` owns connection/reconnection, serialized I/O, typed decoding and EMS writes. `registers.py` is canonical for register definitions and read blocks.

EMS contract:

```text
47511 = mode
47512 = non-negative mode-specific setpoint magnitude
```

Write ordering remains:

```text
write 47512
wait briefly
write 47511
```

Do not reorder or reinterpret this path without hardware evidence.

## Sign conventions

```text
GoodWe meter 36008
  negative = import
  positive = export

Battery power
  negative = charging
  positive = discharging

EMHASS P_grid
  positive = planned import
  negative = planned export
```

The GoodWe and EMHASS grid signs are intentionally opposite.

## Automatic controller ownership

`switch.automatic_control` is the master automatic EMS ownership switch.

When OFF:

```text
mode 1 · GoodWe Auto / AI
setpoint 0 W
```

When ON, one normal strategy owns the actuator unless a documented safety override such as EV anti-discharge protection is active.

### Battery control

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt near 0 W    -> mode 8 Battery Hold
```

This is the backwards-compatible mapping when no explicit `control_strategy` exists and the old `use_goodwe_smart_meter` value is missing/false.

### Grid control

```text
P_grid > +deadband -> mode 9 Grid import target
P_grid < -deadband -> mode 10 Grid export target
P_grid near 0 W    -> mode 1 GoodWe Auto / self-use
```

Modes 9/10 close the fast loop inside GoodWe against its own smart meter/PCC. No parallel EnergyPilot mode-11 trim loop should be reintroduced without an explicit redesign.

### Hybrid control

```text
if P_batt < -deadband:
    mode 11 Battery charge target = abs(P_batt)
elif P_grid < -deadband:
    mode 10 Grid export target = abs(P_grid)
else:
    mode 1 GoodWe Auto / self-use
```

Hybrid gives a direct battery-power target to planned charging and a PCC target to planned export. It intentionally does not translate normal discharge directly into mode 12; GoodWe mode 1 handles self-use when there is no explicit charge or export action.

The legacy boolean remains synchronized for compatibility. Without an explicit new strategy: false/missing -> Battery, true -> Grid.

## EV anti-discharge override

EV charging ownership remains external. EnergyPilot only constrains home-battery direction while an EV is active:

```text
P_batt > +deadband -> mode 8 Battery Hold
P_batt near 0 W    -> mode 8 Battery Hold
P_batt < -deadband -> mode 11 Battery charge allowed
```

This override is evaluated before Battery/Grid/Hybrid execution. When native orchestration is enabled and EV charging stops, EnergyPilot waits for a fresh optimization before normal automatic control resumes.

## EMHASS orchestration

The active orchestrator chain remains:

```text
orchestrator_v013.GWEnergyPilotOrchestrator
    -> orchestrator_v012.GWEnergyPilotOrchestrator
        -> orchestrator.GWEnergyPilotOrchestrator
```

Native orchestration performs:

```text
current SOC + load forecast + optional runtime prices
    -> /action/dayahead-optim
    -> validate success
    -> /action/publish-data
    -> validate fresh outputs/status
    -> controller executes selected strategy
```

`emhass_config.py` preserves unrelated EMHASS configuration by reading the complete config before selected-field updates.

## Persistent optimization history

`optimization_log.py` stores the newest 50 EnergyPilot-owned optimization attempts per config entry. Successful and failed manual/scheduled/event-triggered runs share one history.

Recorded context includes:

```text
start/end + duration
reason + success
soc_init / soc_final
current load
price source / area / points
load forecast points
P_batt on success
optimize/publish HTTP statuses
error text
```

A log write failure is diagnostic-only and must never make an otherwise successful optimize/publish cycle fail.

The admin-only `optimization_log/get` API feeds the read-only Settings LOG page. `last_success` remains a separate runtime contract: failed runs can appear in history without erasing the latest successful timestamp.

## Persistent grid accounting

`GWEnergyPilotAccounting` owns derived daily grid accounting. It consumes one coherent lifetime-counter pair from the normal coordinator.

Available source layouts are already defined in `registers.py`:

```text
extended: 36104 export / 36120 import
legacy:   36015 export / 36017 import
```

Selection rules:

1. prefer the extended pair when both values are valid and the pair is populated;
2. a readable but empty `0/0` extended pair does not override usable legacy values;
3. use legacy when extended is unavailable;
4. once extended is active, one transient missing optional read does not cause source flapping.

The selected source pair is persisted. Any source change establishes a new baseline before accumulating further deltas, so absolute totals from different layouts are never subtracted from one another. Same-day Today/Yesterday values are preserved through a source migration.

For a first switch to extended counters, EnergyPilot deliberately does not fabricate the part of the current day that occurred before the new baseline.

The established physical lifetime Home Assistant entities remain unchanged. Source selection affects the **derived daily accounting input**, not their unique IDs or state classes.

Recorder is not part of the live accounting loop. It is only an optional legacy-boundary bootstrap/history source. The 24-hour power graph remains Recorder-backed visualization.

See `docs/ACCOUNTING.md`.

## Load semantics

On the reference GW15K-ETA-G20, register `35172` is the primary GoodWe load value and normally matches the sum of the three phase-load values.

```text
PV - grid + battery
```

remains a system power-balance diagnostic, not a replacement house-load entity.

## Frontend

The active entrypoint is selected in `__init__.py`:

```text
gw-energy-pilot-v025.js
  -> gw-energy-pilot-v024.js   three-strategy / Hybrid UI
      -> earlier layered dashboard chain
```

The versioned files are active dependencies, not automatically dead historical assets. Trace the import chain before deleting or consolidating them.

## Design principles

1. Local operation first.
2. Startup tolerates unavailable inverter/EMHASS services.
3. Automatic/manual/safety ownership is explicit.
4. Optimizer readiness and finite outputs gate control.
5. GoodWe register/mode semantics are evidence-based.
6. Do not run competing feedback loops over the same EMS actuator.
7. Preserve stable device identity and entity unique IDs.
8. Keep user configuration separate from persistent runtime/accounting history.
9. Re-baseline whenever accounting source semantics change.
10. Diagnostic logging must never become a control failure source.
