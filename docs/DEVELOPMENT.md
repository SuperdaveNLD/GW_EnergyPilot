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
registers.py         canonical register definitions
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
6. Check startup and unavailable-device behaviour.
7. Check config-entry reload/unload behaviour.
8. Check unique IDs and Recorder/statistics compatibility.
9. Update docs/changelog for externally visible behaviour.

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

### 1. Duplicate telemetry block definitions

`registers.py` contains `TELEMETRY_BLOCKS`, while `client.py` currently maintains separate active read blocks plus an optional block.

The counts/ranges are not identical.

Do not casually synchronize them by eye. A safe refactor should first add validation that every register definition is covered, including the second word of all 32-bit/float values.

### 2. Layered orchestrator versions

The v0.12 and v0.13 modules subclass earlier orchestration code. This made incremental releases safer, but future maintenance would benefit from a tested consolidation into a single implementation.

Do not delete `orchestrator.py` or `orchestrator_v012.py` while `orchestrator_v013.py` inherits from them.

### 3. Versioned frontend assets

Several historical dashboard JavaScript files are retained in `frontend/`.

Only the module referenced by `PANEL_MODULE` in `__init__.py` is the active panel entry point. Confirm imports/dependencies before deleting or modifying historical assets.

## Testing priorities

The project should progressively add automated coverage for:

- register decoding (uint/int/float, scaling and signed values);
- telemetry-block coverage;
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
