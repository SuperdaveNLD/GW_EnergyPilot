# Changelog

All notable changes to GW EnergyPilot are documented here.

## [0.12] - 2026-08-23

### Added

- EMHASS `/healthz` probe before optimization, with health/version diagnostics.
- Nord Pool fallback support for sensors exposing `raw_today` and `raw_tomorrow`.
- Clear `error_prices` state when runtime pricing is enabled without a compatible source.
- Detection of other active Home Assistant `goodwe` config entries in the support snapshot.
- Diagnostics visibility toggle in the dashboard layout menu.

### Changed

- EnergyPilot no longer starts an EMHASS optimization during Home Assistant startup.
- The first Modbus refresh, restored Automatic Control command and EMHASS SOC reads run as background tasks so entity/platform setup does not hold Home Assistant startup open.
- EMHASS output entity IDs use text inputs and can be saved before EMHASS creates those entities.
- Native load forecast returned to the validated 24-hour inclusive shape of 25 hourly points.
- Whole-home demand uses the validated power balance `PV - grid + battery` when those values are available; register 35172 remains visible as a raw diagnostic.
- EMHASS HTTP/HTML errors are reduced to concise diagnostic messages.
- Flow particles use full-track position animation with stable phase offsets, and the dashboard rerenders only for relevant entity changes.
- Optimize and battery-control hover effects no longer move or scale the controls.
- README and EMHASS documentation now describe a fresh installation only.
- Dashboard frontend moved to `gw-energy-pilot-v012.js` and reports v0.12.

## [0.11] - 2026-08-23

### Added

- Native EMHASS minimum and maximum battery SOC number entities backed by EMHASS `/get-config` and `/set-config`.
- Minimum/maximum SOC sliders directly on the dashboard EMHASS card.
- Event-driven EMHASS re-optimization when configured EV charging changes from active to stopped.
- Dashboard **Diagnostics snapshot** card with GoodWe EMS, controller, EMHASS and power-balance values plus a copy-to-clipboard support snapshot.
- Diagnostic comparison of GoodWe house-load register 35172, the three load-phase sum and a power-balance-derived house load.

### Changed

- Default periodic EMHASS optimization interval changed from 15 minutes to 60 minutes. Immediate optimizations still run on **Optimize now**, **AUTO**, tomorrow-price publication and configured EV charging stop.
- The Home card now identifies register 35172 as the GoodWe house/load value rather than implying it is inverter self-consumption.
- Flow animation now uses three continuously spaced round particles across the full link. The LIVE indicator no longer pulses in sync with the energy particles.
- Dashboard frontend moved to the v0.11 module chain.

## [0.10] - 2026-08-22

### Added

- Native EMHASS orchestrator inside GW EnergyPilot; the package YAML is no longer required for normal operation.
- Native **Optimize now** Home Assistant button entity.
- **Optimize now** control directly on the built-in EnergyPilot dashboard.
- Four native one-touch GoodWe battery buttons: **Maximum export**, **Pause battery**, **Maximum charge**, and **AUTO**.
- **AUTO** forces one fresh EMHASS optimization and only resumes Automatic Control after that optimization succeeds.
- Battery quick actions are shown directly on the dashboard Battery card.
- Manual quick actions take manual ownership and disable Automatic Control before applying the requested GoodWe EMS mode.
- Current GoodWe battery SOC is passed to every optimization as runtime `soc_init`.
- Recorder-based load forecast with current-load fallback for fresh Home Assistant installations.
- Optional Home Assistant Nord Pool price retrieval using `nordpool.get_prices_for_date`.
- Runtime import-price addition and export-price deduction settings.
- Configurable optimization when tomorrow prices become available.
- Configurable EMHASS URL, optimization interval, final SOC target and fallback house load.
- HTTP result validation for both `/action/dayahead-optim` and `/action/publish-data`.
- Fresh numeric `P_batt` validation after publishing.
- Orchestrator status/diagnostics exposed on the native Optimize now button and displayed in the dashboard.
- Reusable `gw-energy-pilot-logo.svg` frontend asset while Home Assistant local-brand surfaces continue to use PNG brand files.

### Changed

- EMHASS optimization is a first-class EnergyPilot function and remains independent from the GoodWe Automatic Control switch.
- When runtime Nord Pool pricing is enabled, `load_cost_forecast` and `prod_price_forecast` are supplied directly to EMHASS.
- Flow-direction chevrons were replaced with round moving energy particles.
- Manual EMS mode selection takes manual ownership instead of competing with Automatic Control.
- EnergyPilot remains the only component that writes GoodWe EMS registers; the optimizer only creates and publishes the power plan.

## [0.09] - 2026-08-22

### Added

- Prefilled EMHASS controller defaults:
  - `sensor.p_batt_forecast`
  - `sensor.optim_status`
  - required optimization state `Optimal`
- Tested local EMHASS orchestrator reference.
- Recorder-based load forecast for fresh Home Assistant installations.
- HTTP response validation for EMHASS optimization and publish calls.
- Fresh `p_batt_forecast` validation after publishing.
- Updated installation and EMHASS mapping documentation.

### Changed

- EnergyPilot setup suggests the normal EMHASS output entities automatically.
- EMHASS optimization is independent from the EnergyPilot Automatic Control switch.
- The orchestration layer never writes GoodWe registers; EnergyPilot remains the only GoodWe EMS controller.

## [0.08] - 2026-08-22

### Added

- Draggable dashboard layout with persistent card ordering.
- Dashboard layout/visibility menu.
- Flow-animation toggle and stronger moving particles.

### Changed

- Automatic Control restores its previous Home Assistant state after reload/restart.
- First installation defaults Automatic Control to OFF.

## [0.07] - 2026-08-22

### Added

- Compact live PV / Home / Grid / Battery flow widget.
- Live flow-direction mapping.

### Fixed

- Inline SVG dashboard branding.
- Temperature values follow the Home Assistant temperature unit.

## [0.06] - 2026-08-22

### Fixed

- High-contrast dashboard logo handling and frontend cache busting.

## [0.05] - 2026-08-22

### Added

- Built-in Home Assistant sidebar dashboard.
- Solar, Home, Grid, Battery, Controller, EMHASS and System Health cards.

## [0.04] - 2026-08-22

### Added

- GW EnergyPilot branding and improved EMHASS setup documentation.

### Changed

- Cleaner default entity set with diagnostic/duplicate entities disabled by default.

## [0.03] - 2026-08-22

### Changed

- English setup/options UI.
- Static-IP guidance.
- Improved controller descriptions, maximum inverter power and deadband guidance.

## [0.02] - 2026-08-22

### Added

- Native GoodWe ETA telemetry over direct Modbus TCP including PV, inverter, meter, battery/BMS, temperatures, loads and diagnostics.

## [0.01] - 2026-08-22

### Added

- Initial HACS-compatible integration.
- EMS registers 47511/47512.
- Modes 1-12.
- Manual EMS control.
- Automatic EMHASS `P_batt` mapping to modes 8/11/12.
- Optional EV coordination.
