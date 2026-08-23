# Grid-neutral charging and PCC control

This document explains the transition from the v0.18-v0.21 EnergyPilot mode-11 feedback loop to the v0.22 GoodWe smart-meter/PCC strategy.

## Current v0.22 behavior

When **GOODWE → GoodWe smart meter active** is enabled, EnergyPilot no longer maintains its own 30-second mode-11 charge correction loop.

Instead, EMHASS `P_grid` is mapped directly to the GoodWe smart-meter target modes:

```text
P_grid > +deadband  -> mode 9  Grid import target
P_grid < -deadband  -> mode 10 Grid export target
P_grid near 0 W     -> mode 1  GoodWe Auto / self-use
```

EMHASS convention:

```text
P_grid > 0 = planned import
P_grid < 0 = planned export
```

GoodWe smart-meter telemetry convention:

```text
36008 < 0 = actual import
36008 > 0 = actual export
```

The important distinction is that modes 9 and 10 close the control loop **inside GoodWe** against the inverter's own smart meter / point of common coupling (PCC). EnergyPilot supplies the target; GoodWe reacts to real PV, real house load and the measured grid flow.

## Why v0.22 changed the actuator

The older problem was real: a forecast could request battery charging while real PV was lower than forecast. A direct mode-11 command then kept the requested battery charge power and silently imported the missing energy from the grid.

The v0.18-v0.21 solution used:

```text
P_batt charge request
        ↓
mode 11 battery target
        ↓
EnergyPilot reads GoodWe meter
        ↓
30-second charge correction / hold / restart loop
```

That protected against unintended import, but it duplicated a control function that the tested ETA-G20 can perform natively through modes 9 and 10.

v0.21 hardware tests established the difference:

```text
mode 9  setpoint = net grid import target at PCC
mode 10 setpoint = net grid export target at PCC
mode 11 setpoint = direct battery charge target
mode 12 setpoint = direct battery discharge target
```

Examples from the reference inverter:

- mode 10 at `400 W` produced about `395 W` export;
- mode 9 at `400 W` produced about `331 W` import;
- mode 9 at `15 kW` held grid import around `15 kW` while local DC PV was added on top, producing roughly `16.9 kW` battery charge;
- mode 11 at `15 kW` kept battery charge near `15 kW`, while local PV merely reduced the amount that had to come from the grid.

## Zero-grid behavior

Around a planned `P_grid = 0 W`, v0.22 uses mode 1 GoodWe Auto / AI.

On the reference GW15K-ETA-G20 this was observed to:

- serve the house;
- absorb available PV surplus into the battery;
- keep grid flow close to zero;
- do so without EnergyPilot continuously adjusting a battery-power target.

This remains GoodWe-owned self-use behavior. The BMS, inverter SOC limits and GoodWe protection settings remain authoritative.

## Smart meter disabled fallback

If **GoodWe smart meter active** is disabled, EnergyPilot deliberately restores the direct battery strategy:

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt near 0 W    -> mode 8  Battery Hold
```

This fallback does not require `P_grid` to be available.

The switch therefore provides a compatibility path for installations that do not have a usable GoodWe smart meter or that have not yet validated modes 9/10 on their hardware.

## External AC-coupled PV

Modes 9/10 are especially useful with external AC-coupled PV. A separate PV inverter may not appear on the GoodWe DC PV registers, but its power is still visible at the GoodWe smart meter. PCC control therefore sees the net effect automatically.

Directly connected GoodWe PV retains the efficiency benefit of the DC path to the battery. The control objective is still site-level import/export at the meter.

## Legacy diagnostics

The old `grid_neutral_*` diagnostic fields are temporarily retained as inactive compatibility values so older support/frontend layers do not fail during the transition. They should remain zero/false in v0.22 and must not be mistaken for an active second controller.

## Safety boundary

- EMS registers remain `47511` and `47512`.
- The write order remains `47512` power → brief wait → `47511` mode.
- Manual EMS mode selection is unchanged.
- EV coordination remains able to take temporary Battery Hold ownership.
- Automatic Control remains the only automatic EMS writer.
- The GoodWe smart-meter strategy setting does not modify EMHASS configuration; it only chooses which GoodWe actuator primitive executes the published plan.
