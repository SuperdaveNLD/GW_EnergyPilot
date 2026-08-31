
# Frontend stable-DOM architecture

## Status

This document is the canonical frontend render/interaction decision for **GW
EnergyPilot v1.1.1**. The stable release retains the complete validated
v1.1.0-beta.1 behavior and all v1.0.1-beta.4 fixes through presentation-only
wrappers; its nested v0.51
feature layer supplies the scoped execution-history card.

No GoodWe register, Modbus, EMS or EMHASS backend behavior is defined here.

## Problem statement

The inherited base panel builds its complete ShadowRoot with `innerHTML`. Older release layers filtered and batched relevant Home Assistant updates, but an accepted update still ran the complete render chain. That detached and recreated cards and controls while WebKit could simultaneously be processing a touch pan or momentum scroll.

The v0.38-v0.40 stack attempted to compensate with interaction guards, delayed renders, button reuse, scroll snapshots/restoration and transition suppression. Those mechanisms reduced individual symptoms but could not make a destructive telemetry render equivalent to a stable page.

Issue #84 exposed the remaining architectural gap after v0.41: normal
telemetry no longer replaced the dashboard, but operational controls were still
created and mutated by multiple historical modules. A native click could
therefore cross a later Home Assistant publication while an inherited listener,
local busy flag, localization pass or targeted `innerHTML` update still owned
part of the same control. The permanent control boundary below removes that
shared ownership instead of adding another press-specific workaround.

## Active entrypoint chain

```text
Home Assistant PANEL_MODULE
  -> gw-energy-pilot-v110.js?v=1.1.1-stable1
       -> gw-energy-pilot-v101.js?v=1.1.1-stable1
            -> gw-energy-pilot-v051.js?v=1.1.1-stable1
                 -> gw-energy-pilot-v051-history.js?v=1.1.1-stable1
                 -> gw-energy-pilot-v050.js?v=1.1.1-stable1
                 -> gw-energy-pilot-v049.js?v=1.1.1-stable1
                      -> gw-energy-pilot-v048.js?v=1.1.1-stable1
                           -> gw-energy-pilot-v047.js?v=1.1.1-stable1
                                -> gw-energy-pilot-v046.js?v=1.1.1-stable1
                                     -> gw-energy-pilot-v045.js?v=1.1.1-stable1
                                          -> gw-energy-pilot-v044.js?v=1.1.1-stable1
                                               -> gw-energy-pilot-v043.js?v=1.1.1-stable1
                                                    -> gw-energy-pilot-v042.js?v=1.1.1-stable1
                                                         -> gw-energy-pilot-v041-emhass-settings.js?v=1.1.1-stable1
                                                              -> gw-energy-pilot-v041.js?v=1.1.1-stable1
                                                                   -> gw-energy-pilot-v039.js?v=1.1.1-stable1
                                                                        -> gw-energy-pilot-v038.js?v=1.1.1-stable1
                                                                             -> gw-energy-pilot-v038-runtime.js?v=1.1.1-stable1
```

Every import in the active graph uses `1.1.1-stable1`. This ensures an
upgraded browser cannot reuse older button, strategy, settings or nested
plan/history modules while both release wrappers remain presentation-only.

The graph additionally imports a vendored Lit 3.3.3 production bundle and
`ep-control-surface.js` with the same cache boundary. The versioned files remain
the Home Assistant panel entry and presentation chain; v0.41 now mounts and
feeds the permanent component boundary.

## Permanent declarative control boundary

The operational controls are one fixed light-DOM Lit tree:

```text
ep-control-surface
├── ep-battery-actions
├── ep-automatic-control
├── ep-emhass-strategy
├── ep-battery-strategy
├── ep-optimize-action
└── ep-manual-ems-controls
```

The inherited structural renderer commits detached legacy markup around an
anchor and preserves the exact `ep-control-surface` node. It never assigns
`shadowRoot.innerHTML`. A real structural update may replace legacy cards, but
it must retain the ShadowRoot, `main`, control surface and every operational
control node. Settings hides the connected surface instead of disconnecting it.

The panel supplies frozen, narrowly scoped models and a small action gateway;
it does not pass the full Home Assistant object into the component tree.
Telemetry and API responses update component properties. Lit then patches only
the dynamic parts of the existing controls.

Every asynchronous control follows one state machine:

```text
idle -> pending -> acknowledged
                -> error
```

One native `click` starts at most one backend request. While pending, the
control group rejects another activation. A successful service or WebSocket
return is necessary but not sufficient: selected state remains derived from a
matching Home Assistant publication or API payload. Completion requires both,
in either order. A service error or a 15-second missing-publication timeout is
visible inline and leaves the confirmed selection unchanged. The original
focused node is retained and refocused after acknowledgement or error.

Battery AUTO/manual highlighting is exclusive. AUTO is selected only for
confirmed Automatic Control `on`; manual actions are eligible only for
confirmed `off` plus the matching canonical `control_command`. Unknown or
unavailable ownership selects nothing and disables unsafe actions. Manual EMS
mode buttons remain separate native actions: their existing select entity is
the sole service route and the backend remains responsible for applying the
already stored manual power value.

## Render ownership

### Initial structural render

The inherited complete renderer is allowed when the panel is first created or entity discovery has not completed.

### Context/structure render

A complete render is allowed for Home Assistant language/locale, user/admin context, theme/dark-mode context, entity-registry mapping, optional-card topology, configured PV-source topology or explicit narrow/layout structural changes.

### Normal telemetry patch

When context and structure signatures are unchanged, the `hass` setter does not queue the inherited complete render. It batches a live patch and mutates existing power/SOC/energy text, configured PV-source values, status classes, controller/EMHASS metrics, sliders, meter widths, diagnostics, static flow semantics and thermal values. The existing `main`, cards and controls remain connected.

Automatic Control ownership changes patch the existing Lit manual EMS pad in place.
While automatic ownership is active, the manual mode grid and power row use the
native `hidden` state and a compact ownership summary remains visible. When
manual control becomes available, those same mode-button and slider nodes are
revealed and enabled; they are not removed, replaced or reconstructed.

Home Assistant also assigns `narrow`, `route` and `panel` during host updates. The stable-DOM layer ignores repeated normalized values and semantically identical plain-JSON `panel` values, including a newly allocated clone of unchanged panel configuration. A real narrow-layout change patches `main` layout and the immutable control model only. A real nested panel-config/context change may still request structural legacy-content rendering, while preserving `main` and the complete permanent control tree. This keeps a pressed control connected between `pointerdown` and its native `click` without intercepting or synthesizing touch events.

### Header connectivity status

The one reachability control is created during structural render between Automatic Control ownership and the version badge. Normal status updates patch that same button and its three detail rows for Modbus, charger and effective EV coordination. Fine-pointer hover may reveal the details; keyboard focus, Escape and native tap/click provide the equivalent interaction without pointer capture, gesture cancellation or a hover/render lock.

### Battery quick actions

The four Battery quick actions keep their existing Lit button nodes while an action is pending and when Home Assistant publishes ownership and command state in separate events. The component derives one selection with explicit precedence: Automatic Control ON selects only AUTO; otherwise an exact manual `control_command` selects Max export, Pause or Max charge; an unrelated or unavailable command selects none. `.active` and `aria-pressed` are rendered together. Inactive AUTO uses the same neutral surface as the other inactive actions, so color no longer implies a second selection.

The persistent EMHASS cost-function selector follows the same rule: service completion and later entity publication update its component model without rebuilding `main`. Its explicit pending state remains authoritative across intervening telemetry patches. Manual EMS controls derive Automatic Control ownership from their newest immutable model rather than retaining a value from structural creation.

The persisted latest EMS-setpoint update time is rendered as secondary text inside the existing EMS-setpoint metric. A controller dispatcher update publishes the existing `control_command` entity attributes, and the v0.41 live patch updates only that text node. It does not rebuild the Controller card or treat ordinary telemetry polling as a new setpoint update.
### Battery Strategy refresh

Loading, pending, success/error, Custom values and SOC feedback belong to
`ep-battery-strategy`. Stable backend mode keys, not translated labels, remain
the control identity. Draft input state is local to that connected component;
backend confirmation updates its model without replacing the form or sliders.

The separate Hybrid strategy explanation is owned by v0.48 presentation while Hybrid is selected. Historical localization/presentation layers respect that marker, so normal telemetry preserves the existing note and strong-emphasis nodes. A genuine language or strategy context change may update the contents once.

### Plan graph refresh

A changed `plan_revision` or configured `P_batt` state invalidates graph data. Only the non-interactive body and footer of `.ep-v027-battery-plan-card` are rebuilt. The connected card shell, 12h/24h/36h range selector, S/M/L selector, expand action and window bar retain their DOM identity so a concurrent scoped refresh cannot cancel a native press. Range changes filter the existing cached dataset and must not trigger a Recorder request. Actual and forecast SOC are part of this same canonical scoped card.

### Execution-history refresh

The nested v0.51 module creates one canonical `.ep-v051-history-card` after the plan
card. Normal decision/read-back updates reuse its shell and replace only the
table body/note when the render key changes. Duplicate instances are removed.
The full table is a native-overflow modal with no backdrop filter, pointer
capture, gesture cancellation or scroll-position write. Closing it removes
only the modal. A normal history refresh must preserve `main`, the history-card
shell and every unrelated control.

### Optimize now

Optimize now is owned by `ep-optimize-action`. Its pending transaction requires
both the service return and a changed canonical `plan_revision`; an
orchestrator-running state alone is not optimistic success. A targeted plan
refresh rebuilds the Battery · Plan · Price contents inside its connected
interactive shell; `main`, Optimize now, Automatic Control and Battery Strategy
nodes remain connected.

## Native interaction and scroll contract

The active v0.41 normal telemetry path never writes `scrollTop` or `scrollLeft`, captures a touch pointer, cancels a vertical pan, delays telemetry because of hover, restores an earlier viewport snapshot or reuses a detached control to compensate for a full telemetry render. The Home Assistant browser/WebView owns pan and momentum scrolling.

Legacy v0.38 interaction and scroll-restoration functions remain available for historical entrypoints, but `__epV041StableRuntime` bypasses them before installation or use. The active architecture also bypasses the old base Automatic Control listener, v0.10/v0.16/v0.21/v0.38/v0.44 operational creators and the delegated v0.38 strategy listener. Historical localization and presentation passes must skip descendants of `ep-control-surface`.

All permanent actions are native `button[type="button"]` controls with native
`click` and keyboard semantics. EnergyPilot does not synthesize clicks, capture
pointers, call `preventDefault()` for these controls or add `touchstart` /
`touchend` action routes. Targets are at least 44 by 44 CSS pixels, pseudo
elements cannot receive pointer events, controls use `touch-action:
manipulation`, and containers preserve vertical `pan-y` scrolling.

On coarse-pointer/touch devices, native `:hover` never owns selected presentation. The v0.43 release layer restores inactive hover styles for Optimize now, EMHASS strategy, Battery Strategy, manual battery quick actions and the layout menu. Existing `.active` and `aria-pressed="true"` state remains authoritative. This rule is presentation-only: v0.43 adds no touch/pointer listeners, pointer capture or event cancellation.

## Motion contract

EnergyPilot-owned content has no CSS animations, CSS transitions, moving flow particles, animated pseudo-elements or modal backdrop filters. The policy is applied after complete renders and after scoped strategy, graph and modal updates.

The live-flow alternative is deliberately static. Existing connector nodes receive a fixed pipeline with an integrated arrowhead and directional brightness for active power, a quiet dot for finite near-zero idle power or a dashed line/question mark for unavailable power. Low/medium/high line thickness uses restrained 3/4/5-pixel steps relative to the strongest finite active connector in the same telemetry snapshot. Arrow/state children are created once per structural render and patched in place; they never pulse, move or transition. Each connector exposes a localized `role="img"` accessible name.

PV remains one compact group with one combined total. A structural render creates at most one internal ETA/DC source node and one aggregated external AC/PCC source node. Ordinary telemetry patches their values, link state and accessibility text without replacing either node or connector. Internal PV ends at the battery-side branch; external AC-coupled PV ends at the shared PCC side. The split is display-only and does not infer source-to-load attribution or alter EMHASS/control inputs.

## Required invariants

A normal telemetry burst must preserve the ShadowRoot, `main`, permanent
surface and every operational control node; keep idle scroll drift within two
pixels; produce no backward controlled-scroll samples; emit no JavaScript/page
errors or unknown WebSocket calls; and have zero
computed active EnergyPilot animations and transitions. One thousand telemetry
updates, a plan refresh, language/narrow/panel structural changes and Settings
open/close must satisfy the same operational-control identity invariant. An
Automatic Control ON/OFF cycle must change the manual pad's semantic disabled
state without replacing it. A plan refresh must preserve the graph card shell
and its 12h/24h/36h, S/M/L, expand and window controls while rebuilding its
data-dependent contents.

## Regression matrix

`tests/browser/test_frontend_control_surface.py` is the authoritative permanent
control gate. On desktop Chromium, iPad WebKit touch and iPhone WebKit touch it
executes 50 successful activations of every rendered control across the
critical groups: Battery actions,
Automatic Control, EMHASS strategy, Battery Strategy, Optimize, manual modes,
manual power, Custom save, minimum SOC and maximum SOC. Every group must record
exactly one backend call per activation. That is 1,500 activations per profile
and 4,500 in the complete three-profile gate.

The gate additionally covers delayed publication, backend state before service
return, service errors, missing acknowledgement, unknown/unavailable state,
duplicate activation while pending, telemetry between pointer-down and
pointer-up, scroll starting on a control, Enter/Space keyboard activation,
focus retention, portrait/landscape geometry, target size, overlap and 1,000
telemetry updates with complete node-identity preservation. WebKit here is an
automated browser-engine profile; physical iPhone Safari and Home Assistant
Companion acceptance remains the separate protocol in
`docs/FRONTEND_IPHONE_ACCEPTANCE.md`.

The complete stability matrix uses desktop Chromium at 1440 × 900, iPad
WebKit touch at 834 × 1112 and iPhone WebKit touch at 390 × 844. It is
implemented in `tests/browser/test_frontend_stability.py` and selected for the
active release by `tests/browser/test_frontend_stability_v110.py`. It retains
the established PV topology, 12h/24h/36h chart, settings, connectivity,
history, EV protection, native scrolling, static-flow and no-motion gates in
addition to the permanent-control assertions above.

## Contributor rules

- Do not call `_queueRender()` for normal v0.41 telemetry feedback when an existing scoped callback owns the update.
- Do not add scroll-position writes as a visual correction for render movement.
- Do not add pointer capture or global gesture cancellation to protect a control from telemetry.
- Do not install an operational listener outside the permanent Lit component
  tree or mutate its descendants from a historical module.
- Do not interpret a resolved service call as confirmed selected state; wait
  for the matching Home Assistant/API model.
- Do not re-enable motion without a separately documented ownership model and browser regressions on all three profiles.
- Preserve entity IDs, unique IDs, settings, backend APIs and GoodWe/EMHASS semantics unless a separate change explicitly requires them.
