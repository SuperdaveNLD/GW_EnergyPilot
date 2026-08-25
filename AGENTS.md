# GW EnergyPilot — AI development instructions

This file defines working rules for AI coding assistants and contributors. The repository is the source of truth for current behavior.

## Source of truth

- Always inspect the current repository before proposing or applying a change.
- Never reconstruct current code from an older chat, pasted fragment or previous release.
- Repository code and current documentation take precedence over conversation history.
- If documentation and code disagree, treat code as current behavior and fix the documentation mismatch.

## Current scope

GW EnergyPilot is an unofficial Home Assistant custom integration for local GoodWe ETA-G20 telemetry, EMS control, EMHASS orchestration, optional runtime pricing, EV anti-discharge protection, persistent grid accounting, persistent EMHASS plan resilience and a built-in dashboard.

Primary tested inverter:

```text
GoodWe GW15K-ETA-G20
```

Current release line:

```text
v0.33 Beta
```

EMHASS is an external prerequisite. EnergyPilot integrates with EMHASS but must not install or silently replace it.

## Before changing code

1. Read the live files involved in the requested behavior.
2. Trace callers, listeners, config/options, entities, persistence and frontend dependencies.
3. Identify the root cause before rewriting code.
4. Prefer the smallest robust change.
5. Preserve working behavior outside the requested scope.
6. Check backwards compatibility for entity unique IDs, device identifiers, config entries, storage keys and Recorder/statistics history.
7. Update documentation when architecture, register semantics, optimizer policy, public entities, persistent state or operator workflow changes.

## Home Assistant rules

- Follow current Home Assistant development conventions.
- Keep config-entry setup non-blocking where practical.
- Do not hold Home Assistant startup on slow or unavailable Modbus/EMHASS I/O.
- Use coordinator-backed telemetry for polled inverter data.
- Keep unique IDs stable unless an explicit migration exists.
- Current device identity is `(DOMAIN, config_entry_id)`; do not revert to mutable `host:slave` identity.
- Prefer config/options over hard-coded Home Assistant entity IDs.
- Do not create duplicate entities or parallel implementations for the same concept without a migration plan.
- Persistent runtime/history belongs in Home Assistant `Store`, not in user configuration.

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

### Automatic strategies

Battery:

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt near 0 W    -> mode 8 Battery Hold
```

Grid:

```text
P_grid > +deadband -> mode 9 Grid import target
P_grid < -deadband -> mode 10 Grid export target
P_grid near 0 W    -> mode 1 GoodWe Auto / self-use
```

Hybrid:

```text
P_grid > +deadband -> mode 9 using abs(P_grid)
else P_batt > +deadband -> mode 12 using abs(P_batt)
else P_batt near 0 W -> mode 8
otherwise -> mode 1 GoodWe Auto / self-use
```

Hybrid is deliberately asymmetric: buy/import is PCC mode 9; sell/discharge is direct battery mode 12. A battery-charge plan without planned grid import falls through to mode 1 so GoodWe can absorb local PV.

Legacy compatibility remains: missing/false old smart-meter flag -> Battery; explicit true -> Grid.

EV anti-discharge is a higher-priority directional override. See `docs/EV_ANTI_DISCHARGE.md`.

## v0.33 plan-resilience rules

EMHASS remains the canonical plan owner. EnergyPilot mirrors the official `GET /api/v1/plan` result in:

```text
gw_energypilot.plan.<config_entry_id>
```

This is a resilience mirror only.

Current control source order:

```text
finite live configured HA P_batt/P_grid
-> current still-valid persistent-plan point
-> unavailable/wait
```

Rules:

- explicit live non-ready optimizer status remains authoritative;
- only missing/unknown/unavailable optimizer publication may be bridged by a valid mirrored plan;
- the plan must have an inferred timestep and explicit `valid_until`;
- never extrapolate the last plan row after expiry;
- a failed refresh must not delete a still-valid mirror;
- do not create duplicate P_batt/P_grid entities or a second optimization engine.

See `docs/EMHASS_PLAN_RUNTIME.md`.

## EMHASS output freshness

Do not use `State.last_updated` alone as proof of a fresh publish. Repeated state/attributes can be reported without advancing it.

Current contract:

```text
State.last_reported primary
State.last_updated compatibility fallback
+ finite numeric output
+ optimizer ready
```

## Battery Saver policy

Public modes are exactly:

```text
Mad-Steve
Gold Rush
Balanced
Battery Saver
```

Hard Minimum/Maximum SOC is separate from soft Battery Saver preferences.

v0.33 uses two distinct mechanisms:

- `weight_battery_charge` / `weight_battery_discharge`: linear anti-churn cost per battery-throughput kWh;
- `battery_stress_cost`: current EMHASS quadratic/PWL penalty for high instantaneous battery power.

All four managed profiles use:

```text
weight_battery_charge    = 1.5% × dynamic price reference
weight_battery_discharge = 1.5% × dynamic price reference
```

This prevents unrestricted micro-arbitrage even in current Mad-Steve. Gold Rush uses a **5–96% soft SOC zone**. Do not silently turn 96% into a hard maximum.

Battery Saver owns eight EMHASS fields after explicit profile selection:

```text
battery_soc_deficit_threshold
battery_soc_deficit_cost
battery_soc_surplus_threshold
battery_soc_surplus_cost
battery_stress_cost
battery_stress_segments
weight_battery_charge
weight_battery_discharge
```

Existing unmanaged/custom values remain untouched until selection. Multi-battery profile ownership is rejected rather than guessed. See `docs/BATTERY_SAVER.md`.

## Hybrid inverter power interpretation

Before changing limits because `P_batt` is below 15 kW, check the shared hybrid inverter constraint. PV and battery share the inverter path in the current EMHASS hybrid model. `P_hybrid_inverter` can already be 15 kW while `P_batt` is lower because PV supplies the remainder.

Also inspect SOC, neighboring prices and `battery_stress_cost` before concluding that the optimizer left usable power idle.

## EMHASS rules

- EMHASS must already be installed, running and configured.
- Use the configured EMHASS base URL; do not assume `localhost` works from Home Assistant Core.
- Preserve unrelated EMHASS configuration when changing selected settings.
- `/set-config` must receive the complete intended configuration.
- Treat optimizer readiness and finite numeric outputs as safety gates.
- Cost-function changes alter the optimizer objective only; never silently change GoodWe actuator strategy with them.
- Battery Saver policy changes must preserve unrelated config and roll back all EnergyPilot-owned fields on failed first application.

## Persistent state

Configuration and runtime history are deliberately separate.

Current EnergyPilot stores include:

```text
gw_energypilot.runtime.<config_entry_id>
gw_energypilot.accounting.<config_entry_id>
gw_energypilot.optimization_log.<config_entry_id>
gw_energypilot.plan.<config_entry_id>
```

The debug session is deliberately memory-only and is not persisted.

## Persistent grid accounting

Daily grid accounting may select one coherent source pair:

```text
preferred when populated/valid: 36104 export / 36120 import
fallback:                       36015 export / 36017 import
```

A source change must re-baseline before accumulation. Never subtract absolute counters from different layouts. Recorder is optional bootstrap/history infrastructure, not the live accounting source.

See `docs/ACCOUNTING.md`.

## Active orchestrator chain

Do not assume `orchestrator.py` alone is active:

```text
orchestrator_v033
  -> orchestrator_v031
       -> orchestrator_v026
            -> orchestrator_v013
                 -> orchestrator_v012
                      -> orchestrator
```

Inspect all active subclasses before changing orchestration behavior.

## Active frontend chain

The top-level module is selected in `__init__.py`:

```text
gw-energy-pilot-v033.js
  -> gw-energy-pilot-v031-battery-saver.js
       -> gw-energy-pilot-v031-window-controls.js
            -> gw-energy-pilot-v031.js
                 -> gw-energy-pilot-v030.js
                      -> earlier active layers
```

Do not delete versioned frontend files based on filename alone. Trace imports first. Avoid new behavioral monkey-patch layers unless a bounded compatibility fix requires one.

The Battery · Plan · Price card must keep one canonical instance. A fresh plan should rebuild/replace it, not create a duplicate or remain stale behind the frontend cache.

## Repository checks

Substantial changes must pass the `Quality` workflow:

```text
python -m compileall -q custom_components/gw_energypilot scripts tests
python -m unittest discover -s tests -v
python scripts/validate_repo.py
```

Release PRs also require green HACS validation and hassfest on the exact final head.

Static CI proves repository consistency, not GoodWe hardware meaning or browser rendering.

## Documentation map

- `README.md` — user-facing overview/current behavior.
- `docs/ARCHITECTURE.md` — runtime architecture/ownership.
- `docs/DEVELOPMENT.md` — maintainer workflow/current active chain.
- `docs/MODBUS.md` — register/control semantics and evidence policy.
- `docs/EMS_MODES.md` — exact modes 1–12.
- `docs/EMHASS_PLAN_RUNTIME.md` — persistent plan resilience.
- `docs/BATTERY_SAVER.md` — optimizer profile ownership/tuning.
- `docs/EV_ANTI_DISCHARGE.md` — EV battery-direction protection.
- `docs/ACCOUNTING.md` — persistent grid accounting.
- `docs/RUNTIME_STATE.md` — persistent EnergyPilot runtime history.
- `docs/EMHASS_SETUP.md` — EMHASS setup/operator guidance.
- `docs/SETTINGS.md` — settings ownership/security.
- `docs/ENTITIES.md` — Home Assistant entity/device contract.
- `docs/RELEASE_NOTES.md` — per-version status/user-facing notes.
- `CHANGELOG.md` — detailed technical history.

## Definition of done

For a substantial change verify at least:

- runtime behavior;
- unavailable/failure behavior;
- config/options/storage compatibility;
- entity unique IDs and device identity;
- persistent-state migration/rollback behavior;
- translations/copy for user-visible changes;
- dashboard impact;
- relevant unit tests;
- Quality + HACS + hassfest for releases;
- README/architecture/development/changelog/release notes;
- no undocumented register/control semantic changes.
