# Changelog

All notable changes to GW EnergyPilot will be documented in this file.

## [0.06] - 2026-08-22

### Fixed

- Dashboard logo is now rendered as a high-contrast embedded vector mark instead of relying on the dark PNG asset.
- Added a versioned dashboard module wrapper for reliable frontend cache busting.
- Dashboard version badge and footer now report v0.06.

## [0.05] - 2026-08-22

### Added

- Built-in EnergyPilot JavaScript dashboard registered automatically in the Home Assistant sidebar.
- Responsive Solar, Home, Grid and Battery overview.
- Live battery SOC, power and charging/discharging state.
- Grid import/export state with L1/L2/L3 values.
- EnergyPilot controller status, EMS mode, setpoint, target and command.
- EMHASS overview with P_batt target, optimization status and forecast entities.
- Thermal and BMS limits overview.
- Automatic-control toggle with an EMHASS safety confirmation.
- Automatic discovery of EnergyPilot entities through the Home Assistant entity registry.
- Local frontend assets served by the integration; no manual Lovelace resource is required.

### Changed

- Roadmap now treats the built-in dashboard as an implemented feature instead of a future dashboard example.

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
