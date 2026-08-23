# GW EnergyPilot — AI development instructions

This file defines working rules for AI coding assistants and contributors. The repository is the source of truth for current behavior.

## Source of truth

- Always inspect the current repository before proposing or applying a change.
- Never reconstruct current code from an older chat, pasted fragment, or previous release.
- Repository code and current documentation take precedence over conversation history.
- If documentation and code disagree, treat code as current behavior and fix the documentation mismatch.

## Current scope

GW EnergyPilot is an unofficial Home Assistant custom integration for local GoodWe ETA-G20 telemetry, EMS control, EMHASS orchestration, optional Nord Pool pricing, optional EV anti-discharge protection, persistent grid accounting and a built-in dashboard.

Primary tested inverter:

```text
GoodWe GW15K-ETA-G20
```

Current release line:

```text
v0.23 Beta
```

EMHASS is an external prerequisite. EnergyPilot may integrate with EMHASS but must not install or silently replace it.

## Before changing code

1. Read the live files involved in the requested behavior.
2. Trace callers, listeners, config/options, entities and frontend dependencies.
3. Identify the root cause before rewriting code.
4. Prefer the smallest robust change.
5. Preserve working behavior outside the requested scope.
6. Check backwards compatibility for entity unique IDs, device identifiers, config entries, storage keys and Recorder/statistics history.
7. Update documentation when architecture, register semantics, public entities, persistent state or operator workflow changes.

## Home Assistant rules

- Follow current Home Assistant development conventions.
- Keep config-entry setup non-blocking where practical.
- Do not hold Home Assistant startup on slow or unavailable Modbus/EMHASS I/O.
- Use coordinator-backed telemetry for polled inverter data.
- Keep unique IDs stable unless an explicit migration exists.
- Current device identity is `(DOMAIN, config_entry_id)`; do not revert to mutable `host:slave` identity.
- Prefer config/options over hard-coded Home Assistant entity IDs.
- Do not create duplicate entities or parallel implementations for the same concept without a migration plan.
- Persistent runtime history belongs in Home Assistant `Store`, not in user configuration.

## Modbus rules

- Never invent or guess GoodWe register addresses, data types, scales or sign conventions.
- `custom_components/gw_energypilot/registers.py` is the canonical register/read-block source.
- `client.py` imports the canonical read blocks; do not recreate them locally.
- Register changes require evidence from tested hardware, vendor documentation, maintained upstream implementations or repeatable diagnostics.
- Preserve tested signs unless evidence proves them wrong:

```text
GoodWe grid meter power
  negative = import
  positive = export

battery power
  negative = charging
  positive = discharging

EMHASS P_grid
  positive = planned import
  negative = planned export
```

- EMS control uses `47511` for mode and `47512` for the non-negative mode-specific setpoint magnitude.
- Keep the established write order:

```text
write 47512
brief wait
write 47511
```

- An incorrect EMS write can move significant real power; control changes require explicit tests and hardware evidence.

## Beta register policy

Beta means **not yet extensively field-tested**.

For unconfirmed hardware semantics:

- keep candidate registers optional;
- keep them read-only unless a separately reviewed/verified write path exists;
- do not feed Beta values into automatic EMS control or canonical accounting;
- label Beta values clearly in UI/entities/docs;
- collect model/firmware and matching SolarGo/SEMS+ evidence;
- promote semantics only through an intentional code/docs change.

Current Beta exceptions are documented in `docs/MODBUS.md` and `docs/RELEASE_NOTES.md`.

## Control ownership

Automatic and manual control must remain explicit.

- Automatic Control OFF returns GoodWe to mode `1`, setpoint `0 W`.
- Manual actions take manual ownership before writing an EMS command.
- Manual mode numbers always mean exactly the selected GoodWe mode; automatic strategy settings must never remap manual commands.
- Do not introduce competing automatic feedback loops over the same EMS actuator.

### Automatic actuator strategy

With **GoodWe smart meter active = ON**:

```text
P_grid > +deadband  -> mode 9  Grid import target
P_grid < -deadband  -> mode 10 Grid export target
P_grid near 0 W     -> mode 1  Auto / self-use
```

GoodWe closes the fast loop against its own smart meter/PCC. `P_batt` remains a required plan-validity/diagnostic output.

With **GoodWe smart meter active = OFF**:

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt near 0 W    -> mode 8  Battery Hold
```

This fallback must remain usable when `P_grid` is missing/unavailable.

### EV anti-discharge protection

The EV feature protects battery direction; it does not control the EV charger.

During EV charging:

```text
P_batt > +deadband -> mode 8  Battery Hold
P_batt near 0 W    -> mode 8  Battery Hold
P_batt < -deadband -> mode 11 Battery charge allowed
```

The stored option name `enable_ev_coordination` remains for backwards compatibility. User-facing terminology is **EV anti-discharge protection**.

If native orchestration is enabled, EV stop waits for a fresh optimization before normal automatic execution resumes.

See `docs/EV_ANTI_DISCHARGE.md`.

## EMHASS rules

- EMHASS must already be installed, running and configured.
- Use the configured EMHASS base URL; do not assume `localhost` works from Home Assistant Core.
- Preserve unrelated EMHASS configuration when changing selected settings.
- `/set-config` must receive the complete intended configuration.
- Do not execute stale `P_batt`/`P_grid` after a condition that requires re-optimization.
- Treat optimizer readiness and finite numeric outputs as safety gates.
- Cost-function changes alter the optimizer objective only; never silently change the GoodWe actuator strategy with them.

## Persistent runtime state

Configuration and runtime history are deliberately separate.

`runtime_store.py` owns small EnergyPilot runtime evidence that must survive reload/restart.

Current key:

```text
gw_energypilot.runtime.<config_entry_id>
```

`last_success` is restored before active orchestrator setup and persisted only after a complete EnergyPilot-owned optimize + publish cycle succeeds.

Rules:

- do not put user configuration in this Store;
- failed later optimizations must not erase a previous successful timestamp;
- stored datetimes must be timezone-aware;
- invalid persisted data must fail safe.

See `docs/RUNTIME_STATE.md`.

## Persistent grid accounting

v0.23 adds `GWEnergyPilotAccounting` and `accounting_model.py`.

Canonical physical inputs remain:

```text
36017 = lifetime grid import
36015 = lifetime grid export
```

Rules:

- derive only positive lifetime-counter deltas;
- re-baseline on counter decreases;
- local-midnight rollover moves current totals to previous-day totals;
- persist derived daily state through Home Assistant storage;
- Recorder is optional bootstrap/history infrastructure, not the live accounting source;
- Beta `36104/36120` counters must not replace the canonical inputs without explicit promotion evidence;
- future cost/revenue accounting must consume the same physical energy deltas rather than reconstructing energy independently in the frontend.

See `docs/ACCOUNTING.md`.

## Settings APIs

Dashboard configuration uses:

```text
settings_api.py
smart_meter_api.py
beta_soc_api.py
```

Rules:

- dashboard write APIs remain admin-only;
- the existing Home Assistant `ConfigEntry` is the single configuration source;
- do not add a parallel settings database;
- GoodWe connection changes must be validated before storage;
- smart-meter actuator selection is GoodWe/config-entry data, not EMHASS config;
- preserve stable device identity and entity unique IDs.

See `docs/SETTINGS.md`.

## Active orchestrator chain

Do not assume `orchestrator.py` alone is active:

```text
orchestrator_v013.GWEnergyPilotOrchestrator
  -> orchestrator_v012.GWEnergyPilotOrchestrator
       -> orchestrator.GWEnergyPilotOrchestrator
```

`orchestrator_v013.py` also owns v0.23 runtime-store restore/save timing.

Until intentionally consolidated, inspect all three layers for orchestration changes.

## Active frontend chain

The active top-level module is selected in `__init__.py`.

v0.23 upper chain:

```text
gw-energy-pilot-v023.js
  -> gw-energy-pilot-v022-flow-direction.js
       -> gw-energy-pilot-v022.js
            -> gw-energy-pilot-v021.js
                 -> earlier layered frontend files
```

Responsibilities:

- v0.23: persistent Grid Today/Yesterday UI + release badge;
- flow-direction overlay: remove double reversal;
- v0.22: Smart Meter strategy UI + PCC/battery target labeling;
- v0.21: manual 12-mode EMS test pad.

Do not delete versioned frontend files based on filename alone. Trace the import chain first.

Current visual flow contract:

```text
PV production         -> hub
Grid import           -> hub
Grid export           hub -> grid
Battery charging      hub -> battery
Battery discharging   battery -> hub
House consumption     hub -> house
```

## Repository checks

Substantial changes must pass the `Quality` workflow:

```text
python -m compileall -q custom_components/gw_energypilot scripts tests
python -m unittest discover -s tests -v
python scripts/validate_repo.py
```

Release PRs also require green HACS validation and hassfest on the exact final head.

The repository validator checks register coverage, JSON validity, frontend imports, active frontend/manifest version agreement and release-note/changelog version coverage.

Static CI proves repository consistency, not GoodWe hardware meaning.

## Documentation map

- `README.md` — user-facing overview/current behavior.
- `docs/ARCHITECTURE.md` — runtime architecture/ownership.
- `docs/MODBUS.md` — register/control semantics and evidence policy.
- `docs/EMS_MODES.md` — exact modes 1–12.
- `docs/EV_ANTI_DISCHARGE.md` — EV battery-direction protection.
- `docs/ACCOUNTING.md` — persistent grid accounting.
- `docs/RUNTIME_STATE.md` — persistent EnergyPilot runtime history.
- `docs/EMHASS_SETUP.md` — EMHASS setup/operator guidance.
- `docs/SETTINGS.md` — settings ownership/security.
- `docs/ENTITIES.md` — Home Assistant entity/device contract.
- `docs/KNOWN_ISSUES.md` — field issues outside/adjacent to EnergyPilot.
- `docs/RELEASE_NOTES.md` — per-version status/user-facing notes.
- `CHANGELOG.md` — detailed technical history.

## Release documentation rule

Every version bump must update both:

1. `CHANGELOG.md`;
2. `docs/RELEASE_NOTES.md` with explicit Beta/Validated status.

Also update README/current architecture when runtime behavior or active frontend changes.

## Definition of done

For a substantial change verify at least:

- runtime behavior;
- unavailable/failure behavior;
- config/options/storage compatibility;
- entity unique IDs and device identity;
- persistent-state migration/rollback behavior;
- translations for user-visible changes;
- dashboard impact;
- relevant unit tests;
- Quality + HACS + hassfest for releases;
- README/architecture/changelog/release notes;
- no undocumented register/control semantic changes.
