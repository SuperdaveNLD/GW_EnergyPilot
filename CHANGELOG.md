# Changelog

All notable changes to GW EnergyPilot are documented here.

## [0.16] - 2026-08-23

### Added

- Read-only beta diagnostics for candidate GoodWe SOC-protection registers `45356`, `45358` and `47500`.
- Read-only beta diagnostics for the extended 15 kW+ smart-meter lifetime counters at `36104` (export) and `36120` (import).
- Unsigned 64-bit Modbus decoding for the extended meter counters.
- A dedicated BETA diagnostics block and Copy beta diagnostics action in the dashboard.
- Unit tests for UINT64 decoding, four-word register coverage and beta optional-read block coverage.

### Changed

- Candidate registers are now shipped to the small active tester group instead of remaining isolated in draft branches.
- Every candidate remains optional and read-only; unsupported firmware cannot make normal required telemetry unavailable.
- Legacy `36015/36017` remain the canonical grid-energy source until the extended counters are validated against physical SEMS lifetime totals.

### Safety boundary

- `45356`, `45358` and `47500` are not used by controller logic and are never written by EnergyPilot.
- `36104/36120` are diagnostics only and do not alter Recorder-facing grid energy entities.
- EMS modes, setpoints, sign conventions, write ordering and automatic-control ownership are unchanged.

## [0.15] - 2026-08-23

### Added

- Three native EMHASS cost-function buttons for `profit`, `cost` and `self-consumption`.
- Matching one-touch strategy controls in the EnergyPilot EMHASS dashboard card.
- Regression tests proving selected EMHASS configuration patches preserve unrelated settings.

### Changed

- Selecting an EMHASS cost function reads the complete active configuration, changes only `costfun`, writes the complete configuration back through `/set-config`, and immediately runs/publishes a fresh optimization.
- Dashboard frontend moved to `gw-energy-pilot-v015.js`, layering the new strategy controls on top of the existing v0.14 battery diagnostics.

### Notes

- GoodWe Automatic Control remains `P_batt`-driven and still uses the existing EMS modes 8, 11 and 12.
- No GoodWe register definitions, sign conventions, EMS write ordering or control ownership behaviour are changed by v0.15.
- Candidate SOC-protection and extended-meter register work remained in draft validation PRs until v0.16.

## [0.14] - 2026-08-23

### Added

- Optional GoodWe battery energy accounting telemetry from registers `35206` (lifetime charge), `35208` (today charge), `35209` (lifetime discharge), and `35211` (today discharge).
- Battery SOH and charge/discharge energy values in the Diagnostics snapshot and copied support report.
- Internal battery accounting groundwork for later cost, revenue, throughput and degradation calculations.

### Changed

- Battery accounting telemetry is intentionally kept out of the normal dashboard and exposed only through diagnostics for now.
- The `35206-35211` telemetry block is optional so unsupported firmware does not make the main inverter telemetry unavailable.
- No estimated cycle count or equivalent-full-cycle value is generated yet; EnergyPilot will only add that once usable battery capacity/model semantics are validated.
- Dashboard frontend moved to `gw-energy-pilot-v014.js`.

## [0.13] - 2026-08-23

### Added

- Tested-hardware documentation centered on the **GoodWe GW15K-ETA-G20** and a request for model/firmware feedback from other ETA-G20 users.
- Native GoodWe smart-meter cumulative grid energy sensors from registers `36015` (export) and `36017` (import).
- Interactive Grid card with a Recorder-backed previous-24-hour power graph.
- Today and yesterday grid import/export energy totals using Recorder statistic changes.
- Lifetime GoodWe grid import/export totals in the Grid detail view.
- Refresh-frequency labels on dashboard cards.
- SOC guidance `i` popup explaining the recommended 5–95% normal on-grid operating range and the separate GoodWe/SEMS+/BMS protection layers.
- Dashboard groundwork for future Nord Pool cost/revenue accounting without repeated history scans.

### Changed

- Home card again treats GoodWe register `35172` as the primary load value because it matches the G20 load-phase sum; `PV - grid + battery` is now labelled **system power balance**, not house load.
- Registers `35138` and `35140` are labelled inverter-side diagnostics and are no longer presented as inverter self-consumption.
- The EMHASS load forecast consistently uses GoodWe load register `35172` plus Recorder history.
- Grid hero value is shown as an absolute number because the Importing/Exporting badge already communicates direction; diagnostics retain the signed value.
- Modbus offline handling uses shorter retries and reconnects on the normal polling cycle instead of holding a dead connection for a long time.
- EMHASS SOC changes are debounced for 3 seconds, so moving a slider results in one optimization after it settles.
- Flow particles now animate the individual CSS `translate` property, avoiding the v0.12 `transform:none!important` conflict that suppressed visible movement.
- Dashboard frontend moved to `gw-energy-pilot-v013.js`.

## [0.12] - 2026-08-23

### Added

- EMHASS `/healthz` probe and EMHASS version/health diagnostics.
- Nord Pool fallback support for sensors with `raw_today` and `raw_tomorrow`.
- Clear runtime-price error state and additional GoodWe/EMHASS diagnostics.
- Diagnostics card visibility toggle.

### Changed

- No EMHASS optimization is started during Home Assistant startup.
- First Modbus refresh, Automatic Control restore and EMHASS SOC reads run in background tasks.
- EMHASS output IDs can be configured before those entities exist.
- Native load forecast uses a 24-hour inclusive horizon.
- HTTP/HTML EMHASS errors are reduced to concise messages.
- Dashboard rerenders only for relevant entity changes.
- Hover effects no longer move controls.

## [0.11] - 2026-08-23

### Added

- Native EMHASS minimum/maximum battery SOC number entities.
- SOC sliders on the dashboard.
- EV-stop re-optimization.
- Diagnostics snapshot card with GoodWe, controller, EMHASS and power-balance data.

### Changed

- Default periodic optimization interval changed from 15 to 60 minutes.
- Home/load diagnostics identify GoodWe register `35172` explicitly.
- Flow animation changed to continuously spaced particles.

## [0.10] - 2026-08-22

### Added

- Native EMHASS orchestrator.
- Optimize now button.
- Maximum export, Pause, Maximum charge and AUTO battery controls.
- Runtime SOC, load forecast and optional Nord Pool pricing.
- HTTP validation and fresh `P_batt` validation.

### Changed

- Optimization is independent from Automatic Control.
- EnergyPilot remains the only component writing GoodWe EMS registers.

## [0.09] - 2026-08-22

### Added

- Default EMHASS output entity IDs and optimization status.
- Recorder-based bootstrap load forecast.
- Optimization/publish validation.

## [0.08] - 2026-08-22

### Added

- Draggable dashboard layout, visibility menu and animation control.

### Changed

- Automatic Control restores its previous Home Assistant state after reload/restart.

## [0.07] - 2026-08-22

### Added

- Compact live PV / Home / Grid / Battery flow widget.

### Fixed

- Dashboard branding and Home Assistant temperature-unit handling.

## [0.06] - 2026-08-22

### Fixed

- Dashboard logo handling and frontend cache busting.

## [0.05] - 2026-08-22

### Added

- Built-in Home Assistant sidebar dashboard.

## [0.04] - 2026-08-22

### Added

- GW EnergyPilot branding and improved EMHASS setup documentation.

### Changed

- Cleaner default entity set with low-value diagnostics disabled by default.

## [0.03] - 2026-08-22

### Changed

- English setup/options UI, static-IP guidance and controller descriptions.

## [0.02] - 2026-08-22

### Added

- Native GoodWe ETA telemetry over direct Modbus TCP.

## [0.01] - 2026-08-22

### Added

- Initial HACS-compatible integration.
- EMS register control for modes 1–12.
- Manual EMS control and automatic EMHASS `P_batt` mapping.
- Optional EV coordination.
