# GW EnergyPilot v0.41 Beta

v0.41 is the frontend stability release requested after repeated mobile scroll and control failures. It changes the active dashboard render architecture rather than adding another visual, pointer or scroll-restoration patch.

## Operator-visible behavior

- Ordinary GoodWe and EMHASS telemetry no longer rebuilds the complete dashboard DOM.
- The Dashboard menu, Automatic Control button and Battery Strategy buttons keep the same DOM identity during ordinary telemetry updates.
- Native browser and Home Assistant WebView scrolling owns the viewport; the active v0.41 path does not restore an older EnergyPilot `scrollTop` snapshot during a pan or momentum scroll.
- Selecting a Battery Strategy updates only the strategy section while the existing Battery Saver API applies the mode and starts the established optimization/publish transaction.
- A changed EMHASS plan refreshes only the Battery · Plan · Price card. The rest of the dashboard is not rebuilt.
- EnergyPilot animations, transitions, moving flow particles and modal backdrop filters are disabled. Static direction and state labels remain available.

## Stable-DOM architecture

The active entrypoint is `gw-energy-pilot-v041.js`.

Normal telemetry follows this path:

1. accept the new Home Assistant `hass` object;
2. compare context and structural signatures;
3. when structure is unchanged, batch a small live patch;
4. update existing text, classes, attributes, slider values, status pills, diagnostics and meter widths;
5. leave `main`, cards and interactive controls connected.

A full render remains valid only for:

- first panel initialization;
- Home Assistant language, user or theme changes;
- entity-registry changes;
- optional-card topology changes, such as PV4 becoming structurally present or absent;
- an explicit layout or narrow-mode structural change.

The inherited v0.38 pointer/render guard and mobile scroll snapshot restoration remain available to historical v0.38-v0.40 entrypoints. The active v0.41 runtime explicitly bypasses them.

## Scoped refresh ownership

### Battery Strategy

`gw-energy-pilot-v038-strategy.js` uses a v0.41 callback to rerender only `.ep-v038-strategy` for loading, pending, success/error and Custom-SOC feedback. Older entrypoints retain the existing full-render fallback.

### Battery · Plan · Price

`gw-energy-pilot-v027-battery-plan-data.js` and `gw-energy-pilot-v027-battery-plan-core.js` expose a targeted graph-card refresh. A loading flag and active-promise check form one busy state, preventing re-entrant refresh while a request is being registered.

## Motion policy

v0.41 intentionally enforces a no-motion dashboard:

- zero active EnergyPilot CSS animations;
- zero active EnergyPilot CSS transitions;
- no moving flow particle layers;
- no animated pseudo-elements;
- no modal backdrop filters;
- `scroll-behavior: auto` for EnergyPilot-owned content.

This policy is applied to initial content and late-added strategy, graph and modal content.

## Browser validation

The release matrix runs the exact v0.41 entrypoint in real browser engines:

| Profile | Engine | Viewport / input |
|---|---|---|
| Desktop | Chromium | 1440 × 900, mouse/keyboard |
| iPad | WebKit | 834 × 1112, mobile + touch |
| iPhone | WebKit | 390 × 844, mobile + touch |

Each profile verifies scroll range, idle scroll stability, monotonic telemetry scrolling, stable control identity, menu open/close, Automatic Control OFF/ON, Battery Strategy apply, graph-only plan refresh, Dutch localization, post-structure controls, zero active motion and clean JavaScript/WebSocket diagnostics.

These are deterministic browser-engine and viewport regressions. They are not a claim of broad physical-device, firmware or Home Assistant Companion App validation; that wider field validation remains part of the Beta status.

## Upgrade notes

1. Install v0.41 through HACS after the release is published.
2. Restart Home Assistant as requested by HACS.
3. Reload the dashboard or browser so the new `0.41-stable1` frontend cache keys are used.
4. Verify scrolling and the Dashboard menu before enabling Automatic Control.
5. Confirm Battery Strategy and Optimize now update the plan graph without moving the page.

## Safety and compatibility

v0.41 is frontend-only. It does not change GoodWe register definitions or Modbus read blocks; EMS modes, setpoints or write ordering; Automatic Control decisions; EMHASS optimization/configuration ownership; entity IDs or unique IDs; config-entry data or migrations; persistent Store keys; or stable device identity.
