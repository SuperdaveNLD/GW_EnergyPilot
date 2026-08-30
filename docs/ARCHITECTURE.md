# GW EnergyPilot architecture

This document describes the current runtime architecture of **GW EnergyPilot v0.47 Beta**.

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
    |----------------------> GWEnergyPilotConnectivity
    |----------------------> GWEnergyPilotController (controller_v033)
    `----------------------> GWEnergyPilotOrchestrator (orchestrator_v044)
                                  |
                                  +--> EnergyPilot Battery Saver policy
                                  +--> EMHASS optimize/publish
                                  +--> wall-clock active-plan-step publish
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

Read-only PV insight is a separate presentation path:

```text
coordinator pv_total_power + up to four configured HA power entities
    -> pv_generation_power sensor
    -> dashboard PV total/source breakdown/live-flow value
```

That aggregate does not feed the controller, orchestrator, EMHASS or accounting. External entity changes update the aggregate independently; internal GoodWe PV continues to follow coordinator updates. See `docs/PV_INSIGHT.md`.

EV charger load balancing is a separate actuator domain:

```text
selected HA one-phase current sensor
    -> GWEnergyPilotEVLoadBalancer
    -> number.set_value on one configured three-phase charger control
```

It has no reference to `GWModbusClient`, EMS registers or Automatic Control. It
uses a continuous soft condition window and fails without a write when source or
charger state is invalid. See `docs/EV_LOAD_BALANCING.md`.

Persistent EnergyPilot-owned data is split by purpose:

```text
ConfigEntry data/options                   user/integration configuration
GoodWe registers                           hardware state + inverter settings
EMHASS configuration/output                optimizer configuration + canonical plan
gw_energypilot.runtime.<entry_id>          last_success runtime evidence
gw_energypilot.control.<entry_id>          latest successful EMS setpoint update
gw_energypilot.accounting.<entry_id>       derived daily grid accounting
gw_energypilot.optimization_log.<entry_id> newest optimization attempts
gw_energypilot.plan.<entry_id>             bounded mirror of latest valid EMHASS plan
gw_energypilot.ev_load_balancing_audit.<entry_id> append-only >16 A acknowledgements
```

No Home Assistant Store is a second configuration database or optimizer.

## Runtime objects

`__init__.py` creates per config entry:

- `GWModbusClient`;
- `GWEnergyPilotCoordinator`;
- `GWEnergyPilotControlHistory`;
- `GWEnergyPilotController` from `controller_v033.py`;
- `GWEnergyPilotOrchestrator` from `orchestrator_v044.py`;
- `GWEnergyPilotPlanRuntime`;
- `GWEnergyPilotAccounting`;
- `GWEnergyPilotConnectivity`;
- `GWEnergyPilotDebugRuntime`.
- `GWEnergyPilotEVLoadBalancer`.

Entity platforms remain sensor, switch, number, select and button.

During setup, the last valid plan mirror is restored before the normal control/orchestration lifecycle starts. A bounded background task then retries the official EMHASS plan endpoint while startup dependencies settle. The initial Modbus refresh also remains a background config-entry task.

### Connectivity runtime

`connectivity.py` derives one canonical status from the existing coordinator poll result and an optional Home Assistant charger-online entity. It never opens a second Modbus connection or starts another polling loop: GoodWe reachability therefore updates on the configured coordinator interval. A configured charger source also updates on its normal Home Assistant state-change signal.

Missing, `unknown` and `unavailable` sources are unreachable. A binary sensor is explicit (`on` online, `off` unreachable); any usable state from another domain means that integration is reporting, so an idle `switch.* = off` remains reachable.

When EV coordination was requested by the user, five continuous minutes of charger unreachability suspend its effective runtime guard. Five continuous minutes online resume it. Either transition timer resets on a flap. The configured `enable_ev_coordination` option is never rewritten, and a user disable during recovery cancels automatic resume. The existing controller remains the only EMS decision and write owner.

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
P_batt near 0 W -> mode 8
else P_grid near 0 W -> mode 1
else P_grid > +deadband -> mode 9 using abs(P_grid)
else P_grid < -deadband -> mode 10 using abs(P_grid)
```

Hybrid first preserves an explicit neutral battery plan through mode 8. Every non-neutral plan is PCC-controlled: mode 1 lets GoodWe close the actual local balance around a zero grid target, while modes 9/10 own non-zero planned import/export. The configured deadband is evaluated independently against `P_batt` and `P_grid` in that order; exact boundaries remain neutral and the threshold is never subtracted from the final mode-9/10 setpoint.

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

The optional charger-online guard is evaluated before this override. While that guard is suspended, the controller follows its normal configured Automatic Control strategy and does not infer EV activity from stale charger mode/power entities.

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

EnergyPilot accepts the supported versioned EMHASS schema, normalizes timestamped `P_batt` and `P_grid` points plus optional single-battery `SOC_opt`, infers the plan timestep and calculates:

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
optional SOC_opt horizon normalized from fraction to percent
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

- base/v012/v013: optimization, fixed wall-clock scheduling, active-plan-step publication and runtime-evidence behavior;
- v026: canonical timestamped price-series support for dashboard/optimizer use;
- v031: Battery Saver policy ownership, canonical EMHASS runtime-contract application, GoodWe minimum-SOC synchronization before owned solves and runtime final-SOC clamping;
- v033: refresh the persistent canonical plan after a successful optimize/publish cycle and increment `plan_revision` in a `finally` block after the refresh attempt.
- v044: schedule one non-blocking first post-restart optimization after 60 seconds, retry transient dependency failures after 15/30/60 seconds, and skip the sequence after any newer successful optimization.

The EnergyPilot-required runtime contract is defined once in `emhass_sync.py` and reused by both explicit **Synchronize required config** and automatic pre-solve preparation:

```text
continual_publish = false
method_ts_round = first
set_use_battery = true
```

EnergyPilot is the single scheduling owner. The configured full optimization
cadence is 15, 30 or 60 minutes (15 recommended) and is anchored to local clock
boundaries at second 15. The same clock callback publishes the active row when
the inferred persisted-plan timestep is due. A due full optimization runs first
and its initial publish suppresses a duplicate timestep publish. The complete
solve/publish/fresh-output/control transaction is serialized. Controller
plan-source listeners are deferred until fresh `P_batt` and, for Grid/Hybrid,
fresh `P_grid` are proven; EV anti-discharge remains higher priority.

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

When a profile is explicitly managed, its EMHASS hard maximum SOC is part of the profile transaction. Every current profile can reach the complete 100% range:

```text
Mad-Steve     100%
Gold Rush     100%
Balanced      100%
Battery Saver 100%
```

The verified GoodWe-synchronized minimum SOC remains a separate hard lower boundary.

All profiles use `battery_soc_surplus_threshold = 0.95`. Above that shared soft red-zone boundary, EMHASS charges a virtual cost for every kWh and every hour spent there. The price-relative surplus factors are 5% / 10% / 25% / 50% for Mad-Steve / Gold Rush / Balanced / Battery Saver, so 100% remains available for high-value opportunities without becoming the default dwell state.

v0.34 distinguishes two economic mechanisms:

1. **battery throughput / anti-churn cost** — linear EMHASS `weight_battery_charge` and `weight_battery_discharge` costs;
2. **battery power stress** — EMHASS `battery_stress_cost`, which current EMHASS models as a quadratic/PWL cost versus instantaneous battery power.

Mad-Steve deliberately retains the established aggressive anti-churn floor:

```text
weight_battery_charge    = 2.25% × dynamic price reference
weight_battery_discharge = 2.25% × dynamic price reference
```

Gold Rush, Balanced and Battery Saver apply a 6% floor per direction. The captured Gold Rush comparison showed this removes the low-value 765 W, 857 W and 426 W reversals while retaining full 15 kW dispatch. Gold Rush additionally uses a lower 1% battery power-stress factor; Balanced and Battery Saver retain 8% and 20% respectively. Battery efficiency and inverter topology remain installation-owned.

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

The administrator-only Custom editor in the dashboard and EMHASS settings shares one `gw_energypilot/battery_saver/custom_set` transaction. It accepts the five visible non-negative economic cost values, preserves scalar versus one-item-list EMHASS shapes, writes the complete merged EMHASS configuration, runs one optimization and rolls back the previous Battery Saver-owned configuration on failure. The existing Minimum/Maximum SOC number entities retain their separate ownership and optimization behavior.

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

`battery_price_api.py` exposes read-only chart data. The payload uses schema `5`, includes `plan_revision`, and uses future-plan source order:

```text
1. persistent validated official EMHASS plan mirror
2. existing Home Assistant battery_scheduled_power / forecasts compatibility path
```

Actual bars remain Recorder history from the existing GoodWe battery-power entity. Actual SOC is read separately as Recorder 5-minute means from the registry-resolved GoodWe `battery_soc` percentage entity. Forecast SOC uses only exact, validated `SOC_opt` from the official plan mirror; no output-entity fallback or multi-battery aggregate is guessed. Native GoodWe day counters remain the headline charged/discharged energy values.

The frontend keeps one canonical Battery · Plan · Price card. A mismatch between the live orchestrator `plan_revision` and the cached API payload forces an immediate refresh; `P_batt.last_updated` remains a compatibility fallback for plan changes outside EnergyPilot. The card is replaced/rebuilt rather than duplicated.

The header reachability pill is also canonical stable DOM. It is created only during structural render, placed between Automatic Control ownership and the version badge, and patched from the connectivity sensor. Hover on fine pointers and focus/tap on touch expose Modbus, charger and effective EV-coordination details.

## Frontend

Active top-level module:

```text
gw-energy-pilot-v047.js
  -> gw-energy-pilot-v046.js
       -> gw-energy-pilot-v045.js
            -> gw-energy-pilot-v044.js
                 -> gw-energy-pilot-v043.js
                      -> gw-energy-pilot-v042.js
                           -> gw-energy-pilot-v041-emhass-settings.js
                                -> gw-energy-pilot-v041.js
                                     -> gw-energy-pilot-v039.js
                                          -> gw-energy-pilot-v038.js
                                               -> gw-energy-pilot-v038-runtime.js
                                                    -> gw-energy-pilot-v034.js
                                                         -> existing v0.34 feature chain
```

The v0.38 base deliberately bypasses the historical v0.35/v0.36.x/v0.37 stability wrappers in a fresh browser session. Their files remain for release history, but the v0.35 pointer/render lock and v0.36.3 old-button-node reuse are no longer active owners. v0.41 replaces normal telemetry renders with stable-DOM patches; v0.42-v0.44 add bounded settings, touch-presentation and Optimize behavior; v0.45-v0.47 add only release presentation and cache boundaries.

The active frontend keeps `gw-energy-pilot-v038-model.js` as the pure localization/profile/physical-flow model owner. `gw-energy-pilot-v041.js` applies direction, state and relative intensity to stable connector nodes with fixed arrows plus explicit idle/unavailable markers and localized accessible labels. `gw-energy-pilot-v038-strategy.js` still owns key-based delegated Battery Strategy actions and active state; historical particle CSS remains present for compatibility but is hidden by the active no-motion policy.

Visible/translated text is never a control identity. Canonical profile keys plus `aria-pressed` define action and selected state. Live-flow direction is single-owner through the explicit physical mapping instead of accumulated reversal rules; current presentation is static and patched in place. See `docs/FRONTEND_CONTROL_REBUILD.md` and `docs/FRONTEND_STABLE_DOM.md`.

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

`control_history.py` persists the latest successfully completed EMS setpoint update separately. The controller advances it only after `async_set_mode()` completes; skipped matching commands and failed commands retain the previous timestamp. It is diagnostic evidence of a completed write transaction, while coordinator mode/setpoint telemetry remains the hardware read-back source.

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
EV charger current         -> ev_load_balancing.py only
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
