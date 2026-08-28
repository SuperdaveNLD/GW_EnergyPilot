# GW EnergyPilot architecture

This document describes the current runtime architecture of **GW EnergyPilot v0.44 Beta**.

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
    |----------------------> GWEnergyPilotController (controller_v033)
    `----------------------> GWEnergyPilotOrchestrator (orchestrator_v044)
                                  |
                                  +--> EnergyPilot Battery Saver policy
                                  +--> EMHASS optimize/publish
                                  +--> canonical timestamped price cache
                                  +--> refresh official EMHASS /api/v1/plan
                                  +--> advance plan_revision
                                  |
                                  v
                          GWEnergyPilotPlanRuntime
                                  |
                         Home Assistant Store mirror
                                  |
                    live-first P_batt / P_grid fallback
                                  |
                                  v
                           Automatic Control
```

EMHASS remains an external prerequisite and remains the canonical owner of the optimization plan. The EnergyPilot plan Store is only a resilience mirror.

Persistent EnergyPilot-owned data is split by purpose:

```text
ConfigEntry data/options                   user/integration configuration
GoodWe registers                           hardware state + inverter settings
EMHASS configuration/output                optimizer configuration + canonical plan
gw_energypilot.runtime.<entry_id>          last_success runtime evidence
gw_energypilot.accounting.<entry_id>       derived daily grid accounting
gw_energypilot.optimization_log.<entry_id> newest optimization attempts
gw_energypilot.plan.<entry_id>             bounded mirror of latest valid EMHASS plan
```

No Home Assistant Store is a second configuration database or optimizer.

## Runtime objects

`__init__.py` creates per config entry:

- `GWModbusClient`;
- `GWEnergyPilotCoordinator`;
- `GWEnergyPilotController` from `controller_v033.py`;
- `GWEnergyPilotOrchestrator` from `orchestrator_v044.py`;
- `GWEnergyPilotPlanRuntime`;
- `GWEnergyPilotAccounting`;
- `GWEnergyPilotDebugRuntime`.

Entity platforms remain sensor, switch, number, select and button.

During setup, the last valid plan mirror is restored before the normal control/orchestration lifecycle starts. A bounded background task then retries the official EMHASS plan endpoint while startup dependencies settle. The initial Modbus refresh also remains a background config-entry task.

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

- **buy/import** is a PCC target and uses mode 9 with the EMHASS `P_grid` import magnitude;
- **sell/discharge** is a battery-power target and uses mode 12 with the EMHASS `P_batt` discharge magnitude;
- a neutral battery plan is held with mode 8;
- a battery-charge plan without planned grid import normally falls through to mode 1/self-use so locally available PV can be absorbed by GoodWe without forcing the EMHASS forecast-sized charge setpoint.

Legacy compatibility remains: without explicit `control_strategy`, old `use_goodwe_smart_meter=false/missing` maps to Battery and `true` maps to Grid.

### EV anti-discharge override

The EV feature is a higher-priority directional safety guard, not an EV charger controller.

During an active EV charging session:

```text
P_batt >= -deadband -> mode 8 Battery Hold
P_batt < -deadband  -> explicit home-battery charge remains allowed
```

Charge execution follows the selected strategy as far as safely possible:

```text
Battery -> mode 11 using abs(P_batt)
Grid    -> mode 9 when P_grid > deadband, otherwise mode 11 fallback
Hybrid  -> mode 9 when P_grid > deadband, otherwise mode 11 fallback
```

The v0.34 override is implemented in `controller_v033.py` so the existing canonical controller and EMS write path remain single-owner. EV-stop stale-plan protection remains unchanged.

## Plan-resilient controller layer

`controller_v033.py` also provides source availability resilience for configured `P_batt` / `P_grid` values:

```text
1. finite live Home Assistant entity state
2. current value from GWEnergyPilotPlanRuntime when the live state is unavailable
3. no value / existing waiting-unavailable behavior
```

Optimizer readiness remains conservative:

- a present live optimizer state that is explicitly non-ready remains authoritative;
- only a missing/unknown/unavailable optimizer publication may be bridged by a still-valid mirrored plan;
- an expired or out-of-range plan never overrides readiness.

This prevents a Home Assistant publication lifecycle gap from discarding a valid EMHASS plan while also preventing stale control from continuing indefinitely.

## Canonical EMHASS plan mirror

`plan_runtime.py` owns the resilience mirror introduced in v0.33.

Canonical refresh source:

```text
GET <EMHASS base URL>/api/v1/plan
```

EnergyPilot accepts the supported versioned EMHASS schema, normalizes timestamped `P_batt` and `P_grid` points, infers the plan timestep and calculates:

```text
valid_until = final P_batt timestamp + inferred timestep
```

The mirror stores:

```text
source
generated_at
emhass_schema_version
step_seconds
valid_until
configured P_batt/P_grid entity IDs
P_batt horizon
P_grid horizon
```

The Store key is:

```text
gw_energypilot.plan.<config_entry_id>
```

If the official endpoint is temporarily unavailable, the existing Home Assistant schedule attributes may be accepted as a compatibility fallback. An official plan can replace the mirror. An ever-shrinking continual-publish Home Assistant remainder does not replace a longer valid canonical snapshot merely because it was republished later.

A refresh failure never deletes a still-valid cached plan. Once `valid_until` is passed, current plan values become unavailable; EnergyPilot does not repeat the last command.

See `docs/EMHASS_PLAN_RUNTIME.md` for the detailed lifecycle and validation contract.

## EMHASS orchestration, runtime contract and output freshness

The active orchestrator chain is:

```text
orchestrator_v044.GWEnergyPilotOrchestrator
    -> orchestrator_v033.GWEnergyPilotOrchestrator
        -> orchestrator_v031.GWEnergyPilotOrchestrator
            -> orchestrator_v026.GWEnergyPilotOrchestrator
                -> orchestrator_v013.GWEnergyPilotOrchestrator
                    -> orchestrator_v012.GWEnergyPilotOrchestrator
                        -> orchestrator.GWEnergyPilotOrchestrator
```

Responsibilities are layered deliberately:

- base/v012/v013: existing optimization, publication and runtime-evidence behavior;
- v026: canonical timestamped price-series support for dashboard/optimizer use;
- v031: Battery Saver policy ownership, canonical EMHASS runtime-contract application, GoodWe minimum-SOC synchronization before owned solves and runtime final-SOC clamping;
- v033: refresh the persistent canonical plan after a successful optimize/publish cycle and increment `plan_revision` in a `finally` block after the refresh attempt.
- v044: schedule one non-blocking first post-restart optimization after 60 seconds, retry transient dependency failures after 15/30/60 seconds, and skip the sequence after any newer successful optimization.

The EnergyPilot-required runtime contract is defined once in `emhass_sync.py` and reused by both explicit **Synchronize required config** and automatic pre-solve preparation:

```text
continual_publish = true
method_ts_round = first
set_use_battery = true
```

This contract deliberately does **not** contain installation/model topology. The following remain EMHASS/operator-owned and are preserved exactly:

```text
set_use_pv
inverter_is_hybrid
```

`inverter_is_hybrid` must not be inferred from the physical GoodWe hardware type. EMHASS uses it to choose optimizer topology/constraints, and the operator can intentionally model an installation differently, including external or AC-coupled generation. v0.35 therefore preserves explicit `false`, explicit `true` and an absent key through both configuration-write paths.

The Settings → EMHASS synchronization API derives its managed-value list from the same `SYNCED_CONFIG_KEYS` definition, so UI ownership cannot drift away from the backend contract.

`plan_revision` is deterministic freshness evidence for UI consumers. It does not replace EMHASS plan content or become a second optimizer version.

Fresh-output validation in v031 uses Home Assistant `State.last_reported` as proof of a new `P_batt` report. `last_updated` remains a compatibility fallback for older State-like test doubles. A repeated numeric `P_batt` is therefore valid when EMHASS actually reported it again. The existing finite-number and optimizer-ready gates remain mandatory.

See `docs/EMHASS_CONFIG_SYNC.md` for the synchronization ownership contract.

## Battery Saver policy

`battery_saver.py` owns the four public modes:

```text
Mad-Steve
Gold Rush
Balanced
Battery Saver
```

When a profile is explicitly managed, its EMHASS hard maximum SOC is part of the profile transaction:

```text
Mad-Steve     100%
Gold Rush      96%
Balanced       95%
Battery Saver  90%
```

The verified GoodWe-synchronized minimum SOC remains a separate hard lower boundary.

v0.34 distinguishes two economic mechanisms:

1. **battery throughput / anti-churn cost** — linear EMHASS `weight_battery_charge` and `weight_battery_discharge` costs;
2. **battery power stress** — EMHASS `battery_stress_cost`, which current EMHASS models as a quadratic/PWL cost versus instantaneous battery power.

All four EnergyPilot profiles apply the same anti-churn floor:

```text
weight_battery_charge    = 2.25% × dynamic price reference
weight_battery_discharge = 2.25% × dynamic price reference
```

At the field-test price reference around `0.31`, this is approximately `0.007` currency/kWh per direction. Profile differentiation remains through hard maximum SOC and the profile-specific deficit/surplus/power-stress policy.

Battery Saver owns exactly nine EMHASS fields after the user explicitly selects a managed mode:

```text
battery_maximum_state_of_charge
battery_soc_deficit_threshold
battery_soc_deficit_cost
battery_soc_surplus_threshold
battery_soc_surplus_cost
battery_stress_cost
battery_stress_segments
weight_battery_charge
weight_battery_discharge
```

Existing unmanaged/custom values are preserved. Multi-battery Battery Saver ownership is rejected instead of broadcasting scalar policy values across heterogeneous batteries. Failed first-apply optimization transactions restore the previous option and all owned EMHASS fields.

See `docs/BATTERY_SAVER.md`.

## Hybrid inverter power interpretation

`P_batt < 15 kW` does not automatically mean available power was ignored.

When the **EMHASS configuration itself** has `inverter_is_hybrid = true`, current EMHASS hybrid modeling puts PV and battery on the same DC/AC path. Therefore:

```text
PV + battery discharge -> shared hybrid inverter AC output limit
```

During evening discharge, the inverter can already be at 15 kW AC while battery discharge is only about 14–14.8 kW because PV supplies the remaining DC power. When neither physical limit binds, EMHASS may also reserve energy for later higher-price timesteps or reduce instantaneous power because of `battery_stress_cost`.

This interpretation applies only when the operator has selected the hybrid EMHASS topology. EnergyPilot no longer forces that topology in v0.35.

Diagnostics and plan reviews must compare the active EMHASS topology, `P_batt`, `P_PV`, `P_hybrid_inverter`, SOC and neighboring prices before concluding that a power limit is wrong.

## Prices and Battery · Plan · Price chart

`orchestrator_v026.py` caches the exact timestamped price maps produced by the EnergyPilot price path:

```text
market price
market + buy adder      = effective load_cost
market - sell deduction = effective prod_price
```

`battery_price_api.py` exposes read-only chart data. The payload remains schema `4`, includes `plan_revision`, and uses future-plan source order:

```text
1. persistent validated official EMHASS plan mirror
2. existing Home Assistant battery_scheduled_power / forecasts compatibility path
```

Actual bars remain Recorder history from the existing GoodWe battery-power entity. Native GoodWe day counters remain the headline charged/discharged energy values.

The frontend keeps one canonical Battery · Plan · Price card. A mismatch between the live orchestrator `plan_revision` and the cached API payload forces an immediate refresh; `P_batt.last_updated` remains a compatibility fallback for plan changes outside EnergyPilot. The card is replaced/rebuilt rather than duplicated.

## Frontend

Active top-level module:

```text
gw-energy-pilot-v038.js
    -> gw-energy-pilot-v038-runtime.js
        -> gw-energy-pilot-v034.js
            -> existing v0.34 feature chain
```

v0.38 deliberately bypasses the historical v0.35/v0.36.x/v0.37 stability wrappers in a fresh browser session. Their files remain for release history, but the v0.35 pointer/render lock and v0.36.3 old-button-node reuse are no longer active owners.

The v0.38 frontend is split by responsibility: `gw-energy-pilot-v038-model.js` owns pure localization/profile/physical-flow models, `gw-energy-pilot-v038-strategy.js` owns key-based delegated Battery Strategy actions and active state, `gw-energy-pilot-v038-styles.js` owns final control/particle presentation, and `gw-energy-pilot-v038-runtime.js` owns relevant-state rendering, interaction completion, scroll stability and applying physical flow motion to the live DOM.

Visible/translated text is never a control identity. Canonical profile keys plus `aria-pressed` define action and selected state. Live-flow direction is likewise single-owner through explicit physical motion instead of accumulated animation reversals. See `docs/FRONTEND_CONTROL_REBUILD.md`.

Historical frontend layering remains technical debt below the v0.34 base. Further consolidation must preserve behavior under executable browser/model regression tests before historical assets are removed.

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

The orchestrator also reasserts the currently verified GoodWe minimum into EnergyPilot-owned EMHASS optimizations and clamps runtime `soc_final` to the effective hard EMHASS range.

The low-level Beta SOC API remains available for controlled diagnostics/tooling. When Battery Saver manages a profile, maximum SOC remains EMHASS-owned but is included in the EnergyPilot profile transaction.

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

## Optimization history and debug runtime

`optimization_log.py` stores the newest 50 EnergyPilot-owned optimization attempts per config entry. Failed and successful runs share the log. A log persistence failure must never convert a successful optimize/publish cycle into a control failure.

`last_success` remains a separate contract in `runtime_store.py`.

`GWEnergyPilotDebugRuntime` is deliberately different: it is bounded, memory-only, disabled by default and observes the existing runtime. It does not add Modbus polling, EMHASS optimization or hardware writes.

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
gw_energypilot/debug_log/get
gw_energypilot/debug_log/set_enabled
gw_energypilot/debug_log/clear
gw_energypilot/battery_price/get
gw_energypilot/battery_saver/get
gw_energypilot/battery_saver/set
gw_energypilot/emhass_sync/...
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
controller decision        -> controller.py + bounded controller_v033 availability/EV layer
EMHASS config ownership    -> emhass_sync.py / emhass_sync_api.py / emhass_config.py
EMHASS optimization        -> orchestrator*.py
persistent plan resilience -> plan_runtime.py / battery_plan.py
Battery Saver policy       -> battery_saver.py / battery_saver_api.py / orchestrator_v031.py
battery/price chart data   -> orchestrator_v026.py / price_series.py / battery_price_api.py
SOC synchronization        -> number.py + existing verified client 45356 helper
daily grid totals          -> accounting.py / accounting_model.py
runtime/log persistence    -> runtime_store.py / optimization_log.py
presentation               -> active frontend chain
```

Do not fix a presentation problem by changing Modbus semantics unless the underlying data is proven wrong. Do not fix a temporary Home Assistant publication gap by creating duplicate optimizer or hardware-control ownership. Do not infer EMHASS inverter topology from the physical GoodWe model; preserve the operator's EMHASS topology unless a future explicit configuration control is introduced.
