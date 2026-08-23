# EV anti-discharge protection

This document defines the EV protection behavior prepared for the next GW EnergyPilot update.

## Purpose

The EV feature is an **anti-discharge protection**, not an EV charging controller.

Its purpose is simple:

> While the EV is charging, the home battery must not be used as the energy source for the EV. If EMHASS explicitly wants to charge the home battery at the same time, that charging request may still be executed.

The EV charger remains responsible for starting, stopping and modulating the EV charging session. GW EnergyPilot only uses the configured EV state/power entities to determine whether the anti-discharge guard should be active.

## Why a directional guard is needed

EV charging is not always scheduled purely around the lowest spot price. External charging services can deliberately move EV consumption to moments that are useful for the electricity grid.

A specific example is **Tibber Grid Rewards**. Tibber describes Grid Rewards as a service where connected chargers can help balance the grid; charging can be started or paused according to grid conditions and users receive a reward for that flexibility.

Official information: https://tibber.com/nl/grid-rewards

That means an EV may intentionally charge at a moment when the normal home-battery optimization would otherwise prefer to discharge. A blanket EV `Battery Hold` avoids feeding the car from the home battery, but it also unnecessarily blocks a valid home-battery charging plan.

The anti-discharge rule separates those two concerns.

GW EnergyPilot does **not** integrate with, control or depend on Tibber Grid Rewards. Tibber Grid Rewards is documented only as a concrete example of why EV charging ownership must remain external to EnergyPilot.

## Ownership boundary

```text
EV charger / external charging service
    -> decides when and how the EV charges

EMHASS
    -> decides the desired home-battery direction

GW EnergyPilot EV anti-discharge protection
    -> blocks home-battery discharge while EV charging is active
    -> permits an explicit home-battery charge plan

GoodWe ETA / BMS / smart meter
    -> performs the inverter-side power control and remains authoritative for hardware limits
```

EnergyPilot does not send charge-current commands to the EV charger and does not attempt to reproduce EV load balancing.

## Control rule

During an active EV charging session, `P_batt` is used as the directional guard:

| EV state | EMHASS `P_batt` plan | EnergyPilot behavior |
|---|---|---|
| Not charging | Any valid plan | Normal configured automatic strategy |
| Charging | `P_batt > +deadband` — discharge | **Battery Hold** |
| Charging | `P_batt` inside deadband — neutral | **Battery Hold** |
| Charging | `P_batt < -deadband` — charge | **Battery charging allowed** |

This guarantees that an active EV session cannot turn the home battery into the EV's supply simply because the normal PCC target would otherwise call for discharge.

## GoodWe execution while EV charging

When EV anti-discharge protection is active and EMHASS explicitly requests home-battery charging, EnergyPilot uses GoodWe mode `11` (**Battery charge power**) with the requested `P_batt` magnitude, capped by the configured EnergyPilot maximum setpoint.

For discharge or neutral plans, EnergyPilot uses mode `8` (**Battery Hold**) at `0 W`.

This directional override applies even when the normal automatic strategy uses GoodWe smart-meter/PCC modes `9/10/1`. The reason is that a site-level PCC target can change the resulting battery direction when EV load changes. During an EV session the anti-discharge guarantee takes priority over preserving the normal PCC actuator primitive.

No new Modbus registers are introduced. The existing EMS registers remain:

```text
47511  EMS mode
47512  mode-specific setpoint magnitude
```

The established `47512 -> wait -> 47511` write sequence remains unchanged.

## EV detection

The existing configuration remains backwards compatible.

The stored option key remains:

```text
enable_ev_coordination
```

It is retained to avoid breaking existing Home Assistant config entries. The user-facing name changes to **EV anti-discharge protection**.

EV activity can still be detected through:

- the configured EV charging-mode entity;
- the configured EV charging-power entity and activity threshold.

Those entities are observation inputs only. They do not give EnergyPilot ownership of the charger.

## EV stop behavior

When the native EMHASS orchestrator is enabled and an EV charging session ends, EnergyPilot keeps the existing stale-plan protection:

1. detect that EV charging stopped;
2. keep the battery held while the old pre-stop plan is considered stale;
3. request/wait for a fresh optimization;
4. resume normal automatic control from the new plan.

This avoids briefly executing an optimizer target that was produced for a different load situation.

## Safety boundary

The anti-discharge feature does not replace GoodWe, BMS or installation protection. GoodWe and the battery BMS remain authoritative for inverter, battery, SOC and electrical limits.

EnergyPilot must not infer or invent GoodWe registers for this feature, and it must not introduce a second fast feedback loop on top of GoodWe's own control.

## Non-goals

This feature intentionally does **not**:

- schedule EV charging;
- choose EV departure times or target SOC;
- change EV charger current;
- integrate with Tibber APIs;
- reproduce Tibber Grid Rewards;
- optimize Grid Rewards revenue;
- replace charger-side or GoodWe-side load balancing.

Its responsibility is limited to preventing home-battery discharge into an actively charging EV while still allowing a legitimate home-battery charging plan.