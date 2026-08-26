# Frontend interaction and flow-direction contract

This document records the dashboard ownership rules introduced after the v0.35 interaction regression.

## Control interaction

The EnergyPilot dashboard still has a legacy renderer that can rebuild the complete panel Shadow DOM. Interactive controls must therefore remain simple and browser-native.

The canonical card-window controls are implemented in:

```text
custom_components/gw_energypilot/frontend/gw-energy-pilot-v031-window-controls.js
```

Required rules:

- visual highlighting is CSS-only through `:hover`, `:focus-visible` and `:active`;
- do not use JavaScript hover state;
- do not use `pointerdown`/`pointerup` locks;
- do not call `setPointerCapture`;
- do not move actions from native `click` to pointer events;
- use one delegated `click` listener on the persistent ShadowRoot;
- store hide/collapse/maximize state in the existing localStorage keys;
- apply the requested card state directly instead of forcing an immediate full-panel rebuild.

The outer v0.35 hotfix may filter and batch Home Assistant state-driven renders, but it must always retain the newest `hass` snapshot. It may not suppress, capture or reinterpret operator input.

## Energy-flow direction

GoodWe and EnergyPilot signs remain:

```text
GoodWe grid meter power: negative import, positive export
GoodWe battery power:    negative charge, positive discharge
```

The dashboard geometry is:

```text
PV      left of hub
Grid    right of hub
House   above hub
Battery below hub
```

Therefore the final animation directions are:

| Link | Positive value | Negative value |
| --- | --- | --- |
| PV | normal, left to right | reverse |
| Grid | normal, hub to grid export | reverse, grid to hub import |
| House | reverse, hub to house load | normal |
| Battery | reverse, battery to hub discharge | normal, hub to battery charge |

`gw-energy-pilot-v036-flow-direction.js` is the final animation-direction authority. Earlier semantic classes may still describe the energy direction, but they must not reverse the particle animation again. The final layer controls both the legacy pseudo-element particle and the later `.ep-v011-particles span` implementation.

## Regression validation

The repository runs:

```text
python -m unittest discover -s tests -v
node --test tests/frontend_v036_runtime.mjs
python scripts/validate_repo.py
```

The Node tests execute the sign/geometry mapping and relevant-state render-filter contract. Static Python tests additionally reject pointer capture and pointer-lock code in the active controls path.
