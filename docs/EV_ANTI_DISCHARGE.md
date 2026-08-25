# EV anti-discharge protection

This document defines the EV protection behavior for GW EnergyPilot v0.34.

## Purpose

The EV feature is an **anti-discharge protection**, not an EV charging controller.

While the EV is charging, the home battery must not discharge into the EV. If EMHASS explicitly requests home-battery charging at the same time, GW EnergyPilot must continue that charge request instead of holding the battery.

The EV charger remains responsible for starting, stopping and modulating the EV charging session. GW EnergyPilot only observes the configured EV state/power entities.

## Ownership boundary

```text
EV charger / external charging service
    -> decides when and how the EV charges

EMHASS
    -> decides the desired home-battery direction

GW EnergyPilot EV anti-discharge protection
    -> blocks home-battery discharge while EV charging is active
    -> lets an explicit home-battery charge plan continue

GoodWe ETA / BMS / smart meter
    -> performs inverter-side power control and remains authoritative for hardware limits
```

## Control rule

During an active EV charging session, `P_batt` is the directional safety guard:

| EV state | EMHASS `P_batt` plan | EnergyPilot behavior |
|---|---|---|
| Not charging | Any valid plan | Normal configured automatic strategy |
| Charging | `P_batt > +deadband` — discharge | **Mode 8 Battery Hold** |
| Charging | `P_batt` inside deadband — neutral | **Mode 8 Battery Hold** |
| Charging | `P_batt < -deadband` — charge | **Continue charging** |

This means EV coordination is strictly anti-discharge: discharge and neutral are paused, charging is allowed to proceed.

## GoodWe execution while EV charging

When EMHASS requests battery charging while the EV is active, GW EnergyPilot preserves the configured control strategy as far as safely possible:

- **Battery control**: mode `11` (**Battery charge power**) using the requested `P_batt` magnitude.
- **Grid control**: mode `9` (**Grid import target**) when `P_grid` contains a positive import target.
- **Hybrid control**: mode `9` when `P_grid` contains a positive import target.
- **Grid/Hybrid fallback**: when `P_batt` explicitly requests charging but there is no positive usable `P_grid` import target, mode `11` is used so the valid battery-charge request is not incorrectly converted to Hold.

For discharge or neutral plans, EnergyPilot always uses mode `8` (**Battery Hold**) at `0 W` while EV charging is active.

No new Modbus registers are introduced. The existing EMS registers remain:

```text
47511  EMS mode
47512  mode-specific setpoint magnitude
```

The established `47512 -> wait -> 47511` write sequence remains unchanged.

## EV detection

The stored option key remains `enable_ev_coordination` for backwards compatibility.

EV activity can be detected through the configured EV charging-mode entity and/or the configured EV charging-power entity plus activity threshold. These are observation inputs only and do not give EnergyPilot ownership of the charger.

## EV stop behavior

When the native EMHASS orchestrator is enabled and EV charging stops, the existing stale-plan protection remains unchanged:

1. detect that EV charging stopped;
2. keep the battery held while the old plan is stale;
3. request/wait for a fresh optimization;
4. resume normal automatic control from the new plan.

## Safety boundary

GoodWe and the battery BMS remain authoritative for inverter, battery, SOC and electrical limits. This feature does not infer or add GoodWe registers and does not introduce a second fast feedback loop.

## Non-goals

This feature does not schedule EV charging, choose EV target SOC, change charger current, integrate with charger-cloud APIs, or replace charger-side/GoodWe-side load balancing. Its responsibility is limited to preventing home-battery discharge into an actively charging EV while still allowing a legitimate home-battery charging plan.
