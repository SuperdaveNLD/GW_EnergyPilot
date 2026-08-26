# GW EnergyPilot v0.36.1 Beta

v0.36.1 is a focused mobile frontend hotfix for the customer Battery strategy controls introduced in v0.36.

## Fixed

- Fixed Home Assistant mobile scrolling becoming unstable when a vertical swipe starts over the large **Mad-Steve**, **Gold Rush**, **Balanced**, **Battery Saver** or **Custom** strategy buttons.
- The v0.35 interaction guard no longer calls `setPointerCapture()` for touch input. Pointer capture remains available for desktop mouse presses where it protects a click without interfering with native touch panning.
- Touch movement is now distinguished from a tap after an 8 px movement threshold. During a touch scroll, destructive full-dashboard renders remain deferred until the gesture has settled, preventing telemetry updates from replacing the Shadow DOM mid-scroll.
- Added a 5 second pointer-interaction safety timeout so an interrupted mobile gesture cannot leave the dashboard permanently render-locked.
- Strategy buttons explicitly allow native vertical panning with `touch-action: pan-y`.

## Compatibility and safety

- No GoodWe register definitions, Modbus read blocks or EMS mappings changed.
- No automatic-control strategy or EMHASS optimization behavior changed.
- No entity IDs, unique IDs, device identity or configuration ownership changed.
- The v0.36 customer Battery strategy behavior remains unchanged; this hotfix only changes frontend pointer/touch handling and cache-busting.
- EMHASS remains the canonical optimizer and plan owner.

## Validation

Repository regression coverage now verifies that touch input is not pointer-captured, touch movement is detected and settled before deferred rendering resumes, the strategy buttons expose native vertical panning, and the v0.36.1 frontend/manifest/cache-busting wiring is consistent.

Field validation should include repeated portrait and landscape swipes through the Battery strategy section in the Home Assistant mobile app while live GoodWe telemetry is updating.
