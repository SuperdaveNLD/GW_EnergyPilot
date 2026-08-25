# GW EnergyPilot v0.36 Beta

v0.36 consolidates the customer-facing battery-strategy controls with two dashboard reliability fixes that were developed separately after v0.35. The release keeps the existing GoodWe and EMHASS control architecture: EMHASS remains the canonical optimizer and EnergyPilot remains the component that translates the active plan into the established GoodWe EMS control modes.

## Customer-facing battery strategy

The normal **Controller** card now presents the active battery policy as a customer-facing **Battery strategy** instead of exposing the internal controller command as a primary value.

Available choices are:

- **Mad-Steve**
- **Gold Rush**
- **Balanced**
- **Battery Saver**
- **Custom**

The selected strategy is highlighted as active. Selecting one of the four managed profiles uses the existing Battery Saver profile implementation; no duplicate profile definitions are introduced in the frontend.

The low-level controller command such as `hybrid_battery_discharge` is intentionally removed from the customer Controller presentation. It remains available in the existing Diagnostics/support snapshot for troubleshooting.

## Profile selection, optimization and graph refresh

A Battery strategy change is a complete EnergyPilot policy transaction:

```text
select strategy
    ↓
persist EnergyPilot Battery Saver mode / release preset ownership for Custom
    ↓
prepare the effective EMHASS battery policy
    ↓
run a fresh EnergyPilot-owned EMHASS optimization
    ↓
initial publish-data
    ↓
refresh the persistent plan mirror
    ↓
increment plan_revision
    ↓
Battery · Plan · Price bypasses its normal cache and reloads
```

This means the graph is not updated by a separate frontend guess or timer. It follows the existing backend `plan_revision` contract after a successful optimization.

If a managed-profile transition fails during its first complete optimization/publish transaction, EnergyPilot restores the previous mode and Battery Saver-owned EMHASS fields.

## Custom mode

**Custom** explicitly releases EnergyPilot's managed Battery Saver preset ownership while preserving the currently effective EMHASS battery values. Switching to Custom therefore does not reset battery penalties or replace the current configuration with defaults.

The Controller card exposes the existing Home Assistant minimum/maximum SOC controls when Custom is active. These reuse the established NumberEntities rather than creating duplicate settings or entities.

- Minimum SOC keeps its existing GoodWe on-grid minimum-SOC synchronization contract.
- Maximum SOC keeps its existing EMHASS NumberEntity path.
- Existing EMHASS low-SOC cost, high-SOC cost, power-stress cost and charge/discharge weights are shown read-only for transparency.
- Each completed SOC change continues through the existing debounced optimization path.

Custom remains available even when a configuration does not satisfy the one-battery restriction of the managed EnergyPilot presets, because Custom does not claim ownership of those profile fields.

## Dashboard render-storm protection

Some Home Assistant installations publish state changes at a much higher rate than others. The inherited dashboard component previously queued a complete render for every new `hass` snapshot, including unrelated entities. Because the legacy renderer replaces the complete Shadow DOM, high-update installations could repeatedly destroy and recreate controls while the user was interacting with them.

v0.36 keeps every incoming Home Assistant snapshot available but schedules a dashboard rebuild only when a relevant source changes. Relevant sources include:

- current GW EnergyPilot entity-registry mappings;
- configured `P_batt`, `P_grid` and optimization-status entities;
- the active Battery Plan source entity;
- retained legacy EMHASS fallback entity IDs/suffixes;
- Home Assistant locale/user/theme context.

Relevant bursts are grouped into an 80 ms render batch. A narrow pointer/keyboard guard defers destructive rendering only while an actual button/control press is in progress. Hovering does not freeze telemetry.

No coordinator, Modbus or EMHASS polling cadence changes are introduced by this frontend optimization.

## Live-flow direction and mobile sizing

The power-sign and physical-flow mappings were already correct. The remaining visual defect came from layered CSS: older two-class `animation-direction: reverse !important` rules could reverse a geometry-specific animation a second time.

v0.36 adds an active-layer rule with matching specificity so the existing geometry-specific forward/reverse keyframes remain the single direction mechanism. Expected visual directions remain:

- PV → hub
- Grid import → hub
- hub → Grid export
- hub → Battery charge
- Battery discharge → hub
- hub → House

For narrow Home Assistant panels the flow card now derives its node, hub, connector and stage geometry from the measured card width instead of fixed desktop dimensions.

- compact layout activates at 430 px and below;
- a tighter layout activates at 340 px and below;
- `ResizeObserver` recalculates geometry after panel resizing and phone rotation;
- particle travel distance follows the measured connector length;
- desktop/wide geometry remains unchanged.

## Tests and validation scope

The v0.36 test suite adds regression contracts for:

- final v0.36 frontend/manifest/cache-busting wiring;
- managed strategy and Custom API paths;
- Custom preserving EMHASS values while releasing preset ownership;
- immediate optimization after every strategy transition;
- rollback after a failed strategy transition;
- customer Controller reuse of existing SOC NumberEntities;
- relocation of the low-level command to Diagnostics;
- `plan_revision`-driven chart cache invalidation;
- live-flow direction specificity;
- compact/tight mobile geometry and `ResizeObserver` tracking;
- relevant-state render filtering and 80 ms batching;
- destructive-render deferral during an actual pointer/keyboard press.

The repository release candidate is expected to pass the normal **Quality**, **HACS validation** and **Hassfest** workflows before merge. A dedicated live-validation checklist is provided in `docs/RELEASE_NOTES_V036_TEST.md` for strategy transitions, graph refresh, high-update interaction and phone/rotation behavior.

## Safety and compatibility

- No new or guessed GoodWe register definitions.
- No Modbus read-block changes.
- No change to EMS registers `47511` / `47512` or the established `47512 -> wait -> 47511` write order.
- No Automatic Control mode mapping changes are introduced by the customer-strategy UI or dashboard reliability work.
- Existing entity IDs, unique IDs and stable device identity are preserved.
- Existing Home Assistant SOC NumberEntities are reused; no duplicate sensors/settings are added.
- EMHASS remains an external prerequisite and the canonical optimizer/plan owner.
- The persistent EnergyPilot plan remains a resilience mirror, not a second optimizer.
- Custom mode preserves current EMHASS battery values instead of silently resetting them.
- The internal controller command remains available in Diagnostics for support analysis.

See also `docs/BATTERY_SAVER.md`, `docs/BATTERY_PLAN_CHART.md`, `docs/RELEASE_NOTES_V036_TEST.md` and `docs/RELEASE_NOTES.md`.
