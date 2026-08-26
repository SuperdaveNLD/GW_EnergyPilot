# GW EnergyPilot v0.40 Beta

v0.40 is a focused frontend stability release. It extends the v0.39 Battery Strategy hover fix to the other dashboard controls that are still recreated by the inherited full ShadowRoot render, including the dashboard-layout menu and per-card window controls.

## Root cause

Relevant Home Assistant state updates are intentionally filtered and batched by the v0.38 runtime, but a relevant update still rebuilds the inherited dashboard DOM. Most older controls are created again during that render. Their CSS transitions then start from the new node's initial state and immediately enter `:hover` when the pointer is stationary above the same visual location. That transition restart looks like a periodic blink even though the click handler itself is working.

v0.39 solved this specifically for the reused Battery Strategy section. v0.40 solves the remaining presentation problem generically without changing action ownership.

## Render-settle behavior

During an inherited full render, v0.40:

- marks the panel as being in a short render-settle phase before the old controls are detached;
- temporarily disables CSS **transitions** for `button`, `input`, `select`, `textarea`, links, role-buttons, tabindex controls, their descendants and their pseudo-elements;
- keeps that settle state through the first paint of the rebuilt controls using two animation-frame boundaries;
- uses a generation token so a callback from an older render cannot end the settle phase of a newer render;
- keeps the rule in a ShadowRoot `adoptedStyleSheets` stylesheet where supported, so the rule survives the inherited `innerHTML` replacement; an ordinary ShadowRoot style is used as fallback.

After that first painted frame, normal hover/focus/switch transitions work again.

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
- disable live-flow CSS animations;
- change GoodWe registers, Modbus reads, EMS modes/setpoints/write ordering, Automatic Control decisions or EMHASS behavior.

## Safety and compatibility

No Home Assistant entity IDs, unique IDs, config-entry data, persistent Store keys or stable device identity are changed. The release is frontend-only and retains the v0.38 active-press guard, relevant-state filtering, touch scrolling, mobile scroll restoration and delegated Battery Strategy control contract.

## Validation

The final v0.40 candidate must pass:

- JavaScript syntax validation including the active `gw-energy-pilot-v040.js` entrypoint;
- the existing executable v0.38 model/control/localization tests;
- v0.40 render-settle regression tests;
- the complete Python unit suite and repository invariant validator;
- HACS validation;
- Hassfest validation.
