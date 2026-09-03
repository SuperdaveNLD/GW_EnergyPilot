# Physical iPhone control acceptance

## Status and evidence boundary

The automated desktop Chromium, iPad WebKit and iPhone WebKit gates are green,
but Playwright WebKit is not branded iPhone Safari and does not exercise the
Home Assistant Companion WebView. Until this protocol is completed on a
physical device, the release status is:

> **Software ready, hardware acceptance open.**

This run validates the browser interaction path only. It must not be used to
change or infer GoodWe registers, EMS modes, setpoint signs, controller policy
or EMHASS ownership.

## Local Beta tests first pass

Run this harmless isolation pass before operating a real EnergyPilot control:

1. Open the dashboard layout menu and select **Beta tests**.
2. Tap each of the five numbered method buttons five times, at a normal pace.
   Wait one second after the final tap so the deliberately delayed counters are
   displayed.
3. Make one vertical scroll gesture starting on methods 2–5. That gesture must
   not increase `actions`. The original eight control variants remain under
   **Oude acht controletests tonen** when a legacy comparison is useful.
4. Open **Laatste events en export** and retain the JSON shown there. With a
   Web Inspector console the same payload is available as
   `__epBetaTests.json()`.
5. Repeat in Safari and Home Assistant Companion, ideally once in portrait and
   once in landscape.

The page uses local browser state only. It sends no Home Assistant service or
WebSocket call and cannot write GoodWe or start EMHASS. Interpret the counters
as follows:

- `pointerdown` absent: the physical event did not reach that target;
- `pointerdown` and `pointerup` rise but `click` does not: WebKit cancelled the
  native click before the action handler;
- methods 2 and 3 should produce one `pointer_action` per valid pointerup;
- method 4 reports `native_actions` when click arrives and `fallback_actions`
  when the 120 ms recovery supplies the missing action;
- method 5 should produce one `pointer_action` and at most one `deduped` click
  per tap, while `actions` remains exactly one per valid pointerup;
- `actions` rises exactly once per use: that native control path is healthy.

The counters are buffered without a reactive render during native click
synthesis and refresh after 650 ms of inactivity. For the legacy label-wrapped
switch, one physical use can legitimately produce click events for both the
label and its checkbox; `actions` remains the canonical completed-action count.
The result narrows the failing browser path, but does not by itself close the
real operational-control acceptance below.

## Beta.5 production-fallback pass

Beta.5 keeps the five numbered method buttons raw, but applies method 4's
120 ms recovery to the rest of the EnergyPilot panel. After installing beta.5
in Companion:

1. tap the dashboard layout button, Beta Tests entry and close button once;
2. reopen the layout menu and toggle one harmless card-visibility switch, then
   reset the dashboard layout;
3. open Settings, change tabs and return without saving;
4. test an operational action only when its real hardware effect is safe and
   reconcile it with the Home Assistant service/action log;
5. export `__epBetaTests.json()` and retain its
   `production_touch_fallback.metrics` and `targets` sections.

For every deliberate tap, `fallback_clicks` may rise when Companion omitted
native click. `late_clicks_suppressed` may rise if WebKit delivered it later.
Neither is an error. One physical tap must still cause exactly one visible
action and, for operational controls, exactly one matching backend request.
Starting a vertical scroll on a control must raise neither the completed action
nor its target fallback count.

## Beta.6 chart-control touch pass

The next beta additionally enlarges the real coarse-pointer targets for
`S/M/L`, `12h/24h/36h`, chart expand/footer actions and execution-history
open/close controls to at least 44 × 44 CSS pixels. Verify every segment with
one ordinary tap, then open and close the full 48-hour history once. Each tap
must visibly take effect once; starting a vertical scroll within the same
controls must not activate them. Confirm that the two segmented groups wrap
without horizontal card overflow in portrait and landscape.

## Safety prerequisites

Battery quick actions and manual EMS modes can move significant real power.
Run their 50-activation repetitions only on an authorized acceptance
installation with an operator who understands the inverter, a documented safe
power envelope, working protective equipment and an immediate way to return to
mode 1 / 0 W. Do not exercise mode 7 Off-grid on a live installation unless
that installation is explicitly designed and prepared for it. A safe
representative manual mode such as Hold may be used for the interaction count;
the protocol tests delivery, not hardware mode semantics.

Before starting:

1. Record EnergyPilot commit, Home Assistant version, Companion version, iOS
   version, iPhone model, inverter model/firmware and EMHASS version.
2. Confirm the Home Assistant service/action trace or an equivalent backend
   audit is available so request counts can be compared with physical taps.
3. Confirm no second operator, automation or browser session will operate the
   same controls during the run.
4. Capture the initial Automatic Control state, EMS mode/setpoint and selected
   EMHASS/Battery strategies.
5. Enable iPhone Web Inspector for the Safari pass and arrange a Mac Safari
   Develop connection. For Companion, use the app's supported WebView debug
   route for the installed build; if unavailable, retain the in-panel trace and
   Home Assistant backend audit.

## Passive trace

The permanent control surface installs a bounded, passive ring buffer. It does
not cancel events or alter service behavior. At the browser console:

```js
__epControlTrace.enable()
__epControlTrace.clear()
__epControlTrace.snapshot()
__epControlTrace.json()
```

The trace records `pointerdown`, `pointermove`, `pointerup`, `pointercancel`,
native `click`, service/WebSocket start/end/error, Home Assistant publication,
surface mounting and structural renders. Every pointer/click row contains the
canonical control ID, stable node identity and `isConnected`; every row also
contains the permanent surface identity and connection state.
Beta.5 additionally records `touch-fallback-native_clicks`,
`touch-fallback-fallback_clicks` and
`touch-fallback-late_clicks_suppressed` without storing credentials or entity
values.

Export `__epControlTrace.json()` before reloading or closing the page. Store it
with the matching Home Assistant action/service audit and a screen recording.
Do not include credentials, access tokens, private URLs or unrelated entity
data in the evidence package.

## Required device passes

Run the complete protocol twice on the same physical iPhone:

- current iOS Safari opened directly to the EnergyPilot panel;
- current Home Assistant Companion app opened to the same panel.

For each host, run portrait and landscape. Begin each orientation with a fresh
panel load, then verify that the six permanent component groups are visible,
no controls overlap, every target is comfortably tappable and vertical scroll
can start on top of a button or slider without activating it.

## Fifty-activation matrix

For each host, execute 50 successful physical activations of every critical
group and reconcile exactly 50 matching backend requests:

| Group | Safe acceptance action | Required confirmation |
| --- | --- | --- |
| Battery actions | Alternate only actions approved for the test power envelope | One exclusive confirmed AUTO/manual selection; no call from scroll |
| Automatic Control | Alternate ON/OFF after each acknowledgement | Confirmed switch state; manual controls lock/unlock without replacement |
| EMHASS strategy | Rotate Profit, Cost and Self-consumption | Confirmed select state; no optimistic highlight |
| Battery Strategy | Rotate approved profiles | Confirmed API payload and fresh plan; Custom remains distinct |
| Optimize now | Wait for each new `plan_revision` | One solve request and one confirmed revision per tap |
| Manual modes | Use an approved safe representative mode or lab plan | One select call per tap and confirmed GoodWe read-back where available |
| Manual power | Alternate two approved values | One number call per committed slider change |
| Custom save | Alternate two validated test value sets | One Custom API call and confirmed returned payload |
| Minimum SOC | Alternate two safe percentages | One number call and confirmed synchronized value |
| Maximum SOC | Alternate two safe percentages above minimum | One number call and confirmed returned value |

During every group:

- include short, normal and long presses;
- include deliberately rapid second taps while the first action is pending;
- start at least five vertical scrolls on the control itself;
- keep normal live telemetry running;
- verify pending feedback, error visibility and focus/selection consistency;
- never count a rejected pending duplicate as a successful activation.

The acceptance criterion is exactly one request for every successful physical
activation, zero requests for scroll gestures, zero duplicate requests, no
false selected state and no disconnected/replaced permanent control node.

## Ordering and failure scenarios

Use a test proxy, developer fixture or safely controlled backend delay; do not
alter production controller semantics. Verify at least once per host:

1. service return delayed until after matching Home Assistant publication;
2. service return first and matching publication delayed;
3. explicit service/WebSocket error followed by a successful retry;
4. missing acknowledgement until the visible timeout;
5. `unknown` and `unavailable` ownership/state;
6. telemetry publication between physical pointer-down and pointer-up;
7. 1,000 ordinary telemetry publications while retaining surface and control
   identities;
8. real language, narrow/orientation and panel-config structural changes;
9. Enter and Space activation with an external keyboard, if available.

For each scenario, the trace must show one continuous node identity from
pointer-down through click and acknowledgement/error. Matching publication may
precede service completion, but the component may leave `pending` only after
both have occurred.

## Acceptance record

Fill and attach this block to the issue or review record:

```text
Commit:
Date/operator:
iPhone / iOS:
Home Assistant Core / frontend:
Companion version:
Inverter / firmware:
EMHASS version:
Safari portrait / landscape: PASS | FAIL
Companion portrait / landscape: PASS | FAIL
10 groups × 50, exact request count: PASS | FAIL
Delayed/reordered/error/unknown cases: PASS | FAIL
1,000 telemetry identity run: PASS | FAIL
Trace files:
Backend audit files:
Screen recording:
Observed defect(s):
Final hardware acceptance: PASS | OPEN
```

Any duplicate/missing request, scroll-triggered action, disconnected control,
optimistic selection or unexplained physical-device-only difference keeps
hardware acceptance open and must be diagnosed from the paired trace before a
new workaround is proposed.

## Standards basis

The architecture follows these primary sources, which must be rechecked when a
future frontend-runtime upgrade changes the assumptions:

- Home Assistant [custom panels](https://developers.home-assistant.io/docs/frontend/custom-ui/creating-custom-panels/), [frontend architecture](https://developers.home-assistant.io/docs/frontend/architecture/) and [data flow](https://developers.home-assistant.io/docs/frontend/data/);
- Lit [rendering](https://lit.dev/docs/v2/components/rendering/), [reactive properties](https://lit.dev/docs/components/properties/) and [events](https://lit.dev/docs/components/events/);
- WAI-ARIA APG [button pattern](https://www.w3.org/WAI/ARIA/apg/patterns/button/) and W3C [Rules for Using ARIA](https://www.w3.org/TR/using-aria/);
- W3C [Pointer Events](https://www.w3.org/TR/pointerevents4/) for `touch-action`;
- Apple [UI design dos and don'ts](https://developer.apple.com/design/tips/) for 44-point touch targets;
- WCAG 2.2 [Target Size (Enhanced)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced);
- Playwright's [browser documentation](https://playwright.dev/docs/browsers), which explains why engine automation is not physical branded-browser acceptance.
