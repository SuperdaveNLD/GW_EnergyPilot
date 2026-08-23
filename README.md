<p align="center">
  <img src="https://raw.githubusercontent.com/SuperdaveNLD/GW_EnergyPilot/main/custom_components/gw_energypilot/brand/logo.png" alt="GW EnergyPilot" width="180">
</p>

# GW EnergyPilot

GW EnergyPilot is an unofficial Home Assistant integration for local GoodWe ETA-G20 telemetry, GoodWe EMS control and EMHASS optimization.

> This project is independent and is not affiliated with or endorsed by GoodWe.

## Status

**v0.22 · Beta**

GW EnergyPilot is developed primarily against the **GoodWe GW15K-ETA-G20** and the current ETA-G20 generation.

In this project, **Beta** means functionality is available to the active tester group but has **not yet been extensively field-tested across installations or firmware versions**.

See:

- `docs/RELEASE_NOTES.md` — status and user-facing notes for every version;
- `CHANGELOG.md` — detailed technical history;
- `docs/EMS_MODES.md` — exact meaning of GoodWe EMS modes 1–12.

## Tested hardware

| Model | Status | Notes |
|---|---|---|
| **GoodWe GW15K-ETA-G20** | Active reference hardware | Primary development and validation inverter |

Other ETA-G20 models must be validated individually rather than assumed compatible.

When reporting compatibility, include:

```text
Inverter model
Firmware version
Battery model
GoodWe smart meter present / absent
Whether modes 9 / 10 / 11 / 12 work as documented
```

## What it provides

- direct local Modbus TCP telemetry;
- GoodWe EMS mode/setpoint control;
- manual access to all twelve EMS modes;
- selectable automatic **PCC smart-meter control** or **direct battery control**;
- native EMHASS optimization and publishing;
- stateful EMHASS `profit`, `cost` and `self-consumption` strategy control;
- optional Nord Pool runtime pricing;
- optional EV coordination;
- built-in EnergyPilot dashboard;
- native grid import/export power and cumulative energy;
- optional battery accounting diagnostics;
- Beta G20 SOC-protection/extended-meter diagnostics;
- verified manual `45356/45358` minimum-SOC field-test controls;
- copyable support/Beta diagnostics.

## Requirements

- Home Assistant 2026.8 or newer;
- HACS;
- GoodWe ETA-G20 reachable through Modbus TCP;
- fixed inverter IP address or DHCP reservation;
- EMHASS installed, started and configured;
- optional Nord Pool source when runtime prices are used.

Typical GoodWe ETA-G20 connection:

```text
Port:    502
Unit ID: 247
```

Use only one integration for continuous direct GoodWe polling/control where practical.

## Installation

1. Install and start EMHASS.
2. Add this repository to HACS as an **Integration**.
3. Install **GW EnergyPilot**.
4. Restart Home Assistant.
5. Add **GW EnergyPilot** under **Settings → Devices & services**.
6. Enter inverter IP, port and Unit ID.
7. Keep **Automatic Control OFF** during initial validation.
8. Verify PV, grid, battery and load values.
9. Configure EMHASS source/output entities.
10. Press **Optimize now**.
11. Verify numeric `P_batt`, `P_grid` and expected optimization status.
12. Choose the correct GoodWe automatic strategy under dashboard gear → **GOODWE**.
13. Enable Automatic Control.

## Dashboard settings

The administrator settings gear has three pages:

- **EP** — maximum control power, control deadband, telemetry cadence and EV coordination;
- **EMHASS** — URL, scheduler, output entities, runtime price settings and related EnergyPilot options;
- **GOODWE** — inverter connection, **GoodWe smart meter active**, and manual G20 minimum-SOC field tests.

The existing Home Assistant config entry remains the single integration configuration source.

See `docs/SETTINGS.md` for ownership, security and reload behavior.

# Automatic control in v0.22

v0.22 has two explicit actuator strategies.

## GoodWe smart meter active = ON

This is the default on v0.22 and is intended for installations with a working and validated GoodWe smart meter.

Automatic Control executes EMHASS `P_grid` at the point of common coupling:

```text
P_grid > +deadband  → mode 9  Grid import target
P_grid < -deadband  → mode 10 Grid export target
P_grid near 0 W     → mode 1  GoodWe Auto / AI
```

EMHASS convention:

```text
P_grid > 0 = planned import
P_grid < 0 = planned export
```

GoodWe meter telemetry uses the opposite sign:

```text
36008 < 0 = actual import
36008 > 0 = actual export
```

GoodWe modes 9/10 then close the fast loop against the inverter's own smart meter/PCC.

### Why this is useful

Hardware testing on the reference ETA-G20 confirmed that mode 9/10 setpoints are **grid targets**, not battery targets.

Example:

```text
mode 9 setpoint        15.0 kW
measured grid import   ~15.0 kW
local DC PV            ~3.9 kW
battery charge         ~16.9 kW
```

The local PV was added behind the meter on top of the requested grid import.

By contrast, mode 11 at `15 kW` kept the **battery** near 15 kW and let PV reduce the required grid import.

This distinction is the basis of v0.22 control.

## GoodWe smart meter active = OFF

Automatic Control falls back to direct EMHASS `P_batt` execution:

```text
P_batt < -deadband → mode 11 Battery charge power
P_batt > +deadband → mode 12 Battery discharge power
P_batt near 0 W    → mode 8  Battery Hold
```

This fallback does not require a valid `P_grid` output.

Use it when the GoodWe smart meter is absent/unavailable or while validating another model/firmware.

## Manual modes

The Controller card contains a 12-mode test pad.

- Automatic Control **ON** → buttons/slider are locked, but the live `47511` mode remains highlighted.
- Automatic Control **OFF** → modes 1–12 and the manual setpoint slider become active.
- modes `1`, `6`, `7`, `8` force `0 W`;
- mode `7` asks for explicit off-grid confirmation.

The Smart Meter automatic setting does **not** remap manual commands.

See `docs/EMS_MODES.md`.

# Power/sign conventions

## Battery

```text
negative = charging
positive = discharging
```

## GoodWe smart meter (`36008`)

```text
negative = grid import
positive = grid export
```

## EMHASS `P_grid`

```text
positive = planned import
negative = planned export
```

The GoodWe meter and EMHASS `P_grid` signs are intentionally opposite. Do not interchange them.

# Live energy flow

The dashboard shows PV, house, grid and battery flow around the EnergyPilot hub.

v0.22 makes particle direction authoritative in the active frontend layer:

```text
PV production         → hub
Grid import           → hub
Grid export           hub → grid
Battery charging      hub → battery
Battery discharging   battery → hub
House consumption     hub → house
```

# EMHASS setup

Normal EnergyPilot outputs:

```text
sensor.p_batt_forecast
sensor.p_grid_forecast
sensor.optim_status
```

Recommended publishing behavior when EnergyPilot owns publish-data:

```json
"continual_publish": false
```

EnergyPilot validates optimizer readiness and finite outputs before automatic EMS execution.

Full setup: `docs/EMHASS_SETUP.md`.

# GoodWe power semantics

## Load

Register `35172` is the primary GoodWe load value on the reference GW15K-ETA-G20 and closely matches:

```text
Load L1 + Load L2 + Load L3
```

`PV - grid + battery` is retained as a **system power balance diagnostic**, not a replacement house-load sensor.

Registers `35138` and `35140` are inverter-side diagnostics and must not be labelled as household consumption.

## Grid energy

Canonical Recorder-facing cumulative counters remain:

```text
36015 = total exported grid energy
36017 = total imported grid energy
```

The extended `36104/36120` values remain Beta diagnostics until physical lifetime correlation is sufficient.

# Battery SOC limits

EnergyPilot exposes EMHASS minimum/maximum SOC controls.

A normal grid-connected starting range is approximately:

```text
minimum SOC: 5%
maximum SOC: 95%
```

GoodWe/SEMS+ and the battery BMS have separate protection limits. The most restrictive layer wins.

Current Beta G20 field controls include:

```text
45356  On-grid minimum SOC floor
45358  Off-grid minimum SOC floor
```

They are manual, admin-only, validated/read-back writes and are not automatically changed by EMHASS or Automatic Control.

# EMS write contract

Main registers:

```text
47511 = EMS mode
47512 = EMS power/setpoint magnitude
```

Write ordering remains:

```text
write 47512 power
wait briefly
write 47511 mode
```

Do not change this ordering without hardware validation.

# Known GoodWe/SEMS issue

When SEMS/SEMS+ is used, some users have observed issues with the official GoodWe Home Assistant integration/plugin route. See `docs/KNOWN_ISSUES.md` for the current recommendation and the distinction from EnergyPilot's local Modbus control.

# Documentation

- `docs/ARCHITECTURE.md` — runtime structure and ownership;
- `docs/EMHASS_SETUP.md` — EMHASS installation/output/control setup;
- `docs/EMS_MODES.md` — modes 1–12;
- `docs/GRID_NEUTRAL_CHARGING.md` — migration from old mode-11 feedback to v0.22 PCC control;
- `docs/MODBUS.md` — register semantics and evidence policy;
- `docs/SETTINGS.md` — configuration ownership/security;
- `docs/ENTITIES.md` — Home Assistant entity contract;
- `docs/KNOWN_ISSUES.md` — known field issues;
- `docs/RELEASE_NOTES.md` — every release and Beta/validation status;
- `CHANGELOG.md` — detailed history.

# Safety

This integration can command significant battery/grid power.

Before enabling Automatic Control verify:

- correct inverter/model/firmware;
- correct grid and battery signs;
- correct maximum power setting;
- correct EMHASS outputs;
- GoodWe smart meter presence/status when PCC control is enabled;
- battery/BMS/SOC limits;
- grid connection and contract limits.

GW EnergyPilot remains an unofficial community project. Use real hardware validation for control changes.
