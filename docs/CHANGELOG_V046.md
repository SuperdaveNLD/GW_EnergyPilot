# GW EnergyPilot v0.46 changelog

## Added

- Added the independent `enable_external_pv` master switch to dashboard PV settings.
- Added backwards-compatible enablement for v0.45 installations that already contain an external PV entity.

## Changed

- Grouped all four external PV entity selectors inside one visual panel.
- Disabled and dimmed the selectors while external PV is off, and enabled them immediately when the switch is on.
- Preserved configured external entity IDs while the master switch is off.
- Added `gw-energy-pilot-v046.js` and refreshed the active frontend dependency graph with `0.46-external-pv1`.
- Extended the real-browser matrix with grouped-panel, master-switch, enabled-state and value-preservation assertions.

## Safety and compatibility

- External PV remains presentation-only and cannot affect GoodWe/EMS control, Automatic Control, EMHASS, plan resilience or accounting.
- No existing entity ID, unique ID, config entry or persistent Store contract changes.
