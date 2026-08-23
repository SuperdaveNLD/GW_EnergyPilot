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
| **1** | Auto | GoodWe Auto / AI | unused / `0 W` | normal inverter ownership; used when Automatic Control is off |
| **2** | Charge PV | PV-priority charging | `Xmax` grid assist allowed for charging; `0 W` = GoodWe-visible PV only | manual only |
| **3** | Discharge PV | PV + battery supply | `Xmax` allowable battery discharge; PV has priority | manual only |
| **4** | Import AC | Inverter import / AC charging | `Xset` inverter-level grid purchase target | manual only |
| **5** | Export AC | Inverter export power | `Xset` inverter-level grid sale/export target | manual only |
| **6** | Conserve | Reserve / Conserve | unused / `0 W` | manual reserve/off-grid preparation |
| **7** | Off-Grid | Off-grid | unused / `0 W` | manual forced off-grid only |
| **8** | Battery Standby | Battery Hold | unused / `0 W` | automatic/manual hold |
| **9** | Buy Power | Grid import target | `Xset` net import target at smart meter/PCC | manual only; not automatic ownership |
| **10** | Sell Power | Grid export target | `Xset` net export target at smart meter/PCC | manual selector + Maximum export action |
| **11** | Charge Bat | Battery charge power | `Xset` direct battery charge-power target | main automatic charge mode |
| **12** | Discharge Bat | Battery discharge power | `Xset` direct battery discharge-power target | main automatic discharge mode |

## Do not confuse these pairs

| Pair | Difference |
|---|---|
| **2 vs 11** | Mode 2 controls a grid-assist **limit** with PV priority; mode 11 directly targets **battery charge power**. |
| **3 vs 12** | Mode 3 is PV-priority supply with a battery-discharge **allowance**; mode 12 directly targets **battery discharge power**. |
| **4 vs 9** | Mode 4 is **inverter-level** grid-import scheduling; mode 9 targets **net site import at the smart meter/PCC**. |
| **5 vs 10** | Mode 5 is **inverter-level** export scheduling; mode 10 targets **net site export at the smart meter/PCC**. |

## EnergyPilot automatic-control boundary

Current automatic ownership deliberately stays conservative:

```text
Automatic Control OFF  -> mode 1
P_batt charge          -> mode 11
hold / deadband        -> mode 8
P_batt discharge       -> mode 12
```

During planned near-zero-grid charging, mode 11 remains the actuator but EnergyPilot trims `47512` from live smart-meter feedback rather than blindly applying the full EMHASS charge target.

Modes 9 and 10 are grid-target modes. They are not silently substituted for modes 11 and 12 because a grid-target mode can take ownership of battery direction as part of meeting the net grid target.

Mode 2 is not used by EnergyPilot's AC-coupled-PV grid-neutral controller because external AC-coupled generation can appear at the GoodWe meter without appearing as GoodWe PV input.

## Manual selector

All twelve modes are available through the Home Assistant manual EMS mode select. Selecting a manual mode disables Automatic Control ownership before writing the command.

EnergyPilot forces `47512 = 0 W` for modes:

```text
1, 6, 7, 8
```

Other manual modes use the configured Manual power value as `47512`.

## Safety

Modes can materially change battery, grid and off-grid behavior. In particular:

- mode 7 can force off-grid operation;
- modes 4, 5, 9 and 10 control grid-related targets rather than direct battery power;
- modes 11 and 12 directly request battery charge/discharge power;
- BMS, inverter, SOC and grid limits remain authoritative even when a setpoint is requested.

The write sequence remains:

```text
write 47512 power
wait briefly
write 47511 mode
```

Do not change that ordering without hardware validation.
