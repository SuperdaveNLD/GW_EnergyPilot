# GW EnergyPilot v0.38 Beta

v0.38 rebuilds the dashboard control-stability layer after v0.37 showed that preserving old button DOM nodes was not a safe solution on all Home Assistant installations and produced a language-dependent control identity.

## Fixed

- Replaced v0.37's active stable-button-node reuse with fresh rendered controls and persistent `shadowRoot` event delegation.
- Battery Strategy actions and active highlighting now use stable backend mode keys plus `aria-pressed`; English/Dutch labels and descriptions are presentation only and cannot change button identity or behavior.
- Removed the v0.35 pointer-capture/render-lock stack from the fresh v0.38 active import chain. v0.38 never pointer-captures a button and never blocks `_render()` because a pointer is active.
- Added a narrow 300 ms render quiet window that only delays HASS-triggered telemetry rendering after a press, allowing the native browser click/service path to complete normally.
- Preserved relevant-state HASS filtering with 80 ms batching so unrelated Home Assistant state changes do not rebuild the complete dashboard.
- Preserved the v0.36.2 mobile scroll-position protection directly inside v0.38.
- Replaced inherited live-flow direction interactions with one final canonical semantic mapping and explicit v0.38 keyframes.

## Expected live-flow directions

```text
PV production       PV -> hub
Grid import         Grid -> hub
Grid export         hub -> Grid
House consumption   hub -> House
Battery discharge   Battery -> hub
Battery charge      hub -> Battery
```

The existing GoodWe signs remain unchanged: smart-meter power is negative for import / positive for export; battery power is negative for charge / positive for discharge.

## Active frontend architecture

A fresh v0.38 installation loads:

```text
gw-energy-pilot-v038.js
    -> gw-energy-pilot-v034.js
        -> existing pre-v0.35 dashboard chain
```

v0.35, v0.36.x and v0.37 frontend wrappers remain historical files but are no longer part of the fresh v0.38 active chain. A small compatibility bypass prevents an already-open browser realm that previously executed v0.37 from restoring stale v0.36.3 button nodes during the transition.

See `docs/FRONTEND_V038.md` for the detailed ownership contract.

## Safety / compatibility

This release is frontend-only:

- no GoodWe register or Modbus read-block changes;
- no EMS mode mapping, setpoint or write-order changes;
- no Automatic Control decision changes;
- no EMHASS optimization/Battery Saver backend changes;
- no entity ID, unique ID, config-entry data, Store key or stable device identity changes.

v0.38 remains **Beta** while the rebuilt control path and canonical flow animation receive multi-installation field validation.
