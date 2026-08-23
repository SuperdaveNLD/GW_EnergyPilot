# Changelog

All notable changes to GW EnergyPilot are documented here.

## [0.19] - 2026-08-23

### Added

- A dedicated **SOC / CONSTRAINT LAYERS** diagnostics group that shows current battery SOC, last optimization `soc_init`, EnergyPilot runtime `soc_final`, EMHASS minimum SOC, EMHASS `battery_target_state_of_charge`, EMHASS SOC-deficit threshold/cost and GoodWe on-grid minimum SOC register `45356` side by side.
- SOC-related EMHASS config diagnostics are decoded from the same `/get-config` response already used by the stateful cost-function selector; no additional periodic HTTP request is introduced.
- Unit tests for explicit percentage/numeric decoding and invalid/missing EMHASS SOC diagnostic values.

### Changed

- The EMHASS settings label **Target final SOC** is clarified in the dashboard as **Runtime final SOC target**.
- The setting description now states explicitly that EnergyPilot sends this value as runtime `soc_final`, that the runtime value overrides the configured target for that optimization, and that it does not rewrite EMHASS `battery_target_state_of_charge` in `config.json`.
- The active frontend is `gw-energy-pilot-v019.js`, layered on top of the complete v0.18 G20 field-test controls.

### Safety boundary

- No EMHASS optimization objective, constraint or payload semantics are changed; v0.19 only exposes values that already exist in EnergyPilot or EMHASS.
- No additional GoodWe registers are read or written.
- The v0.18 manual Beta write path for `45356/45358`, Automatic Control ownership, EMS modes/registers and `P_batt` mapping are unchanged.

## [0.18] - 2026-08-23

### Added

- Manual **G20 Beta battery minimum-SOC** controls inside the GOODWE settings page for register `45356` (on-grid) and `45358` (off-grid).
- Admin-only WebSocket commands `gw_energypilot/beta_soc/get` and `gw_energypilot/beta_soc/set` for the dedicated field-test controls.
- Verified write support that writes exactly one selected Beta SOC-floor register and immediately reads the same register back before reporting success.
- Hardware-independent tests for the `45356/45358` write whitelist, bounds validation and verified read-back path.

### Changed

- The current `45356` interpretation is refined from ambiguous "discharge depth" wording to the raw **minimum SOC floor** used by the tested G20. This matches current upstream GoodWe handling where on-grid DoD is `100 - register 45356`.
- `45358` is treated as the corresponding off-grid minimum-SOC floor for field validation.
- A successful Beta write updates the coordinator snapshot immediately so the existing Diagnostic entity reflects the verified read-back without waiting for the next normal poll.
- The active frontend is `gw-energy-pilot-v018.js`, layered on top of the complete v0.17 settings/strategy implementation.

### Beta safety boundary

- The new write path is **manual field-test only** and is not used by Automatic Control, EMHASS, event triggers or any scheduled task.
- Only the two already-known canonical register definitions `45356` and `45358` are accepted; arbitrary register writes are not exposed.
- Values are limited to whole percentages from `0` through `100` and the register must already be readable on the current inverter before a write is allowed.
- Each user action changes exactly one register and requires a separate dashboard confirmation.
- Register `47500` remains read-only because its G20 semantics are still unresolved and the tested inverter has returned the sentinel-like value `65535`.
- EMS modes `8/11/12`, registers `47511/47512`, sign conventions, control ownership and canonical grid-energy accounting remain unchanged.

## [0.17] - 2026-08-23

### Added

- A settings gear in the EnergyPilot dashboard header for Home Assistant administrators.
- Dedicated **EP**, **EMHASS** and **GOODWE** configuration pages backed by the existing Home Assistant config entry.
- Admin-only WebSocket settings commands for reading and updating the existing configuration.
- GoodWe connection validation before host, Modbus TCP port or unit-ID changes are saved.
- Multi-entry selection for installations with more than one GW EnergyPilot config entry.
- Enabled-by-default Home Assistant Diagnostic sensors for the Beta SOC candidates `45356`, `45358` and `47500`.
- A device-registry migration from the legacy mutable `host:slave` identifier to the stable config-entry ID.
- A stateful **EMHASS optimization strategy** select that reads the active `costfun` from EMHASS `/get-config`.

### Changed

- GoodWe host/port/unit-ID changes can now be made from the dashboard and reload the existing integration after successful validation.
- EP controller/telemetry/EV options and EnergyPilot-owned EMHASS orchestration/price options can be maintained from the dashboard settings pages.
- The dashboard now highlights the active Profit / Cost / Self-consumption strategy instead of presenting three ambiguous stateless actions.
- The strategy select refreshes after EnergyPilot EMHASS config writes and periodically so direct EMHASS UI changes are reflected in Home Assistant.
- Existing v0.15 cost-function button unique IDs remain available for backwards-compatible automations and are classified as explicit configuration actions.
- A successful `costfun` save is distinguished from a later fresh-optimization failure; the saved strategy remains visible even when re-optimization fails.
- The active frontend is `gw-energy-pilot-v017.js`, layering the settings UI on top of all v0.16 Beta diagnostics and strategy readback behavior.
- Home Assistant device identity no longer depends on mutable inverter connection data after migration.

### Beta status

- v0.17 remains **Beta** because the new settings UI/device migration has only limited field exposure and the G20 candidate register semantics are still being correlated across the active tester installations.
- The G20 Beta registers remain read-only and optional.
- The settings pages and stateful strategy selector do not change GoodWe EMS modes, register write ordering, `P_batt` mapping, sign conventions or controller ownership.

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
