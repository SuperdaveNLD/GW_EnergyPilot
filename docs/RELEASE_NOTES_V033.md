# GW EnergyPilot v0.33 Beta

Release date: **2026-08-25**

v0.33 consolidates EMHASS plan resilience, fresh-publication detection, Battery · Plan · Price refresh fixes and the first field-tested Battery Saver anti-churn tuning into one release.

## Persistent EMHASS plan

EMHASS remains the canonical plan owner. EnergyPilot now mirrors the validated official `GET /api/v1/plan` horizon in Home Assistant Store as:

```text
gw_energypilot.plan.<config_entry_id>
```

The mirror records timestamped `P_batt` / `P_grid`, inferred timestep and an explicit final validity boundary.

Automatic Control source order is:

```text
live configured P_batt/P_grid
-> current still-valid persistent-plan point
-> unavailable/wait
```

An explicit live non-ready optimization status remains authoritative. EnergyPilot never extrapolates the final plan row after the horizon expires.

## Fresh-output fix

A newly published EMHASS row may have the same numeric `P_batt` and attributes as the previous row. Home Assistant can then leave `last_updated` unchanged. v0.33 validates new publication through `State.last_reported`, with `last_updated` retained as compatibility fallback. Finite numeric output and optimizer-ready state remain required.

## Battery · Plan · Price refresh

The chart keeps its duplicate-card protection but now rebuilds the canonical card when new chart data arrives. A newer active-plan timestamp bypasses the normal five-minute chart cache so a manual or scheduled optimization is reflected immediately instead of leaving a stale graph.

## Battery Saver v0.33

The four public modes remain:

```text
Mad-Steve
Gold Rush
Balanced
Battery Saver
```

All four now use the same small linear anti-churn cost:

```text
weight_battery_charge    = 1.5% × dynamic price reference
weight_battery_discharge = 1.5% × dynamic price reference
```

This gives battery throughput a real virtual cost even in Mad-Steve, reducing very small quarter-hour charge/discharge reversals while keeping the existing profile-specific SOC and power-stress penalties.

**Gold Rush** changes its soft high-SOC threshold from 98% to **96%**. Its low threshold remains 5%; its existing high-SOC cost factor and power-stress factor are unchanged. The 96% threshold is soft and does not replace the separately configured hard Maximum SOC.

Battery Saver ownership expands to eight EMHASS fields so apply/rollback includes both throughput weights.

See `docs/BATTERY_SAVER.md` for the exact profile table and field-test rationale.

## Why a 15 kW battery may plan below 15 kW

The plan can legitimately show less than the battery power limit. PV and battery share the hybrid inverter path, so the inverter may already be at 15 kW AC with `P_batt` below 15 kW. When no hardware constraint binds, EMHASS can also reserve energy for a later higher-price slot or reduce instantaneous power because `battery_stress_cost` is a quadratic/PWL power penalty.

v0.33 documents this behavior; it does not add another battery/inverter power cap.

## Safety / compatibility

- No new or guessed GoodWe registers.
- No Modbus read-block changes.
- EMS remains on `47511/47512` with `47512 -> wait -> 47511` ordering.
- Battery/Grid/Hybrid mode mappings are unchanged.
- No existing entity IDs, unique IDs or stable device identity changes.
- The persistent plan is a resilience mirror, not a second optimizer.
- Unmanaged/custom EMHASS Battery Saver values remain untouched until explicit profile selection.
- Multi-battery Battery Saver ownership remains rejected rather than guessed.

v0.33 remains **Beta** pending broader live restart/reload and Battery Saver tuning validation.
