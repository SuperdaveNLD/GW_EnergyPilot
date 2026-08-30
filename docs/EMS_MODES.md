# GoodWe EMS Power Mode reference

This page is the compact operator reference for GoodWe EMS registers `47511` and `47512` used by GW EnergyPilot.

For the full Modbus contract, rationale, safety notes and register details, see `docs/MODBUS.md`.

## Registers

```text
47511  EMS Power Mode   uint16
47512  EMS Power Set    uint16, watts
```

`47511` selects the control strategy. `47512` is a non-negative watt magnitude whose electrical meaning depends on the selected mode.

GoodWe distinguishes:

```text
Xmax = upper limit; actual power may be lower.
Xset = target value the inverter tries to reach.
```

## All 12 EMS modes

| Mode | GoodWe/OpenEMS name | EnergyPilot label | `47512` meaning | EnergyPilot policy |
|---:|---|---|---|---|
| **1** | Auto | GoodWe Auto / AI | unused / `0 W` | normal inverter ownership; also used around a zero `P_grid` target when smart-meter control is enabled |
| **2** | Charge PV | PV-priority charging | `Xmax` grid assist allowed for charging; `0 W` = GoodWe-visible PV only | manual only |
| **3** | Discharge PV | PV + battery supply | `Xmax` allowable battery discharge; PV has priority | manual only |
| **4** | Import AC | Inverter import / AC charging | `Xset` inverter-level grid purchase target | manual only |
| **5** | Export AC | Inverter export power | `Xset` inverter-level grid sale/export target | manual only |
| **6** | Conserve | Reserve / Conserve | unused / `0 W` | manual reserve/off-grid preparation |
| **7** | Off-Grid | Off-grid | unused / `0 W` | manual forced off-grid only |
| **8** | Battery Standby | Battery Hold | unused / `0 W` | automatic fallback hold when direct battery strategy is selected; manual hold |
| **9** | Buy Power | Grid import target | `Xset` net import target at smart meter/PCC | automatic import actuator when GoodWe smart meter control is enabled; manual otherwise |
| **10** | Sell Power | Grid export target | `Xset` net export target at smart meter/PCC | automatic export actuator when GoodWe smart meter control is enabled; manual + Maximum export action |
| **11** | Charge Bat | Battery charge power | `Xset` direct battery charge-power target | automatic charge actuator when GoodWe smart meter control is disabled; manual direct charge |
| **12** | Discharge Bat | Battery discharge power | `Xset` direct battery discharge-power target | automatic discharge actuator when GoodWe smart meter control is disabled; manual direct discharge |

## Do not confuse these pairs

| Pair | Difference |
|---|---|
| **2 vs 11** | Mode 2 controls a grid-assist **limit** with PV priority; mode 11 directly targets **battery charge power**. |
| **3 vs 12** | Mode 3 is PV-priority supply with a battery-discharge **allowance**; mode 12 directly targets **battery discharge power**. |
| **4 vs 9** | Mode 4 is **inverter-level** grid-import scheduling; mode 9 targets **net site import at the smart meter/PCC**. |
| **5 vs 10** | Mode 5 is **inverter-level** export scheduling; mode 10 targets **net site export at the smart meter/PCC**. |

## Hardware-validated PCC behavior on the reference ETA-G20

The v0.21 field tests produced consistent site-level behavior:

```text
mode 10 + 400 W  -> approximately 395 W export at the GoodWe meter
mode 9  + 400 W  -> approximately 331 W import at the GoodWe meter
mode 9  + 15 kW  -> approximately 15 kW import, while DC PV was added on top
mode 11 + 15 kW  -> battery remained near 15 kW charge, while PV reduced grid import
```

The 15 kW mode-9 test is particularly important: `47512 = 15000` did **not** limit battery charge to 15 kW. The inverter held the **grid import** around 15 kW and added available DC PV, resulting in battery charge around 16.9 kW on that test point.

This confirms that modes 9/10 are site/PCC targets, while modes 11/12 are direct battery-power targets.

## EnergyPilot automatic-control strategies

v0.22 adds a reversible **GoodWe smart meter active** setting under GOODWE configuration.

### Smart meter active = ON

EMHASS `P_grid` is the actuator plan:

```text
P_grid > +deadband  -> mode 9  -> import target = P_grid
P_grid < -deadband  -> mode 10 -> export target = abs(P_grid)
P_grid near 0 W     -> mode 1  -> GoodWe Auto / self-use
```

EMHASS grid convention:

```text
P_grid > 0 = import
P_grid < 0 = export
```

The GoodWe meter telemetry uses the opposite sign:

```text
36008 < 0 = actual import
36008 > 0 = actual export
```

GoodWe closes the fast regulation loop against its own smart meter/PCC. This means actual house load and generation can change without EnergyPilot continuously trimming a battery target.

### Smart meter active = OFF

EnergyPilot falls back to direct battery execution from EMHASS `P_batt`:

```text
P_batt < -deadband -> mode 11 -> direct battery charge target
P_batt > +deadband -> mode 12 -> direct battery discharge target
P_batt near 0 W    -> mode 8  -> Battery Hold
```

This fallback does not require a valid `P_grid` entity.

### Hybrid control

Hybrid evaluates the configured per-entry deadband in two stages:

```text
abs(P_batt) <= deadband -> mode 8  -> Battery Hold
else abs(P_grid) <= deadband -> mode 1 -> GoodWe Auto / self-use
else P_grid > deadband -> mode 9  -> import target = abs(P_grid)
else P_grid < -deadband -> mode 10 -> export target = abs(P_grid)
```

The neutral battery branch is evaluated first so ordinary forecast house import or PV export cannot turn an idle EMHASS battery plan into active buying or selling. Every non-neutral plan then follows the signed PCC target. Exact positive and negative deadband boundaries remain neutral. The deadband only selects the branch and is never subtracted from the transmitted mode-9/10 setpoint; maximum-power clamping remains the only reduction.

## Why mode 1 is used around zero grid target

On the reference GW15K-ETA-G20, mode 1 was observed naturally consuming available PV surplus into the battery while holding grid flow close to zero. That behavior avoids maintaining a second slow EnergyPilot meter-feedback loop around mode 11.

Mode 1 remains GoodWe-owned self-use behavior, so BMS, inverter, SOC and grid limits remain authoritative.

## Manual selector

All twelve modes remain available through the Home Assistant manual EMS mode select and the v0.21+ Controller test pad. Selecting a manual mode disables Automatic Control ownership before writing the command.

EnergyPilot forces `47512 = 0 W` for modes:

```text
1, 6, 7, 8
```

Other manual modes use the configured Manual power value as `47512`.

The manual pad is independent of the **GoodWe smart meter active** automatic strategy switch: manual mode 9/10/11/12 always means exactly the mode selected by the operator.

## Safety

Modes can materially change battery, grid and off-grid behavior. In particular:

- mode 7 can force off-grid operation;
- modes 4, 5, 9 and 10 control grid-related targets rather than direct battery power;
- modes 11 and 12 directly request battery charge/discharge power;
- a mode-9 grid target can result in battery power greater than the mode-9 setpoint when local PV is also available;
- BMS, inverter, SOC and grid limits remain authoritative even when a setpoint is requested.

The write sequence remains:

```text
write 47512 power
wait briefly
write 47511 mode
```

Do not change that ordering without hardware validation.
