# GW EnergyPilot release notes

This page is the user-facing release index for every GW EnergyPilot version.

`CHANGELOG.md` remains the detailed technical history. This page records the current validation status and the main operator-visible change in each release.

## Status definitions

- **Validated** — no intentionally unconfirmed control/hardware semantics are introduced by that release and the repository checks passed. This does not imply validation on every ETA-G20 model or firmware.
- **Beta** — functionality is intentionally available before broad field testing is complete. Beta behavior must be clearly bounded and reversible where practical.
- **Validated + beta diagnostics** — the release behavior is otherwise validated but includes optional diagnostic values still under field correlation.
- **Historical** — older development milestone retained for release history; current support/testing focuses on the latest release.

## Version overview

| Version | Date | Status | Main release notes |
|---|---|---|---|
| **0.24** | 2026-08-23 | **Beta** | Fixes the v0.22/v0.23 automatic-control compatibility regression: when no explicit GoodWe smart-meter strategy is stored, Automatic Control again follows EMHASS `P_batt` through modes 11/12/8. PCC `P_grid` control through modes 9/10/1 remains available only when explicitly enabled. |
| **0.23** | 2026-08-23 | **Beta** | Consolidated release: persistent native Today/Yesterday grid accounting from canonical GoodWe lifetime counters; directional EV anti-discharge protection that still allows an explicit home-battery charge plan; persistent orchestrator `last_success` across reload/restart; and the final live-flow particle double-reversal fix. Existing v0.22 PCC 9/10 control remains unchanged. |
| **0.22** | 2026-08-23 | **Beta** | Promotes hardware-validated GoodWe smart-meter/PCC modes into an optional automatic strategy. Smart-meter ON maps EMHASS `P_grid` to modes 9/10/1; OFF restores direct `P_batt` control through modes 11/12/8. |
| **0.21** | 2026-08-23 | **Beta** | Adds the manual 12-mode EMS test pad, live mode highlight, hover descriptions and a `0..max_power` manual setpoint slider. |
| **0.20** | 2026-08-23 | **Beta** | Corrects SOC diagnostics by separating configured runtime final SOC from last-sent runtime values and by exposing invalid raw EMHASS SOC configuration safely. |
| **0.19** | 2026-08-23 | **Beta** | Makes current SOC, runtime SOC values, EMHASS SOC constraints/costs and GoodWe on-grid minimum SOC visible together. |
| **0.18** | 2026-08-23 | **Beta** | Adds admin-only, read-back-verified manual field-test writes for G20 minimum-SOC registers `45356/45358`. |
| **0.17** | 2026-08-23 | **Beta** | Adds EP/EMHASS/GOODWE dashboard settings, stable Home Assistant device identity migration, stateful EMHASS strategy readback and enabled Beta SOC Diagnostic sensors. |
| **0.16** | 2026-08-23 | **Beta** | Ships optional G20 SOC-protection and extended-meter candidate diagnostics, including UINT64 decoding, to the active tester group. |
| **0.15** | 2026-08-23 | **Validated** | Adds stateful EMHASS profit/cost/self-consumption strategy controls while preserving unrelated EMHASS configuration. |
| **0.14** | 2026-08-23 | **Validated + beta diagnostics** | Adds optional battery SOH and charge/discharge energy accounting diagnostics from `35206-35211`. |
| **0.13** | 2026-08-23 | **Validated** | Establishes ETA-G20 load semantics, canonical grid energy counters, 24-hour Grid history, daily totals, refresh labels and SOC guidance. |
| **0.12** | 2026-08-23 | **Historical** | Improves startup reliability, EMHASS health diagnostics, Nord Pool fallback and error visibility. |
| **0.11** | 2026-08-23 | **Historical** | Adds EMHASS min/max SOC controls, EV-stop optimization and the diagnostics snapshot. |
| **0.10** | 2026-08-22 | **Historical** | Introduces the native EMHASS orchestrator, Optimize now and core manual battery actions. |
| **0.09** | 2026-08-22 | **Historical** | Adds default EMHASS output IDs, Recorder load bootstrap and publish validation. |
| **0.08** | 2026-08-22 | **Historical** | Adds draggable dashboard layout, visibility/animation controls and Automatic Control restore behavior. |
| **0.07** | 2026-08-22 | **Historical** | Adds the compact PV / Home / Grid / Battery live-flow widget. |
| **0.06** | 2026-08-22 | **Historical** | Fixes dashboard branding and frontend cache busting. |
| **0.05** | 2026-08-22 | **Historical** | Adds the built-in Home Assistant sidebar dashboard. |
| **0.04** | 2026-08-22 | **Historical** | Adds GW EnergyPilot branding and improved EMHASS setup documentation. |
| **0.03** | 2026-08-22 | **Historical** | Improves English setup/options UI, static-IP guidance and controller descriptions. |
| **0.02** | 2026-08-22 | **Historical** | Adds native GoodWe ETA telemetry over direct Modbus TCP. |
| **0.01** | 2026-08-22 | **Historical** | Initial HACS-compatible integration with EMS modes 1–12, manual control, EMHASS mapping and EV coordination groundwork. |

# v0.24 — Automatic-control compatibility fix

v0.24 is a focused control regression release. It does not introduce new GoodWe register semantics or a new actuator primitive.

## What was wrong

v0.22 introduced **GoodWe smart meter active** and set the missing-value default to ON. Existing installations created before that setting existed therefore silently started using the `P_grid` PCC strategy after upgrading, even though the operator had never selected it.

With PCC control active, a plan such as:

```text
P_batt = +962 W   (EMHASS wants battery discharge)
P_grid ≈ 0 W      (inside the configured grid deadband)
```

was intentionally translated by the v0.22/v0.23 PCC strategy to:

```text
mode 1
setpoint 0 W
command grid_zero_auto
```

That is internally consistent with the PCC strategy, but it is not backwards-compatible with an installation that previously expected `P_batt` to own battery direction.

## v0.24 behavior

When `use_goodwe_smart_meter` is **missing** or explicitly `false`:

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt near 0 W    -> mode 8  Battery Hold
```

When `use_goodwe_smart_meter` is explicitly `true`:

```text
P_grid > +deadband -> mode 9  Grid import target
P_grid < -deadband -> mode 10 Grid export target
P_grid near 0 W    -> mode 1  GoodWe Auto / self-use
```

This preserves the validated PCC feature while making it an explicit opt-in instead of a silent upgrade behavior.

## Field-log review

The Home Assistant log supplied with this regression report contains no GW EnergyPilot runtime exception, Modbus transport error or failed EnergyPilot EMS write that explains the mode mismatch. The evidence is consistent with a controller strategy selection problem rather than a failed `47511/47512` write.

The same log does contain a separate Home Assistant script validation error for a legacy script named **GoodWe ETA EMS normaal**. Home Assistant rejected its YAML structure and disabled it. That script is not part of the GW EnergyPilot integration and is not the cause of this v0.24 controller fix.

Other Audi, OpenAI dependency, ONVIF, template-sensor and unrelated custom-integration errors in that startup log are outside this release scope.

## Compatibility and safety

- no new GoodWe register addresses;
- no Modbus telemetry block changes;
- EMS registers remain `47511` and `47512`;
- write order remains power/setpoint first, brief wait, then mode;
- explicit Smart Meter/PCC opt-in remains unchanged;
- manual EMS commands remain direct operator commands;
- entity unique IDs and device identity remain unchanged;
- persistent grid accounting and orchestrator runtime stores are unchanged.

v0.24 remains **Beta** while this corrected upgrade/default behavior receives field verification.

# v0.23 — Complete Beta release

v0.23 combines the queued post-v0.22 work into one release instead of shipping several partial intermediate versions.

## 1. Persistent grid accounting

The physical source of truth remains unchanged:

```text
36017 = lifetime grid import
36015 = lifetime grid export
```

EnergyPilot now owns one persistent accounting runtime per config entry. It stores the last observed lifetime values and accumulates only positive deltas into native daily counters:

```text
grid_energy_imported_today
grid_energy_exported_today
```

Both use Home Assistant energy semantics and expose the completed previous local day through `last_period`.

A decrease in a lifetime counter causes a re-baseline; EnergyPilot does not invent negative energy or guess reset semantics.

For existing installations, Recorder may be used **once** after the first fresh GoodWe poll to recover lifetime-counter values around the previous/current local-midnight boundaries. Recorder is not part of the live accounting loop. If boundary history is unavailable, accounting starts from the current physical counters without fabricating historical energy.

The Grid card and Grid modal use these native daily entities. The existing 24-hour signed power graph remains Recorder-backed because it is historical visualization.

This accounting runtime is intentionally the future insertion point for interval-based financial accounting:

```text
import_cost    += delta_import_kWh * effective_buy_price
export_revenue += delta_export_kWh * effective_sell_price
```

See `docs/ACCOUNTING.md`.

## 2. EV anti-discharge protection

The former broad EV coordination behavior is clarified as **EV anti-discharge protection** while retaining the existing stored config key for backwards compatibility.

When EV charging is active:

```text
P_batt requests discharge  -> mode 8 Battery Hold
P_batt is neutral          -> mode 8 Battery Hold
P_batt requests charge     -> mode 11 Battery charge allowed
```

The EV charger or external charging service remains the owner of the EV session. EnergyPilot only protects the home battery from becoming the EV's energy source.

The direct mode-11 charge override is deliberate even when normal Automatic Control uses PCC modes 9/10/1: a changing EV load must not turn a stale site-level target into home-battery discharge.

When native orchestration is enabled, EV stop keeps the existing fresh-plan protection: EnergyPilot waits for a new optimization before normal automatic execution resumes.

See `docs/EV_ANTI_DISCHARGE.md`.

## 3. Persistent `Last success`

The orchestrator's successful optimize/publish timestamp is no longer memory-only.

v0.23 stores the last successful **EnergyPilot-owned** optimize + publish timestamp per config entry using Home Assistant storage:

```text
gw_energypilot.runtime.<config_entry_id>
```

A config-entry reload or Home Assistant restart restores that timestamp, so the dashboard no longer returns to **Last success: Never** after a previously successful EnergyPilot run.

Only a complete successful EnergyPilot-owned cycle updates the value. A later failed optimization does not erase the previous success. Invalid or timezone-less stored timestamps are ignored safely.

See `docs/RUNTIME_STATE.md`.

## 4. Live-flow direction final fix

The layered frontend had two direction mechanisms at the same time: geometry-correct Forward/Reverse keyframes plus `animation-direction: reverse` overrides. That could double-reverse a flow such as grid import even while the Grid node correctly said **Importing**.

v0.23 makes the geometry-correct animation keyframe authoritative by forcing the particle animation direction itself to normal.

Expected visual directions:

```text
PV production         -> hub
Grid import           -> hub
Grid export           hub -> grid
Battery charging      hub -> battery
Battery discharging   battery -> hub
House consumption     hub -> house
```

This is frontend-only; no GoodWe sign convention or power value changes.

## Existing v0.22 automatic control remains

GoodWe smart meter active = ON:

```text
P_grid > +deadband -> mode 9  Grid import target
P_grid < -deadband -> mode 10 Grid export target
P_grid near 0 W    -> mode 1  GoodWe Auto / self-use
```

GoodWe smart meter active = OFF:

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt near 0 W    -> mode 8  Battery Hold
```

The reference ETA-G20 hardware validation behind this mapping remains the v0.22 evidence set; v0.23 does not change the EMS register definitions or the `47512 -> wait -> 47511` write order.

## Why v0.23 is still Beta

The release is intentionally Beta because these areas still need broader field exposure:

- persistent Today/Yesterday accounting across real restarts and midnight rollovers;
- EV anti-discharge behavior with different charger/service ownership patterns;
- the final live-flow visual correction across browsers/clients;
- the already-Beta automatic mode-9/mode-10 strategy across additional ETA-G20 firmware/hardware combinations.

The rollback boundary remains clear: disabling **GoodWe smart meter active** restores direct `P_batt` control through modes 11/12/8.

## Safety / compatibility boundary

- no new GoodWe register definitions are introduced by the v0.23 consolidation;
- no Modbus read-block change is required for the new accounting runtime;
- EMS registers remain `47511` and `47512`;
- EMS write order remains power first, brief wait, then mode;
- existing lifetime grid-energy entity unique IDs remain unchanged;
- new daily accounting entities use new deterministic unique IDs;
- Beta `36104/36120` counters remain diagnostics and are not promoted to canonical accounting;
- device identity remains `(DOMAIN, config_entry_id)`;
- manual EMS commands remain direct operator commands and are not remapped by the automatic strategy.

## Release validation

The release is merged only after the exact final head passes:

- repository **Quality** workflow, including unit tests and repository invariants;
- **HACS validation**;
- Home Assistant **hassfest**.

## Release-note maintenance rule

Every version bump must update both:

1. `CHANGELOG.md` — detailed technical changes;
2. `docs/RELEASE_NOTES.md` — user-facing summary and explicit Beta/validation status.

Do not present unconfirmed hardware semantics as validated merely because static CI is green.
