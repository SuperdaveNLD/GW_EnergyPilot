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
6. Check backwards compatibility for entity unique IDs, device identifiers, config entries, options, and Home Assistant Recorder history.
7. Update documentation when an architectural rule, register semantic, public entity, or operator workflow changes.

## Home Assistant rules

- Follow current Home Assistant development conventions.
- Keep config-entry setup non-blocking where practical.
- Do not hold Home Assistant startup on slow or unavailable Modbus/EMHASS I/O.
- Use coordinator-backed telemetry for polled inverter data.
- Keep unique IDs stable unless a migration is explicitly implemented.
- Device identifiers are also a migration contract: v0.17 uses `(DOMAIN, config_entry_id)` and migrates the legacy `(DOMAIN, host:slave)` identifier before platform setup.
- Do not revert device identity to mutable host/unit-ID data.
- Prefer config/options over hard-coded Home Assistant entity IDs.
- Consider entity registry behaviour, device registry behaviour, translations, reload behaviour, availability, restore state, diagnostics, and error handling.
- Do not create duplicate sensors or parallel implementations for the same concept without a documented migration plan.

## Modbus rules

- Never invent or guess GoodWe register addresses, data types, scales, or sign conventions.
- `custom_components/gw_energypilot/registers.py` is the canonical source for register definitions and telemetry read blocks.
- `client.py` must import `TELEMETRY_BLOCKS` and `OPTIONAL_TELEMETRY_BLOCKS`; do not recreate block lists there.
- Changes to register definitions require evidence from tested hardware, vendor documentation, upstream implementation evidence, or repeatable diagnostics.
- Preserve the tested sign conventions unless evidence proves they are wrong:
  - GoodWe grid meter power: negative = import, positive = export;
  - battery power: negative = charging, positive = discharging.
- EMHASS `P_grid` uses the opposite sign from GoodWe meter telemetry:
  - EMHASS `P_grid` positive = planned import;
  - EMHASS `P_grid` negative = planned export.
- EMS control uses register `47511` for mode and `47512` for the non-negative mode-specific power magnitude.
- Be conservative with write operations: an incorrect EMS write can move significant battery/grid power.
- Keep `python scripts/validate_repo.py` passing; it verifies that every register definition, including all words of multi-word values, is covered by a configured read block.

### Beta register policy

A small active tester group may justify shipping selected unconfirmed values as **Beta diagnostics** before broad field validation.

For Beta hardware semantics:

- Beta means **not yet extensively field-tested**;
- keep candidate registers read-only unless a separate validated write design exists;
- keep them in optional read blocks so unsupported firmware cannot fail required telemetry;
- do not feed Beta values into EMS control, ownership, SOC enforcement, Recorder-facing canonical energy entities, or automatic migration logic;
- label them clearly as Beta in user-facing diagnostics, Home Assistant entities, and documentation;
- collect inverter model, firmware and matching SolarGo/SEMS+ values when validating;
- promotion from Beta to confirmed semantics requires real-installation evidence and an intentional code/docs change.

Static CI being green proves repository consistency, not GoodWe register meaning.

## Control ownership

Automatic and manual control must remain explicit.

- Automatic Control OFF returns the inverter to GoodWe Auto / AI (`mode 1`, `0 W`).
- Manual quick actions take manual ownership before writing their requested EMS mode.
- EV coordination may temporarily hold the battery and trigger a fresh optimization after charging stops.
- Do not introduce code paths that silently fight each other for EMS ownership.

### Automatic actuator strategy

v0.22 supports two deliberate automatic actuator strategies selected by the GoodWe config-entry setting **GoodWe smart meter active**.

When the setting is **ON** (default):

```text
EMHASS P_grid > +deadband  -> GoodWe mode 9  Grid import target
EMHASS P_grid < -deadband  -> GoodWe mode 10 Grid export target
EMHASS P_grid near 0 W     -> GoodWe mode 1  Auto / self-use
```

GoodWe modes 9/10 close the fast control loop against the inverter's own smart meter/PCC. Do not reintroduce a second 30-second EnergyPilot mode-11 trimming loop on top of this strategy without new hardware evidence and an explicit design change.

When the setting is **OFF**:

```text
EMHASS P_batt < -deadband -> GoodWe mode 11 direct battery charge
EMHASS P_batt > +deadband -> GoodWe mode 12 direct battery discharge
EMHASS P_batt near 0 W    -> GoodWe mode 8  Battery Hold
```

The direct battery fallback must remain usable even when `P_grid` is missing/unavailable.

Manual mode 9/10/11/12 commands always mean exactly the mode selected by the operator; the automatic strategy setting must not remap manual commands.

## EMHASS rules

- EMHASS must already be installed, running, and configured.
- Use the configured EMHASS base URL; do not assume `localhost` works from Home Assistant Core.
- Preserve unrelated EMHASS configuration when changing selected settings.
- `/set-config` must receive the complete intended configuration; read the current config first when patching selected values.
- Do not execute stale `P_batt` or `P_grid` output after a condition that requires re-optimization.
- Treat optimizer readiness and numeric output validation as safety gates.
- When GoodWe smart-meter control is enabled, `P_grid` is the automatic actuator plan and `P_batt` remains a required plan-validity/diagnostic output.
- When GoodWe smart-meter control is disabled, `P_batt` is the actuator plan and a valid `P_grid` is not required.
- Strategy/cost-function changes alter the optimizer objective only; do not silently change the GoodWe actuator strategy at the same time.

Existing setup/operator guidance lives in `docs/EMHASS_SETUP.md`.

## Dedicated settings APIs

Dashboard configuration uses:

```text
custom_components/gw_energypilot/settings_api.py
custom_components/gw_energypilot/smart_meter_api.py
custom_components/gw_energypilot/beta_soc_api.py
```

Rules:

- dashboard write APIs remain admin-only;
- the existing Home Assistant `ConfigEntry` is the single configuration source;
- do not add a parallel settings database;
- EP/EMHASS option writes must preserve the existing config-flow validation/conversion path;
- GoodWe host/port/unit-ID changes must be validated against the inverter before storage;
- the smart-meter actuator selection is GoodWe hardware/config-entry data, not EMHASS config;
- changing the smart-meter setting while Automatic Control is active may immediately re-evaluate the current plan and must remain explicit in the UI;
- connection changes update the existing entry and reload it;
- preserve the stable config-entry-based device identifier and existing entity unique IDs.

See `docs/SETTINGS.md`.

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

The sidebar panel module is selected in `__init__.py`. Multiple versioned JavaScript files exist in `frontend/`.

Current top-level chain in v0.22:

```text
gw-energy-pilot-v022.js
  -> gw-energy-pilot-v021.js          manual 12-mode EMS test pad
       -> gw-energy-pilot-v020.js     SOC diagnostics validity layer
            -> earlier layered frontend chain
```

The v0.22 layer also adds the GoodWe smart-meter strategy toggle and authoritative live-flow particle directions. Do not edit an older layer merely to change current runtime behaviour unless the import chain and override order have been checked.

The lower versioned files themselves import earlier layers. Do not delete or modify a versioned file merely because its name looks historical. Trace the complete import chain first.

The repository validator checks that relative frontend imports resolve and that the active frontend `VERSION` matches `manifest.json` when the entry module declares one.

## Repository checks

Before merging a substantial change, run or rely on the `Quality` GitHub Actions workflow. It performs:

- Python syntax compilation without importing the full Home Assistant runtime;
- hardware-independent unit tests from `tests/`;
- register-block coverage validation;
- JSON parsing checks;
- frontend dependency/import checks;
- active frontend/manifest version consistency;
- changelog/release-notes version coverage.

These checks complement HACS and hassfest; they do not replace runtime testing on Home Assistant or hardware validation.

## Bug-fixing workflow

When a bug is reported:

1. Reproduce the expected versus actual state from logs/diagnostics where possible.
2. Trace the live code path.
3. Check configuration and ownership state.
4. Check external prerequisites (GoodWe reachability, EMHASS health/output, Home Assistant entity state).
5. Identify the smallest root-cause fix.
6. Consider startup, reload, unavailable-device, stale-data, and migration edge cases.
7. Avoid unrelated refactors in the same fix unless they are required for correctness.

## Documentation map

- `README.md` — user-facing overview and installation.
- `docs/ARCHITECTURE.md` — runtime architecture and ownership boundaries.
- `docs/MODBUS.md` — Modbus semantics, Beta register status and change rules.
- `docs/EMS_MODES.md` — compact 12-mode GoodWe EMS control contract and current automatic strategy.
- `docs/ENTITIES.md` — Home Assistant entity/device contract.
- `docs/DEVELOPMENT.md` — contributor workflow and known technical debt.
- `docs/EMHASS_SETUP.md` — EMHASS setup/operator guidance.
- `docs/SETTINGS.md` — dedicated settings ownership, authorization and device migration.
- `docs/KNOWN_ISSUES.md` — field issues adjacent to or outside EnergyPilot runtime code.
- `docs/RELEASE_NOTES.md` — user-facing release summaries and Beta/validation status for every version.
- `CHANGELOG.md` — detailed technical release history.

## Release documentation rule

Every version bump must update both:

1. `CHANGELOG.md` with the detailed technical changes;
2. `docs/RELEASE_NOTES.md` with the user-facing summary and explicit **Beta** or validation status.

Do not release a version whose manifest/frontend version changed without updating both files.

## Definition of done

For a substantial change, check at least:

- runtime behaviour;
- failure/unavailable behaviour;
- config/options compatibility;
- entity/unique-ID/device-identifier compatibility;
- translations when user-visible entities/options change;
- dashboard impact;
- relevant unit tests;
- repository quality checks;
- README/docs impact;
- `CHANGELOG.md` impact;
- `docs/RELEASE_NOTES.md` impact and Beta status.
