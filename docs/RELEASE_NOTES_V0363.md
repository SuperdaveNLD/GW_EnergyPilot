# GW EnergyPilot v0.36.3 Beta

v0.36.3 is a focused frontend hotfix for dashboard controls that visibly flashed during periodic live telemetry refreshes.

## Root cause

v0.36.2 correctly preserves the Home Assistant mobile scroll position, but the current layered dashboard renderer still rebuilds the complete EnergyPilot Shadow DOM whenever a relevant Home Assistant state changes. GoodWe telemetry therefore recreates every dashboard button on normal polling cycles. Replacing those DOM nodes resets browser hover/focus/compositing state and produces the visible button flash even though the control itself did not change.

## Fixed

- Added a top-level control-stability layer on top of the existing v0.36.2 scroll-stability frontend.
- Existing button DOM nodes are captured before a full dashboard render.
- When the freshly rendered button structure is equivalent, EnergyPilot restores the existing button nodes instead of leaving newly recreated copies in place.
- Fresh attributes and inner content are synchronized first, so disabled/active state and labels still follow the current render.
- Keyboard focus is preserved with `preventScroll` where supported.
- If the number or identity of controls actually changes, the new render remains untouched so legitimate UI changes are never hidden.

## Compatibility and safety

- GoodWe polling cadence and live telemetry freshness remain unchanged.
- The v0.36.2 mobile scroll-position protection remains in the frontend chain.
- No GoodWe register definitions, Modbus read/write behavior, EMS mode mapping, Automatic Control strategy or coordinator behavior changed.
- No EMHASS configuration ownership, optimization behavior or persistent plan behavior changed.
- No entity IDs, unique IDs, device identity or config-entry storage changed.

## Validation focus

Keep the dashboard open through several normal GoodWe polling cycles while hovering controls on desktop and while viewing/scrolling around controls in the Home Assistant mobile app. Controls whose state does not change should remain visually stable while telemetry values continue updating. Trigger a real control-state change as well and confirm that the new button state is still rendered correctly.
