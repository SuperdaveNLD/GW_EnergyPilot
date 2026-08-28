# GW EnergyPilot v0.43 Beta

v0.43 is a focused mobile frontend reliability update for iPhone and iPad users. It fixes controls that could appear to retain an old selection, or show two selected states, after tapping another option.

## Operator-visible changes

- Optimize now no longer retains a misleading touch-hover presentation after activation.
- EMHASS Profit, Cost and Self-consumption always show only the application-selected strategy.
- Battery Strategy always shows only the profile whose `aria-pressed` state is active.
- Manual battery quick actions, including max export, no longer look active solely because WebKit retained `:hover` after a tap.
- The dashboard layout menu button returns to its inactive presentation when the menu closes.

## Root cause and implementation

Mobile WebKit can retain CSS `:hover` after a tap. Several older frontend layers styled `:hover` similarly to the true selected state, so the previous button could remain blue/green even though the application had already selected and executed another action.

v0.43 adds one touch/coarse-pointer media-query layer that restores the inactive base presentation for those hover states. Actual selection remains owned by the existing `.active` class or `aria-pressed="true"`. The layer does not intercept native events and does not modify the backend or any action handler.

Normal v0.41+ telemetry already preserves control nodes. Complete structural renders still rebuild controls with their existing handlers; the expanded browser regression deliberately triggers such a render during activation and verifies that the action still executes.

## Validation scope

The release candidate includes automated coverage for:

- desktop Chromium at 1440 × 900;
- iPad WebKit touch at 834 × 1112;
- iPhone WebKit touch at 390 × 844;
- repeated taps and action-call evidence for Optimize now, EMHASS strategy, Battery Strategy and manual battery quick actions;
- exactly one visible active/pressed selection per selector group;
- repeated layout-menu open/close;
- interaction during telemetry, after a deliberate structure render and during a structure render started on pointer-down;
- JavaScript errors, unknown WebSocket calls, stable DOM identity, scroll behavior and the existing zero-motion contract.

These deterministic browser profiles are release regressions; broad physical-device and Home Assistant companion-app field coverage remains Beta scope.

## Safety and compatibility

v0.43 does not change:

- GoodWe register definitions, Modbus read blocks or write behavior;
- EMS mappings, setpoint semantics or the established `47512 -> wait -> 47511` write order;
- Automatic Control decisions, Battery Saver optimization behavior or EMHASS ownership;
- Home Assistant entity IDs, unique IDs, config-entry data, persistent Store keys or stable device identity.

EMHASS remains an external prerequisite and is not installed or bundled by GW EnergyPilot.
