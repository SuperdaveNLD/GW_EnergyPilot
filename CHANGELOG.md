# Changelog

All notable changes to GW EnergyPilot will be documented in this file.

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
