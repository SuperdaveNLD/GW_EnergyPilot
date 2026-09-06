# EV anti-discharge protection

This document defines current development behavior, including the v1.3.0-beta.9 Hybrid 2.0 test mapping. Published beta.8 used the earlier EV import reference.

## Purpose

The EV feature is an **anti-discharge protection**, not an EV charging controller.

While the EV is charging, the home battery should not supply the EV. The
Hybrid 2.0 test uses mode 5 with inverter output set to fresh local load 35172
minus measured EV power for grid-neutral self-use, including neutral P_batt.
Outside the grid deadband, planned battery charging uses mode 11 at the
planned watts and explicit discharge is held. The load boundary and PV
surplus behavior still need field validation. Battery, Grid and original
Hybrid retain their existing plan-direction guards below.

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

For the original Battery, Grid and Hybrid strategies, `P_batt` is the directional safety guard:

| EV state | EMHASS `P_batt` plan | EnergyPilot behavior |
|---|---|---|
| Not charging | Any valid plan | Normal configured automatic strategy |
| Charging | `P_batt > +deadband` — discharge | **Mode 8 Battery Hold** |
| Charging | `P_batt` inside deadband — neutral | **Mode 8 Battery Hold** |
| Charging | `P_batt < -deadband` — charge | **Continue according to strategy below** |

Hybrid 2.0 classifies the grid deadband first, including P_batt = 0 and
positive battery plans for house self-use. Within the band it uses mode 5 at
bounded max(0, local load minus EV). Outside it, charging follows battery watts
in mode 11 and explicit discharge uses mode 8. Neutral battery/net-only EV
plans are unresolved and use protective Hold. This does not make a zero
battery plan an explicit Pause. See [the complete test matrix](HYBRID_2.md).

## GoodWe execution while EV charging

When EMHASS requests battery charging while the EV is active:

- **Battery control**: mode `11` using the requested `P_batt` magnitude.
- **Grid/Hybrid control**: mode `9` for import, mode `1` inside the grid
  deadband, or mode `10` for export. Export alongside a charging battery plan
  can represent PV export and is not itself a battery-discharge request.
- **Hybrid 2.0 Beta**: mode `11` at bounded `abs(P_batt)` for battery charging
  outside the grid deadband. Grid-neutral self-use uses mode `5` at local
  load minus EV, updated every 15 seconds. Both local load and EV power must
  be finite and fresh within 30 seconds; stale/failed/missing inputs Hold.
  Missing/non-ready/suspended plans also Hold. Mode 5 may curtail PV rather
  than charge the battery from surplus; that field test remains open.
- Original Grid/Hybrid with missing/non-finite required `P_grid`: wait without
  an EMS write. A valid persistent plan may supply it. Hybrid 2.0 with active
  EV charging uses Hold for missing plan inputs as described above.

EV activity must not convert a Grid/Hybrid command to mode `11`. Only the
planned battery direction gates the original Battery/Grid/Hybrid override.
Their plan-based guard is not a guarantee of instantaneous battery direction in PCC/Auto modes
when actual load differs from the forecast. ETA retains local power control;
no new hardware limit or register semantics are inferred from this fix.

The original Battery/Grid/Hybrid strategies hold neutral and discharge plans. Hybrid 2.0 uses the grid-first exception above; an explicit manual Pause always retains mode `8` and manual ownership.

No new Modbus registers are introduced. The existing EMS registers remain:

```text
47511  EMS mode
47512  mode-specific setpoint magnitude
```

The established `47512 -> wait -> 47511` write sequence remains unchanged.

## EV detection

The stored option key remains `enable_ev_coordination` for backwards compatibility.

The EV page offers one explicit charging-detection choice:

- **Charger power sensor**: active when the selected measured-power entity is
  above the configured watt threshold.
- **Charging status / boolean**: active only for `on`, `true`, `charging` or
  `connected_charging`. This supports binary sensors such as Tesla Wall
  Connector `Opladen` and status sensors such as Zaptec charger mode.

Only the selected source controls the anti-discharge guard. Allocated or
available charger current is deliberately not an activity signal: it is a limit
and can remain at (for example) `16 A` while the EV draws no current. Existing
config entries without the new method key retain their exact former
`connected_charging`-or-power behavior until the operator saves an explicit
choice. Both detection sources are observation-only and do not give EnergyPilot
ownership of the charger.

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

If that immediate optimization collides with another plan cycle or fails
transiently, EnergyPilot keeps Battery Hold and retries after 5, 15, 30 and 60
seconds. A new EV charging start cancels the pending retry. The regular
wall-clock schedule remains the fallback after the bounded retry sequence.

## Dashboard status

The Controller card presents the current EV protection state directly from the
existing controller command:

- **Anti-discharge active**: EV charging is active and home-battery discharge is
  blocked with mode `8` (**Battery Hold**).
- **Battery charge allowed**: EV charging is active and the explicit
  home-battery charging plan continues (Hybrid 2.0 classifies the grid deadband first).
- **House self-consumption**: Hybrid 2.0 tests inverter AC output at measured
  local load minus EV. Battery discharge for the ordinary house is allowed.
- **House control on Hold**: required plan/reference data is missing or cannot
  be used within the configured power range. Do not reuse a stale house-output target.
- **Fresh plan required**: EV charging has stopped, but Battery Hold remains
  active until the native orchestrator publishes a fresh EMHASS plan.

The status is presentation-only. It does not add an override, charger control,
new controller ownership mode or additional Modbus write path. A future
override would change safety and control ownership semantics and therefore
requires a separate explicit design decision and review.

Hybrid 2.0's house-self-consumption exception is the explicit user-requested
test policy. Its periodic reference update remains inside the same controller.

The Power overview flow also shows a charger branch only when an existing EV
status, power, online or load-balancing charger source is configured. When the
selected charging-power sensor is available, its value is normalized to watts
and displayed live; otherwise the node remains a status-only configured branch.
It is drawn beneath House ownership because charger demand is already included
in total house load. This visualization does not add the value again or change
control, accounting or optimization inputs.

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
