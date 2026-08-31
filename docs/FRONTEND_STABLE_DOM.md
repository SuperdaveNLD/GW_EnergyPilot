
# Frontend stable-DOM architecture

## Status

This document is the canonical frontend render/interaction decision for **GW EnergyPilot v1.0.1-beta.4**. The beta retains the complete stable behavior through a presentation-only wrapper; its nested v0.51 feature layer supplies the scoped execution-history card.

No GoodWe register, Modbus, EMS or EMHASS backend behavior is defined here.

## Problem statement

The inherited base panel builds its complete ShadowRoot with `innerHTML`. Older release layers filtered and batched relevant Home Assistant updates, but an accepted update still ran the complete render chain. That detached and recreated cards and controls while WebKit could simultaneously be processing a touch pan or momentum scroll.

The v0.38-v0.40 stack attempted to compensate with interaction guards, delayed renders, button reuse, scroll snapshots/restoration and transition suppression. Those mechanisms reduced individual symptoms but could not make a destructive telemetry render equivalent to a stable page.

## Active entrypoint chain

```text
Home Assistant PANEL_MODULE
  -> gw-energy-pilot-v101.js?v=1.0.1-beta4
       -> gw-energy-pilot-v051.js?v=1.0.1-beta4
            -> gw-energy-pilot-v051-history.js?v=1.0.1-beta4
            -> gw-energy-pilot-v050.js?v=1.0.1-beta4
            -> gw-energy-pilot-v049.js?v=1.0.1-beta4
                 -> gw-energy-pilot-v048.js?v=1.0.1-beta4
                      -> gw-energy-pilot-v047.js?v=1.0.1-beta4
                           -> gw-energy-pilot-v046.js?v=1.0.1-beta4
                                -> gw-energy-pilot-v045.js?v=1.0.1-beta4
                                     -> gw-energy-pilot-v044.js?v=1.0.1-beta4
                                          -> gw-energy-pilot-v043.js?v=1.0.1-beta4
                                               -> gw-energy-pilot-v042.js?v=1.0.1-beta4
                                                    -> gw-energy-pilot-v041-emhass-settings.js?v=1.0.1-beta4
                                                         -> gw-energy-pilot-v041.js?v=1.0.1-beta4
                                                              -> gw-energy-pilot-v039.js?v=1.0.1-beta4
                                                                   -> gw-energy-pilot-v038.js?v=1.0.1-beta4
                                                                        -> gw-energy-pilot-v038-runtime.js?v=1.0.1-beta4
```

Every import in the active v1.0.1-beta.4 graph uses `1.0.1-beta4`. This ensures
an upgraded browser cannot reuse older button-patch or nested plan/history
modules while keeping the beta wrapper presentation-only.

## Render ownership

### Initial structural render

The inherited complete renderer is allowed when the panel is first created or entity discovery has not completed.

### Context/structure render

A complete render is allowed for Home Assistant language/locale, user/admin context, theme/dark-mode context, entity-registry mapping, optional-card topology, configured PV-source topology or explicit narrow/layout structural changes.

### Normal telemetry patch

When context and structure signatures are unchanged, the `hass` setter does not queue the inherited complete render. It batches a live patch and mutates existing power/SOC/energy text, configured PV-source values, status classes, controller/EMHASS metrics, sliders, meter widths, diagnostics, static flow semantics and thermal values. The existing `main`, cards and controls remain connected.

Automatic Control ownership changes patch the existing manual EMS pad in place.
While automatic ownership is active, the manual mode grid and power row use the
native `hidden` state and a compact ownership summary remains visible. When
manual control becomes available, those same mode-button and slider nodes are
revealed and enabled; they are not removed, replaced or reconstructed.

Home Assistant also assigns `narrow`, `route` and `panel` during host updates. The stable-DOM layer ignores repeated normalized `narrow` values and semantically identical plain-JSON `panel` values, including a newly allocated clone of unchanged panel configuration. A real narrow-layout or nested panel-config change still delegates to the inherited setter and requests a complete structural render. This keeps a pressed control connected between `pointerdown` and its native `click` without intercepting or synthesizing touch events.

### Header connectivity status

The one reachability control is created during structural render between Automatic Control ownership and the version badge. Normal status updates patch that same button and its three detail rows for Modbus, charger and effective EV coordination. Fine-pointer hover may reveal the details; keyboard focus, Escape and native tap/click provide the equivalent interaction without pointer capture, gesture cancellation or a hover/render lock.

### Battery quick actions

The four Battery quick actions keep their existing button nodes while an action is pending and when Home Assistant publishes ownership and command state in separate events. The v0.41 live patch derives one selection with explicit precedence: Automatic Control ON selects only AUTO; otherwise an exact manual `control_command` selects Max export, Pause or Max charge; an unrelated or unavailable command selects none. `.active` and `aria-pressed` are patched together. Inactive AUTO uses the same neutral surface as the other inactive actions, so color no longer implies a second selection.

The persistent EMHASS cost-function selector follows the same rule: service completion and later entity publication patch its existing buttons, label and accessibility state without rebuilding `main`. Its explicit busy state remains authoritative across intervening telemetry patches, so a second strategy/optimization request cannot start while the first service call is still running. Manual EMS controls read Automatic Control ownership at event time rather than retaining the ownership value from the structural render; pending, enabled and message feedback is patched in place. This matters when Automatic Control changes through a normal stable-DOM state event after those controls were created.

The persisted latest EMS-setpoint update time is rendered as secondary text inside the existing EMS-setpoint metric. A controller dispatcher update publishes the existing `control_command` entity attributes, and the v0.41 live patch updates only that text node. It does not rebuild the Controller card or treat ordinary telemetry polling as a new setpoint update.

### Battery Strategy refresh

Loading, pending, success/error and Custom-SOC feedback rerender only `.ep-v038-strategy`. Stable backend mode keys, not translated labels, remain the control identity.

The separate Hybrid strategy explanation is owned by v0.48 presentation while Hybrid is selected. Historical localization/presentation layers respect that marker, so normal telemetry preserves the existing note and strong-emphasis nodes. A genuine language or strategy context change may update the contents once.

### Plan graph refresh

A changed `plan_revision` or configured `P_batt` state invalidates graph data. Only the non-interactive body and footer of `.ep-v027-battery-plan-card` are rebuilt. The connected card shell, S/M/L selector, expand action and window bar retain their DOM identity so a concurrent scoped refresh cannot cancel a native press. Actual and forecast SOC are part of this same canonical scoped card.

### Execution-history refresh

The nested v0.51 module creates one canonical `.ep-v051-history-card` after the plan
card. Normal decision/read-back updates reuse its shell and replace only the
table body/note when the render key changes. Duplicate instances are removed.
The full table is a native-overflow modal with no backdrop filter, pointer
capture, gesture cancellation or scroll-position write. Closing it removes
only the modal. A normal history refresh must preserve `main`, the history-card
shell and every unrelated control.

### Optimize now

The inherited v0.10 Optimize listener calls the existing Home Assistant `button.press` entity correctly, but requested `_queueRender()` when the asynchronous solve/publish service completed. v0.44 replaces only that listener and moves the one canonical action under `main` as a safe-area-aware fixed control, independent of the optional EMHASS card. Busy/idle text, `aria-busy`, orchestrator state, last-success/error details and the canonical plan revision are patched in place. A targeted plan refresh rebuilds the Battery · Plan · Price contents inside its connected interactive shell; `main`, Optimize now, layout, Automatic Control and Battery Strategy nodes also remain connected.

## Native interaction and scroll contract

The active v0.41 normal telemetry path never writes `scrollTop` or `scrollLeft`, captures a touch pointer, cancels a vertical pan, delays telemetry because of hover, restores an earlier viewport snapshot or reuses a detached control to compensate for a full telemetry render. The Home Assistant browser/WebView owns pan and momentum scrolling.

Legacy v0.38 interaction and scroll-restoration functions remain available for historical entrypoints, but `__epV041StableRuntime` bypasses them before installation or use.

On coarse-pointer/touch devices, native `:hover` never owns selected presentation. The v0.43 release layer restores inactive hover styles for Optimize now, EMHASS strategy, Battery Strategy, manual battery quick actions and the layout menu. Existing `.active` and `aria-pressed="true"` state remains authoritative. This rule is presentation-only: v0.43 adds no touch/pointer listeners, pointer capture or event cancellation.

## Motion contract

EnergyPilot-owned content has no CSS animations, CSS transitions, moving flow particles, animated pseudo-elements or modal backdrop filters. The policy is applied after complete renders and after scoped strategy, graph and modal updates.

The live-flow alternative is deliberately static. Existing connector nodes receive a fixed pipeline with an integrated arrowhead and directional brightness for active power, a quiet dot for finite near-zero idle power or a dashed line/question mark for unavailable power. Low/medium/high line thickness uses restrained 3/4/5-pixel steps relative to the strongest finite active connector in the same telemetry snapshot. Arrow/state children are created once per structural render and patched in place; they never pulse, move or transition. Each connector exposes a localized `role="img"` accessible name.

## Required invariants

A normal telemetry burst must preserve `main`, Dashboard layout-button, Automatic Control button, header connectivity button and Battery Strategy button identity; keep idle scroll drift within two pixels; produce no backward controlled-scroll samples; emit no JavaScript/page errors or unknown WebSocket calls; and have zero computed active EnergyPilot animations and transitions. An Automatic Control ON/OFF cycle must additionally preserve the manual pad, mode-grid, mode-button, power-row and slider nodes while changing their semantic visibility and disabled state. A plan refresh must preserve the graph card shell and its S/M/L, expand and window controls while rebuilding its data-dependent contents.

## Regression matrix

The required release gate uses desktop Chromium at 1440 × 900, iPad WebKit touch at 834 × 1112 and iPhone WebKit touch at 390 × 844. It is implemented in `tests/browser/test_frontend_stability.py` and selected for v1.0.1-beta.4 by `tests/browser/test_frontend_stability_v101.py`. Touch profiles repeatedly tap every affected group, verify executed actions and exactly one active selection, cycle the menu, run telemetry concurrently and exercise deliberate structural renders. All three profiles emulate Home Assistant's repeated same-value and cloned-equivalent host-property assignments, hold a native press across one such update and prove that a genuinely changed nested panel config still renders. They also hold Optimize now and EMHASS strategy presses across rapid live-copy patches and require unchanged button child nodes until the native click is delivered. They force a plan-card refresh during a physical S/M/L press and require exactly one delivered click with stable card/header/control identity. They also require the Hybrid explanation to retain node identity, height and child-list stability through sixty telemetry patches. The matrix further requires the zero-centered two-deadband scale, overlap validation and responsive settings layout; the header reachability control in its exact position with green/red/live-detail transitions and stable node identity; one external-PV group with four fields and correct switch/value preservation; compact manual controls with stable node identity across ownership changes; split/delayed Battery quick-action and EMHASS publication; authoritative busy locking; editable Custom costs with stable main-node identity and larger typography; combined PV and bounded SOC telemetry; all static flow states; the single history card, immutable wanted-SOC history, detailed source bars, verified EV-protection underlays and full-table modal; a stationary unfocused SOC slider draft; one viewport-safe Optimize action; zero complete Optimize renders; native scroll anchoring; and working scroll after scoped card refreshes.

## Contributor rules

- Do not call `_queueRender()` for normal v0.41 telemetry feedback when an existing scoped callback owns the update.
- Do not add scroll-position writes as a visual correction for render movement.
- Do not add pointer capture or global gesture cancellation to protect a control from telemetry.
- Do not re-enable motion without a separately documented ownership model and browser regressions on all three profiles.
- Preserve entity IDs, unique IDs, settings, backend APIs and GoodWe/EMHASS semantics unless a separate change explicitly requires them.
