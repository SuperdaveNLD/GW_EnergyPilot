# EMHASS plan runtime

GW EnergyPilot treats EMHASS as the canonical owner of optimization plans. Home Assistant entities such as `sensor.p_batt_forecast` and `sensor.p_grid_forecast` are publication surfaces, not durable plan storage.

## Problem

EMHASS publishes the current battery/grid target into Home Assistant. During a Home Assistant restart, integration reload or update, those external entities can temporarily be missing, `unknown` or `unavailable` even though EMHASS still has a valid optimization plan.

Before v0.33 this created two avoidable dependencies:

- Automatic Control read the published Home Assistant `P_batt` / `P_grid` state directly;
- Battery · Plan · Price read the future horizon from the current entity attributes.

A temporary Home Assistant publication gap could therefore make control wait for `P_batt` and make the future chart disappear.

## Canonical ownership

The ownership model is:

```text
EMHASS optimization
        |
        v
EMHASS persistent plan store
GET /api/v1/plan
        |
        v
EnergyPilot plan runtime mirror
        |
        +--> Automatic Control fallback
        |
        +--> Battery · Plan · Price future horizon
```

Current EMHASS persists its latest optimization result in its own `plan_latest.json` and exposes it through the versioned read-only `GET /api/v1/plan` API. Schema 1.x defines `P_batt` and `P_grid` in watts with these signs:

```text
P_batt > 0  battery discharge
P_batt < 0  battery charge
P_grid > 0  grid import
P_grid < 0  grid export
```

Schema 1.x also defines bare `SOC_opt` for a single battery as a fraction in `0..1`. EnergyPilot validates that exact column and normalizes it once to percentage for visualization. It never treats other numeric columns or already-published Home Assistant percentages as plan fractions.

EnergyPilot does not write or replace that EMHASS plan.

## EnergyPilot mirror

EnergyPilot maintains one per-config-entry Home Assistant Store mirror:

```text
gw_energypilot.plan.<entry_id>
```

The mirror contains only the latest validated plan evidence:

- source;
- EMHASS `generated_at`;
- EMHASS schema version when available;
- inferred timestep derived from adjacent plan timestamps;
- exclusive `valid_until` boundary;
- normalized `P_batt` points;
- normalized `P_grid` points;
- optional normalized `SOC_opt` percentage points;
- configured Home Assistant publication entity IDs for diagnostics.

This is a resilience cache, not a second optimizer or a second settings database.

## Refresh order

On integration setup:

1. restore the previous EnergyPilot mirror from Home Assistant Store;
2. start a bounded background refresh against `GET /api/v1/plan`;
3. retry while EMHASS/Home Assistant startup dependencies settle;
4. if the official endpoint is temporarily unavailable, accept the existing Home Assistant schedule attributes only as a compatibility fallback.

After every successful EnergyPilot-owned optimization/publish cycle, the mirror is refreshed again.

The Battery · Plan · Price refresh action also requests a plan refresh when no current mirror exists, or when the user explicitly forces a chart refresh.

## Control resolution

Automatic Control keeps the established live path as first priority:

```text
live Home Assistant P_batt/P_grid
        |
        | missing/unavailable
        v
valid EnergyPilot plan mirror at current timestamp
        |
        | no valid timestep
        v
existing unavailable/waiting behavior
```

A valid mirrored plan may also satisfy the temporary `optim_status` publication gap during Home Assistant startup. An explicit live non-ready optimization status still wins and is never overridden by the cache.

No existing GoodWe EMS mode mapping or write order changes.

## Time validity and stale-plan protection

The mirror is stepwise. EnergyPilot derives the timestep from adjacent timestamps and resolves the value whose interval contains the current time.

EnergyPilot never extrapolates beyond the final plan interval. When the horizon has genuinely expired, the cache becomes unavailable rather than repeating the last charge/discharge value indefinitely.

This distinction is intentional:

- restart/reload publication gap + still-valid plan -> continue from the plan;
- genuinely expired plan -> require a fresh plan.

## Dashboard

Battery · Plan · Price obtains the future `P_batt` horizon and optional single-battery `SOC_opt` forecast from the same official plan runtime used by control. Recorder remains the source for historical published targets, actual GoodWe battery power and actual GoodWe SOC.

The Home Assistant schedule fallback intentionally fills only `P_batt`/`P_grid`. EnergyPilot does not have a configured SOC-forecast output entity, so it does not guess EMHASS's default or a custom runtime ID. Multi-battery plans expose only per-battery SOC columns and remain unavailable in the aggregate chart.

This removes the previous split where the controller and chart could disagree about whether a valid plan existed.

## Compatibility

- EMHASS remains an external prerequisite and canonical plan owner.
- No new GoodWe register or Modbus block is introduced.
- No existing entity ID or unique ID is replaced.
- EnergyPilot does not overwrite `sensor.p_batt_forecast` or `sensor.p_grid_forecast`.
- Existing custom entity mappings remain the live publication path.
- Home Assistant schedule attributes remain a fallback for older/custom EMHASS publication paths.
