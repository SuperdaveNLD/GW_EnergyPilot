<p align="center">
  <img src="https://raw.githubusercontent.com/SuperdaveNLD/GW_EnergyPilot/main/custom_components/gw_energypilot/brand/logo.png" alt="GW EnergyPilot" width="180">
</p>

# GW EnergyPilot

GW EnergyPilot is an unofficial Home Assistant integration for local GoodWe ETA-G20 telemetry, GoodWe EMS control and EMHASS optimization.

> This project is independent and is not affiliated with or endorsed by GoodWe.

## Status

**v0.25 · Beta**

Primary development and validation hardware is the **GoodWe GW15K-ETA-G20**. Other ETA-G20 models and firmware combinations must be validated individually.

Beta means functionality is available to the active tester group before broad multi-installation field exposure is complete.

Key documentation:

- `docs/RELEASE_NOTES.md` — user-facing release status;
- `CHANGELOG.md` — detailed technical history;
- `docs/ARCHITECTURE.md` — runtime ownership and data flow;
- `docs/EMS_MODES.md` — GoodWe EMS modes 1–12;
- `docs/ACCOUNTING.md` — persistent grid accounting;
- `docs/RUNTIME_STATE.md` — persistent runtime/optimization history;
- `docs/EV_ANTI_DISCHARGE.md` — EV battery-protection behavior;
- `docs/SETTINGS.md` — dashboard configuration ownership.

## What it provides

- direct local GoodWe Modbus TCP telemetry;
- GoodWe EMS mode/setpoint control through the existing `47511/47512` path;
- manual access to all twelve EMS modes;
- three selectable Automatic Control strategies: **Battery**, **Grid** and **Hybrid**;
- native EMHASS optimization and publishing;
- EMHASS `profit`, `cost` and `self-consumption` strategy control;
- optional Nord Pool runtime pricing;
- optional EV anti-discharge protection;
- persistent orchestrator `last_success`;
- persistent newest-50 optimization history with an admin-only Settings **LOG** page;
- native PV, load, battery and grid telemetry;
- persistent Today/Yesterday grid import/export accounting;
- safe source selection between legacy and extended GoodWe lifetime meter layouts for derived accounting;
- Beta G20 SOC-protection and meter diagnostics;
- verified manual `45356/45358` minimum-SOC field-test controls.

## Requirements

- Home Assistant 2026.8 or newer;
- HACS;
- GoodWe ETA-G20 reachable through Modbus TCP;
- fixed inverter IP address or DHCP reservation;
- EMHASS installed, started and configured;
- optional Nord Pool source when runtime prices are used.

Typical GoodWe connection:

```text
Port:    502
Unit ID: 247
```

Use only one integration for continuous direct GoodWe polling/control where practical.

## Installation

1. Install and start EMHASS.
2. Add this repository to HACS as an **Integration**.
3. Install **GW EnergyPilot** and restart Home Assistant.
4. Add GW EnergyPilot under **Settings -> Devices & services**.
5. Enter inverter IP, port and Unit ID.
6. Keep **Automatic Control OFF** during initial validation.
7. Verify PV, grid, battery and GoodWe load values.
8. Configure the EMHASS output entities (`P_batt`, `P_grid`, optimization status).
9. Run **Optimize now** and confirm a successful fresh plan.
10. Choose the intended Automatic Control strategy under dashboard gear -> **GOODWE**.
11. Enable Automatic Control.

# Automatic Control in v0.25

The GOODWE settings page exposes three explicit strategies.

## Battery control

This is the backwards-compatible default for installations without an explicit new strategy when the legacy smart-meter setting is absent/false.

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt near 0 W    -> mode 8  Battery Hold
```

This path does not require a valid `P_grid` output.

## Grid control

For installations with a working and validated GoodWe smart meter/PCC:

```text
P_grid > +deadband -> mode 9  Grid import target
P_grid < -deadband -> mode 10 Grid export target
P_grid near 0 W    -> mode 1  GoodWe Auto / self-use
```

EMHASS and GoodWe grid signs are deliberately opposite:

```text
EMHASS P_grid > 0 = planned import
EMHASS P_grid < 0 = planned export

GoodWe 36008 < 0 = actual import
GoodWe 36008 > 0 = actual export
```

Mode 9/10 setpoints are PCC/grid targets, not direct battery-power targets. On the reference ETA-G20 a 15 kW mode-9 target held roughly 15 kW grid import while locally connected DC PV was added behind the meter.

## Hybrid control

Hybrid combines the useful direct-charge and PCC-export primitives:

```text
P_batt < -deadband      -> mode 11 Battery charge target
else P_grid < -deadband -> mode 10 Grid export target
otherwise               -> mode 1  GoodWe Auto / self-use
```

Hybrid intentionally does not force mode 12 for normal discharge. When there is no explicit charge request and no planned export, GoodWe mode 1 owns self-use balancing.

The legacy `use_goodwe_smart_meter` value remains synchronized/fallback-compatible so existing installations do not silently change strategy on upgrade.

## EV anti-discharge protection

EV protection is a safety override above the normal strategy. When an EV is actively charging:

```text
P_batt requests discharge -> mode 8 Battery Hold
P_batt neutral            -> mode 8 Battery Hold
P_batt requests charge    -> mode 11 Battery charge allowed
```

EnergyPilot does not own or schedule the EV charger. After EV charging stops, native orchestration waits for a fresh EMHASS plan before normal automatic execution resumes.

# Grid accounting

Physical lifetime telemetry remains available using the existing entity contract. For **derived Today/Yesterday accounting**, v0.25 can select one coherent lifetime-counter pair:

```text
extended: 36104 export / 36120 import
legacy:   36015 export / 36017 import
```

The populated extended pair is preferred when available on applicable ETA/ET hardware such as the reference 15 kW G20. An empty `0/0` optional extended block does not displace a usable legacy pair.

The accounting source is persisted. Switching source pairs always re-baselines before accumulating new deltas; EnergyPilot never subtracts absolute lifetime totals from different layouts. Existing daily values survive a same-day source migration, but EnergyPilot does not fabricate energy from before the first new baseline.

The existing lifetime energy entity unique IDs remain unchanged.

# Optimization history

v0.25 stores the newest 50 EnergyPilot-owned optimization attempts per config entry, including successful and failed manual, scheduled and event-triggered runs.

Open dashboard **Settings -> LOG** as a Home Assistant administrator to view the read-only history. Typical fields include run reason/timing, SOC values, current load, price source/points, forecast points, `P_batt`, EMHASS HTTP statuses and errors.

This history is separate from `last_success`: a failed run is useful diagnostic evidence but must not erase the latest successful optimize/publish timestamp.

# Power/sign conventions

```text
Battery power: negative = charging, positive = discharging
GoodWe grid 36008: negative = import, positive = export
EMHASS P_grid: positive = planned import, negative = planned export
```

# GoodWe load and SOC

Register `35172` is the primary GoodWe load value on the reference GW15K-ETA-G20 and normally matches the sum of the three load phases. `PV - grid + battery` remains a system-balance diagnostic, not a replacement house-load sensor.

EnergyPilot exposes EMHASS minimum/maximum SOC controls. A common normal grid-connected starting range is approximately 5–95%, but GoodWe/SEMS+ and the BMS have independent protection limits and the most restrictive layer wins.

Manual Beta field-test controls currently include:

```text
45356  On-grid minimum SOC floor
45358  Off-grid minimum SOC floor
```

These are admin-only, validated/read-back writes and are not automatically changed by EMHASS or Automatic Control.

# EMS write contract

```text
47511 = EMS mode
47512 = non-negative mode-specific power/setpoint magnitude
```

Write ordering remains:

```text
write 47512
wait briefly
write 47511
```

Do not change this ordering or GoodWe register semantics without hardware/vendor/upstream evidence.

# Safety

Before enabling Automatic Control verify inverter/firmware identity, grid and battery signs, configured maximum power, EMHASS output freshness/status, smart-meter validity when Grid/Hybrid is selected, battery/BMS/SOC limits and the installation's grid/contract limits.

GW EnergyPilot can command significant battery/grid power. Real hardware validation remains required for control changes.
