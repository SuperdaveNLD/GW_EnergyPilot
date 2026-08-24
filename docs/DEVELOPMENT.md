# Development guide

This document defines the practical development workflow for GW EnergyPilot.

## Repository is authoritative

Inspect the current repository before changing behavior. Do not reconstruct active behavior from older chats, old release wrappers or filenames alone.

For AI-assisted work, read `AGENTS.md` and `docs/ARCHITECTURE.md` first.

## Current v0.28 runtime structure

```text
custom_components/gw_energypilot/
```

Core modules:

```text
__init__.py             config-entry setup, APIs, runtime wiring, panel entrypoint
registers.py            canonical GoodWe register definitions/read blocks
client.py               asynchronous Modbus TCP I/O + verified hardware writes
coordinator.py          periodic telemetry snapshot
controller.py           automatic/manual EMS ownership + Battery/Grid/Hybrid strategy
number.py               manual power, EMHASS SOC numbers, synchronized min-SOC transaction
emhass_config.py        safe full EMHASS config read/write helpers
orchestrator.py         base EMHASS orchestration
orchestrator_v012.py    reliability/startup/price refinements
orchestrator_v013.py    G20 load semantics + persistent last_success/optimization log
orchestrator_v026.py    canonical dashboard price-series cache/read path
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
event_triggers.py       event-driven optimization hooks
frontend/               layered dashboard/settings assets
tests/                  hardware-independent regressions
```

## Active orchestrator chain

```text
orchestrator_v026.py
    -> orchestrator_v013.py
        -> orchestrator_v012.py
            -> orchestrator.py
```

All four layers are active runtime code. Check subclasses before changing a base method.

`orchestrator_v026.py` adds read-only dashboard price-series caching; it must not silently change optimization objectives or turn dashboard reads into optimization triggers.

## Active frontend chain

Top level:

```text
gw-energy-pilot-v028.js
    -> gw-energy-pilot-v027-battery-plan.js
        -> v0.27/v0.26 support, chart and language layers
            -> historical active layers
```

Current ownership:

- `v028` — corrected Hybrid 9/12 strategy explanation + final v0.28 badge;
- `v027-battery-plan` — S/M/L Battery plan/actual/price view and plan overlays;
- v0.26 layers — compact Support, synchronized minimum-SOC presentation, price chart and Dutch/English localization;
- older assets remain active dependencies.

**Do not add another release monkey-patch layer by default.** The layered frontend is technical debt and has caused small regressions. v0.28 uses one bounded wrapper because the controller strategy wording changes while the complete v0.27 presentation must remain intact. New presentation work should prefer functional components or deliberate consolidation under browser-level regression coverage.

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

The mode-9 import branch precedes mode 12. Legacy strategy fallback remains false/missing smart-meter flag -> Battery, true -> Grid.

EV anti-discharge is a higher-priority directional override. Manual commands never inherit or reinterpret the automatic strategy.

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

No startup/background synchronization is allowed without a separate design decision. The old direct minimum-SOC dashboard panel is not a normal settings path; the bounded low-level Beta SOC API remains available for controlled diagnostics/tooling. Maximum SOC remains EMHASS-only.

## Battery plan / actual / price ownership

Actual bars:

```text
existing battery_power entity
-> Home Assistant Recorder 5-minute mean statistics
-> frontend visualization
```

Historical/future plan:

```text
configured P_batt history + current EMHASS forecasts attribute
-> read-only chart payload
-> frontend visualization
```

Price line:

```text
existing EnergyPilot runtime price-source path
-> orchestrator_v026 cache
-> battery_price/get WebSocket API
-> frontend visualization
```

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
Automatic EMS decision    -> controller.py
SOC config synchronization-> number.py / emhass_config.py / verified client helper
EMHASS optimization       -> orchestrator*.py / emhass_config.py / event_triggers.py
Battery/price chart backend -> orchestrator_v026.py / price_series.py / battery_price_api.py
Daily grid totals         -> accounting.py / accounting_model.py / accounting_sensor.py
Runtime/log persistence   -> runtime_store.py / optimization_log.py
Presentation              -> active frontend chain
```

Do not fix a presentation issue by changing Modbus semantics unless the data itself is proven wrong.

## Current technical debt priorities

1. **Frontend layering** — consolidate versioned monkey-patch layers into functional components under browser-level regression tests.
2. **Orchestrator inheritance** — eventually replace release-version inheritance with composable forecast/price/runner services under existing tests.
3. **Home Assistant lifecycle tests** — add config-entry/WebSocket/Recorder fixtures for integration-level coverage.
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
- translations for user-facing changes;
- Quality, HACS and hassfest on exact final head;
- no accidental unique-ID/device-identifier/storage-key changes;
- no undocumented register/control semantic changes;
- Beta features are bounded and reversible where practical.
