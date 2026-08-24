<p align="center">
  <img src="https://raw.githubusercontent.com/SuperdaveNLD/GW_EnergyPilot/main/custom_components/gw_energypilot/brand/logo.png" alt="GW EnergyPilot" width="180">
</p>

# GW EnergyPilot

GW EnergyPilot is an unofficial Home Assistant integration for local GoodWe ETA-G20 telemetry, GoodWe EMS control and EMHASS optimization.

> This project is independent and is not affiliated with or endorsed by GoodWe.

## Status

**v0.26 · Beta**

Primary reference hardware: **GoodWe GW15K-ETA-G20**.

In this project, **Beta** means functionality is intentionally available before broad field testing across installations and firmware versions is complete.

Release documentation:

- `docs/RELEASE_NOTES.md` — current release index and Beta scope;
- `CHANGELOG.md` — detailed technical history;
- `docs/EMS_MODES.md` — GoodWe EMS modes 1–12;
- `docs/ACCOUNTING.md` — persistent grid accounting;
- `docs/RUNTIME_STATE.md` — persistent runtime evidence;
- `docs/BATTERY_PRICE_CHART.md` — Battery & Price graph/data ownership;
- `docs/SETTINGS.md` — settings and synchronized minimum-SOC contract.

## v0.26 highlights

- Home Assistant language-aware dashboard with Dutch and English support.
- Full-width **Battery & Price** graph comparing actual battery power with market price for the current local day.
- Read-only backend price-series API using the same EnergyPilot price path as EMHASS.
- Synchronized normal on-grid minimum SOC: one explicit minimum-SOC change updates and verifies GoodWe register `45356`, then writes the same value to EMHASS.
- GoodWe rollback attempt if the subsequent EMHASS minimum-SOC write fails.
- The legacy direct **Battery minimum SOC limits** field-test panel is no longer shown; normal on-grid minimum SOC uses the synchronized control path.
- Existing Battery/Grid/Hybrid Automatic Control, accounting and optimization-log behavior retained.

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
- stateful EMHASS profit/cost/self-consumption strategy;
- persistent optimization history and `last_success`;
- persistent Today/Yesterday grid import/export accounting;
- optional Nord Pool/runtime prices;
- Battery & Price visualization;
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
P_batt requests charge -> mode 11 direct battery charge
else P_grid requests export -> mode 10 grid export target
otherwise -> mode 1 GoodWe Auto / self-use
```

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

The old direct **Battery minimum SOC limits** dashboard panel is not exposed as a normal settings path. The low-level Beta SOC API remains available for diagnostics/backwards-compatible tooling. Maximum SOC remains EMHASS-only.

## Battery & Price chart

The chart is read-only.

- battery bars use Recorder 5-minute means from the existing GoodWe `battery_power` entity;
- charging is below zero, discharging above zero;
- the market-price line comes from the same EnergyPilot runtime price source used for EMHASS;
- chart data is cached for five minutes;
- displayed charged/discharged energy is an approximate visualization integral, not persistent accounting.

Future persistent financial accounting must consume backend grid-accounting deltas and effective prices, not reconstruct totals from chart pixels/buckets.

## Persistent state

Configuration remains in Home Assistant `ConfigEntry.data/options`, EMHASS config or GoodWe registers depending on ownership.

EnergyPilot-owned persistent runtime stores are separate:

```text
gw_energypilot.runtime.<entry_id>
gw_energypilot.accounting.<entry_id>
gw_energypilot.optimization_log.<entry_id>
```

They are not a second settings database.

## Safety boundary

Do not guess GoodWe register addresses, sizes, scales or signs.

`registers.py` is canonical for telemetry/register definitions. Changes to EMS mode semantics, registers `47511/47512`, sign conventions or write ordering require explicit hardware evidence.

Beta register candidates remain bounded and reversible where practical.
