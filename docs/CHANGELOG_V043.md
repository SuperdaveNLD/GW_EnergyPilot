# GW EnergyPilot v0.43 changelog

## Fixed

- Fixed sticky WebKit touch-hover presentation for Optimize now, the EMHASS Profit/Cost/Self-consumption selector, Battery Strategy, manual battery quick actions including max export, and the dashboard layout menu.
- Kept inactive controls visually inactive on coarse-pointer/touch devices even when the browser retains native `:hover`; only application-owned `.active` and `aria-pressed="true"` state renders as selected.

## Changed

- Added `gw-energy-pilot-v043.js` as the active frontend release layer over the unchanged v0.42 entrypoint, with fresh browser cache wiring and v0.43 version presentation.
- Extended the shared browser harness and release workflow to run repeated real taps on desktop Chromium, iPad WebKit touch and iPhone WebKit touch profiles.
- Added assertions for executed Home Assistant actions, exactly one visible active selection, repeated layout-menu open/close, concurrent telemetry, post-structure-render operation and a structural render during Optimize now pointer activation.

## Safety and compatibility

- The fix is CSS/presentation-only and does not install pointer/touch handlers, capture pointers, prevent native events or cancel scrolling.
- No backend service or WebSocket behavior changes.
- No GoodWe register definitions, Modbus reads/writes, EMS mode mapping/setpoint/write order, Automatic Control decision or EMHASS optimization/configuration ownership change.
- No entity ID, unique ID, config-entry migration, persistent Store key or stable device identity change.
