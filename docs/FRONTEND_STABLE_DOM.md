
# Frontend stable-DOM architecture

## Status

This document is the canonical frontend render/interaction decision for **GW EnergyPilot v0.46 Beta**. v0.46 retains the full v0.45 stable behavior and adds the grouped external-PV master-switch presentation through the existing settings owner.

No GoodWe register, Modbus, EMS or EMHASS backend behavior is defined here.

## Problem statement

The inherited base panel builds its complete ShadowRoot with `innerHTML`. Older release layers filtered and batched relevant Home Assistant updates, but an accepted update still ran the complete render chain. That detached and recreated cards and controls while WebKit could simultaneously be processing a touch pan or momentum scroll.

The v0.38-v0.40 stack attempted to compensate with interaction guards, delayed renders, button reuse, scroll snapshots/restoration and transition suppression. Those mechanisms reduced individual symptoms but could not make a destructive telemetry render equivalent to a stable page.

## Active entrypoint chain

```text
Home Assistant PANEL_MODULE
  -> gw-energy-pilot-v046.js?v=0.46-external-pv1
  -> gw-energy-pilot-v045.js?v=0.46-external-pv1
  -> gw-energy-pilot-v044.js?v=0.46-external-pv1
  -> gw-energy-pilot-v043.js?v=0.46-external-pv1
  -> gw-energy-pilot-v042.js?v=0.46-external-pv1
  -> gw-energy-pilot-v041-emhass-settings.js?v=0.46-external-pv1
  -> gw-energy-pilot-v041.js?v=0.46-external-pv1
  -> gw-energy-pilot-v039.js?v=0.46-external-pv1
  -> gw-energy-pilot-v038.js?v=0.46-external-pv1
  -> gw-energy-pilot-v038-runtime.js?v=0.46-external-pv1
  -> gw-energy-pilot-v038-strategy.js?v=0.46-external-pv1
```

Every local import reachable from the v0.46 entrypoint uses `0.46-external-pv1`. This reloads the modified settings module after upgrade while preserving the behavioral ownership of historical layers.

## Render ownership

### Initial structural render

The inherited complete renderer is allowed when the panel is first created or entity discovery has not completed.

### Context/structure render

A complete render is allowed for Home Assistant language/locale, user/admin context, theme/dark-mode context, entity-registry mapping, optional-card topology, configured PV-source topology or explicit narrow/layout structural changes.

### Normal telemetry patch

When context and structure signatures are unchanged, the `hass` setter does not queue the inherited complete render. It batches a live patch and mutates existing power/SOC/energy text, configured PV-source values, status classes, controller/EMHASS metrics, sliders, meter widths, diagnostics, static flow semantics and thermal values. The existing `main`, cards and controls remain connected.

### Battery Strategy refresh

Loading, pending, success/error and Custom-SOC feedback rerender only `.ep-v038-strategy`. Stable backend mode keys, not translated labels, remain the control identity.

### Plan graph refresh

A changed `plan_revision` or configured `P_batt` state invalidates graph data. Only `.ep-v027-battery-plan-card` is replaced. Actual and forecast SOC are part of this same canonical scoped card.

### Optimize now

The inherited v0.10 Optimize listener calls the existing Home Assistant `button.press` entity correctly, but requested `_queueRender()` when the asynchronous solve/publish service completed. v0.44 replaces only that listener and moves the one canonical action under `main` as a safe-area-aware fixed control, independent of the optional EMHASS card. Busy/idle text, `aria-busy`, orchestrator state, last-success/error details and the canonical plan revision are patched in place. A targeted plan refresh may replace the Battery · Plan · Price card, but `main`, Optimize now, layout, Automatic Control and Battery Strategy nodes remain connected.

## Native interaction and scroll contract

The active v0.41 normal telemetry path never writes `scrollTop` or `scrollLeft`, captures a touch pointer, cancels a vertical pan, delays telemetry because of hover, restores an earlier viewport snapshot or reuses a detached control to compensate for a full telemetry render. The Home Assistant browser/WebView owns pan and momentum scrolling.

Legacy v0.38 interaction and scroll-restoration functions remain available for historical entrypoints, but `__epV041StableRuntime` bypasses them before installation or use.

On coarse-pointer/touch devices, native `:hover` never owns selected presentation. The v0.43 release layer restores inactive hover styles for Optimize now, EMHASS strategy, Battery Strategy, manual battery quick actions and the layout menu. Existing `.active` and `aria-pressed="true"` state remains authoritative. This rule is presentation-only: v0.43 adds no touch/pointer listeners, pointer capture or event cancellation.

## Motion contract

EnergyPilot-owned content has no CSS animations, CSS transitions, moving flow particles, animated pseudo-elements or modal backdrop filters. The policy is applied after complete renders and after scoped strategy, graph and modal updates.

The live-flow alternative is deliberately static. Existing connector nodes receive a fixed pipeline, one physical-direction arrow for active power, a dot for finite near-zero idle power or a dashed line/question mark for unavailable power. Low/medium/high line thickness is relative to the strongest finite active connector in the same telemetry snapshot. Arrow/state children are created once per structural render and patched in place; they never pulse, move or transition. Each connector exposes a localized `role="img"` accessible name.

## Required invariants

A normal telemetry burst must preserve `main`, Dashboard layout-button, Automatic Control button and Battery Strategy button identity; keep idle scroll drift within two pixels; produce no backward controlled-scroll samples; emit no JavaScript/page errors or unknown WebSocket calls; and have zero computed active EnergyPilot animations and transitions. A plan refresh may replace the graph card, but none of those four persistent nodes.

## Regression matrix

The required release gate uses desktop Chromium at 1440 × 900, iPad WebKit touch at 834 × 1112 and iPhone WebKit touch at 390 × 844. It is implemented in `tests/browser/test_frontend_stability.py` and selected for v0.46 by `tests/browser/test_frontend_stability_v046.py`. All three profiles require one external-PV group, four fields, off-state disabling/dimming, on-state activation and value preservation, plus every inherited v0.45 stable-DOM, touch, SOC, flow, Optimize and scrolling assertion.

## Contributor rules

- Do not call `_queueRender()` for normal v0.41 telemetry feedback when an existing scoped callback owns the update.
- Do not add scroll-position writes as a visual correction for render movement.
- Do not add pointer capture or global gesture cancellation to protect a control from telemetry.
- Do not re-enable motion without a separately documented ownership model and browser regressions on all three profiles.
- Preserve entity IDs, unique IDs, settings, backend APIs and GoodWe/EMHASS semantics unless a separate change explicitly requires them.
