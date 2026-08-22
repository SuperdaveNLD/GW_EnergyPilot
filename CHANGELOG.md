# Changelog

All notable changes to GW EnergyPilot are documented here.

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
