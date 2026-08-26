# GW EnergyPilot v0.36.2 Beta

v0.36.2 is a focused mobile dashboard hotfix for the periodic viewport jump that remained after v0.36.1.

## Root cause

The v0.36.1 touch fix removed pointer capture and protected an active swipe, but the dashboard still intentionally performs a complete Shadow DOM rebuild for relevant Home Assistant state changes. GoodWe telemetry is coordinator-polled, so an installation using a 15-second scan interval can still trigger a full dashboard render every 15 seconds. On mobile Home Assistant/WebView, replacing the complete dashboard subtree can cause the browser to choose a different scroll anchor after layout, moving the viewport down around the forecast/cards area even when the user did not click anything.

## Fixed

- Added a top-level mobile scroll-stability layer around the complete current v0.36 customer-controller render chain.
- Before a narrow/mobile render, EnergyPilot captures every scrollable composed ancestor of the custom panel plus `document.scrollingElement`.
- After the complete render chain has rebuilt the dashboard, the exact scroll positions are restored immediately and across two animation frames so late layout/ResizeObserver settling cannot move the viewport.
- The EnergyPilot panel subtree uses `overflow-anchor: none` on narrow/mobile layouts so browser scroll anchoring cannot select a newly recreated dashboard node as a replacement anchor.
- Wide/desktop behavior is unchanged.

## Compatibility and safety

- GoodWe polling cadence and live telemetry freshness are unchanged; the fix does not hide or delay inverter updates.
- No GoodWe register definitions, Modbus blocks, EMS modes or write ordering changed.
- No Automatic Control strategy, Battery Saver profile, EMHASS optimization/configuration ownership or persistent plan behavior changed.
- No entity IDs, unique IDs, device identity, config-entry data or storage keys changed.

## Validation focus

On the Home Assistant mobile app, scroll to and through SOC Forecast / Battery Plan / Battery strategy content and remain there for several GoodWe polling cycles. The viewport should remain at the same vertical position while live values continue to update. Repeat in portrait and landscape and with the configured GoodWe scan interval (including 15 seconds where applicable).
