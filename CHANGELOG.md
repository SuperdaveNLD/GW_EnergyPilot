# Changelog

All notable changes to GW EnergyPilot will be documented in this file.

## [0.1.0] - 2026-08-22

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
- English and Dutch translations.
- HACS and hassfest validation workflows.
