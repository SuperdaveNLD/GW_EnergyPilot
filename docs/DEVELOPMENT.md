# Development guide

This document defines the practical development workflow for GW EnergyPilot.

## Repository is authoritative

Inspect the current repository before changing behavior. Do not reconstruct active behavior from older chats, old release wrappers or filenames alone.

For AI-assisted work, read `AGENTS.md` and `docs/ARCHITECTURE.md` first.

## Current v0.33 runtime structure

```text
custom_components/gw_energypilot/
```

Core modules:

```text
__init__.py             config-entry setup, APIs, runtime wiring, v0.33 panel entrypoint
registers.py            canonical GoodWe register definitions/read blocks
client.py               asynchronous Modbus TCP I/O + verified hardware writes
coordinator.py          periodic telemetry snapshot
controller.py           canonical automatic/manual EMS ownership + Battery/Grid/Hybrid strategy
controller_v033.py      live-first persistent-plan fallback; no new mode mapping
number.py               manual power, EMHASS SOC numbers, synchronized min-SOC transaction
emhass_config.py        safe full EMHASS config read/write helpers
orchestrator.py         base EMHASS orchestration
orchestrator_v012.py    reliability/startup/price refinements
orchestrator_v013.py    G20 load semantics + persistent last_success/optimization log
orchestrator_v026.py    canonical dashboard price-series cache/read path
orchestrator_v031.py    Battery Saver policy + min-SOC/final-SOC ownership + fresh-output validation
orchestrator_v033.py    persistent official-plan refresh after successful optimization
plan_runtime.py         validated /api/v1/plan mirror + Store lifecycle/current-value lookup
battery_plan.py         pure plan normalization/timestep/validity helpers
battery_saver.py        four Battery Saver profiles + owned EMHASS policy fields
battery_saver_api.py    admin Battery Saver read/apply/rollback API
price_series.py         pure timestamped price-series helpers
battery_price_api.py    read-only battery/price/plan chart WebSocket API
accounting.py           persistent daily grid-accounting runtime
accounting_model.py     pure accounting source/delta/rollover model
accounting_sensor.py    native Today import/export entities
runtime_store.py        persistent last_success evidence
optimization_log.py     bounded optimization-attempt history
optimization_log_api.py read-only optimization history API
settings_api.py         EP/EMHASS/GoodWe connection settings
smart_meter_api.py      automatic control-strategy API
beta_soc_api.py         bounded verified 45356/45358 low-level field-test API
debug_log_runtime.py    bounded memory-only runtime diagnostic capture
debug_log_api.py        admin debug-session API
event_triggers.py       event-driven optimization hooks
frontend/               layered dashboard/settings assets
tests/                  hardware-independent regressions
```

## Active orchestrator chain

```text
orchestrator_v033.py
    -> orchestrator_v031.py
        -> orchestrator_v026.py
            -> orchestrator_v013.py
                -> orchestrator_v012.py
                    -> orchestrator.py
```

All layers are active runtime code. Check subclasses before changing a base method.

Ownership by active layer:

- v026: read-only dashboard/optimizer price-series caching;
- v031: Battery Saver EMHASS policy, hard-SOC alignment and fresh `P_batt` publication validation;
- v033: refresh the persistent canonical EMHASS plan after a successful optimize/publish cycle.

Do not add release inheritance merely to change a label or constant when an existing bounded module can own the behavior.

## Active frontend chain

Top level:

```text
gw-energy-pilot-v033.js
    -> gw-energy-pilot-v031-battery-saver.js
        -> gw-energy-pilot-v031-window-controls.js
            -> gw-energy-pilot-v031.js
                -> gw-energy-pilot-v030.js
                    -> historical active layers
```

The v0.33 wrapper owns the current release badge/footer only. Battery Saver rendering remains in the v031 Battery Saver module and reads current backend profile metadata. The Battery · Plan · Price core contains the bounded live-plan refresh fix.

**Do not add another behavioral release monkey-patch layer by default.** The layered frontend is technical debt and has caused regressions. New presentation work should prefer functional components or deliberate consolidation under browser-level regression coverage.

## Automatic-control contract

Battery strategy:

```text
P_batt < -deadband -> mode 11
P_batt > +deadband -> mode 12
P_batt near 0 W    -> mode 8
```

Grid strategy:

```text
P_grid > +deadband -> mode 9
P_grid < -deadband -> mode 10
P_grid near 0 W    -> mode 1
```

Hybrid strategy:

```text
P_grid > +deadband -> mode 9  (buy/import; setpoint abs(P_grid))
else P_batt > +deadband -> mode 12 (sell/discharge; setpoint abs(P_batt))
else P_batt near 0 W -> mode 8
otherwise -> mode 1 GoodWe Auto / self-use
```

The Hybrid import branch intentionally uses `P_grid` because mode 9 owns the PCC import target. The Hybrid sell branch intentionally uses `P_batt` because mode 12 owns direct battery discharge. A charging plan without planned grid import falls through to mode 1 so GoodWe can absorb available local PV instead of forcing a forecast-sized battery charge.

EV anti-discharge is a higher-priority directional override. Manual commands never inherit or reinterpret the automatic strategy.

## v0.33 plan availability contract

`controller_v033.py` does not change the decision policy. It changes only where the current plan value may be read when a Home Assistant publication is temporarily absent.

Source order:

```text
finite live configured Home Assistant P_batt/P_grid
-> still-valid current point from plan_runtime.py
-> unavailable / existing wait behavior
```

Optimizer status rules:

- explicit live ready/non-ready status remains authoritative;
- missing/unknown/unavailable status may be bridged only by a still-valid mirrored plan;
- a plan outside its inferred validity window is not usable.

Never weaken this into “last known value” behavior. The final plan command must not be repeated indefinitely after the horizon expires.

## Persistent EMHASS plan contract

EMHASS is the canonical plan owner. EnergyPilot reads the official read-only endpoint:

```text
GET /api/v1/plan
```

`plan_runtime.py` normalizes `P_batt` and `P_grid`, infers the timestep and stores an explicit final validity boundary in:

```text
gw_energypilot.plan.<config_entry_id>
```

The Store is a resilience mirror, not configuration and not a second optimizer.

Rules:

1. restore the last validated mirror during config-entry setup;
2. retry the official endpoint in a bounded startup background task;
3. refresh after every successful EnergyPilot optimize/publish cycle;
4. preserve a still-valid mirror if a refresh fails;
5. do not replace a longer canonical official snapshot with an ever-shrinking continual-publish Home Assistant remainder;
6. never extrapolate past `valid_until`.

See `docs/EMHASS_PLAN_RUNTIME.md`.

## Fresh EMHASS output validation

Do not use only `State.last_updated` as proof that EMHASS published a new plan value. Home Assistant can receive an identical state/attribute report without advancing `last_updated`.

The v0.33 contract is:

```text
State.last_reported primary
State.last_updated compatibility fallback
+ finite numeric P_batt
+ optimizer ready
```

Capture the report timestamp before starting an EnergyPilot optimization and require a later report during the output wait.

## Battery Saver contract

The public profile keys/names remain:

```text
mad_steve    -> Mad-Steve
gold_rush    -> Gold Rush
balanced     -> Balanced
battery_saver-> Battery Saver
```

Battery Saver is opt-in for unmanaged installations. Do not silently adopt/overwrite existing custom EMHASS policy values on upgrade.

### Linear anti-churn versus quadratic power stress

These mechanisms solve different problems and must remain separate in reasoning/tests:

```text
weight_battery_charge / weight_battery_discharge
    -> linear virtual cost per battery-throughput kWh
    -> determines whether small-value cycling is worth doing

battery_stress_cost
    -> current EMHASS quadratic/PWL power cost
    -> determines how expensive high instantaneous power is
```

v0.33 applies a shared anti-churn floor to all four managed modes:

```text
weight_battery_charge    = 1.5% × dynamic price reference
weight_battery_discharge = 1.5% × dynamic price reference
```

Gold Rush soft thresholds are 5–96% in v0.33. This is not a hard 96% maximum. Hard Minimum/Maximum SOC stays separately configured and authoritative.

Battery Saver now owns eight EMHASS fields:

```text
battery_soc_deficit_threshold
battery_soc_deficit_cost
battery_soc_surplus_threshold
battery_soc_surplus_cost
battery_stress_cost
battery_stress_segments
weight_battery_charge
weight_battery_discharge
```

When extending this list, update apply, rollback, unmanaged/custom detection, diagnostics, tests and `docs/BATTERY_SAVER.md` together.

Battery Saver currently supports one EMHASS battery model. Do not broadcast a scalar/list profile over multi-battery configurations without an explicit per-battery ownership design.

## Hybrid inverter power interpretation

Before diagnosing “why not 15 kW”, inspect all relevant constraints.

For current EMHASS hybrid modeling, PV and battery share the inverter path. The following can independently bind:

```text
battery charge/discharge max
hybrid inverter AC input/output max
SOC/terminal-energy availability
optimizer price opportunity across neighboring timesteps
battery_stress_cost
```

A plan with `P_batt = 14.5 kW` can already have `P_hybrid_inverter = 15 kW` when PV contributes the remaining DC power. Do not compensate for that by increasing battery limits or changing GoodWe registers.

## EMS / Modbus safety

`registers.py` is canonical. Never guess addresses, widths, scaling or sign.

EMS contract:

```text
47511 = mode
47512 = non-negative mode-specific setpoint magnitude
```

Write order:

```text
write 47512
brief wait
write 47511
```

Do not reorder without explicit hardware validation.

## Synchronized minimum SOC contract

The existing EMHASS minimum-SOC NumberEntity is the supported normal on-grid operator control.

An explicit write must follow this order:

```text
validate EMHASS peer maximum
require readable current GoodWe 45356
write GoodWe 45356 through the canonical verified client helper
verify read-back
write the same percentage to EMHASS battery_minimum_state_of_charge
update coordinator with verified hardware state
schedule existing debounced fresh optimization
```

If `45356` is unavailable, do not change EMHASS. If the later EMHASS write fails, attempt to restore the previous `45356` value.

The orchestrator may synchronize the already verified GoodWe minimum into an EnergyPilot-owned solve and clamps runtime `soc_final` to the effective hard range. Do not invent a second soft reserve in the controller.

## Battery plan / actual / price ownership

Actual bars:

```text
existing battery_power entity
-> Home Assistant Recorder 5-minute mean statistics
-> frontend visualization
```

Future plan:

```text
official EMHASS /api/v1/plan
-> validated plan_runtime Store mirror
-> battery_price/get payload
-> frontend

compatibility fallback only:
current Home Assistant battery_scheduled_power / forecasts attributes
```

Historical active plan still uses configured `P_batt` Home Assistant history so the displayed past reflects the target that was actually published then.

Price line:

```text
existing EnergyPilot runtime price-source path
-> orchestrator_v026 cache
-> battery_price/get WebSocket API
-> frontend visualization
```

The frontend chart cache must be bypassed when a newer active-plan entity timestamp proves that the plan changed. Keep one canonical card and replace/rebuild it; do not solve refresh bugs by allowing duplicates.

Do not discover Nord Pool independently in the browser. Chart energy summaries are visualization only; persistent cost/revenue accounting must consume backend accounting deltas and effective prices.

## Persistent accounting

Daily grid accounting selects one coherent lifetime pair:

```text
preferred populated extended: 36104 export / 36120 import
fallback legacy:             36015 export / 36017 import
```

Source changes re-baseline before accumulation. Never subtract absolute totals from different layouts. Recorder is not part of the live grid-accounting loop.

## Development workflow

For each bug/feature:

1. Inspect the current active runtime chain.
2. Identify ownership: hardware, controller, optimizer, persistence or presentation.
3. Reproduce expected versus actual behavior from diagnostics/logs/field evidence.
4. Apply the smallest robust change inside the correct ownership boundary.
5. Add hardware-independent regression coverage.
6. Check startup/reload/unavailable/stale-data behavior.
7. Check entity/device/storage compatibility.
8. Update user and maintainer documentation for externally visible behavior.
9. Run repository checks.
10. For releases require Quality + HACS + hassfest on the exact final head.

## Repository checks

```text
python -m compileall -q custom_components/gw_energypilot scripts tests
python -m unittest discover -s tests -v
python scripts/validate_repo.py
```

Quality runs these automatically.

The validator covers register/read-block structure, JSON validity, frontend import existence, active frontend/manifest version agreement and changelog/release-note version coverage.

Static CI does not prove GoodWe hardware semantics or browser rendering.

## Isolation rule for debugging

```text
GoodWe register/transport -> registers.py / client.py / coordinator.py
Automatic EMS decision    -> controller.py + controller_v033.py availability fallback
SOC config synchronization-> number.py / emhass_config.py / verified client helper
EMHASS optimization       -> orchestrator*.py / emhass_config.py / event_triggers.py
Persistent plan           -> plan_runtime.py / battery_plan.py
Battery Saver policy      -> battery_saver.py / battery_saver_api.py / orchestrator_v031.py
Battery/price chart       -> orchestrator_v026.py / price_series.py / battery_price_api.py
Daily grid totals         -> accounting.py / accounting_model.py / accounting_sensor.py
Runtime/log persistence   -> runtime_store.py / optimization_log.py
Presentation              -> active frontend chain
```

Do not fix a presentation issue by changing Modbus semantics unless the data itself is proven wrong. Do not solve an entity lifecycle gap by duplicating control or optimizer ownership.

## Current technical debt priorities

1. **Frontend layering** — consolidate versioned monkey-patch layers into functional components under browser-level regression tests.
2. **Orchestrator inheritance** — eventually replace release-version inheritance with composable policy/forecast/price/runner services under existing tests.
3. **Home Assistant lifecycle tests** — add config-entry/WebSocket/Recorder fixtures for integration-level startup/reload coverage, especially persistent-plan recovery.
4. **Control policy extraction** — separate pure Battery/Grid/Hybrid decision logic from Home Assistant state reading and Modbus execution when the next control refactor is scheduled.

Do not perform these refactors opportunistically inside unrelated feature/bug releases.

## Release checklist

Before merge verify:

- manifest version;
- active frontend module/cache-buster and frontend `VERSION`;
- changelog version entry;
- release-notes version/status row;
- README current version/behavior;
- architecture/development docs when runtime structure changes;
- translations/copy for user-facing changes;
- Quality, HACS and hassfest on exact final head;
- no accidental unique-ID/device-identifier/storage-key changes;
- no undocumented register/control semantic changes;
- Beta features are bounded and reversible where practical.
