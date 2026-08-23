# GW EnergyPilot — AI development instructions

This file defines the working rules for AI coding assistants and contributors.
The repository is the source of truth for the current implementation.

## Source of truth

- Always inspect the current repository before proposing or applying a code change.
- Never reconstruct current code from an older chat, pasted fragment, or previous release.
- Repository code and current documentation take precedence over conversation history.
- If documentation and code disagree, treat the code as current behaviour and flag the documentation mismatch.

## Project scope

GW EnergyPilot is an unofficial Home Assistant custom integration for local GoodWe ETA-G20 telemetry, EMS control, EMHASS orchestration, optional Nord Pool pricing, optional EV coordination, and a built-in dashboard.

Primary tested inverter:

- GoodWe GW15K-ETA-G20

Current integration domain:

- `gw_energypilot`

EMHASS is an external prerequisite. GW EnergyPilot may integrate with EMHASS, but must not install or silently replace EMHASS.

## Before changing code

1. Read the files involved in the requested behaviour.
2. Trace callers, listeners, dispatcher signals, config/options, and entity dependencies.
3. Identify the root cause before rewriting code.
4. Prefer the smallest robust change.
5. Preserve working behaviour outside the requested scope.
6. Check backwards compatibility for entity unique IDs, config entries, options, and Home Assistant Recorder history.
7. Update documentation when an architectural rule, register semantic, public entity, or operator workflow changes.

## Home Assistant rules

- Follow current Home Assistant development conventions.
- Keep config-entry setup non-blocking where practical.
- Do not hold Home Assistant startup on slow or unavailable Modbus/EMHASS I/O.
- Use coordinator-backed telemetry for polled inverter data.
- Keep unique IDs stable unless a migration is explicitly implemented.
- Prefer config/options over hard-coded Home Assistant entity IDs.
- Consider entity registry behaviour, translations, reload behaviour, availability, restore state, diagnostics, and error handling.
- Do not create duplicate sensors or parallel implementations for the same concept without a documented migration plan.

## Modbus rules

- Never invent or guess GoodWe register addresses, data types, scales, or sign conventions.
- `custom_components/gw_energypilot/registers.py` is the canonical source for register definitions and telemetry read blocks.
- `client.py` must import `TELEMETRY_BLOCKS` and `OPTIONAL_TELEMETRY_BLOCKS`; do not recreate block lists there.
- Changes to register definitions require evidence from tested hardware, vendor documentation, or repeatable diagnostics.
- Preserve the tested sign conventions unless evidence proves they are wrong:
  - grid power: negative = import, positive = export;
  - battery power: negative = charging, positive = discharging.
- EMS control currently uses register `47511` for mode and `47512` for power setpoint.
- Be conservative with write operations: an incorrect EMS write can move significant battery/grid power.
- Keep `python scripts/validate_repo.py` passing; it verifies that every register definition, including all words of multi-word values, is covered by a configured read block.
- A draft that introduces unconfirmed register semantics is not release-ready merely because static CI is green; keep it in validation until the required evidence exists.

## Control ownership

Automatic and manual control must remain explicit.

- Automatic Control ON: EnergyPilot may translate a valid EMHASS `P_batt` target into GoodWe EMS commands.
- Automatic Control OFF: the controller returns the inverter to GoodWe Auto / AI (`mode 1`, `0 W`).
- Manual quick actions take manual ownership before writing their requested EMS mode.
- EV coordination may temporarily hold the battery and trigger a fresh optimization after charging stops.

Do not introduce code paths that silently fight each other for EMS ownership.

## EMHASS rules

- EMHASS must already be installed, running, and configured.
- Use the configured EMHASS base URL; do not assume `localhost` works from Home Assistant Core.
- Preserve unrelated EMHASS configuration when changing selected settings.
- `/set-config` must receive the complete intended configuration; read the current config first when patching selected values.
- Do not execute a stale `P_batt` target after a condition that requires re-optimization.
- Treat optimizer readiness and numeric output validation as safety gates.
- Strategy/cost-function changes alter the optimizer objective only; do not silently change the GoodWe actuator/control primitive at the same time.

Existing setup/operator guidance lives in `docs/EMHASS_SETUP.md`.

## Current orchestration implementation

Do not assume `orchestrator.py` alone is the active implementation.

Current runtime import chain:

```text
__init__.py
  -> orchestrator_v013.GWEnergyPilotOrchestrator
       -> orchestrator_v012.GWEnergyPilotOrchestrator
            -> orchestrator.GWEnergyPilotOrchestrator
```

Until this inheritance chain is deliberately consolidated, changes to orchestration require inspecting all three layers.

## Frontend

The sidebar panel module is selected in `__init__.py`. Multiple versioned JavaScript files exist in `frontend/`. In v0.15 the active entry point imports v0.14, which imports v0.13 and the earlier layers below it. Do not delete or modify a versioned file merely because its name looks historical. Trace the JavaScript import chain first.

The repository validator checks that relative frontend imports resolve and that the active frontend `VERSION` matches `manifest.json` when the entry module declares one.

## Repository checks

Before merging a substantial change, run or rely on the `Quality` GitHub Actions workflow. It performs:

- Python syntax compilation without importing the full Home Assistant runtime;
- hardware-independent unit tests from `tests/`;
- register-block coverage validation;
- JSON parsing checks;
- frontend dependency/import checks;
- active frontend/manifest version consistency.

These checks complement HACS and hassfest; they do not replace runtime testing on Home Assistant or hardware validation.

## Bug-fixing workflow

When a bug is reported:

1. Reproduce the expected versus actual state from logs/diagnostics where possible.
2. Trace the live code path.
3. Check configuration and ownership state.
4. Check external prerequisites (GoodWe reachability, EMHASS health/output, Home Assistant entity state).
5. Identify the smallest root-cause fix.
6. Consider startup, reload, unavailable-device, and stale-data edge cases.
7. Avoid unrelated refactors in the same fix unless they are required for correctness.

## Documentation map

- `README.md` — user-facing overview and installation.
- `docs/ARCHITECTURE.md` — runtime architecture and ownership boundaries.
- `docs/MODBUS.md` — Modbus semantics and change rules.
- `docs/ENTITIES.md` — Home Assistant entity contract.
- `docs/DEVELOPMENT.md` — contributor workflow and known technical debt.
- `docs/EMHASS_SETUP.md` — EMHASS setup/operator guidance.
- `docs/KNOWN_ISSUES.md` — field issues adjacent to or outside EnergyPilot runtime code.
- `CHANGELOG.md` — release history.

## Definition of done

For a substantial change, check at least:

- runtime behaviour;
- failure/unavailable behaviour;
- config/options compatibility;
- entity/unique-ID compatibility;
- translations when user-visible entities/options change;
- dashboard impact;
- relevant unit tests;
- repository quality checks;
- README/docs impact;
- changelog/release impact where appropriate.
