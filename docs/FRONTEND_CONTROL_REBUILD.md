# Frontend control and live-flow rebuild

## Status

This document describes the **v0.38 Beta release** frontend control and live-flow architecture. It replaces the released v0.37 presentation stack while keeping the existing GoodWe, EMS and EMHASS backend/control behavior unchanged. The rebuilt controls are covered by executable English/Dutch delegated-click tests and explicit physical flow-direction tests in the normal Quality workflow.

> **v0.41 supersession:** the v0.38-v0.40 control/scroll mechanisms below remain historical compatibility behavior, but the active v0.41 runtime no longer uses a complete render for ordinary telemetry. It patches stable DOM nodes in place, scopes strategy/graph refreshes and disables EnergyPilot motion. See `docs/FRONTEND_STABLE_DOM.md`.

## v0.40 render-settle follow-up

v0.39 proved that the remaining visible blink was a presentation problem caused by a full ShadowRoot rebuild under a stationary pointer, not by control identity or click ownership. The Battery Strategy section already has explicit hover continuity because that section is intentionally reused. Older dashboard/menu/window controls are still recreated and can therefore restart their CSS transitions when the fresh node immediately matches `:hover`.

v0.40 addresses that shared cause at the render boundary instead of adding per-button patches. A persistent ShadowRoot stylesheet temporarily disables **transitions** for interactive controls while the inherited synchronous rebuild settles and until the rebuilt controls have painted once. A generation token prevents an older render callback from releasing a newer settle period. The fallback style is inserted in the same render task when constructable/adopted stylesheets are unavailable.

This mechanism intentionally does not suppress CSS animations, defer telemetry while a mouse pointer merely hovers, capture pointers or transplant old DOM nodes/listener closures. v0.39 remains responsible for Battery Strategy hover continuity.

### Mobile touch/render contract

Phone field validation of the v0.40 candidate exposed a separate regression in the v0.38 runtime's touch/render boundary. The runtime had copied mobile scroll-position restoration from v0.36.2, but its newer interaction guard only started on interactive controls and released the guard as soon as a touch moved 8 px. The queued post-render scroll restores could therefore write an old `scrollTop` while the browser was already processing a swipe or momentum scroll.

The active v0.40 chain keeps the v0.38 architecture but restores these explicit rules:

- a primary **touch** beginning anywhere inside the EnergyPilot ShadowRoot starts an interaction guard; mouse/pen still require an actual interactive target;
- a touch movement of at least 8 px marks the interaction as a scroll gesture but does not end it;
- full dashboard renders remain deferred until pointer-up/cancel and, for a moved touch, a 350 ms settle interval;
- pending animation-frame scroll restorations abort when a touch interaction is active, so an older telemetry snapshot cannot overwrite the browser/WebView's current native scroll position;
- touch handling never calls `preventDefault` and never captures the pointer;
- the existing three-second pointer safety timeout and window-blur cleanup remain the final stuck-interaction escape path.

This keeps two responsibilities separate: scroll-position restoration protects an idle mobile viewport from a telemetry-driven DOM rebuild, while the touch guard gives the browser exclusive ownership of `scrollTop` during an active native pan/momentum gesture.

## Why the v0.37 control stack was replaced

The released frontend combined two mechanisms that interacted badly:

1. `gw-energy-pilot-v035.js` deferred complete Shadow DOM renders while a pointer or keyboard interaction was active.
2. `gw-energy-pilot-v0363-control-stability.js` transplanted old button DOM nodes back into a newly rendered dashboard.

The second mechanism also retained the old nodes' event-listener closures. Some controls therefore continued to reference DOM objects from the previous, already disconnected dashboard. Its button identity included visible text, so Home Assistant language changes or browser translation could produce a different code path for English and Dutch controls.

The replacement has these rules:

- visible text is never a control identity;
- Battery strategy actions use only fixed mode keys such as `mad_steve`, `balanced` and `battery_saver`;
- English and Dutch always receive the same canonical four profiles plus `custom`, in the same order;
- active state uses `aria-pressed`, not label matching;
- the complete strategy section is retained across telemetry renders, but its actions are handled by one listener on the persistent ShadowRoot;
- English and Dutch labels/descriptions are rendered explicitly from the same fixed keys;
- `translate="no"` prevents browser translation from mutating the strategy-control DOM;
- no old button node with a per-node event-listener closure is transplanted;
- no pointer is captured;
- pointer and keyboard completion are observed through pointer-up/cancel, focus-out, window blur and independent three-second safety timers;
- moved touch gestures retain render ownership through their short momentum-settle window;
- an action updates and re-enables all profile buttons immediately after its WebSocket result, before depending on another dashboard render.

## Live-flow direction contract

v0.38 no longer derives visible movement from stacked `inbound`, `outbound`, semantic direction and `animation-direction` overrides. It assigns one physical direction to each connector and selects a dedicated forward or reverse keyframe.

Expected movement:

```text
PV production: left to right, PV -> hub
Grid import: right to left, grid -> hub
Grid export: left to right, hub -> grid
House consumption: bottom to top, hub -> house
Battery charging: top to bottom, hub -> battery
Battery discharging: bottom to top, battery -> hub
```

House movement uses the same corrected GoodWe load resolution as the visible overview. A negative or clearly inconsistent raw house value therefore cannot make the particles contradict the displayed house load.

The existing confirmed sign conventions remain unchanged:

```text
GoodWe meter power: positive export, negative import
GoodWe battery power: positive discharge, negative charge
```

## Automated pre-PR checks

The exact candidate modules uploaded to the branch passed locally:

- JavaScript syntax checks for the active release/runtime chain;
- executable Node flow assertions for PV, grid import/export, house load and battery charge/discharge;
- executable Node localization assertions proving English and Dutch both produce exactly five identical mode keys;
- an executable delegated-click test proving translated visible text still sends exactly one `battery_saver` WebSocket action;
- the same click test proves exactly one profile becomes active and all five controls are immediately enabled after completion;
- Python contract tests for active wiring, excluded legacy layers, stable key-based controls, Dutch/English labels, global pointer/keyboard completion, mobile touch-scroll ownership and physical flow ownership.

GitHub-hosted Quality, HACS and Hassfest runs are mandatory release gates. The release is merged only after those checks pass on the final release head.

## Multi-installation field-validation matrix

After automated release gates, continue validating:

1. English Home Assistant: all five Battery strategy buttons click once and show exactly one active profile.
2. Dutch Home Assistant: the same fixed mode keys execute, with Dutch labels and exactly one active profile.
3. Browser translation disabled and enabled: strategy identity and API mode values remain unchanged.
4. Repeated GoodWe telemetry refresh while hovering and pressing a profile button: no flashing active state, no lost click and no stuck disabled state.
5. Mouse and touch scrolling across the strategy grid: normal vertical scrolling remains available.
6. Start a phone swipe on non-interactive dashboard content while telemetry is updating: the viewport must continue moving smoothly and must not snap toward the top.
7. Release a phone swipe with momentum: no full dashboard render or stale `scrollTop` restore may interrupt the short momentum window.
8. PV production, grid import/export, battery charge/discharge and house load each show the physical movement listed above.

## Safety and compatibility

This is a frontend-only replacement. **No GoodWe register** definition, Modbus read block, EMS mode mapping, setpoint, write order, Automatic Control decision, EMHASS optimization/configuration ownership, entity ID, unique ID, config-entry value or persistent Store key changes.
