# GW EnergyPilot v0.46 changelog

## Added

- Added the independent `enable_external_pv` master switch to dashboard PV settings.
- Added backwards-compatible enablement for v0.45 installations that already contain an external PV entity.

## Fixed

- Prevent Home Assistant's repeated same-value `narrow` and cloned-equivalent `panel` assignments from replacing dashboard controls during a native press, while preserving structural renders for genuine nested configuration changes (#84).
- Keep Battery quick-action selection, EMHASS cost-function busy locking and manual EMS feedback stable through delayed or split Home Assistant state publication (#84).
- Prevent a second EMHASS strategy tap from starting another optimization while the first service transaction is still running (#84).

## Changed

- Grouped all four external PV entity selectors inside one visual panel.
- Disabled and dimmed the selectors while external PV is off, and enabled them immediately when the switch is on.
- Preserved configured external entity IDs while the master switch is off.
- Refined the inherited static live-flow presentation with integrated arrowheads, directional pipe brightness, restrained 3/4/5-pixel intensity steps and quieter idle/unknown styling.
- Compacted the manual EMS pad while Automatic Control owns the inverter, preserved its mounted control nodes and restored working controls when automatic ownership is released (#87).
- Added `gw-energy-pilot-v046.js` and refreshed the active frontend dependency graph with `0.46-external-pv1`.
- Extended the real-browser matrix with grouped-panel, master-switch, enabled-state, value-preservation, host-property churn, native-press, delayed-publication and double-tap assertions.

## Safety and compatibility

- External PV remains presentation-only and cannot affect GoodWe/EMS control, Automatic Control, EMHASS, plan resilience or accounting.
- No existing entity ID, unique ID, config entry or persistent Store contract changes.
