# EV anti-discharge protection

This document defines the EV protection behavior for GW EnergyPilot v0.34.

## Purpose

The EV feature is an **anti-discharge protection**, not an EV charging controller.

While the EV is charging, the home battery must not discharge into the EV. If EMHASS explicitly requests home-battery charging at the same time, GW EnergyPilot must continue that charge request instead of holding the battery.

The anti-discharge feature only observes the configured EV state/power entities.
The separately opt-in EV load balancer may modulate one charger current entity,
but it is not part of this GoodWe battery-direction controller. See
`EV_LOAD_BALANCING.md`.

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

An optional EV online entity separately reports charger reachability. Missing, `unknown` and `unavailable` are unreachable. A binary sensor is explicit (`on` online, `off` unreachable); for other domains every usable state is online, so an idle charging switch that reports `off` is not mistaken for an offline charger.

### Five-minute reachability guard

If EV coordination is enabled and the configured charger-online source remains unreachable for five continuous minutes, EnergyPilot suspends the EV anti-discharge override. It does not overwrite `enable_ev_coordination`: the saved option remains the user's intent, while the runtime exposes requested and effective state separately.

After suspension, five continuous online minutes restore the override only if the user setting is still enabled. An online/offline flap resets the active window. Turning EV coordination off during recovery cancels automatic resume. Connectivity loss/restoration and suspension/resume transitions are recorded in the Home Assistant log and, when enabled, the bounded debug log.

This guard does not poll the charger, control it or add a fast loop. Charger reachability follows the selected Home Assistant entity, while Modbus status follows the configured GoodWe coordinator refresh interval.

## EV stop behavior

When the native EMHASS orchestrator is enabled and EV charging stops, the existing stale-plan protection remains unchanged:

1. detect that EV charging stopped;
2. keep the battery held while the old plan is stale;
3. request/wait for a fresh optimization;
4. resume normal automatic control from the new plan.

## Dashboard status

The Controller card presents the current EV protection state directly from the
existing controller command:

- **Anti-discharge active**: EV charging is active and home-battery discharge is
  blocked with mode `8` (**Battery Hold**).
- **Battery charge allowed**: EV charging is active and the explicit
  home-battery charging plan continues.
- **Fresh plan required**: EV charging has stopped, but Battery Hold remains
  active until the native orchestrator publishes a fresh EMHASS plan.

The status is presentation-only. It does not add an override, charger control,
new controller ownership mode or additional Modbus write path. A future
override would change safety and control ownership semantics and therefore
requires a separate explicit design decision and review.

### Historical chart evidence

v1.0.0 draws EV protection underlays from the existing execution-history
Store. Only post-refresh `verified` records qualify: solid means discharge was
blocked through `ev_anti_discharge_hold`, while stripes mean an explicit
strategy-aware battery/grid charging command was allowed. The overlay adds no
control decision, Store or charger write.

Intervals are limited to one controller runtime session. A Home Assistant
restart therefore leaves an intentional gap until a new verified decision is
recorded; retained records on opposite sides of a restart are never joined.

## Safety boundary

GoodWe and the battery BMS remain authoritative for inverter, battery, SOC and electrical limits. This feature does not infer or add GoodWe registers and does not introduce a second fast feedback loop.

## Non-goals

This feature does not schedule EV charging, choose EV target SOC, change charger current, or integrate with charger-cloud APIs. Its responsibility is limited to preventing home-battery discharge into an actively charging EV while still allowing a legitimate home-battery charging plan. The independent EV load balancer is the only EnergyPilot component permitted to change the configured charger-current NumberEntity.
