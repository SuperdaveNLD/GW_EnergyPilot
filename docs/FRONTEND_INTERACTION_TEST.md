# Frontend interaction and flow validation

Use this checklist on an installation that previously showed flashing or unclickable dashboard controls.

## Preparation

1. Install the candidate branch.
2. Restart Home Assistant so the old ES-module graph and monkey patches are removed from memory.
3. Fully reload the browser or Home Assistant companion app webview.
4. Confirm the panel URL contains the cache key `0.35-controls-flow2`.
5. Leave the dashboard open while normal GoodWe and Home Assistant state updates continue.

A browser refresh without the Home Assistant restart is not sufficient when testing replacement prototype wrappers from an earlier candidate.

## Interaction validation

Repeat each action several times, including while live values are changing:

- open and close Dashboard layout;
- toggle card visibility;
- collapse and restore every card with the yellow button;
- maximize and restore every card with the green button;
- hide a card with the red button and restore it through Dashboard layout;
- open Settings, change tabs and return to the dashboard;
- press Optimize now;
- open the Battery · Plan · Price detail view;
- use chart size and refresh controls;
- test mouse, touch and keyboard Enter/Space where available.

Expected result:

- no control flashes because JavaScript changes hover state;
- no pointer is captured;
- one native click performs exactly one action;
- live telemetry continues updating;
- collapse/maximize does not rebuild the complete panel immediately.

## Flow-direction validation

GoodWe signs:

```text
grid negative = import
grid positive = export
battery negative = charging
battery positive = discharging
```

Verify the moving particles visually:

| Situation | Expected motion |
| --- | --- |
| PV production | PV -> center hub |
| Grid import | Grid -> center hub |
| Grid export | Center hub -> grid |
| House consumption | Center hub -> house |
| Battery charging | Center hub -> battery |
| Battery discharging | Battery -> center hub |

Test import/export and charge/discharge separately. A mixed-energy moment is not sufficient evidence because several links move simultaneously.

## Failure evidence

When a failure remains, capture:

- browser/app and version;
- desktop/mobile and input type;
- the exact button/action;
- relevant grid and battery signed power values;
- a short screen recording;
- browser console errors;
- EnergyPilot debug report when the problem also involves backend state changes.
