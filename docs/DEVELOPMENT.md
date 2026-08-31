# Development guide

This document defines the practical development workflow for GW EnergyPilot.

## Repository is authoritative

Inspect the current repository before changing behavior. Do not reconstruct active behavior from older chats, old release wrappers or filenames alone.

For AI-assisted work, read `AGENTS.md` and `docs/ARCHITECTURE.md` first.

## Current v1.1.0 runtime structure

```text
custom_components/gw_energypilot/
```

Core modules:

```text
__init__.py             config-entry setup, APIs, v1.1.0 panel and v0.44 orchestrator entrypoints
registers.py            canonical GoodWe register definitions/read blocks
client.py               asynchronous Modbus TCP I/O + verified hardware writes
coordinator.py          periodic telemetry snapshot
connectivity_model.py   pure charger reachability debounce/state machine
connectivity.py         coordinator/entity-backed status, five-minute timer and transition logging
controller.py           canonical automatic/manual EMS ownership + Battery/Grid/Hybrid strategy
controller_v033.py      live-first persistent-plan fallback + v0.34 EV anti-discharge strategy override
control_decision.py     pure shared Battery/Grid/Hybrid/EV command mapping
ev_detection.py         exclusive power/status EV activity interpretation + legacy compatibility
control_history.py      persistent latest successful EMS-setpoint update evidence
execution_history.py    bounded plan/decision/write/read-back evidence Store
number.py               manual power, EMHASS SOC numbers, synchronized min-SOC transaction
emhass_config.py        safe full EMHASS config read/write helpers
emhass_sync.py          canonical EnergyPilot runtime contract + safe required-config synchronization
emhass_sync_api.py      admin sync/readback API using canonical sync ownership keys
orchestrator.py         base EMHASS orchestration
orchestrator_v012.py    reliability/startup/price refinements
wall_clock.py           pure wall-clock cadence/plan-step helpers
orchestrator_v013.py    G20 load semantics + persistent last_success/optimization log
orchestrator_v026.py    canonical dashboard price-series cache/read path
orchestrator_v031.py    Battery Saver policy + canonical runtime contract + min-SOC/final-SOC ownership + fresh-output validation
orchestrator_v033.py    persistent official-plan refresh + deterministic plan_revision
orchestrator_v044.py    bounded non-blocking post-restart optimization recovery
plan_runtime.py         validated /api/v1/plan mirror + Store lifecycle/current-value lookup
battery_plan.py         pure plan normalization/timestep/validity helpers
battery_saver.py        five Battery Saver profiles + ten owned EMHASS policy fields
battery_saver_api.py    admin Battery Saver read/apply/rollback API
soc_limits.py           shared verified GoodWe minimum-SOC read/write/publish helper
price_series.py         pure timestamped price-series helpers
battery_price_api.py    read-only battery/price/plan chart WebSocket API
accounting.py           persistent daily grid-accounting runtime
accounting_model.py     pure accounting source/delta/rollover model
accounting_sensor.py    native Today import/export entities
runtime_store.py        persistent last_success evidence
optimization_log.py     bounded optimization-attempt history
optimization_log_api.py read-only optimization history API
ev_load_balancing.py    GoodWe phase-aware EV charger control/feedback + audit Store
settings_api.py         EP/EV/EMHASS/PV/GoodWe settings
smart_meter_api.py      automatic control-strategy API
beta_soc_api.py         bounded verified 45356/45358 low-level field-test API
debug_log_runtime.py    bounded memory-only runtime diagnostic capture
debug_log_api.py        admin debug-session API
event_triggers.py       event-driven optimization hooks
frontend/               layered dashboard/settings assets
tests/                  hardware-independent regressions
```

Connectivity must reuse `coordinator.last_update_success` and the configured scan interval. Do not substitute the transport client's socket flag or add a health-check poll. The charger timer may only change whether the existing EV override is effective; it must not write the saved user option or create another EMS owner.

## Active orchestrator chain

```text
orchestrator_v044.py
    -> orchestrator_v033.py
        -> orchestrator_v031.py
            -> orchestrator_v026.py
                -> orchestrator_v013.py
                    -> orchestrator_v012.py
                        -> orchestrator.py
```

All layers are active runtime code. Check subclasses before changing a base method.

Ownership by active layer:

- v026: read-only dashboard/optimizer price-series caching;
- v012: one reload-safe local wall-clock callback for full optimization and active-plan-step publication, with optimization priority at coincident boundaries and a pre-log Home Assistant `RUNNING` gate;
- v031: Battery Saver EMHASS policy, canonical runtime-contract application, hard-SOC alignment and fresh `P_batt` publication validation;
- v033: refresh the persistent canonical EMHASS plan after a successful optimize/publish cycle and advance `plan_revision` after the refresh attempt.
- v044: schedule the cancellable 60-second post-restart recovery attempt and bounded 15/30/60-second retry back-off without blocking config-entry setup or recording a slow Core startup as a failed optimization.

Do not add release inheritance merely to change a label or constant when an existing bounded module can own the behavior.

## EMHASS required-config ownership

`emhass_sync.py` is the canonical definition for the small EnergyPilot runtime contract used by both explicit **Synchronize required config** and automatic pre-solve preparation:

```text
continual_publish = false
method_ts_round = first
set_use_battery = true
```

The helper `apply_emhass_runtime_contract()` applies only those values to a copy of the complete current EMHASS configuration. `orchestrator_v031.py` must use that helper rather than maintaining a second required-value list. `continual_publish = false` reserves schedule ownership for the v012 wall-clock callback; do not add another periodic publisher.

Installation/model topology is outside this contract:

```text
set_use_pv
inverter_is_hybrid
```

Both are EMHASS/operator-owned. Preserve explicit `false`, explicit `true` and an absent `inverter_is_hybrid` key. Never infer it from the fact that the physical reference GoodWe inverter is hybrid; EMHASS can intentionally model external/AC-coupled or otherwise different topology.

`emhass_sync_api.py` derives its displayed managed values from `SYNCED_CONFIG_KEYS`. Do not recreate a separate ownership tuple in the API/frontend path.

See `docs/EMHASS_CONFIG_SYNC.md`.

## Active controller layer

`__init__.py` imports `GWEnergyPilotController` from `controller_v033.py`. That class inherits the canonical `controller.py` implementation.

The inherited base still owns normal Battery/Grid/Hybrid execution. The v033 subclass owns two bounded behaviors:

1. live-first fallback to a still-valid persistent EMHASS plan while configured Home Assistant plan entities are temporarily absent;
2. the v0.34 EV anti-discharge override that blocks discharge but preserves an explicit home-battery charge request using the configured strategy.

Do not move either behavior into a second controller or duplicate the EMS write path.

The pure mapping in `control_decision.py` is the one source for translating a
finite plan plus strategy/two deadbands/maximum/EV state into an expected mode and
setpoint. Live control and read-only future projections call it. It must remain
side-effect-free and must not infer missing `P_grid`, future EV state or
ownership. `execution_history.py` records the live controller context and
post-refresh read-back but can never own or retry a command.

## Active frontend chain

Top level:

```text
gw-energy-pilot-v110.js
    -> gw-energy-pilot-v101.js
         -> gw-energy-pilot-v051.js
         -> gw-energy-pilot-v051-history.js
         -> gw-energy-pilot-v050.js
              -> gw-energy-pilot-v049.js
                   -> gw-energy-pilot-v048.js
                        -> gw-energy-pilot-v047.js
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
```

v1.1.0 uses the final presentation-only stable wrapper and advances one
complete `1.1.0-stable1` active-graph cache boundary. The bounded
v1.0.1-beta.4 wrapper remains in the chain so all beta-4 behavior stays present.
The nested v0.51 feature layer owns
one canonical EMHASS-to-GoodWe card and targeted history refresh. The nested
plan data/view owners implement Recorder attribution,
wanted-SOC history and verified runtime-session-bounded EV underlays. v0.50 retains
its release presentation and EV settings ownership; v0.49 retains its release
presentation; v0.48 retains current Hybrid operator copy and stable-note
ownership; v0.47 retains Custom Battery Saver editing, larger
strategy/settings typography and field-tuned profile presentation; v0.46
retains external-PV presentation, v0.44 owns the bounded Optimize
listener/floating action, v0.43 touch-hover presentation, v0.42 the EMHASS
settings overview, and v0.41 ordinary telemetry patching, targeted plan
refresh, PV presentation and static-flow DOM/CSS. The v0.41 PV flow keeps one
combined group total while patching one internal ETA/DC node and one aggregated
external AC/PCC node; it remains independent of control and EMHASS inputs.

The existing settings module owns the two-deadband configuration panel and its
zero-centered explanatory scale. Control behavior remains owned by the backend
config and controller modules; the stable wrapper does not reinterpret it.
The v0.41 stable-DOM EMHASS metric displays the backend controller's canonical
expected mode/setpoint attributes; it must not grow a parallel Hybrid/EV
decision implementation.

**Do not add another behavioral release monkey-patch layer by default.** A compatibility wrapper must stay narrowly scoped and have executable browser-level regression coverage on every required profile.

## Automatic-control contract

Battery strategy:

```text
P_batt < -Battery Hold deadband -> mode 11
P_batt > +Battery Hold deadband -> mode 12
P_batt inside Battery Hold deadband -> mode 8
```

Grid strategy:

```text
P_grid > +GoodWe Auto deadband -> mode 9
P_grid < -GoodWe Auto deadband -> mode 10
P_grid inside GoodWe Auto deadband -> mode 1
```

Hybrid strategy:

```text
abs(P_batt) <= Battery Hold deadband -> mode 8
else abs(P_grid) <= GoodWe Auto deadband -> mode 1 GoodWe Auto / self-use
else P_grid > +GoodWe Auto deadband -> mode 9 using abs(P_grid)
else P_grid < -GoodWe Auto deadband -> mode 10 using abs(P_grid)
```

The Hybrid neutral-battery branch is evaluated first so ordinary forecast house import/export does not become an active PCC target while EMHASS asked the battery to remain idle. Every non-neutral plan is PCC-controlled: mode 1 owns `P_grid` inside the separate GoodWe Auto deadband, while modes 9/10 own import/export targets outside it. Both variable boundaries are inclusive and classify the branch only; never subtract either threshold from the transmitted setpoint.

### EV anti-discharge override

While the configured EV source is actively charging, `P_batt` remains the directional safety guard:

```text
P_batt >= -Battery Hold deadband -> mode 8 Battery Hold
P_batt < -Battery Hold deadband  -> charging remains allowed
```

For an explicit home-battery charge request:

```text
Battery -> mode 11 using abs(P_batt)
Grid    -> mode 9 when P_grid > GoodWe Auto deadband, otherwise mode 11 fallback
Hybrid  -> mode 9 when P_grid > GoodWe Auto deadband, otherwise mode 11 fallback
```

`ev_detection.py` is the single interpretation owner. Explicit power mode
listens only to finite, unit-normalized measured power; explicit status mode
listens only to `on`, `true`, `charging` or `connected_charging`. Never infer
charging from allocated/maximum current. Missing method keys retain the exact
legacy `connected_charging`-or-power behavior until the entry is saved.

This anti-discharge override must not control the EV charger or create a second
fast feedback loop. The separately owned `ev_load_balancing.py` runtime may call
only the selected charger NumberEntity after its full minute-scale condition
window; it never calls this controller or GoodWe. EV-stop fresh-plan protection
keeps Battery Hold and retries a transient optimization failure after 5, 15, 30
and 60 seconds; charging restart cancels the retry. Manual commands never
inherit or reinterpret the automatic strategy.

## Persistent plan availability contract

For configured `P_batt` / `P_grid` values, `controller_v033.py` uses:

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
4. advance one orchestrator `plan_revision` after that refresh attempt, even if mirroring itself fails after a valid solve;
5. preserve a still-valid mirror if a refresh fails;
6. do not replace a longer canonical official snapshot with an ever-shrinking continual-publish Home Assistant remainder;
7. never extrapolate past `valid_until`.

`plan_revision` is freshness evidence for presentation. It is not a second plan version or optimizer state.

See `docs/EMHASS_PLAN_RUNTIME.md`.

## Fresh EMHASS output validation

Do not use only `State.last_updated` as proof that EMHASS published a new plan value. Home Assistant can receive an identical state/attribute report without advancing `last_updated`.

Current contract:

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
chargegasm   -> Chargegasm
balanced     -> Balanced
battery_saver-> Battery Saver
```

Battery Saver is opt-in for unmanaged installations. Do not silently adopt/overwrite existing custom EMHASS policy values on upgrade.

The complete profile ranges are:

```text
Mad-Steve      5–100%  comfort 10–95%
Gold Rush      5–100%  comfort 10–95%
Chargegasm     8–96%   comfort 13–91%
Balanced      10–93%   comfort 15–88%
Battery Saver 10–85%   comfort 20–80%
```

The low/high SOC cost factors are 2/5, 2/12, 2/18, 5/25 and 10/50
percent × dynamic price reference in profile order. The profile minimum is a
verified GoodWe `45356` plus EMHASS transaction; the maximum remains
EMHASS-only. Existing v1.0 managed entries require explicit reselection before
the new minimum is written, so installing the beta alone never mutates the
hardware floor.

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

Mad-Steve deliberately retains the established aggressive anti-churn floor:

```text
weight_battery_charge    = 2.25% × dynamic price reference
weight_battery_discharge = 2.25% × dynamic price reference
```

Gold Rush and Chargegasm use the field-tuned transaction factor:

```text
weight_battery_charge    = 6% × dynamic price reference
weight_battery_discharge = 6% × dynamic price reference
```

Balanced raises anti-churn to 7% and Battery Saver to 9%. Power-stress factors
are 0% / 0% / 2% / 6% / 20% in mode order. Keep these distinctions explicit
in payload metadata, tests and customer documentation. Battery efficiency
remains installation-owned and must not be silently rewritten by a managed
profile.

Battery Saver owns ten EMHASS fields:

```text
battery_minimum_state_of_charge
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

When extending this list, update apply, rollback, unmanaged/custom detection, diagnostics, tests and `docs/BATTERY_SAVER.md` together.

The Custom editor intentionally exposes only the five economic cost fields
already presented in the customer UI. Dashboard and Settings use the same
administrator-only `battery_saver/custom_set` WebSocket transaction. Keep its
validation finite and non-negative, retain EMHASS scalar/list shapes, preserve
the complete unrelated EMHASS configuration and include the write plus first
optimization in the rollback boundary. The existing SOC NumberEntities remain
the only slider path and must reject writes while a managed profile is active.

Battery Saver currently supports one EMHASS battery model. Do not broadcast a scalar/list profile over multi-battery configurations without an explicit per-battery ownership design.

## Hybrid inverter power interpretation

Before diagnosing “why not 15 kW”, inspect all relevant constraints and the active EMHASS topology.

When `inverter_is_hybrid = true` in EMHASS, PV and battery share the modeled inverter path. The following can independently bind:

```text
battery charge/discharge max
hybrid inverter AC input/output max
SOC/terminal-energy availability
optimizer price opportunity across neighboring timesteps
battery_stress_cost
```

A plan with `P_batt = 14.5 kW` can already have `P_hybrid_inverter = 15 kW` when PV contributes the remaining DC power. Do not compensate for that by increasing battery limits or changing GoodWe registers.

If the operator configured `inverter_is_hybrid = false`, do not apply the hybrid-topology interpretation and do not “repair” the setting automatically.

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

SOC visualization:

```text
actual: registry-resolved GoodWe battery_soc (%)
        -> separate Recorder 5-minute means

wanted history: execution Store SOC_opt snapshot at decision time

current/future: official schema-1.x SOC_opt fraction 0..1
                -> plan_runtime validates and normalizes to value_pct
                -> battery_soc_plan payload
```

Do not reuse the power-schedule fallback for SOC. EnergyPilot has no configured EMHASS SOC-output entity, and multi-battery plans have no meaningful bare/fleet `SOC_opt`.

Historical active plan still uses configured `P_batt` Home Assistant history so the displayed past reflects the target that was actually published then.

Detailed actual-flow attribution uses the same Recorder request for combined
PV, load and fast-grid means. It is a load-first estimate with an explicit
unknown residual, not a new accounting source. Optional official `P_PV` and
`P_Load` mirror points are dashboard-only and must never enter the controller.

The execution table uses exact Store events for the last 48 elapsed hours. Its
24-hour future rows run exact plan timestamps through `control_decision.py` and
must remain visibly conditional: do not predict EV/manual ownership, write
success or read-back. UTC is the persistence/range identity; the frontend uses
the Home Assistant timezone and includes an abbreviation in the full table.

Price line:

```text
existing EnergyPilot runtime price-source path
-> orchestrator_v026 cache
-> battery_price/get WebSocket API
-> frontend visualization
```

The chart API uses schema `6` and includes `plan_revision` plus bounded
`execution` history/projection. The frontend should force-refresh the one
canonical plan card and one canonical execution card when live evidence differs
from the cached payload. It also includes backend-derived Home Assistant-timezone
windows for rolling 12h, fixed-today 24h and fixed-today-through-tomorrow-noon
36h views. The frontend filters one shared cached dataset when the range changes.
`P_batt.last_updated` remains the compatibility fallback for changes outside
EnergyPilot. Do not solve range/refresh bugs by adding Recorder calls per click
or allowing duplicate cards.

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
10. For releases require Quality + HACS + hassfest on the exact tagged head and
    follow `docs/RELEASE_WORKFLOW.md`.

## Repository checks

```text
python -m compileall -q custom_components/gw_energypilot scripts tests
python -m unittest discover -s tests -v
python scripts/validate_repo.py
```

Quality runs these automatically.

The validator covers the single integration/domain structure,
register/read-block structure, JSON validity, HACS release-only selection,
frontend import existence, active frontend/manifest version agreement and
changelog/release-note version coverage. `scripts/release_contract.py`
separately validates future v1 tag, channel, branch and release-note metadata.

Static CI does not prove GoodWe hardware semantics or browser rendering.

## Isolation rule for debugging

```text
GoodWe register/transport -> registers.py / client.py / coordinator.py
Automatic EMS decision    -> controller.py + controller_v033.py availability/EV override
SOC config synchronization-> number.py / emhass_config.py / verified client helper
EMHASS config ownership   -> emhass_sync.py / emhass_sync_api.py / emhass_config.py
EMHASS optimization       -> orchestrator*.py / event_triggers.py
Persistent plan           -> plan_runtime.py / battery_plan.py
Battery Saver policy      -> battery_saver.py / battery_saver_api.py / orchestrator_v031.py
Battery/price chart       -> orchestrator_v026.py / price_series.py / battery_price_api.py
Daily grid totals         -> accounting.py / accounting_model.py / accounting_sensor.py
Runtime/log persistence   -> runtime_store.py / optimization_log.py
Presentation              -> active frontend chain
```

Do not fix a presentation issue by changing Modbus semantics unless the data itself is proven wrong. Do not solve an entity lifecycle gap by duplicating control or optimizer ownership. Do not infer EMHASS topology from GoodWe hardware.

## Current technical debt priorities

1. **Frontend layering** — consolidate versioned monkey-patch layers into functional components under browser-level regression tests.
2. **Orchestrator inheritance** — eventually replace release-version inheritance with composable policy/forecast/price/runner services under existing tests.
3. **Home Assistant lifecycle tests** — add config-entry/WebSocket/Recorder fixtures for integration-level startup/reload coverage, especially persistent-plan recovery.
4. **Control policy extraction** — separate pure Battery/Grid/Hybrid decision logic from Home Assistant state reading and Modbus execution when the next control refactor is scheduled.

Do not perform these refactors opportunistically inside unrelated feature/bug releases.

## Release checklist

Before merge verify:

- target branch (`beta` for `1.x.x-beta.N`, `main` for `1.x.x`);
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

Publishing is tag-only. Use `v1.x.x-beta.N` for a prerelease from the exact
remote `beta` head and `v1.x.x` for stable from the exact remote `main` head.
Never reuse or move a published tag. The workflow marks beta as prerelease and
not Latest; stable is a normal/latest release. See `docs/RELEASE_WORKFLOW.md`.
