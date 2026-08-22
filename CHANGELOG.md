# Changelog

All notable changes to GW EnergyPilot are documented here.

## [0.10] - 2026-08-22

### Added

- Native EMHASS orchestrator inside GW EnergyPilot; the package YAML is no longer required for normal operation.
- Native **Optimize now** Home Assistant button entity.
- **Optimize now** control directly on the built-in EnergyPilot dashboard.
- Current GoodWe battery SOC is passed to every optimization as runtime `soc_init`.
- Recorder-based 48-hour load forecast with current-load fallback for fresh Home Assistant installations.
- Optional official Home Assistant Nord Pool price retrieval using `nordpool.get_prices_for_date`.
- Runtime import-price addition and export-price deduction settings.
- Configurable EMHASS URL, optimization interval, final SOC target and fallback house load.
- HTTP result validation for both `/action/dayahead-optim` and `/action/publish-data`.
- Fresh numeric `P_batt` validation after publishing.
- Orchestrator status/diagnostics exposed on the native Optimize now button and displayed in the dashboard.
- Safety detection for the legacy `energypilot_emhass_orchestrator.yaml` scheduler to avoid duplicate recurring optimizations.

### Changed

- EMHASS optimization is now a first-class EnergyPilot function and remains independent from the GoodWe Automatic Control switch.
- Existing v0.09 installations upgrade with the built-in recurring schedule disabled until explicitly enabled, preventing conflicts with an existing YAML scheduler.
- The dashboard frontend moved to `gw-energy-pilot-v010.js` and reports v0.10.
- EnergyPilot remains the only component that writes GoodWe EMS registers; the optimizer only creates and publishes the power plan.

## [0.09] - 2026-08-22

### Added

- Prefilled EMHASS controller defaults:
  - `sensor.p_batt_forecast`
  - `sensor.optim_status`
  - required optimization state `Optimal`
- Tested local EMHASS orchestrator reference at `docs/examples/energypilot_emhass_orchestrator.yaml`.
- Orchestrator status helpers and validation flow.
- Recorder-based load forecast for fresh Home Assistant installations with insufficient EMHASS naive-history data.
- HTTP response validation for EMHASS optimization and publish calls.
- Fresh `p_batt_forecast` validation after publishing.
- Updated installation and EMHASS mapping documentation.
- Dashboard module wrapper `gw-energy-pilot-v009.js` with v0.09 cache busting/version display.

### Changed

- EnergyPilot setup now suggests the normal EMHASS output entities automatically instead of requiring manual selection on every installation.
- Documentation now uses the bootstrap order: install EMHASS, install EnergyPilot, map EMHASS source sensors to EnergyPilot telemetry, optimize/publish, then enable Automatic Control.
- EMHASS optimization is documented as independent from the EnergyPilot Automatic Control switch.
- The reference orchestration layer never writes GoodWe registers; EnergyPilot remains the only GoodWe EMS controller.

## [0.08] - 2026-08-22

### Added

- Draggable dashboard layout with persistent card ordering.
- Dashboard layout/visibility menu.
- Flow-animation toggle and stronger moving particles.

### Changed

- Automatic Control restores its previous Home Assistant state after reload/restart.
- First installation still defaults Automatic Control to OFF.

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
