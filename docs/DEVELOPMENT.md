# Development guide

This document defines the practical development workflow for GW EnergyPilot.

## Repository is authoritative

Before changing code, inspect the current `main` branch. Do not assume snippets from an older chat or release still match runtime behaviour.

For AI-assisted work, also read `AGENTS.md` first.

## Current release structure

The Home Assistant integration lives in:

```text
custom_components/gw_energypilot/
```

Important modules:

```text
__init__.py          config-entry setup, device migration and sidebar panel registration
client.py            asynchronous GoodWe Modbus TCP I/O
registers.py         canonical register definitions and read blocks
coordinator.py       periodic telemetry polling
controller.py        automatic/manual EMS ownership and control
orchestrator.py      base EMHASS orchestration
orchestrator_v012.py reliability/startup/price refinements
orchestrator_v013.py G20 load semantics and v0.13 refinements
emhass_config.py     EMHASS config read/write helpers
settings_api.py      admin-only dashboard settings API
event_triggers.py    event-driven optimization hooks
sensor.py            telemetry/diagnostic sensors
switch.py            Automatic Control ownership switch
number.py            manual power and EMHASS SOC controls
select.py            manual EMS mode selection
button.py            optimize/strategy/manual/resume actions
frontend/            layered sidebar dashboard and settings assets
tests/               hardware-independent safety/regression tests
```

Repository-level tooling:

```text
scripts/validate_repo.py       lightweight consistency checks
.github/workflows/quality.yml  Python compile + unit tests + repository validation
.github/workflows/hacs.yml     HACS validation
.github/workflows/hassfest.yml Home Assistant hassfest validation
```

## Active orchestration chain

The active runtime class comes from:

```text
orchestrator_v013.py
    inherits orchestrator_v012.py
        inherits orchestrator.py
```

Never change only the base file without checking whether a subclass overrides the same behaviour.

This layered implementation is valid current code but is also technical debt. A future release may consolidate it after behaviour is covered by tests.

## Active frontend structure

v0.17 deliberately layers the settings UI on top of the existing dashboard releases:

```text
gw-energy-pilot-v017.js
  -> gw-energy-pilot-v016.js              G20 Beta diagnostics
       -> gw-energy-pilot-v015.js         EMHASS strategy controls
  -> gw-energy-pilot-settings-v016.js     EP / EMHASS / GOODWE settings implementation
```

The lower files import earlier dashboard layers. Do not remove versioned frontend files based on filenames alone.

## Dedicated settings architecture

The dashboard gear uses admin-only WebSocket commands from `settings_api.py`:

```text
gw_energypilot/settings/get
gw_energypilot/settings/update
```

The existing Home Assistant config entry remains the only configuration source.

Rules:

- EP/EMHASS settings reuse the existing config-flow validation/conversion path;
- GOODWE host/port/unit-ID changes must pass real Modbus setup validation before save;
- a successful update modifies the existing entry and requests a reload;
- device identity uses `(DOMAIN, config_entry_id)`, not mutable connection settings;
- v0.17 migrates a legacy `(DOMAIN, host:slave)` device identifier before platform setup;
- existing entity unique IDs remain `{entry_id}_{entity_key}`.

See `docs/SETTINGS.md`.

## Development workflow

For each bug or feature:

1. Inspect the current implementation.
2. Trace the exact runtime path.
3. Confirm whether the issue belongs to GoodWe I/O, Home Assistant state, device/entity migration, controller ownership, settings API, EMHASS orchestration, or frontend presentation.
4. Reproduce with diagnostics/logs where possible.
5. Apply the smallest robust fix.
6. Run the lightweight repository checks and unit tests.
7. Check startup and unavailable-device behaviour.
8. Check config-entry reload/unload behaviour.
9. Check unique IDs, device identifiers and Recorder/statistics compatibility.
10. Update docs/changelog/release notes for externally visible behaviour.

## Lightweight repository checks

Run:

```text
python -m compileall -q custom_components/gw_energypilot scripts tests
python -m unittest discover -s tests -v
python scripts/validate_repo.py
```

The `Quality` GitHub Actions workflow runs the same checks automatically on pushes and pull requests.

The validator currently checks:

- every Modbus register definition is fully covered by a required or optional read block;
- all words of multi-register values, including uint32/int32/float32/uint64 definitions, are covered;
- every Modbus read block stays within the 125-register protocol limit;
- register keys are unique;
- repository JSON files parse;
- relative frontend JavaScript imports point to existing files;
- the active panel JavaScript file exists;
- the active frontend `VERSION` matches `manifest.json` when declared;
- every changelog version appears on the release-notes page with an explicit status.

Unit tests currently cover controller safety/ownership decisions, EMHASS full-config patch preservation, and hardware-independent Modbus decoding/coverage. These checks do not replace real Home Assistant lifecycle, settings API or hardware validation.

## Keep domains separated

A useful debugging split is:

```text
GoodWe telemetry problem
  -> client.py / registers.py / coordinator.py

Home Assistant entity/device problem
  -> sensor.py / switch.py / number.py / select.py / button.py / entity.py / __init__.py

Dashboard settings problem
  -> settings_api.py + config_flow.py + settings frontend layer

Battery control problem
  -> controller.py + client.py

Optimization problem
  -> orchestrator*.py + emhass_config.py + event_triggers.py

Dashboard-only problem
  -> active frontend JS modules + entity attributes
```

Do not solve a presentation issue by changing Modbus semantics unless the underlying data is actually wrong.

## Known technical debt

### 1. Layered orchestrator versions

The v0.12 and v0.13 modules subclass earlier orchestration code. This made incremental releases safer, but future maintenance would benefit from a tested consolidation into a single implementation.

Do not delete `orchestrator.py` or `orchestrator_v012.py` while `orchestrator_v013.py` inherits from them.

### 2. Layered frontend assets

The active dashboard is layered, including a dedicated settings implementation layer in v0.17. Files that look historical can still be runtime dependencies.

Do not delete a versioned frontend asset based on its filename alone. Trace imports first. The repository validator catches missing relative JavaScript imports, but it does not prove behavioural equivalence after a consolidation.

### 3. Limited automated runtime coverage

The repository has hardware-independent unit coverage for controller mapping/ownership, EMHASS selected-config patching and selected Modbus decode invariants, plus structural repository checks. It does not yet have a full Home Assistant test harness covering config-entry lifecycle, settings WebSocket behavior, device-registry migration, orchestrator HTTP flows, entity registry migrations, Recorder integration, or real hardware I/O.

Add focused tests before consolidating orchestration or frontend layers.

## Beta hardware-validation workflow

The active installation base is small enough that some read-only diagnostics may be intentionally shipped before extensive field testing.

For this repository, **Beta** means the feature is available for limited field validation but has not yet been extensively confirmed in real installations.

A Beta register feature must:

- remain read-only unless separately validated for writes;
- use optional Modbus blocks;
- fail independently from required telemetry;
- be clearly labelled Beta in diagnostics, Home Assistant entities and documentation;
- stay out of EMS control and ownership decisions;
- stay out of canonical Recorder-facing energy entities until promoted;
- include a practical way for testers to copy/report values;
- record model, firmware and matching SolarGo/SEMS+ values during validation.

The v0.17 settings UI/device migration is also marked Beta until it has broader real-installation exposure.

Promotion from Beta requires real-installation evidence and an explicit release-note/status change.

## Resolved maintenance issue: telemetry block duplication

Telemetry block ownership is centralized in `registers.py`:

```text
TELEMETRY_BLOCKS
OPTIONAL_TELEMETRY_BLOCKS
```

`client.py` imports those constants instead of maintaining duplicate ranges.

The active runtime ranges were preserved during this refactor. Blocks ending in a multi-word value include all required words. The validator prevents a future register definition from being added without full block coverage.

## Testing priorities

Existing automated coverage includes:

- controller `P_batt` to EMS mapping;
- deadband behaviour;
- maximum power clamping;
- manual ownership versus Automatic Control;
- disabling Automatic Control returning to mode 1 / 0 W;
- invalid/unavailable/non-finite `P_batt` handling;
- EV hold and EV-stop optimization guard behaviour;
- EMHASS selected-config preservation;
- uint64 extended-meter decoding and multi-word register coverage.

Next priorities include:

- device-registry migration from legacy `host:slave` to config-entry ID;
- settings API authorization, validation and reload behavior;
- broader register decoding (uint/int/float, scaling and signed values);
- orchestrator optimize/publish HTTP success and failure paths;
- load forecast using register 35172;
- startup with inverter unavailable;
- startup with EMHASS unavailable;
- config-entry reload/unload;
- entity unique-ID stability and migrations;
- Recorder/statistics interactions.

## Hardware validation

The reference hardware is currently:

- GoodWe GW15K-ETA-G20

When validating another model or a Beta register, record at least:

```text
inverter model
firmware version
battery model
Modbus connection details
raw/decoded candidate value
matching SolarGo/SEMS+ value where relevant
telemetry differences
EMS mode 8 behaviour
EMS mode 11 behaviour
EMS mode 12 behaviour
register/sign differences
```

Do not mark the whole ETA family as tested based on one unit.

## Control changes require extra care

Changes involving registers `47511` or `47512`, EMS modes, setpoints, charge/discharge direction, or maximum power can command significant real power.

For such changes:

- verify sign conventions;
- keep power bounded;
- prefer a non-automatic/manual validation path first;
- confirm the inverter's resulting mode and telemetry;
- ensure failure cannot leave two control paths fighting each other.

## Release checklist

Before a release, verify:

- `manifest.json` version;
- active frontend module/cache-buster and frontend `VERSION`;
- `CHANGELOG.md` detailed changes;
- `docs/RELEASE_NOTES.md` user-facing summary and **Beta/Validated** status;
- README current version/status and behavior;
- `docs/SETTINGS.md` when the settings contract changes;
- translations for new user-facing entities/options;
- HACS metadata where relevant;
- `Quality`, HACS, and hassfest checks;
- no accidental entity unique-ID or device-identifier changes;
- any intentional device migration follows a current Home Assistant registry migration pattern;
- no undocumented register-semantic changes;
- every unconfirmed hardware value is explicitly labelled Beta and remains within the Beta policy boundary.

A Beta release may intentionally contain unconfirmed read-only diagnostics. Static CI is sufficient to prove repository consistency, but never to promote those hardware semantics from Beta to confirmed.

## Documentation ownership

Use these documents for durable project knowledge rather than relying on chat history:

- `AGENTS.md` — instructions to contributors/AI;
- `docs/ARCHITECTURE.md` — runtime design;
- `docs/MODBUS.md` — register/control contract and Beta register status;
- `docs/ENTITIES.md` — Home Assistant entity/device contract;
- `docs/EMHASS_SETUP.md` — operator setup;
- `docs/SETTINGS.md` — dedicated settings behavior and migration;
- `docs/KNOWN_ISSUES.md` — field issues outside or adjacent to EnergyPilot runtime code;
- `docs/RELEASE_NOTES.md` — readable per-version notes and Beta/validation status;
- `CHANGELOG.md` — detailed technical version history.
