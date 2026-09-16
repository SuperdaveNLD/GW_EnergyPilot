# Hybrid 3.0 excl. EV

**Status: opt-in Beta, introduced in v1.3.0-beta.11.** Select **Settings →
GoodWe → Automatic control strategy → Hybrid 3.0 excl. EV** after installing
the beta. Its stored key is `hybrid_3`. An upgrade never selects it for you;
Battery, Grid, original Hybrid and Hybrid 2.0 remain available and unchanged.

## Why this strategy exists

The owner's goal is to make the most of **Tibber Grid Rewards** while Tibber
independently chooses when the EV charges. EnergyPilot does not start, stop,
schedule or throttle that charger. Instead, this strategy aims to avoid the
home battery compensating the EV's grid draw. The house may still use PV and
battery, and a valid battery charge plan may continue alongside EV charging.

This is an operating objective, not a promise of maximum rewards or a claim
about Tibber's settlement rules. Rewards depend on the external service and
actual metered response. Sampling delays, the installation's measurement
boundary and inverter behavior prevent a guarantee of zero battery-to-EV
flow at every instant. EnergyPilot is not affiliated with Tibber or GoodWe.

## Six normal scenarios

| Regulation intent | EV charging | GoodWe mode | Meaning of the setpoint |
|---|---|---|---|
| Self-use / neutral | No | **1 — Auto** | 0 W; GoodWe self-use, not battery-zero Hold |
| Self-use / neutral | Yes | **5 — inverter AC output** | Measured house load excluding EV, refreshed every 15 seconds |
| Directed discharge | No | **3 — PV-priority discharge** | Bounded planned battery discharge watts |
| Directed discharge | Yes | **5 — inverter AC output** | Measured house load excluding EV; no planned battery export into the EV load |
| Directed charge | No | **2 — PV-priority charge** | Bounded planned grid-assistance allowance; available PV may add |
| Directed charge | Yes | **2 — unchanged** | Same allowance as without EV; no EV correction to the charge setpoint |

The dashboard contains this table in English and Dutch. Its disclosure and
table belong to the permanent control surface; telemetry patches retain them.

### How intent is selected

Use the existing EMHASS signs and the installation's separate deadbands.
With a ready, finite `P_batt` and `P_grid`:

1. `abs(P_grid) <= GoodWe Auto deadband` means self-use, regardless of battery
   sign. This preserves the previous grid-first definition, including PV-only
   self-use plans. It does **not** introduce a new automatic mode-2 / 0 W branch.
2. Otherwise `abs(P_batt) <= Battery Hold deadband` also means self-use.
   Hybrid 3.0 has no mode-9/10 net-only branch. The historical deadband's name
   does not mean that a neutral Hybrid 3.0 battery plan is an explicit Pause.
3. Otherwise negative battery watts mean directed charge; positive watts
   mean directed discharge. Exact deadband boundaries are neutral. A deadband
   is never subtracted from the selected watt magnitude.

Mode-2/3 setpoints are bounded by Maximum control power and 15,000 W; a zero
directed-dispatch limit selects mode 8 Hold. Mode 2 uses planned watts, not
maximum watts by default. For example a 700 W charge plan requests a 700 W
grid-assistance allowance, not 15 kW. A 15 kW planned allowance stays 15 kW
when EV charging begins. Available GoodWe-visible PV may contribute on top;
actual battery power and SOC need not equal EMHASS's forecast. Do not add
measured PV or EV to this allowance. Inverter/BMS limits remain authoritative.

## Mode-5 house measurement

```text
house_reference = max(0, fresh local GoodWe load 35172 - fresh measured EV W)
mode5_setpoint = min(house_reference, Maximum control power, 15000 W)
```

Example: 12,500 W total load minus an 11,000 W EV gives a 1,500 W inverter
AC reference, not a 1,500 W battery discharge target. Internal PV can supply
that output. Do not subtract external AC PV a second time. The 35172 boundary
must include the EV and already reflect external AC PV: that installation
assumption remains a **field-validation gate**. Mode-5 PV-surplus/zero-reference
behavior is not fully established. See the retained [hardware observations](HYBRID_2.md#measured-hardware-evidence).

The same controller callback, control lock, canonical registers and ordered
setpoint-before-mode transaction own every write. There is no extra fast
feedback loop, grid-error integrator or charger-control path. The reference
updates at most every 15 seconds; safety and plan-direction changes bypass
that reference throttle. This is not a certified grid/phase-current limiter.

## Failure, recovery and command evidence

- EV house control requires finite, positive measured EV power with explicit
  W/kW/MW/mW units. `last_reported` is primary; `last_updated` is fallback.
  Both the EV report and successful full local Modbus load snapshot must be
  0–30 seconds old, with timestamps at most 15 seconds apart. Missing, future
  or timezone-naive timestamps fail closed; cloud or forecast load is rejected.
- Missing required house measurements immediately select **8 / 0 W Hold**.
  Recovery requires at least 15 seconds and two distinct fresh report pairs,
  with both sources advancing. A repeated old pair alone cannot release Hold.
  Another invalid sample restarts recovery. A valid directed-charge plan is
  independent of this house-reference guard and keeps mode 2.
- Missing, explicitly non-ready or suspended plans select Hold in Hybrid 3.0,
  with or without EV. Existing valid persistent-plan fallback is retained;
  it never overrides explicit non-ready optimizer status or extends expiry.
- Confirmed native EV stop retains Hold until a successful new optimization
  and fresh finite live battery **and** grid publications after that stop.
  Repeated idle EV events cannot release the stale plan. Unavailable activity
  after a known active session is not treated as a confirmed stop.
- After each Hybrid 3.0 automatic write, read the canonical local EMS status
  directly, up to three attempts with 0.5 seconds between mismatches. This
  does not repeat the write or refresh the load timestamp. An identical
  command may be skipped only with a matching confirmed acknowledgement no
  older than 30 seconds and matching current readback. Invalidate that
  acknowledgement **before** any new write, including Hold.
- A read failure or persistent mismatch is recorded as such and propagated;
  it is never presented as hardware verification. Readback confirms the EMS
  mode/setpoint only, not settled physical power. There is no blind retry-write
  storm. The existing controller/orchestrator owns subsequent recovery.
- `mapping_preview.runtime_guard`, execution-history actuals and the debug
  report include measurement ages, exact rejection/hold reason, recovery count
  and command-readback status. The full history table exposes these details;
  write/readback failures take precedence over the generic EV-override label.

Manual mode numbers remain exact. Manual Pause retains mode 8; Automatic OFF
retains mode 1 / 0 W. No entity identities, Store keys/versions, EMHASS
configuration, CUSTOM load forecast (including 700 W), SOC policy or optimizer
schedule is changed. Reverting the strategy is an explicit existing setting;
there is no persistent-state migration or rollback transaction to perform.

## Validation boundary

The release tests cover all six scenarios, exact boundaries, watt clamps,
unchanged legacy/manual behavior, missing/stale/skewed measurements, recovery,
delayed/failed readback, EV-stop freshness, persistence and stable EN/NL UI.
These are software checks, not a completed inverter field test.

Before treating the strategy as proven on an installation, correlate fresh
EV, local load, PV, battery and PCC measurements with requested and read-back
mode/setpoint through EV start, ramps, stop, PV surplus and charge/discharge
windows. Validate the 35172 boundary with external PV separately. The prior
execution-history oscillation did not identify its exact failing sensor; the
new diagnostics are intended to establish that evidence, not to claim all
mode-5/Hold transitions or reward losses are already physically resolved.
