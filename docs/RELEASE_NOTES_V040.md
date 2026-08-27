# GW EnergyPilot v0.40 Beta

v0.40 is a focused frontend stability release. It extends the v0.39 Battery Strategy hover fix to the other dashboard controls that are still recreated by the inherited full ShadowRoot render, including the dashboard-layout menu and per-card window controls. Field validation also exposed and fixes a mobile scroll regression in the active v0.38 runtime path.

## Root cause

Relevant Home Assistant state updates are intentionally filtered and batched by the v0.38 runtime, but a relevant update still rebuilds the inherited dashboard DOM. Most older controls are created again during that render. Their CSS transitions then start from the new node's initial state and immediately enter `:hover` when the pointer is stationary above the same visual location. That transition restart looks like a periodic blink even though the click handler itself is working.

v0.39 solved this specifically for the reused Battery Strategy section. v0.40 solves the remaining presentation problem generically without changing action ownership.

During phone field validation a second interaction between the v0.38 touch guard and mobile scroll restoration was confirmed. v0.38 only kept a destructive render deferred while a pointer started on an interactive element, and it released that protection as soon as a touch moved 8 px. At the same time, mobile scroll stabilization could still write the pre-render `scrollTop` back during two queued animation frames. A normal swipe could therefore hand rendering back to the dashboard while the browser was still panning, after which an older scroll snapshot repeatedly pulled the viewport upward.

## Render-settle behavior

During an inherited full render, v0.40:

- marks the panel as being in a short render-settle phase before the old controls are detached;
- temporarily disables CSS **transitions** for `button`, `input`, `select`, `textarea`, links, role-buttons, tabindex controls, their descendants and their pseudo-elements;
- keeps that settle state through the first paint of the rebuilt controls using two animation-frame boundaries;
- uses a generation token so a callback from an older render cannot end the settle phase of a newer render;
- keeps the rule in a ShadowRoot `adoptedStyleSheets` stylesheet where supported, so the rule survives the inherited `innerHTML` replacement; an ordinary ShadowRoot style is used as fallback.

After that first painted frame, normal hover/focus/switch transitions work again.

## Mobile touch-scroll behavior

The active v0.38 runtime used by v0.40 now restores the intended native phone-scrolling contract:

- a primary touch that starts anywhere inside the EnergyPilot dashboard is tracked, not only touches that begin on a button or input;
- moving 8 px or more classifies the gesture as scrolling but no longer releases the destructive-render guard while the finger is still moving;
- relevant dashboard renders stay deferred through the gesture and a 350 ms settle period after a moved touch, allowing momentum scrolling to continue without a ShadowRoot rebuild underneath it;
- already queued post-render scroll-restoration callbacks check whether a touch is active before writing `scrollTop`, so a stale telemetry snapshot never overwrites the browser's live pan position;
- touch scrolling remains native: there is no `preventDefault`, no pointer capture and no change to the existing vertical-pan CSS contract;
- interrupted gestures still have the existing bounded safety timeout and window-blur cleanup, so the render guard cannot remain stuck.

## What this covers

The generic interactive selector covers, among other current controls:

- the Dashboard layout button;
- menu close/reset buttons and visibility/edit/animation switches;
- Automatic Control and its switch-knob presentation;
- per-card close/minimize/maximize window controls;
- manual/controller buttons, inputs and other native interactive controls created by inherited frontend layers.

The v0.39 Battery Strategy hover-continuity logic remains unchanged.

## Deliberately not changed

v0.40 does **not**:

- defer or suppress live telemetry renders merely because the mouse is hovering a control;
- restore the removed v0.35 hover/render lock;
- transplant old button DOM nodes or their per-node event-listener closures;
- capture pointers;
- call `preventDefault` for touch scrolling;
- disable live-flow CSS animations;
- change GoodWe registers, Modbus reads, EMS modes/setpoints/write ordering, Automatic Control decisions or EMHASS behavior.

## Safety and compatibility

No Home Assistant entity IDs, unique IDs, config-entry data, persistent Store keys or stable device identity are changed. The release is frontend-only and retains the v0.38 relevant-state filtering, delegated Battery Strategy control contract and mobile scroll-position preservation while making the touch/render boundary gesture-aware.

## Validation

The final v0.40 candidate must pass:

- JavaScript syntax validation including the active `gw-energy-pilot-v040.js` entrypoint and refreshed v0.38 runtime;
- the existing executable v0.38 model/control/localization tests;
- v0.40 render-settle regression tests;
- regression assertions for touch gestures starting on both interactive and non-interactive dashboard content, 350 ms scroll settling and gesture-aware `scrollTop` restoration;
- the complete Python unit suite and repository invariant validator;
- HACS validation;
- Hassfest validation.
