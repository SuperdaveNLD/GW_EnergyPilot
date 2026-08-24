# GW EnergyPilot architecture

This document describes the current runtime architecture of **GW EnergyPilot v0.28 Beta**.

## High-level flow

```text
GoodWe ETA-G20
    |
    | Modbus TCP
    v
GWModbusClient
    |
    v
GWEnergyPilotCoordinator
    |----------------------> Home Assistant telemetry/entities
    |----------------------> GWEnergyPilotAccounting
    |----------------------> GWEnergyPilotController
    `----------------------> GWEnergyPilotOrchestrator (v026)
                                  |
                                  +--> EMHASS optimize/publish
                                  +--> canonical timestamped price cache
                                  |
                                  v
                            P_batt / P_grid
                                  |
                                  v
                           Automatic Control
```

Persistent EnergyPilot-owned data remains split by purpose:

```text
ConfigEntry data/options                   user/integration configuration
GoodWe registers                           hardware state + inverter settings
EMHASS configuration/output                optimizer configuration + current plan
gw_energypilot.runtime.<entry_id>          last_success runtime evidence
gw_energypilot.accounting.<entry_id>       derived daily grid accounting
gw_energypilot.optimization_log.<entry_id> newest optimization attempts
```

No Home Assistant Store is a second configuration database.

## Runtime objects

`__init__.py` creates per config entry:

- `GWModbusClient`;
- `GWEnergyPilotCoordinator`;
- `GWEnergyPilotController`;
- `GWEnergyPilotOrchestrator` from `orchestrator_v026.py`;
- `GWEnergyPilotAccounting`.

Entity platforms remain sensor, switch, number, select and button.

The initial Modbus refresh runs as a background config-entry task. Accounting may perform optional Recorder bootstrap only after fresh telemetry is available.

## Modbus boundary

`registers.py` is canonical for register definitions and read blocks. `client.py` owns connection/reconnection, serialized Modbus I/O, decoding and writes.

EMS contract:

```text
47511 = mode
47512 = non-negative mode-specific setpoint magnitude
```

Canonical write order remains:

```text
write 47512
brief wait
write 47511
```

Do not reorder or reinterpret without hardware evidence.

Important signs:

```text
GoodWe 36008: negative import / positive export
Battery power:  negative charging / positive discharging
EMHASS P_grid:  positive planned import / negative planned export
```

## Automatic controller

`switch.automatic_control` owns automatic EMS execution.

When OFF, EnergyPilot returns the inverter to mode 1 / 0 W.

### Battery strategy

```text
P_batt < -deadband -> mode 11
P_batt > +deadband -> mode 12
P_batt near 0 W    -> mode 8
```

### Grid strategy

```text
P_grid > +deadband -> mode 9
P_grid < -deadband -> mode 10
P_grid near 0 W    -> mode 1
```

### Hybrid strategy

```text
P_grid > +deadband -> mode 9  using abs(P_grid)
else P_batt > +deadband -> mode 12 using abs(P_batt)
else P_batt near 0 W -> mode 8
otherwise -> mode 1
```

Hybrid intentionally combines two GoodWe control domains:

- **buy/import** is a PCC target and therefore uses mode 9 with the EMHASS `P_grid` import magnitude;
- **sell/discharge** is a battery-power target and therefore uses mode 12 with the EMHASS `P_batt` discharge magnitude;
- a neutral battery plan is held with mode 8;
- a battery-charge plan without planned grid import falls through to mode 1/self-use so locally available PV can be absorbed by GoodWe without forcing the EMHASS forecast-sized charge setpoint.

The mode-9 branch is evaluated before mode 12 so an explicit planned grid import is the authoritative Hybrid buying signal.

Legacy compatibility remains: without explicit `control_strategy`, old `use_goodwe_smart_meter=false/missing` maps to Battery and `true` maps to Grid.

EV anti-discharge is evaluated before normal strategy execution and can hold the battery or allow explicit mode-11 charging.

## EMHASS orchestration and prices

The active orchestrator chain is:

```text
orchestrator_v026.GWEnergyPilotOrchestrator
    -> orchestrator_v013.GWEnergyPilotOrchestrator
        -> orchestrator_v012.GWEnergyPilotOrchestrator
            -> orchestrator.GWEnergyPilotOrchestrator
```

`orchestrator_v026.py` adds dashboard price-series support without changing the optimizer objective. It caches the exact timestamped price maps produced by the existing EnergyPilot price path:

```text
market price
market + buy adder      = effective load_cost
market - sell deduction = effective prod_price
```

`battery_price_api.py` exposes read-only chart data. Dashboard reads do not launch an optimization. The v0.27 chart layer also combines actual battery history, historical published `P_batt` targets, the current future EMHASS forecast and native GoodWe day-energy counters without creating another Modbus control path.

## Battery plan / actual / price frontend

Active top-level module:

```text
gw-energy-pilot-v028.js
    -> gw-energy-pilot-v027-battery-plan.js
        -> v0.27/v0.26 support, chart and language layers
            -> existing historical frontend chain
```

The v0.28 layer owns only the corrected Hybrid 9/12 explanation and final release badge. The v0.27 layer owns Battery plan/actual/price presentation and S/M/L sizing. Earlier layers retain compact Support diagnostics, synchronized minimum-SOC presentation and Dutch/English localization.

This layering remains technical debt: new releases should avoid adding another behavioral monkey-patch layer unless needed for a bounded compatibility fix. A future frontend consolidation should preserve behavior under browser-level regression tests before deleting historical assets.

## Synchronized minimum SOC

The normal on-grid minimum has cross-system ownership because both EMHASS and GoodWe can impose a floor.

The existing EMHASS minimum-SOC NumberEntity is the single operator control. On explicit writes, `number.py` performs:

```text
validate EMHASS min/max relation
require readable current 45356
write GoodWe 45356
verify read-back
write same percentage to EMHASS battery_minimum_state_of_charge
publish verified 45356 into coordinator state
schedule debounced fresh optimization
```

The operation is GoodWe-first because the hardware floor is authoritative in real inverter behavior. If EMHASS fails after a successful GoodWe write, EnergyPilot attempts to roll `45356` back to the previous value.

There is no periodic/startup synchronization. Register `45356` changes only after an explicit minimum-SOC NumberEntity write.

The old direct minimum-SOC dashboard panel is not a normal settings path. The low-level Beta SOC API remains available for controlled diagnostics/tooling. Maximum SOC remains EMHASS-only.

## Persistent grid accounting

`GWEnergyPilotAccounting` consumes one coherent GoodWe lifetime-counter source pair.

Preferred when populated/valid:

```text
36104 export
36120 import
```

Fallback:

```text
36015 export
36017 import
```

The selected pair is persisted. A source change re-baselines before further accumulation so absolute totals from different layouts are never subtracted.

Recorder is not part of the live accounting loop. It remains an optional bootstrap/history source and supplies historical battery-power statistics for the battery graph.

## Optimization history

`optimization_log.py` stores the newest 50 EnergyPilot-owned optimization attempts per config entry. Failed and successful runs share the log. A log persistence failure must never convert a successful optimize/publish cycle into a control failure.

`last_success` remains a separate contract in `runtime_store.py`.

## APIs

Dashboard APIs include:

```text
gw_energypilot/settings/get
gw_energypilot/settings/update
gw_energypilot/smart_meter/get
gw_energypilot/smart_meter/set
gw_energypilot/beta_soc/get
gw_energypilot/beta_soc/set
gw_energypilot/optimization_log/get
gw_energypilot/battery_price/get
```

Configuration-changing APIs are administrator-protected. Read-only presentation APIs do not gain hardware-write authority.

## Stable identity

Home Assistant device identity remains:

```text
(DOMAIN, config_entry_id)
```

Entity unique IDs remain config-entry based. Host/unit-ID changes must not create a second device.

## Main isolation boundaries

```text
register/transport problem -> registers.py / client.py / coordinator.py
controller decision        -> controller.py
EMHASS optimization        -> orchestrator*.py / emhass_config.py
battery/price chart data   -> orchestrator_v026.py / price_series.py / battery_price_api.py
SOC synchronization        -> number.py + existing verified client 45356 helper
daily grid totals          -> accounting.py / accounting_model.py
runtime/log persistence    -> runtime_store.py / optimization_log.py
presentation               -> active frontend chain
```

Do not fix a presentation problem by changing Modbus semantics unless the underlying data is proven wrong.
