# Changelog

All notable changes to GW EnergyPilot will be documented in this file.

## [0.05] - 2026-08-22

### Added

- Built-in `EnergyPilot` sidebar panel for Home Assistant.
- Responsive JavaScript dashboard served directly by the integration.
- Live PV, home load, battery, grid, inverter and thermal overview.
- Automatic discovery of GW EnergyPilot entities through the Home Assistant entity registry.
- EMHASS status, `P_batt` target and common published forecast values on the dashboard.
- Controller overview with EMS mode, EMS setpoint, EnergyPilot target and current command.
- Guarded Automatic Control toggle with a safety confirmation before enabling automatic control.
- Dashboard uses the GW EnergyPilot branding and requires no separate Lovelace resource or frontend HACS package.

### Changed

- Version bumped to `v0.05`.
- README now documents the built-in dashboard and its behavior.
- Dashboard uses the validated GoodWe smart-meter sign convention: positive power is export and negative power is import.

## [0.04] - 2026-08-22

### Added

- New GW EnergyPilot square brand icon/logo.
- README branding header.
- Explicit EMHASS readiness checklist before automatic-control setup.
- Fresh-Home-Assistant bootstrap note for installations that intentionally use EnergyPilot telemetry as EMHASS source data.

### Changed

- Corrected the documented installation order: EMHASS should be installed, configured, tested and publishing its Home Assistant forecast sensors before EnergyPilot automatic control is configured.
- Updated the installation guide to require a successful EMHASS optimization and working `publish-data` before selecting `sensor.p_batt_forecast` in EnergyPilot.
- Reduced the default visible entity set while keeping detailed GoodWe registers available.
- Lower-value, duplicate and troubleshooting entities are now disabled by default using the Home Assistant entity registry.
- Inverter radiator temperature remains the primary visible inverter temperature.
- Secondary inverter temperatures, PV voltage/current details, duplicate meter values, per-phase inverter details, per-phase load details and raw diagnostics are disabled by default.
- Cell-voltage sensors use higher display precision.
- EV status is disabled by default when EV coordination is not configured.

## [0.03] - 2026-08-22

### Changed

- Setup and options UI is now English, including when Home Assistant uses the Dutch locale.
- First setup screen now explicitly identifies the GoodWe ETA inverter.
- `Host` renamed to `Inverter IP address`.
- Added a clear static IP / DHCP reservation recommendation.
- Added field-level help text using Home Assistant `data_description` strings.
- Controller setup now clearly states that a working EMHASS environment is required before automatic battery control is enabled.
- `Maximum battery power` renamed to `Maximum inverter power`.
- Maximum inverter power is now entered in kW while EnergyPilot continues to store and control power internally in watts.
- Power deadband help now explains Battery Hold behavior and recommends 300 W, with a typical range of 200-500 W.
- Connection error text now explicitly refers to the GoodWe ETA and EMS registers 47511/47512.

## [0.02] - 2026-08-22

### Added

- Native GoodWe ETA telemetry over direct Modbus TCP.
- PV1/PV2/PV3/PV4 voltage, current and power.
- Total PV power.
- Inverter L1/L2/L3 voltage, current, frequency and power.
- Total inverter power and AC active power.
- Smart-meter L1/L2/L3 and total power measurements.
- Smart-meter phase voltage/current and frequency.
- Battery SOC, SOH, power, voltage and current.
- Battery mode and battery string count.
- BMS status, current limits, protocol and version registers.
- Maximum/minimum cell voltage.
- Inverter air, module and radiator temperature.
- BMS package temperature.
- Maximum/minimum battery cell temperature.
- Load and backup-load telemetry registers.
- Extended inverter/BMS warning and error diagnostics.
- Documentation for the required EMHASS setup and publish workflow.
- Documentation for maximum battery control power and power deadband.
- Static IP / DHCP reservation recommendation for the inverter.

### Changed

- Version numbering simplified to `v0.01`, `v0.02`, `v0.03`, etc.
- Documentation updated for clean Home Assistant installations.

## [0.01] - 2026-08-22

### Added

- Initial HACS-compatible custom integration structure.
- Direct Modbus TCP connection to GoodWe ETA.
- EMS mode register 47511 and power setpoint register 47512 support.
- Tested EMS mode names for modes 1 through 12.
- Manual EMS mode selection and configurable manual power.
- Automatic-control master switch.
- EMHASS `P_batt` mapping to mode 8, 11 and 12.
- Mode 1 fallback when automatic control is disabled.
- Optional EV detection based on charging mode and charging power.
- Conservative EV Battery Hold behavior for the first alpha release.
- HACS and hassfest validation workflows.
