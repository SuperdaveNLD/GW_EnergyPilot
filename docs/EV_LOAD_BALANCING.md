# EV charger load balancing

This document defines the first load-balancing actuator for GW EnergyPilot. It is
an opt-in, soft guard for one three-phase EV charger. It does not control GoodWe.

## Ownership

```text
selected Home Assistant current sensor (one phase)
    -> observation input

GWEnergyPilotEVLoadBalancer
    -> waits for one continuous configured window
    -> calls number.set_value for one selected charger entity

GoodWe controller / Modbus EMS path
    -> separate owner; never called by the EV load balancer
```

The selected charger `number` must represent one maximum-current setting that the
charger applies to all three phases together. Per-phase charger actuators, charge
session scheduling and vehicle target SOC are outside this first scope.

## House connection

The EV settings page offers `1 × 25 A`, `1 × 35 A`, `1 × 40 A`, `3 × 25 A`,
`3 × 35 A`, `3 × 40 A`, `3 × 50 A`, `3 × 63 A`, and `3 × 80 A`, plus custom
one-phase and custom three-phase profiles. The ampere value is always a per-phase
limit. `3 × 25 A` is the default.

These profiles follow connection values published by Dutch grid operators. The
operator must still select the actual connection shown by the grid operator or
meter-cabinet documentation; EnergyPilot cannot discover the fuse rating.

## Soft rule

The condition window can be `1`, `2`, `3`, `5`, `10`, or `15` minutes. Five
minutes is recommended.

```text
measured phase > connection limit + 0.5 A for the full window
    -> reduce charger limit by the rounded-up overload

measured phase < connection limit - 0.5 A for the full window
    -> increase charger limit by the whole-amp headroom

measurement returns inside the band or becomes unavailable
    -> cancel the pending adjustment
```

After each adjustment, another complete window is required. This intentionally
avoids a fast competing loop and gives brief overloads time to clear. It does not
model a fuse time/current curve and must not be treated as guaranteed overload
protection.

The regulator respects the configured charger minimum and maximum and the
selected NumberEntity's `min`, `max`, and `step`. If overload remains when the
minimum is reached, it reports `minimum_reached`; it cannot remove non-EV load.
Unknown, unavailable, non-finite or missing source/actuator values fail without a
write.

## Maximum-current safety acknowledgement

The default configured maximum is `16 A`; the default minimum is `6 A`. A new
maximum above `16 A` requires both:

1. a prominent browser confirmation that the complete charger circuit has been
   verified; and
2. a separate backend confirmation flag, so bypassing the browser cannot silently
   raise the boundary.

Every accepted change to a new value above `16 A` is appended to:

```text
gw_energypilot.ev_load_balancing_audit.<config_entry_id>
```

The record contains UTC time, Home Assistant user ID, current limit, charger
entity and connection profile. Earlier records are never trimmed or replaced by
normal integration operation. Unrelated settings and options-flow saves preserve
the configured EV load-balancing values.

While enabled, an externally raised charger NumberEntity above the configured
maximum is clamped back immediately. The regulator never automatically raises its
own configured maximum.

## Safety boundary

This feature is best-effort software control. Correct cable sizing, phase layout,
breaker/fuse selection, charger configuration and charger-side safety remain
authoritative. Measuring only one phase is safe only when that chosen phase is the
intended limiting observation for the installation. Unequal phase loading can
overload another phase without this first implementation seeing it.

EV anti-discharge remains a separate controller feature documented in
`EV_ANTI_DISCHARGE.md`; it may influence GoodWe battery direction but does not
share the charger-current actuator.
