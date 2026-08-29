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
v0.46 Beta
```

EMHASS is an external prerequisite. EnergyPilot integrates with EMHASS but must not install or silently replace it.

## Frontend stability contract (v0.41+, active v0.46)

- Normal Home Assistant telemetry updates must patch the existing dashboard DOM; they must not replace `main`, controls, cards or the ShadowRoot.
- A complete structural render is reserved for first initialization and genuine context/structure changes: language/user/theme, entity registry, optional-card topology or configured PV-source topology.
- The active v0.46 telemetry path must not write `scrollTop` or `scrollLeft`, capture touch pointers, cancel native vertical gestures or use a hover/render lock.
- Battery Strategy feedback must remain scoped to `.ep-v038-strategy`; plan changes must remain scoped to the Battery · Plan · Price card.
- EnergyPilot animations, transitions, moving particle layers and modal backdrop filters remain disabled unless a later release introduces a separately proven, browser-tested motion contract.
- Every frontend change affecting rendering, interaction or CSS must pass desktop Chromium, iPad WebKit touch and iPhone WebKit touch regressions before release.
- `docs/FRONTEND_STABLE_DOM.md` is the canonical architecture decision for this contract.

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

EV anti-discharge is a higher-priority directional override, but it must only block battery discharge while the EV is charging:

```text
EV active + P_batt >= -deadband -> mode 8 Battery Hold
EV active + explicit charge plan:
  Battery strategy -> mode 11 using abs(P_batt)
  Grid strategy -> mode 9 when P_grid > deadband, otherwise mode 11 fallback
  Hybrid strategy -> mode 9 when P_grid > deadband, otherwise mode 11 fallback
```

The EV feature does not control the charger and must not introduce a second fast power-control loop. EV-stop stale-plan protection remains intact. See `docs/EV_ANTI_DISCHARGE.md`.

## Persistent plan-resilience rules

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

A successful EnergyPilot optimization advances the existing `plan_revision` after the persistent-plan refresh attempt. Frontend consumers may use that revision to invalidate cached plan data deterministically; `P_batt.last_updated` remains a compatibility fallback for changes outside EnergyPilot.

See `docs/EMHASS_PLAN_RUNTIME.md` and `docs/BATTERY_PLAN_CHART.md`.

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

The verified GoodWe-synchronized Minimum SOC remains a separate hard lower boundary. When a Battery Saver profile is explicitly managed, its EMHASS `battery_maximum_state_of_charge` is part of the profile transaction.

Current hard maxima are:

```text
Mad-Steve    100%
Gold Rush     96%
Balanced      95%
Battery Saver 90%
```

v0.34 introduced two distinct economic mechanisms that remain active in v0.35:

- `weight_battery_charge` / `weight_battery_discharge`: linear anti-churn cost per battery-throughput kWh;
- `battery_stress_cost`: current EMHASS quadratic/PWL penalty for high instantaneous battery power.

All four managed profiles use:

```text
weight_battery_charge    = 2.25% × dynamic price reference
weight_battery_discharge = 2.25% × dynamic price reference
```

This prevents unrestricted micro-arbitrage even in current Mad-Steve. Profile-specific deficit/surplus thresholds and power-stress penalties remain separate from the hard maximum. Gold Rush has both a 96% hard maximum and a 96% surplus threshold by design.

Battery Saver owns nine EMHASS fields after explicit profile selection:

```text
battery_maximum_state_of_charge
battery_soc_deficit_threshold
battery_soc_deficit_cost
battery_soc_surplus_threshold
battery_soc_surplus_cost
battery_stress_cost
battery_stress_segments
weight_battery_charge
weight_battery_discharge
```

Existing unmanaged/custom values remain untouched until selection. The profile apply/rollback path must include all nine owned fields. Multi-battery profile ownership is rejected rather than guessed. See `docs/BATTERY_SAVER.md`.

## Hybrid inverter power interpretation

Only apply the shared hybrid-inverter power interpretation when the **active EMHASS configuration has `inverter_is_hybrid = true`**. In that topology PV and battery share the modeled inverter path, so `P_hybrid_inverter` can already be 15 kW while `P_batt` is lower because PV supplies the remainder.

Do not set or infer `inverter_is_hybrid` merely because the physical GoodWe reference inverter is hybrid. The EMHASS model can intentionally represent a different installation topology.

Also inspect SOC, neighboring prices and `battery_stress_cost` before concluding that the optimizer left usable power idle.

## EMHASS rules

- EMHASS must already be installed, running and configured.
- Use the configured EMHASS base URL; do not assume `localhost` works from Home Assistant Core.
- Preserve unrelated EMHASS configuration when changing selected settings.
- `/set-config` must receive the complete intended configuration.
- Treat optimizer readiness and finite numeric outputs as safety gates.
- Cost-function changes alter the optimizer objective only; never silently change GoodWe actuator strategy with them.
- Battery Saver policy changes must preserve unrelated config and roll back all EnergyPilot-owned fields on failed first application.
- The canonical EnergyPilot runtime contract is defined once in `emhass_sync.py` and contains exactly:

```text
continual_publish = true
method_ts_round = first
set_use_battery = true
```

- Both explicit EMHASS configuration synchronization and automatic pre-solve preparation must use that shared runtime contract rather than maintaining duplicate required-value lists.
- `set_use_pv` and `inverter_is_hybrid` are installation-specific EMHASS settings. Preserve explicit `false`, explicit `true` and missing values; never infer inverter topology from the GoodWe hardware model.
- `emhass_sync_api.py` must derive its managed-value list from the canonical sync key definition; do not duplicate an ownership list in the API/frontend path.

See `docs/EMHASS_CONFIG_SYNC.md`.

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
orchestrator_v044
  -> orchestrator_v033
       -> orchestrator_v031
            -> orchestrator_v026
                 -> orchestrator_v013
                      -> orchestrator_v012
                           -> orchestrator
```

Inspect all active subclasses before changing orchestration behavior.

v0.44 schedules one non-blocking startup recovery attempt 60 seconds after setup when native orchestration is enabled. Transient failures retry after 15, 30 and 60 seconds. Any successful optimization after setup cancels the remaining startup sequence; the normal periodic schedule remains authoritative after exhaustion.

## Active frontend chain

The top-level module is selected in `__init__.py`:

```text
gw-energy-pilot-v046.js
  -> gw-energy-pilot-v045.js
       -> gw-energy-pilot-v044.js
            -> gw-energy-pilot-v043.js
                 -> gw-energy-pilot-v042.js
                      -> gw-energy-pilot-v041-emhass-settings.js
                           -> gw-energy-pilot-v041.js
                                -> gw-energy-pilot-v039.js
                                     -> gw-energy-pilot-v038.js
                                          -> gw-energy-pilot-v038-runtime.js
```

v0.46 owns only release presentation and the `0.46-external-pv1` cache boundary. The existing settings module owns the external-PV switch/group interaction. v0.45 retains its integrated release presentation, v0.44 owns the bounded Optimize-now listener plus floating presentation, v0.43 touch-hover presentation, v0.42 the EMHASS settings overview, and v0.41 stable-DOM telemetry/plan/PV/static-flow presentation. Do not move GoodWe/EMS/EMHASS control semantics into a frontend release wrapper.

Historical versioned frontend files remain in the repository for dependency compatibility. Do not delete them based on filenames alone; trace imports first. Avoid new behavioral monkey-patch release layers unless a bounded compatibility fix requires one.

The Battery · Plan · Price card must keep one canonical instance. A fresh `plan_revision` should rebuild/replace it, not create a duplicate or remain stale behind the frontend cache.

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
- `docs/EMHASS_CONFIG_SYNC.md` — required EMHASS synchronization and topology ownership.
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
