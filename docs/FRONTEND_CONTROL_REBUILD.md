# Frontend control and live-flow rebuild

## Status

This document describes the **v0.38 frontend field-test candidate** built on the released v0.37 backend and control behavior. The candidate deliberately keeps the integration manifest at `0.37` until it has been tested on installations that reproduced the failure. It must not be presented as a validated v0.38 release before that field test succeeds.

## Why the v0.37 control stack was replaced

The released frontend combined two mechanisms that interacted badly:

1. `gw-energy-pilot-v035.js` deferred complete Shadow DOM renders while a pointer or keyboard interaction was active.
2. `gw-energy-pilot-v0363-control-stability.js` transplanted old button DOM nodes back into a newly rendered dashboard.

The second mechanism also retained the old nodes' event-listener closures. Some controls therefore continued to reference DOM objects from the previous, already disconnected dashboard. Its button identity included visible text, so Home Assistant language changes or browser translation could produce a different code path for English and Dutch controls.

The replacement has these rules:

- visible text is never a control identity;
- Battery strategy actions use only fixed mode keys such as `mad_steve`, `balanced` and `battery_saver`;
- active state uses `aria-pressed`, not label matching;
- the complete strategy section is retained across telemetry renders, but its actions are handled by one listener on the persistent ShadowRoot;
- English and Dutch labels/descriptions are rendered explicitly from the same fixed keys;
- `translate="no"` prevents browser translation from mutating the strategy-control DOM;
- no old button node with a per-node event-listener closure is transplanted;
- no pointer is captured;
- pointer completion is observed at `window` level, with cancel, blur and a short safety timeout, so a render guard cannot remain stuck when a pointer leaves the ShadowRoot.

## Live-flow direction contract

The field-test candidate no longer derives visible movement from stacked `inbound`, `outbound`, semantic direction and `animation-direction` overrides. It assigns one physical direction to each connector and selects a dedicated forward or reverse keyframe.

Expected movement:

```text
PV production: left to right, PV -> hub
Grid import: right to left, grid -> hub
Grid export: left to right, hub -> grid
House consumption: bottom to top, hub -> house
Battery charging: top to bottom, hub -> battery
Battery discharging: bottom to top, battery -> hub
```

The existing confirmed sign conventions remain unchanged:

```text
GoodWe meter power: positive export, negative import
GoodWe battery power: positive discharge, negative charge
```

## Automated pre-PR checks

The exact candidate modules uploaded to the branch passed:

- Python contract tests for active wiring, stable key-based controls, Dutch/English labels, global pointer completion and physical flow ownership;
- JavaScript syntax validation for all five v0.38 modules;
- executable Node assertions for Dutch/English profile mapping and import/export/charge/discharge movement.

The pull request must additionally pass the repository-wide Quality, HACS and Hassfest workflows.

## Field-test matrix

Before release promotion, validate at least:

1. English Home Assistant: all five Battery strategy buttons click once and show exactly one active profile.
2. Dutch Home Assistant: the same fixed mode keys execute, with Dutch labels and exactly one active profile.
3. Browser translation disabled and enabled: strategy identity and API mode values remain unchanged.
4. Repeated GoodWe telemetry refresh while hovering and pressing a profile button: no flashing active state, no lost click and no stuck disabled state.
5. Mouse and touch scrolling across the strategy grid: normal vertical scrolling remains available.
6. PV production, grid import/export, battery charge/discharge and house load each show the physical movement listed above.

## Safety and compatibility

This is a frontend-only replacement. **No GoodWe register** definition, Modbus read block, EMS mode mapping, setpoint, write order, Automatic Control decision, EMHASS optimization/configuration ownership, entity ID, unique ID, config-entry value or persistent Store key changes.
