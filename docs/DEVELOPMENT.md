# Development guide

This document defines the practical development workflow for GW EnergyPilot.

## Repository is authoritative

Inspect the current repository before changing code. Do not reconstruct current behavior from older chats or releases.

For AI-assisted work, read `AGENTS.md` first.

## Current release structure

The integration lives in:

```text
custom_components/gw_energypilot/
```

Important modules:

```text
__init__.py          config-entry setup, device migration, APIs, accounting and panel
client.py            asynchronous GoodWe Modbus TCP I/O
registers.py         canonical register definitions and read blocks
coordinator.py       periodic telemetry polling
controller.py        automatic/manual EMS ownership and actuator strategy
orchestrator.py      base EMHASS orchestration
orchestrator_v012.py reliability/startup/price refinements
orchestrator_v013.py current G20 orchestration + runtime-store persistence
runtime_store.py     persistent EnergyPilot runtime evidence (last_success)
accounting.py        persistent grid-accounting runtime + Recorder bootstrap
accounting_model.py  pure daily-counter state/delta/rollover model
accounting_sensor.py native Today import/export entities
emhass_config.py     complete EMHASS config read/write helpers
settings_api.py      EP/EMHASS/GoodWe connection settings
smart_meter_api.py   GoodWe smart-meter actuator strategy
beta_soc_api.py      verified manual 45356/45358 field-test writes
event_triggers.py    event-driven optimization hooks
sensor.py            telemetry/diagnostics + accounting sensor registration
switch.py            Automatic Control ownership
number.py            manual power + EMHASS SOC controls
select.py            manual EMS mode + EMHASS strategy
button.py            optimize/strategy/manual/resume actions
frontend/            layered dashboard/settings assets
tests/               hardware-independent regression tests
```

Repository tooling:

```text
scripts/validate_repo.py
.github/workflows/quality.yml
.github/workflows/hacs.yml
.github/workflows/hassfest.yml
```

## Active orchestrator chain

```text
orchestrator_v013.py
    inherits orchestrator_v012.py
        inherits orchestrator.py
```

All three remain active runtime code. Check subclasses before modifying base behavior.

v0.23 additionally gives the active v0.13 layer ownership of restoring/persisting `last_success` through `runtime_store.py`.

## Active frontend chain

v0.23 top level:

```text
gw-energy-pilot-v023.js
  -> gw-energy-pilot-v022-flow-direction.js
       -> gw-energy-pilot-v022.js
            -> gw-energy-pilot-v021.js
                 -> earlier layered dashboard/settings assets
```

Current ownership:

- v0.23 — native Grid Today/Yesterday rendering and release badge;
- flow overlay — final particle double-reversal correction;
- v0.22 — Smart Meter strategy UI and PCC/battery target relabelling;
- v0.21 — manual 12-mode EMS pad.

Older filenames are active runtime dependencies. Trace imports before deleting/consolidating anything.

## Automatic-control contract

### GoodWe smart meter active = ON

Default:

```text
EMHASS P_grid > +deadband -> mode 9  Grid import target
EMHASS P_grid < -deadband -> mode 10 Grid export target
EMHASS P_grid near 0 W    -> mode 1  GoodWe Auto / AI
```

`P_grid` sign:

```text
positive = planned import
negative = planned export
```

GoodWe meter sign is opposite:

```text
36008 negative = actual import
36008 positive = actual export
```

Both `P_batt` and `P_grid` are validated as finite plan outputs. `P_grid` is the actuator request. GoodWe modes 9/10 close the fast loop at the PCC.

Do not reintroduce the former mode-11 grid-neutral trim loop on top of PCC control without a new design and hardware evidence.

### GoodWe smart meter active = OFF

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt near 0 W    -> mode 8  Battery Hold
```

This fallback deliberately works without a valid `P_grid` entity.

### EV anti-discharge protection

During active EV charging:

```text
P_batt > +deadband -> mode 8  Battery Hold
P_batt near 0 W    -> mode 8  Battery Hold
P_batt < -deadband -> mode 11 Battery charge allowed
```

This is a battery-direction override, not EV charger control. The legacy option key `enable_ev_coordination` remains for compatibility.

When native orchestration is enabled, EV stop waits for a fresh optimization before normal control resumes.

### Manual ownership

Manual commands never inherit or reinterpret the automatic strategy. Manual mode 9 is mode 9; manual mode 11 is mode 11.

Automatic Control OFF returns the inverter to mode 1 / 0 W.

## Hardware evidence behind PCC control

Reference GW15K-ETA-G20 field tests established:

```text
mode 10 setpoint 400 W -> ~395 W grid export
mode 9  setpoint 400 W -> ~331 W grid import
mode 9  setpoint 15 kW -> ~15 kW grid import + local DC PV; battery ~16.9 kW charge
mode 11 setpoint 15 kW -> battery ~15 kW charge; PV reduces required grid import
mode 1                 -> observed self-use / near-zero-grid with PV surplus charging
```

Therefore:

```text
9 / 10  = PCC/grid targets
11 / 12 = direct battery-power targets
```

Do not use a mode-9 setpoint as a battery-power limit.

## Persistent grid accounting

v0.23 introduces one `GWEnergyPilotAccounting` instance per config entry.

Physical source:

```text
36017 lifetime import
36015 lifetime export
```

Execution rules:

- establish a baseline from physical lifetime counters;
- accumulate only positive deltas;
- re-baseline when a lifetime counter decreases;
- roll current-day totals at local midnight;
- persist current/previous-day state through Home Assistant storage;
- expose native daily import/export sensors;
- optionally use Recorder once to bootstrap existing midnight-boundary history.

Recorder is not part of the live accounting loop. The 24-hour power graph remains Recorder-backed.

Future financial accounting must consume the same per-refresh physical energy deltas rather than reconstructing energy in the frontend.

See `docs/ACCOUNTING.md`.

## Persistent runtime state

`runtime_store.py` stores small EnergyPilot-owned runtime history separately from configuration.

Current key:

```text
gw_energypilot.runtime.<config_entry_id>
```

The active orchestrator restores `last_success` before inherited setup and persists it only after a complete EnergyPilot-owned optimize + publish cycle succeeds.

Failed optimizations preserve the previous timestamp. Invalid/timezone-less data is ignored.

See `docs/RUNTIME_STATE.md`.

## Modbus safety

`registers.py` is canonical for register definitions/read blocks.

Never guess GoodWe addresses, data widths, scales or signs.

EMS contract:

```text
47511 = mode
47512 = non-negative mode-specific setpoint magnitude
```

Write order remains:

```text
write 47512
brief wait
write 47511
```

Do not reorder this without hardware validation.

## Dedicated settings architecture

Dashboard write APIs are admin-only and use the existing ConfigEntry as the single configuration source.

```text
settings_api.py      EP/EMHASS/GoodWe connection
smart_meter_api.py   GoodWe smart-meter strategy
beta_soc_api.py      verified 45356/45358 field-test writes
```

Rules:

- GoodWe host/port/unit-ID changes must pass real Modbus validation before save;
- smart-meter strategy is GoodWe/config-entry data, not EMHASS config;
- device identity remains `(DOMAIN, config_entry_id)`;
- entity unique IDs remain stable;
- persistent runtime/accounting Store data is not user configuration.

## Development workflow

For each bug or feature:

1. Inspect current implementation.
2. Trace the runtime path and ownership boundary.
3. Reproduce expected versus actual behavior from diagnostics/logs where possible.
4. Apply the smallest robust change.
5. Add/adjust hardware-independent regression coverage.
6. Check startup, reload, unavailable-device and stale-data behavior.
7. Check entity/device/storage compatibility.
8. Update docs/changelog/release notes for externally visible behavior.
9. Run repository checks.
10. For release work, require Quality + HACS + hassfest on the exact final head.

## Lightweight repository checks

```text
python -m compileall -q custom_components/gw_energypilot scripts tests
python -m unittest discover -s tests -v
python scripts/validate_repo.py
```

The `Quality` workflow runs these automatically.

The validator checks, among other things:

- Modbus register/read-block coverage;
- multi-word value coverage;
- JSON validity;
- frontend relative-import existence;
- active frontend/manifest version agreement;
- changelog/release-notes version coverage.

Static CI does not prove GoodWe hardware semantics.

## Domain split for debugging

```text
GoodWe telemetry/register issue
  -> client.py / registers.py / coordinator.py

Home Assistant entity/device issue
  -> sensor.py / switch.py / number.py / select.py / button.py / entity.py / __init__.py

Persistent daily grid totals
  -> accounting.py / accounting_model.py / accounting_sensor.py

Persistent Last success/runtime history
  -> runtime_store.py / orchestrator_v013.py

Dashboard settings
  -> settings_api.py / smart_meter_api.py / config_flow.py / settings frontend layers

Battery/PCC control
  -> controller.py / client.py

EMHASS optimization
  -> orchestrator*.py / emhass_config.py / event_triggers.py

Dashboard-only presentation
  -> active frontend chain
```

Do not fix a presentation issue by changing Modbus semantics unless the data itself is wrong.

## Known technical debt

### Layered orchestrator

The v0.12/v0.13 classes subclass earlier code. Keep all active layers until behavior is deliberately consolidated under tests.

### Layered frontend

The v0.23 frontend imports older layers. The repository validator proves import existence, not behavioral equivalence after consolidation.

### Runtime integration coverage

Pure/unit coverage is materially better, including controller, EMHASS config, Modbus decoding, accounting model and runtime-store persistence. The repository still lacks a complete Home Assistant harness covering every config-entry/Recorder/WebSocket lifecycle path.

## Testing priorities after v0.23

Existing coverage includes:

- PCC `P_grid -> 9/10/1` mapping;
- direct `P_batt -> 11/12/8` fallback;
- max-power clamping and invalid outputs;
- manual ownership;
- EV anti-discharge direction rules and EV-stop freshness;
- EMHASS config preservation;
- Modbus decoding/read coverage;
- accounting baseline/delta/reset/rollover/bootstrap/persistence;
- runtime `last_success` persistence and invalid-state handling.

Next useful coverage:

- Home Assistant config-entry lifecycle around accounting Store/Recorder bootstrap;
- settings WebSocket authorization/reload behavior;
- device-registry migration;
- orchestrator HTTP success/failure integration;
- Recorder statistics interactions on real HA test fixtures;
- browser/client verification of the final flow-direction overlay.

## Release checklist

Before a release verify:

- `manifest.json` version;
- active frontend module/cache-buster and frontend `VERSION`;
- `CHANGELOG.md` detailed changes;
- `docs/RELEASE_NOTES.md` current version + status;
- README current version/behavior;
- architecture/development docs when runtime structure changes;
- translations for user-facing changes;
- Quality, HACS and hassfest on the exact final head;
- no accidental unique-ID/device-identifier/storage-key changes;
- no undocumented register/control semantic changes;
- Beta features are explicitly bounded and reversible where practical.
