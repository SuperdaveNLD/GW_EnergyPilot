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
__init__.py          config-entry setup and sidebar panel registration
client.py            asynchronous GoodWe Modbus TCP I/O
registers.py         canonical register definitions and read blocks
coordinator.py       periodic telemetry polling
controller.py        automatic/manual EMS ownership and control
orchestrator.py      base EMHASS orchestration
orchestrator_v012.py reliability/startup/price refinements
orchestrator_v013.py G20 load semantics and v0.13 refinements
emhass_config.py     EMHASS config read/write helpers
event_triggers.py    event-driven optimization hooks
sensor.py            telemetry/diagnostic sensors
switch.py            Automatic Control ownership switch
number.py            manual power and EMHASS SOC controls
select.py            manual EMS mode selection
button.py            optimize/manual/resume actions
frontend/            sidebar dashboard assets
```

Repository-level tooling:

```text
scripts/validate_repo.py       lightweight consistency checks
.github/workflows/quality.yml  Python compile + repository validation
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

## Development workflow

For each bug or feature:

1. Inspect the current implementation.
2. Trace the exact runtime path.
3. Confirm whether the issue belongs to GoodWe I/O, Home Assistant state, controller ownership, EMHASS orchestration, or frontend presentation.
4. Reproduce with diagnostics/logs where possible.
5. Apply the smallest robust fix.
6. Run the lightweight repository checks.
7. Check startup and unavailable-device behaviour.
8. Check config-entry reload/unload behaviour.
9. Check unique IDs and Recorder/statistics compatibility.
10. Update docs/changelog for externally visible behaviour.

## Lightweight repository checks

Run:

```text
python -m compileall -q custom_components/gw_energypilot scripts
python scripts/validate_repo.py
```

The `Quality` GitHub Actions workflow runs the same checks automatically on pushes and pull requests.

The validator currently checks:

- every Modbus register definition is fully covered by a required or optional read block;
- the second word of uint32/int32/float32 definitions is covered;
- every Modbus read block stays within the 125-register protocol limit;
- register keys are unique;
- repository JSON files parse;
- relative frontend JavaScript imports point to existing files;
- the active panel JavaScript file exists;
- the active frontend `VERSION` matches `manifest.json` when declared.

These are repository-consistency checks, not full Home Assistant or hardware tests.

## Keep domains separated

A useful debugging split is:

```text
GoodWe telemetry problem
  -> client.py / registers.py / coordinator.py

Home Assistant entity problem
  -> sensor.py / switch.py / number.py / select.py / button.py / entity.py

Battery control problem
  -> controller.py + client.py

Optimization problem
  -> orchestrator*.py + emhass_config.py + event_triggers.py

Dashboard-only problem
  -> active frontend JS module + entity attributes
```

Do not solve a presentation issue by changing Modbus semantics unless the underlying data is actually wrong.

## Known technical debt

### 1. Layered orchestrator versions

The v0.12 and v0.13 modules subclass earlier orchestration code. This made incremental releases safer, but future maintenance would benefit from a tested consolidation into a single implementation.

Do not delete `orchestrator.py` or `orchestrator_v012.py` while `orchestrator_v013.py` inherits from them.

### 2. Layered frontend assets

The active dashboard is also layered. The v0.13 entry module imports earlier versioned modules, so several files that look historical are still runtime dependencies.

Do not delete a versioned frontend asset based on its filename alone. Trace imports first. The repository validator now catches missing relative JavaScript imports, but it does not prove behavioural equivalence after a consolidation.

### 3. Limited automated runtime coverage

The repository now has lightweight structural checks, but it does not yet have a Home Assistant test harness covering controller, orchestrator, entity lifecycle, or hardware I/O behaviour.

Future work should add focused tests before consolidating orchestration or frontend layers.

## Resolved maintenance issue: telemetry block duplication

Telemetry block ownership is now centralized in `registers.py`:

```text
TELEMETRY_BLOCKS
OPTIONAL_TELEMETRY_BLOCKS
```

`client.py` imports those constants instead of maintaining duplicate ranges.

The active runtime ranges were preserved exactly during this refactor. In particular, blocks ending in a 32-bit value include the second register word. The validator prevents a future register definition from being added without full block coverage.

## Testing priorities

The project should progressively add automated coverage for:

- register decoding (uint/int/float, scaling and signed values);
- controller `P_batt` to EMS mapping;
- deadband behaviour;
- maximum power clamping;
- manual ownership versus Automatic Control;
- disabling Automatic Control returning to mode 1 / 0 W;
- unavailable `P_batt` / optimizer state;
- EV hold and EV-stop optimization behaviour;
- EMHASS config preservation;
- load forecast using register 35172;
- startup with inverter unavailable;
- startup with EMHASS unavailable;
- entity unique-ID stability.

## Hardware validation

The reference hardware is currently:

- GoodWe GW15K-ETA-G20

When validating another model, record at least:

```text
inverter model
firmware version
battery model
Modbus connection details
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
- `CHANGELOG.md`;
- README behaviour and installation instructions;
- active frontend module/cache-buster;
- translations for new user-facing entities/options;
- HACS metadata where relevant;
- `Quality`, HACS, and hassfest checks;
- no accidental entity unique-ID changes;
- no undocumented register-semantic changes.

## Documentation ownership

Use these documents for durable project knowledge rather than relying on chat history:

- `AGENTS.md` — instructions to contributors/AI;
- `docs/ARCHITECTURE.md` — runtime design;
- `docs/MODBUS.md` — register/control contract;
- `docs/ENTITIES.md` — Home Assistant entity contract;
- `docs/EMHASS_SETUP.md` — operator setup;
- `CHANGELOG.md` — version history.
