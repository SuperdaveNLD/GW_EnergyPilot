# GW EnergyPilot v0.46 Beta

v0.46 refines the display-only external PV setup introduced in v0.45.

It also carries the final static live-flow presentation refinement: arrowheads are integrated into the connector pipes, directional brightness reinforces the physical direction, and low/medium/high strength uses restrained 3/4/5-pixel steps. Idle and unavailable states remain deliberately quiet and motion-free.

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
- the inherited PV total, stable-DOM, touch, scrolling, Optimize, SOC chart and static-flow contracts.

## Safety and compatibility

v0.46 remains display-only. It changes no GoodWe register, Modbus read/write, EMS mode or setpoint ordering, Automatic Control decision, EMHASS input/topology/objective, persistent plan, entity unique ID, device identity, Store key or grid-accounting behavior.
