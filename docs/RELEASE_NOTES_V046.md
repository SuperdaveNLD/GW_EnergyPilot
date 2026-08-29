# GW EnergyPilot v0.46 Beta

v0.46 refines the display-only external PV setup introduced in v0.45.

Because v0.46 contains the complete v0.45 chain, upgrading directly from v0.44 or earlier also adds the combined internal/external PV insight sensor and PV settings page, actual-versus-forecast SOC chart, stable Battery Strategy SOC draft, static accessible live-flow direction and the viewport-safe floating **Optimize now** action. See `RELEASE_NOTES_V045.md` for that inherited scope.

It also carries the final static live-flow presentation refinement: arrowheads are integrated into the connector pipes, directional brightness reinforces the physical direction, and low/medium/high strength uses restrained 3/4/5-pixel steps. Idle and unavailable states remain deliberately quiet and motion-free.

The Controller card is more compact under automatic ownership. While **Automatic Control** is on, the twelve-mode manual EMS grid and power slider remain mounted but are semantically hidden behind a concise ownership summary. Turning Automatic Control off reveals and enables those same DOM nodes, including when the dashboard initially loaded in automatic mode. Missing manual entities remain visible as a compact unavailable state.

Mobile control reliability is hardened for Home Assistant host updates. Repeated `narrow` assignments and cloned-but-equivalent panel configuration no longer replace a pressed control between `pointerdown` and the native `click`; a genuine layout or nested configuration change still receives a structural render. Battery quick actions, the EMHASS cost-function selector and manual EMS controls now patch their existing nodes through delayed or split state publication. Automatic Control remains the sole selected quick action while it owns the inverter, and an EMHASS strategy request stays locked until its complete service transaction finishes so a second tap cannot start a duplicate optimization (#84).

## External PV master switch

The dashboard **PV** settings page now has a separate **Include external PV** switch. It is independent from **Include internal GoodWe PV**.

- Switch OFF: the four external entity fields are visibly dimmed and disabled, and external sources are not followed or included in `pv_generation_power`.
- Switch ON: all four fields become active immediately and may be searched or edited.
- Switching OFF preserves the configured entity IDs, so they return when the feature is enabled again.

The four external source fields are grouped inside one panel instead of being presented as four separate cards.

## Upgrade behavior

Fresh installations start with external PV disabled. A v0.45 installation that already has at least one external PV entity configured remains enabled on upgrade until the operator explicitly saves the new switch. This prevents an existing combined PV total from silently disappearing.

## Frontend and validation

`gw-energy-pilot-v046.js` is a presentation-only release wrapper over the complete v0.45 chain. The active module graph uses the fresh `0.46-external-pv1` cache key.

The desktop Chromium, iPad WebKit and iPhone WebKit matrix verifies:

- one grouped external-PV panel containing exactly four entity fields;
- disabled/dimmed fields while the master switch is off;
- immediately enabled fields while the switch is on;
- preservation of configured entity values across an off/on cycle;
- compact manual controls and working manual release after Automatic Control is turned off;
- native presses surviving equivalent Home Assistant host-property churn;
- delayed/split quick-action and EMHASS publication without double selection or duplicate calls;
- the inherited PV total, stable-DOM, touch, scrolling, Optimize, SOC chart and static-flow contracts.

## Safety and compatibility

v0.46 changes dashboard presentation and interaction stability only. It changes no GoodWe register, Modbus read/write, EMS mode or setpoint ordering, Automatic Control decision, EMHASS input/topology/objective, persistent plan, entity unique ID, device identity, Store key or grid-accounting behavior.
