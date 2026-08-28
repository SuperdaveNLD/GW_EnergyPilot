# GW EnergyPilot v0.42 changelog

## Changed

- Redesigned the EMHASS configuration page into grouped **Connection & planning**, **Outputs** and **Price settings** sections.
- Added a top-level EMHASS status summary for connection availability, required-config synchronization and output configuration readiness.
- Added an EMHASS configuration comparison table that shows the friendly setting name, canonical EMHASS key, EnergyPilot-required value, actual value read from EMHASS and per-row synchronization status.
- Clarified which editable fields are EnergyPilot config-entry settings and which values are actually stored in EMHASS `config.json`.
- Added `gw-energy-pilot-v042.js` as the release wrapper over the validated v0.41 stable-DOM runtime and the v0.42 EMHASS settings presentation layer, with fresh cache keys and v0.42 version presentation.

## Validation

- Python/Node Quality suite and repository validator.
- Frontend architecture audit.
- HACS validation.
- Hassfest validation.
- Desktop Chromium, iPad WebKit touch and iPhone WebKit touch browser-stability matrix, including the EMHASS settings layout and configuration-difference presentation.

## Safety and compatibility

- No GoodWe register definitions or Modbus read blocks change.
- No EMS mode mapping, setpoint semantics or `47512 -> wait -> 47511` write-order change.
- No Automatic Control decision or Battery Saver optimization behavior change.
- No additional EMHASS synchronization/configuration write path is introduced; the existing sync API and actions remain authoritative.
- No entity ID, unique ID, config-entry migration, persistent Store key or stable device identity change.
