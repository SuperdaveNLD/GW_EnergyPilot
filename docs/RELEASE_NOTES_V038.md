# GW EnergyPilot v0.38 Beta

v0.38 replaces the dashboard-control stabilization approach used by v0.37 after live installations showed that old button-node reuse could still make controls unusable and could behave differently across translated Dutch/English labels. It also makes live-flow particle direction a single explicit v0.38 responsibility.

## Fixed

- Rebuilt Battery Strategy controls around stable backend keys (`mad_steve`, `gold_rush`, `balanced`, `battery_saver`, `custom`). Visible English/Dutch text is presentation only and is no longer part of control identity.
- Active/highlight state is now driven by `aria-pressed` on the canonical profile key, so language, label length and browser translation cannot choose a different control path.
- Replaced old per-button listener preservation with one delegated listener on the persistent ShadowRoot. Fresh rendered controls keep fresh DOM/listener state instead of transplanting stale button nodes from an older dashboard render.
- A fresh v0.38 session imports the known v0.34 feature base directly and does not load the v0.35 pointer/render lock or v0.36.3 stable-button-node reuse layers.
- Preserved native touch scrolling and narrow/mobile scroll-position recovery without pointer capture.
- Added explicit interaction completion on pointer-up, cancel, window blur and a bounded safety timeout so an interrupted gesture cannot leave the dashboard permanently render-deferred.
- Replaced stacked `inbound`/`outbound` and `animation-direction` interactions with explicit physical v0.38 motion plus dedicated keyframes.

## Canonical live-flow direction

```text
PV production       PV -> hub
Grid import         Grid -> hub
Grid export         hub -> Grid
House consumption   hub -> House
Battery discharge   Battery -> hub
Battery charge      hub -> Battery
```

The existing confirmed GW EnergyPilot signs remain unchanged:

```text
GoodWe grid meter: negative = import, positive = export
Battery power:      negative = charging, positive = discharging
```

## Automated validation

The normal Quality workflow now also runs executable Node.js frontend tests in addition to Python compile/unit/repository checks:

- English and Dutch produce the same five canonical profile keys;
- visible translated text does not determine the dispatched profile mode;
- a delegated profile click invokes the existing `gw_energypilot/battery_saver/set` API exactly once;
- profile controls are enabled again after the action completes;
- import/export/charge/discharge flow cases resolve to the expected physical direction;
- all new v0.38 JavaScript modules pass `node --check`.

HACS validation and Hassfest remain required before release.

## Architecture

Fresh v0.38 frontend path:

```text
gw-energy-pilot-v038.js
    -> gw-energy-pilot-v038-runtime.js
        -> gw-energy-pilot-v034.js
            -> existing v0.34 feature chain
```

The v0.35/v0.36.x/v0.37 files remain in the repository for release history but are not part of a fresh v0.38 active path. See `docs/FRONTEND_CONTROL_REBUILD.md` for the detailed ownership and test contract.

## Safety / compatibility

v0.38 is frontend-only:

- no GoodWe register definitions or Modbus read blocks change;
- no EMS mode mapping, setpoint semantics or `47512 -> wait -> 47511` write order changes;
- no Automatic Control decisions change;
- no EMHASS optimization, Battery Saver backend policy or configuration-ownership behavior changes;
- no entity IDs, unique IDs, config-entry data, persistent Store keys or stable device identity changes.

v0.38 remains **Beta** while the rebuilt control surface and canonical flow animation receive broader multi-installation field validation.
