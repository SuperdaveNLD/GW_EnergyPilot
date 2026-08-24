# Development guide

This document defines the practical development workflow for GW EnergyPilot.

## Repository is authoritative

Inspect the current repository before changing behavior. Do not reconstruct active behavior from older chats, old release wrappers or filenames alone.

For AI-assisted work, read `AGENTS.md` and `docs/ARCHITECTURE.md` first.

## Current v0.26 runtime structure

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
battery_price_api.py    read-only Battery & Price WebSocket API
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
gw-energy-pilot-v026-complete.js
    -> gw-energy-pilot-v026-battery-price.js
        -> gw-energy-pilot-v026.js
            -> gw-energy-pilot-v025.js
                -> historical active layers
```

Current ownership:

- `v026-complete` — final v0.26 badge + synchronized minimum-SOC presentation;
- `v026-battery-price` — Battery & Price graph, Recorder/price cache and visibility integration;
- `v026` — Home Assistant language-aware Dutch/English localization;
- `v025` — optimization LOG and prior dashboard behavior;
- older assets remain active dependencies.

**Do not add another release monkey-patch layer by default.** The layered frontend is technical debt and has caused small regressions. New presentation work should prefer functional components or deliberate consolidation under browser-level regression coverage.

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
P_batt charge request -> mode 11
else P_grid export request -> mode 10
otherwise -> mode 1
```

Legacy strategy fallback remains false/missing smart-meter flag -> Battery, true -> Grid.

EV anti-discharge is a higher-priority directional override.

Manual commands never inherit or reinterpret the automatic strategy.

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

No startup/background synchronization is allowed without a separate design decision.

Register `45358` remains an independent off-grid manual Beta field test. Maximum SOC remains EMHASS-only.

## Battery & Price ownership

Battery bars:

```text
existing battery_power entity
-> Home Assistant Recorder 5-minute mean statistics
-> frontend visualization
```

Price line:

```text
existing EnergyPilot runtime price-source path
-> orchestrator_v026 cache
-> battery_price/get WebSocket API
-> frontend visualization
```

Do not discover Nord Pool independently in the browser.

Approximate chart energy summaries are visualization only. Persistent cost/revenue accounting must consume backend accounting deltas and effective prices.

## Persistent accounting

Daily grid accounting selects one coherent lifetime pair:

```text
preferred populated extended: 36104 export / 36120 import
fallback legacy:             36015 export / 36017 import
```

Source changes re-baseline before accumulation. Never subtract absolute totals from different layouts.

Recorder is not part of the live grid-accounting loop.

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
Price chart backend       -> orchestrator_v026.py / price_series.py / battery_price_api.py
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
