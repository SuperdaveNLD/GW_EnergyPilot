# GW EnergyPilot v0.39 Beta

v0.39 is a focused frontend reliability and localization release on top of the rebuilt v0.38 control path. It publishes the already-reviewed strategy-hover fix and completes the remaining Dutch customer-facing Controller copy without changing GoodWe, EMS or EMHASS control semantics.

## Battery Strategy hover stability

The v0.38 strategy controls already use stable backend profile keys and delegated actions. A remaining visual flicker could still appear under a stationary desktop mouse because the inherited full ShadowRoot render briefly detaches and reinserts the reused strategy node. Native CSS `:hover` disappears during that synchronous detach and returns afterwards, making the transition look like a blink.

v0.39 carries forward the presentation-only hover-continuity fix:

- the already-hovered v0.38 strategy button keeps a visual stable-hover class through the synchronous inherited render;
- delegated pointer movement keeps that class aligned with the real mouse position and panel leave clears it;
- touch/non-mouse input does not keep a synthetic hover state;
- hover never blocks telemetry, never queues a second render lock and never captures a pointer.

This is deliberately separate from click ownership. The v0.38 delegated strategy-control contract remains authoritative.

## Complete Dutch Controller copy

Dutch Home Assistant sessions now localize the remaining inherited customer-facing controller text, including:

- Controller window label, EnergyPilot control heading and Automatic Control button;
- EMS mode label and localized GoodWe mode names for modes 1–12;
- EMS setpoint / EnergyPilot target labels and restart safety note;
- Battery Strategy descriptions, using canonical frontend profile localization rather than English backend metadata;
- manual EMS heading, lock/status text, setpoint label, ARIA label and mode tooltips;
- known manual operator/status messages;
- the automatic-strategy fallback note and telemetry badge.

Technical identifiers and product/profile names remain unchanged where that is clearer and safer, including `EMS`, `P_grid`, `P_batt`, `PCC`, GoodWe mode numbers, **Mad-Steve** and **Gold Rush**.

## Release wiring

`gw-energy-pilot-v039.js` is a thin immutable release wrapper over the merged v0.38 behavior. It owns only the v0.39 dashboard/footer version presentation and a fresh cache key. The v0.38 runtime remains the behavioral owner for rebuilt controls, relevant-state rendering, interaction/scroll stability, physical live-flow direction, hover continuity and Dutch controller localization.

## Safety and compatibility

v0.39 does **not** change:

- GoodWe register definitions or Modbus read blocks;
- EMS mode mapping, setpoint semantics or the `47512 -> wait -> 47511` write order;
- Automatic Control Battery/Grid/Hybrid decisions;
- EMHASS optimization, topology ownership, Battery Saver policy or persistent-plan behavior;
- Home Assistant entity IDs, unique IDs, config-entry data, Store keys or stable device identity.

## Validation

The release candidate must pass Quality, HACS validation and Hassfest on the exact final release head. Quality retains the executable v0.38 model/control/localization regression suite and the full Python repository test/validator set, with the v0.39 release wiring additionally checked.
