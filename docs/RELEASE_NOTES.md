# GW EnergyPilot release notes

This page is the user-facing release index for GW EnergyPilot.

`CHANGELOG.md` remains the detailed technical history. This page records the validation status and operator-visible scope of each release.

## Status definitions

- **Validated** — no intentionally unconfirmed control/hardware semantics are introduced by that release and repository checks passed. This does not imply validation on every ETA-G20 model or firmware.
- **Beta** — functionality is intentionally available before broad field testing is complete. Beta behavior must be clearly bounded and reversible where practical.
- **Validated + beta diagnostics** — release behavior is otherwise validated but includes optional diagnostic values still under field correlation.
- **Historical** — older development milestone retained for release history.

## Version overview

| Version | Date | Status | Main release notes |
|---|---|---|---|
| **0.25** | 2026-08-24 | **Beta** | Consolidates three explicit Automatic Control strategies including Hybrid control, fixes persistent Today/Yesterday accounting on applicable 15 kW+ ETA/ET meters by selecting the populated extended `36104/36120` pair safely, and adds persistent 50-run EMHASS optimization history with a read-only Settings LOG page. |
| **0.24** | 2026-08-23 | **Beta** | Restores backwards-compatible direct `P_batt` control when no explicit smart-meter strategy is stored; PCC `P_grid` control remains explicit opt-in. |
| **0.23** | 2026-08-23 | **Beta** | Adds persistent native Today/Yesterday grid accounting, directional EV anti-discharge protection, persistent orchestrator `last_success`, and the final live-flow particle direction fix. |
| **0.22** | 2026-08-23 | **Beta** | Introduces optional GoodWe smart-meter/PCC control with `P_grid -> 9/10/1`, while direct battery control uses `P_batt -> 11/12/8`. |
| **0.21** | 2026-08-23 | **Beta** | Adds the manual 12-mode EMS test pad, live mode highlight and manual setpoint slider. |
| **0.20** | 2026-08-23 | **Beta** | Corrects SOC diagnostics and separates configured runtime final SOC from last-sent runtime values. |
| **0.19** | 2026-08-23 | **Beta** | Exposes current SOC, runtime SOC values, EMHASS SOC constraints/costs and GoodWe on-grid minimum SOC together. |
| **0.18** | 2026-08-23 | **Beta** | Adds admin-only, read-back-verified manual field-test writes for G20 minimum-SOC registers `45356/45358`. |
| **0.17** | 2026-08-23 | **Beta** | Adds dashboard settings, stable Home Assistant device identity migration and stateful EMHASS strategy readback. |
| **0.16** | 2026-08-23 | **Beta** | Adds optional G20 SOC-protection and extended-meter diagnostics, including UINT64 decoding. |
| **0.15** | 2026-08-23 | **Validated** | Adds stateful EMHASS profit/cost/self-consumption strategy controls while preserving unrelated EMHASS configuration. |
| **0.14** | 2026-08-23 | **Validated + beta diagnostics** | Adds optional battery SOH and charge/discharge energy accounting diagnostics from `35206-35211`. |
| **0.13** | 2026-08-23 | **Validated** | Establishes ETA-G20 load semantics, grid energy counters, 24-hour Grid history, daily totals, refresh labels and SOC guidance. |
| **0.12** | 2026-08-23 | **Historical** | Improves startup reliability, EMHASS health diagnostics, Nord Pool fallback and error visibility. |
| **0.11** | 2026-08-23 | **Historical** | Adds EMHASS min/max SOC controls, EV-stop optimization and diagnostics snapshot. |
| **0.10** | 2026-08-22 | **Historical** | Introduces the native EMHASS orchestrator, Optimize now and core manual battery actions. |
| **0.09** | 2026-08-22 | **Historical** | Adds default EMHASS output IDs, Recorder load bootstrap and publish validation. |
| **0.08** | 2026-08-22 | **Historical** | Adds draggable dashboard layout, visibility/animation controls and Automatic Control restore behavior. |
| **0.07** | 2026-08-22 | **Historical** | Adds the compact PV / Home / Grid / Battery live-flow widget. |
| **0.06** | 2026-08-22 | **Historical** | Fixes dashboard branding and frontend cache busting. |
| **0.05** | 2026-08-22 | **Historical** | Adds the built-in Home Assistant sidebar dashboard. |
| **0.04** | 2026-08-22 | **Historical** | Adds GW EnergyPilot branding and improved EMHASS setup documentation. |
| **0.03** | 2026-08-22 | **Historical** | Improves English setup/options UI, static-IP guidance and controller descriptions. |
| **0.02** | 2026-08-22 | **Historical** | Adds native GoodWe ETA telemetry over direct Modbus TCP. |
| **0.01** | 2026-08-22 | **Historical** | Initial HACS-compatible integration with EMS modes 1–12, manual control and EMHASS mapping. |

# v0.25 — Hybrid control, 15 kW+ accounting and optimization history

v0.25 combines the release-ready work that accumulated after v0.24 into one Beta release.

## Automatic Control strategies

The GOODWE settings now expose three explicit strategies.

### Battery control

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt near 0 W    -> mode 8  Battery Hold
```

This remains the backwards-compatible default when no explicit strategy exists and the legacy smart-meter boolean is absent/false.

### Grid control

```text
P_grid > +deadband -> mode 9  Grid import target
P_grid < -deadband -> mode 10 Grid export target
P_grid near 0 W    -> mode 1  GoodWe Auto / self-use
```

This retains the hardware-validated PCC behavior introduced in v0.22.

### Hybrid control

```text
P_batt < -deadband -> mode 11 Battery charge target
else P_grid < -deadband -> mode 10 Grid export target
otherwise -> mode 1 GoodWe Auto / self-use
```

Hybrid deliberately does **not** map a discharge request directly to mode 12. When the optimizer is not explicitly asking to charge and is not planning grid export, GoodWe mode 1 handles self-use balancing.

EV anti-discharge protection remains a higher-priority safety override regardless of the selected normal strategy.

## 15 kW+ grid-accounting source selection

The persistent Today/Yesterday accounting runtime can now select between the two already-known GoodWe lifetime meter layouts:

```text
extended: 36104 export / 36120 import
legacy:   36015 export / 36017 import
```

EnergyPilot prefers the extended pair only when both values are valid and the pair is populated. An optional `0/0` extended block does not displace a usable legacy pair. Once extended accounting is active, one transient missing optional read does not make the runtime flap back to legacy.

The selected source pair is persisted. A source change always establishes a new baseline before accumulation, so EnergyPilot never subtracts absolute lifetime totals from different register layouts. Existing Today/Yesterday values are preserved during a same-day migration.

On an existing installation that first switches to `36104/36120`, EnergyPilot does not invent the part of the current day that occurred before the new baseline.

The established physical lifetime Home Assistant entities keep their existing unique IDs; this release changes the input used by the derived daily accounting runtime, not those entity identities.

## Persistent optimization history

EnergyPilot now stores the newest 50 EnergyPilot-owned optimization attempts per config entry, including both successes and failures. Manual, scheduled and event-triggered runs use the same history.

Recorded diagnostics include run timing/reason, SOC inputs, current load, price source and point count, load-forecast point count, published `P_batt`, EMHASS optimize/publish HTTP status and any error message.

Home Assistant administrators can open **Settings -> LOG** inside the EnergyPilot dashboard. The viewer is read-only and uses the admin-only command:

```text
gw_energypilot/optimization_log/get
```

Optimization history is stored separately from the existing `last_success` runtime state. A failed optimization is useful log evidence but does not overwrite the previous successful timestamp. A failure to persist diagnostic history is non-fatal to the optimization/control path.

## Safety and compatibility

- no new GoodWe register definitions;
- no Modbus read-block changes;
- EMS remains `47511` mode / `47512` non-negative mode-specific setpoint;
- write ordering remains `47512 -> wait -> 47511`;
- manual EMS modes remain direct operator commands;
- entity unique IDs and stable device identity remain unchanged;
- EV anti-discharge remains active as a safety override;
- v0.25 remains **Beta** pending broader field exposure of Hybrid control, extended-meter accounting selection and persistent optimization history.
