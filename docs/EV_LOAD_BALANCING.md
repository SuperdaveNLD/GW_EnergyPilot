# EV charger load balancing

This document defines the load-balancing actuator for GW EnergyPilot. It is an
opt-in, soft guard for a one- or three-phase EV charger. It reads GoodWe but does
not control it.

## Ownership

```text
linked GoodWe meter_l1_current / meter_l2_current / meter_l3_current
    -> one-phase charger: configured L1, L2 or L3
    -> three-phase charger: max(L1, L2, L3)

GWEnergyPilotEVLoadBalancer
    -> waits for one continuous configured window
    -> calls number.set_value for one writable charger entity
    -> checks one separate read-only allocated-current sensor

GoodWe controller / Modbus EMS path
    -> separate owner; never called by the EV load balancer
```

The selected charger `number` must represent a real writable current-limit
setting. For Zaptec this is normally the installation-level **Available current**
NumberEntity, which applies one value to all three phases. The allocated-current
feedback must be a `sensor` with `device_class: current` and unit `A`, such as
`sensor.zorro_de_zaptec_laadpaal_toegewezen_laadstroom`. A read-only sensor is
never accepted as the actuator.

When a selected EV mode, power, online, control or feedback entity identifies one
Home Assistant config entry, EnergyPilot tries to pair Zaptec control and
feedback automatically. Same-device candidates are preferred. A unique
config-entry match is accepted for Zaptec's installation-level control and
charger-level feedback; tied candidates remain explicit user choices.

## House connection

The EV settings page offers `1 × 25 A`, `1 × 35 A`, `1 × 40 A`, `3 × 25 A`,
`3 × 35 A`, `3 × 40 A`, `3 × 50 A`, `3 × 63 A`, and `3 × 80 A`, plus custom
one-phase and custom three-phase profiles. The ampere value is always a per-phase
limit. `3 × 25 A` is the default.

These profiles follow connection values published by Dutch grid operators. The
operator must still select the actual connection shown by the grid operator or
meter-cabinet documentation; EnergyPilot cannot discover the fuse rating.

## Soft rule

The condition window can be `1`, `2`, `3`, `5`, `10`, or `15` minutes. Fifteen
minutes is recommended, matching Zaptec's guidance not to update Available
current more frequently than every 15 minutes. Existing explicitly saved window
values remain unchanged.

```text
selected/highest GoodWe phase > connection limit + 0.5 A for the full window
    -> reduce charger limit by the rounded-up overload

selected/highest GoodWe phase < connection limit - 0.5 A for the full window
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
For a three-phase charger all three GoodWe meter currents must be finite and
available; otherwise the controller cannot prove that every phase is guarded and
fails without a write. For a one-phase charger only its configured phase is
required. Unknown, unavailable, non-finite or missing actuator values also fail
without a write.

After `number.set_value` returns, EnergyPilot waits up to 60 seconds for the
allocated-current sensor to match the target within 0.25 A. This accommodates
values such as `15.984 A` for a `16 A` request. Diagnostics retain the last
`applied` or `mismatch` result. A mismatch is reported and is not treated as
proof that Zaptec accepted the limit; the normal sustained window prevents a
fast retry loop.

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
authoritative. A one-phase charger must be assigned to its actual connected
phase. Three-phase mode watches the highest measured phase so unequal household
loading is included in the decision.

EV anti-discharge remains a separate controller feature documented in
`EV_ANTI_DISCHARGE.md`; it may influence GoodWe battery direction but does not
share the charger-current actuator.
