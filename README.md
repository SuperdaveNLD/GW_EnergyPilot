<p align="center">
  <img src="https://raw.githubusercontent.com/SuperdaveNLD/GW_EnergyPilot/main/custom_components/gw_energypilot/brand/logo.png" alt="GW EnergyPilot" width="180">
</p>

# GW EnergyPilot

GW EnergyPilot is an unofficial Home Assistant integration for local GoodWe ETA-G20 telemetry, GoodWe EMS control and EMHASS optimization.

> This project is independent and is not affiliated with or endorsed by GoodWe.

## Status

**v0.33 · Beta**

Primary reference hardware: **GoodWe GW15K-ETA-G20**.

In this project, **Beta** means functionality is intentionally available before broad field testing across installations and firmware versions is complete.

Release documentation:

- `docs/RELEASE_NOTES.md` — current release index and Beta scope;
- `CHANGELOG.md` — detailed technical history;
- `docs/EMHASS_PLAN_RUNTIME.md` — persistent canonical EMHASS plan/recovery contract;
- `docs/BATTERY_SAVER.md` — Battery Saver profiles, anti-churn tuning and ownership;
- `docs/DEBUG_LOG.md` — opt-in LOG-tab debug-session/support-report contract;
- `docs/EMS_MODES.md` — GoodWe EMS modes 1–12;
- `docs/ACCOUNTING.md` — persistent grid accounting;
- `docs/RUNTIME_STATE.md` — persistent runtime evidence;
- `docs/BATTERY_PRICE_CHART.md` — Battery & Price graph/data ownership;
- `docs/BATTERY_PLAN_CHART.md` — plan-versus-actual graph/data ownership;
- `docs/SETTINGS.md` — settings and synchronized minimum-SOC contract.

## v0.33 highlights

- EnergyPilot now keeps a validated persistent mirror of the canonical EMHASS `P_batt` / `P_grid` horizon from official `GET /api/v1/plan`, so a temporary Home Assistant entity publication gap after restart/reload does not immediately erase the usable plan.
- Live configured Home Assistant plan entities remain first priority. The persistent mirror is used only while it is still inside its inferred validity window; an explicit non-ready optimizer status remains authoritative.
- Fresh EMHASS output detection now uses Home Assistant `last_reported`, so a valid newly published `P_batt` value is accepted even when its numeric value did not change.
- The Battery · Plan · Price card now rebuilds when the active plan changes and bypasses its normal five-minute cache for a newly published plan without reintroducing duplicate cards.
- All four managed Battery Saver profiles gain the same small price-relative anti-churn charge/discharge weight to suppress low-value quarter-hour reversals. **Gold Rush** now uses a 5–96% soft SOC zone.
- No GoodWe register, Modbus block, EMS mapping, write ordering, entity ID or unique ID changes are introduced by these v0.33 improvements.

## Next-release Battery Saver tuning

The current feature branch prepares the next Battery Saver optimization update:

- managed profiles own the EMHASS hard Maximum SOC as part of the same apply/rollback transaction as their economic penalties;
- hard maxima are **Mad-Steve 100%**, **Gold Rush 96%**, **Balanced 95%** and **Battery Saver/Eco 90%**;
- the common price-relative anti-churn factor moves from `1.5%` to **`2.25%`** per charge/discharge direction, which is approximately `0.007` currency/kWh at the field-test price reference around `0.31`;
- the GoodWe-synchronized minimum SOC remains a separate hard lower boundary and is checked against the effective profile maximum before solving.

## Tested hardware

| Model | Status | Notes |
|---|---|---|
| **GoodWe GW15K-ETA-G20** | Active reference hardware | Primary development and field validation inverter |

Other ETA-G20 models/firmware must be validated individually.

When reporting compatibility, include inverter model/firmware, battery model, GoodWe smart-meter presence and relevant EMS/register observations.

## Main capabilities

- direct local GoodWe Modbus TCP telemetry;
- EMS mode/setpoint control;
- manual access to all twelve EMS modes;
- three Automatic Control strategies: Battery, Grid and Hybrid;
- native EMHASS optimization/publishing;
- persistent validated EMHASS plan continuity across temporary publication gaps;
- four EnergyPilot Battery Saver profiles with price-relative SOC/power preferences, profile-owned maximum SOC and anti-churn battery-throughput costs;
- stateful EMHASS profit/cost/self-consumption strategy;
- persistent optimization history and `last_success`;
- opt-in bounded LOG-tab debug sessions and copyable support reports;
- persistent Today/Yesterday grid import/export accounting;
- optional Nord Pool/runtime prices;
- Battery plan / actual / price visualization;
- EV anti-discharge protection;
- synchronized normal on-grid minimum SOC between EMHASS and GoodWe `45356`;
- low-level Beta SOC API retained for diagnostics/backwards-compatible tooling;
- built-in EnergyPilot dashboard and support diagnostics.

## Requirements

- Home Assistant 2026.8 or newer;
- HACS;
- GoodWe ETA-G20 reachable through Modbus TCP;
- fixed inverter IP address or DHCP reservation;
- EMHASS installed/started/configured for native optimization features;
- optional runtime price source when price-aware optimization/charting is used.

Typical GoodWe ETA-G20 connection:

```text
Port:    502
Unit ID: 247
```

Use only one continuously polling/controlling direct GoodWe integration where practical.

## Installation / first validation

1. Install and start EMHASS.
2. Add this repository to HACS as an Integration.
3. Install GW EnergyPilot.
4. Restart Home Assistant.
5. Add GW EnergyPilot under Settings → Devices & services.
6. Enter inverter IP, port and Unit ID.
7. Keep Automatic Control OFF during first validation.
8. Verify PV, Home, Grid, Battery and EMS read-back values.
9. Configure EMHASS output/status entities and runtime pricing if used.
10. Press Optimize now and verify fresh numeric `P_batt`, `P_grid` and optimization status.
11. Select the intended Automatic Control strategy under dashboard gear → GOODWE.
12. Enable Automatic Control only after telemetry/control semantics are confirmed.

## Automatic Control

### Battery control

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt near 0 W    -> mode 8 Battery Hold
```

This remains the backwards-compatible default when no explicit strategy exists and the legacy smart-meter flag is missing/false.

### Grid control

```text
P_grid > +deadband -> mode 9 Grid import target
P_grid < -deadband -> mode 10 Grid export target
P_grid near 0 W    -> mode 1 GoodWe Auto / self-use
```

This requires a working/validated GoodWe smart meter.

### Hybrid control

```text
P_grid > +deadband -> mode 9 Grid import target (buy/import)
else P_batt > +deadband -> mode 12 Battery discharge power (sell/discharge)
else P_batt near 0 W -> mode 8 Battery Hold
otherwise -> mode 1 GoodWe Auto / self-use
```

Hybrid is deliberately asymmetric. Buying is controlled at the PCC through mode 9 and the EMHASS `P_grid` magnitude. Selling is controlled through direct battery discharge mode 12 and the EMHASS `P_batt` magnitude.

A Hybrid charging plan with no planned grid import falls back to GoodWe self-use. That lets locally available PV flow to the battery according to the inverter's own fast control instead of forcing the battery to the forecast-sized EMHASS charging value. A neutral EMHASS battery plan remains neutral through mode 8.

EV anti-discharge remains a higher-priority directional safety override.

## EMS / sign conventions

Battery power:

```text
negative = charging
positive = discharging
```

GoodWe smart meter register `36008`:

```text
negative = actual import
positive = actual export
```

EMHASS `P_grid` uses the opposite grid sign:

```text
positive = planned import
negative = planned export
```

EMS contract:

```text
47511 = mode
47512 = non-negative mode-specific setpoint magnitude
```

Write ordering remains:

```text
47512 -> brief wait -> 47511
```

## Minimum SOC ownership

The normal on-grid minimum is controlled through the existing EMHASS minimum-SOC NumberEntity.

An explicit change:

```text
validate request
-> require current readable GoodWe 45356
-> write 45356
-> verify read-back
-> write same percentage to EMHASS battery_minimum_state_of_charge
-> refresh coordinator state
-> debounce one fresh optimization
```

If `45356` is unavailable, neither system is changed. If EMHASS fails after a verified GoodWe write, EnergyPilot attempts to restore the previous GoodWe value.

There is no startup/background SOC synchronization.

The old direct **Battery minimum SOC limits** dashboard panel is not exposed as a normal settings path. The low-level Beta SOC API remains available for diagnostics/backwards-compatible tooling. Maximum SOC remains an EMHASS hard limit; when a Battery Saver profile is managed, EnergyPilot owns that EMHASS maximum as part of the selected profile.

## Battery Saver

Battery Saver is an opt-in EnergyPilot policy layer over EMHASS. It never writes a GoodWe mode directly. The public profiles are **Mad-Steve**, **Gold Rush**, **Balanced** and **Battery Saver**.

Managed profiles use a common price-relative charge/discharge anti-churn cost and profile-specific hard maximum SOC/power-stress behavior. The staged next-release maxima are **100% / 96% / 95% / 90%** for Mad-Steve / Gold Rush / Balanced / Battery Saver respectively. Minimum SOC remains the GoodWe-synchronized hard floor.

The common anti-churn factor is staged at **2.25% × price reference per direction**. At the field-test price reference around `0.31`, that is approximately `0.007` per charged or discharged kWh.

See `docs/BATTERY_SAVER.md` for exact profile factors and ownership.

## Battery plan / actual / price chart

The chart is read-only.

- actual battery bars use Recorder 5-minute means from the existing GoodWe `battery_power` entity;
- charging is below zero, discharging above zero, while near-zero samples are not drawn as false directional bars;
- historical plan blocks use the configured EnergyPilot `P_batt` entity history, including the state already active at local midnight;
- future plan blocks prefer the validated persistent official EMHASS plan mirror; current Home Assistant `battery_scheduled_power` and legacy/custom `forecasts` remain compatibility fallbacks;
- the forecast interval active at NOW is clipped at NOW rather than discarded because it began a few minutes earlier;
- dashed plan overlays render above solid actual bars;
- a newly published plan forces a chart refresh without waiting for the normal five-minute cache;
- the market-price series comes from the same EnergyPilot runtime price source used for EMHASS and is rendered as interval steps;
- the card supports S/M/L layouts and an expanded detail view;
- native GoodWe day counters `35208` / `35211` are preferred for the headline charged/discharged totals;
- Recorder-integrated battery power remains a separate visualization comparison and is not calibrated to force a match with the native inverter counter;
- if no usable plan exists, planned-energy summaries display `—` rather than a fabricated zero.

Future persistent financial accounting must consume backend grid-accounting deltas and effective prices, not reconstruct totals from chart pixels/buckets.

## Persistent state

Configuration remains in Home Assistant `ConfigEntry.data/options`, EMHASS config or GoodWe registers depending on ownership.

EnergyPilot-owned persistent runtime stores are separate:

```text
gw_energypilot.runtime.<entry_id>
gw_energypilot.accounting.<entry_id>
gw_energypilot.optimization_log.<entry_id>
gw_energypilot.plan.<entry_id>
```

The plan Store is a bounded resilience mirror of EMHASS's canonical plan, not a second optimizer or settings database. It is valid only through its inferred final plan interval. The debug session is intentionally **not** persistent and is not added to this list.

## Debug logging

Open dashboard settings → **LOG** and select **Start debug logging** only when reproducing a problem. Stop capture after reproduction, then use **Copy debug report** for support.

The debug buffer is bounded and memory-only. It observes the current EnergyPilot runtime rather than polling or controlling hardware independently. See `docs/DEBUG_LOG.md` for captured fields, privacy boundaries and lifecycle details.

## Safety boundary

Do not guess GoodWe register addresses, sizes, scales or signs.

`registers.py` is canonical for telemetry/register definitions. Changes to EMS mode semantics, registers `47511/47512`, sign conventions or write ordering require explicit hardware evidence.

Beta register candidates remain bounded and reversible where practical.
