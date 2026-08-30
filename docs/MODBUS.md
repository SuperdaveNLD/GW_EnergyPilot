# GoodWe Modbus contract

This document records the Modbus assumptions currently used by GW EnergyPilot.

The canonical machine-readable definitions live in:

```text
custom_components/gw_energypilot/registers.py
```

Do not treat this document as permission to invent or extrapolate unverified registers.

## Tested hardware

GW EnergyPilot is specifically designed and developed around the **GoodWe ETA-G20 generation**.

Current confirmed development and validation inverter:

- **GoodWe GW15K-ETA-G20**

Other ETA-G20 models may use closely related telemetry and EMS concepts, but they are not considered tested until verified on real hardware.

The project has a small active tester group. Starting with v0.16, selected candidate registers may be shipped as **Beta diagnostics** so multiple installations can validate them. In this project, Beta means the value has **not yet been extensively field-tested** and must not be treated as confirmed automatic-control semantics.

v0.18 adds one deliberately narrow Beta write exception: the already-known SOC-floor registers `45356` and `45358` may be changed manually from the dedicated GOODWE field-test controls, with a fixed key whitelist, percentage validation and immediate read-back verification. They remain completely outside EnergyPilot automatic control and EMHASS.

## Connection defaults

```text
transport: Modbus TCP
port:      502
unit id:   247
```

These are defaults and may be configurable per installation.

## Sign conventions

Current tested conventions:

```text
Grid power
  negative = import from grid
  positive = export to grid

Battery power
  negative = battery charging
  positive = battery discharging
```

These conventions affect dashboard direction and EMHASS/controller logic and must not be changed without tested evidence.

## Important runtime registers

| Address | Key | Type | Scale | Purpose |
|---:|---|---|---:|---|
| 35301 | `pv_total_power` | uint32 | 1 | Total PV power |
| 35172 | `total_load_power` | int16 | 1 | GoodWe load power; primary Home/load value on tested G20 |
| 35182 | `battery_power` | int32 | 1 | Battery power |
| 35206 | `battery_charge_energy_total` | uint32 | 0.1 | Cumulative battery charge energy in kWh; optional |
| 35208 | `battery_charge_energy_today` | uint16 | 0.1 | Battery charge energy today in kWh; optional |
| 35209 | `battery_discharge_energy_total` | uint32 | 0.1 | Cumulative battery discharge energy in kWh; optional |
| 35211 | `battery_discharge_energy_today` | uint16 | 0.1 | Battery discharge energy today in kWh; optional |
| 37007 | `battery_soc` | uint16 | 1 | Battery state of charge |
| 37008 | `battery_soh` | uint16 | 1 | Battery state of health |
| 36008 | `meter_total_power_fast` | int16 | 1 | Primary instantaneous grid power |
| 36015 | `meter_total_energy_export` | float32 | 0.001 | Current canonical cumulative exported grid energy in kWh |
| 36017 | `meter_total_energy_import` | float32 | 0.001 | Current canonical cumulative imported grid energy in kWh |
| 47511 | `ems_mode` | uint16 | 1 | EMS mode control/state |
| 47512 | `ems_setpoint` | uint16 | 1 | EMS power setpoint |

## G20 Beta diagnostics and v0.18 SOC-floor test

The following values are available for field validation but are **not all confirmed production semantics**:

| Address | EnergyPilot key | Type | Scale | Current Beta meaning | Write policy |
|---:|---|---|---:|---|---|
| 45356 | `battery_discharge_depth_on_grid` | uint16 | 1 | Raw on-grid minimum SOC floor; user-facing DoD = `100 - raw` | Manual v0.18 field-test only |
| 45358 | `battery_discharge_depth_off_grid` | uint16 | 1 | Raw off-grid minimum SOC floor | Manual v0.18 field-test only |
| 47500 | `battery_soc_protection` | uint16 | 1 | Battery SOC-protection/status candidate | Read-only |
| 36104 | `meter_total_energy_export_extended` | uint64 | 0.01 | Extended 15 kW+ lifetime grid export counter | Read-only |
| 36120 | `meter_total_energy_import_extended` | uint64 | 0.01 | Extended 15 kW+ lifetime grid import counter | Read-only |

### Why `45356` is treated as minimum SOC

Current maintained GoodWe implementations define register `45356` as the battery discharge-depth setting, but expose the user-facing on-grid depth of discharge as:

```text
on-grid DoD = 100 - register 45356
```

So a raw register value of `10` corresponds to a **10% minimum SOC floor** and 90% depth of discharge. This also matches the reference GW15K-ETA-G20 observation that the battery stopped discharging at approximately 10% while `45356` read `10`.

Independent maintained GoodWe/OpenEMS mappings also associate `45356` with the minimum-SOC-under-limit setting and `45358` with the off-grid counterpart. EnergyPilot therefore keeps the existing internal keys for entity compatibility but presents the raw values as minimum-SOC floors in the v0.18 field-test UI.

### v0.18 write safety contract

The v0.18 test path is intentionally not a generic Modbus editor.

- `registers.py` remains the canonical source for the two addresses;
- the client derives the write addresses from the existing register definitions instead of duplicating numeric constants;
- only `battery_discharge_depth_on_grid` and `battery_discharge_depth_off_grid` are whitelisted;
- values must be whole percentages in the range `0..100`;
- the selected register must already be present in the coordinator telemetry before the API permits a write;
- one user action writes exactly one register;
- the dashboard requires an explicit confirmation for each write;
- the client reads the same register back immediately after writing;
- a write is reported successful only when the read-back equals the requested value;
- verified read-back is reflected in the coordinator immediately and then confirmed again by normal polling;
- no automatic rollback is attempted after a write error or read-back mismatch; the operator must inspect the current value before retrying.

This path is manual field-validation only. Automatic Control, controller ownership, EMHASS, event triggers and schedulers do not read these values as control targets and do not write them.

Register `47500` is explicitly excluded. On the reference G20 it has returned `65535`, and its firmware-dependent meaning is not sufficiently established for a write path.

## Load semantics

On the tested GW15K-ETA-G20, register `35172` closely matches the sum of the three load phase registers:

```text
35164 + 35166 + 35168 ~= 35172
```

For that reason, GW EnergyPilot uses `35172` as the primary household/load value and as the load source for EMHASS forecasting.

The calculated expression:

```text
PV - grid + battery
```

is a whole-system power balance. It may include conversion losses, auxiliary consumption, and differences between measurement points. It must not silently replace register `35172` as the Home/load entity.

## Inverter-side diagnostic power

Registers `35138` and `35140` are exposed as inverter-side diagnostics:

```text
35138 = total_inverter_power
35140 = ac_active_power
```

Do not label `35138` as inverter self-consumption unless independent validation proves that interpretation.

## Grid meter energy

The currently canonical EnergyPilot cumulative grid-energy source uses:

```text
36015 = exported energy total
36017 = imported energy total
```

These are decoded as IEEE-754 big-endian float32 values scaled by `0.001` to kWh. Home Assistant exposes them as `total_increasing` energy sensors so Recorder can derive daily/monthly/yearly deltas efficiently.

### Extended 15 kW+ counter validation

On GW15K-ETA-G20 installations, the legacy cumulative counters can be compared with the Beta candidates:

```text
36104 = candidate extended total exported energy
36120 = candidate extended total imported energy
```

The extended candidates are decoded as unsigned 64-bit big-endian register sequences and scaled by `0.01 kWh`.

On the reference GW15K-ETA-G20, both have produced plausible non-zero lifetime values. They remain diagnostics until delta testing against an independent meter/SEMS lifetime source confirms both direction and scaling. Promotion must preserve existing Home Assistant unique IDs and Recorder history where practical.

## Battery energy accounting

GoodWe-compatible ET register documentation and the maintained Python GoodWe implementation identify the battery charge/discharge counters at `35206-35211` as integer energy values with `0.1 kWh` scaling.

EnergyPilot keeps this block optional while it is being validated on additional ETA-G20 firmware revisions. The values are available internally and in support diagnostics, but are not used for EMS control or synthetic cycle calculations.

Current mapping:

```text
35206-35207  lifetime battery charge energy    uint32 / 10 -> kWh
35208        battery charge energy today       uint16 / 10 -> kWh
35209-35210  lifetime battery discharge energy uint32 / 10 -> kWh
35211        battery discharge energy today    uint16 / 10 -> kWh
```

Do not derive equivalent full cycles until usable battery capacity/model semantics are available from a validated source or explicit configuration. The BMS SOH value from register `37008` remains a separate measurement and must not be treated as a cycle counter.

## Battery SOC protection layers

EMHASS minimum/maximum SOC values are optimizer constraints. They do not override inverter or BMS protection.

The practical hierarchy is:

```text
EMHASS optimizer limit
GoodWe / inverter SOC floor
Battery BMS limit

most restrictive active limit wins
```

That is why an inverter whose raw on-grid `45356` value is `10` can refuse a mode-12 discharge request below about 10% even if EMHASS has a lower minimum SOC target.

The v0.18 manual test exists specifically to correlate that raw GoodWe floor with observed G20 behavior. It does not make the GoodWe floor an EnergyPilot planning variable. EMHASS remains free to plan within its own configured limits, while the inverter remains the independent hardware enforcement layer.

## GoodWe EMS Power modes (`47511` / `47512`)

GoodWe EMS control is a two-register contract:

```text
47511  EMS Power Mode   uint16
47512  EMS Power Set    uint16, watts
```

The mode in `47511` defines **what is being controlled**. The value in `47512` is always a non-negative watt magnitude; charge/import/discharge/export direction comes from the selected mode, not from a signed setpoint.

The maintained GoodWe/OpenEMS mapping describes two different setpoint concepts:

```text
Xmax = an upper limit; actual power may be lower because of PV, load, BMS,
       inverter or grid limits.

Xset = a target value the inverter tries to reach, still bounded by physical
       and configured limits.
```

This distinction is important. Modes that all accept a value in watts are **not interchangeable**: some control battery power, some control grid power at the smart meter/PCC, and some implement PV/grid priority rules inside the inverter.

### Complete 12-mode map

| Mode | GoodWe/OpenEMS name | EnergyPilot label | Meaning of `47512` | Current EnergyPilot use |
|---:|---|---|---|---|
| **1** | Auto | GoodWe Auto / AI | Not used; EnergyPilot writes `0 W` | Return ownership to the inverter / normal self-use |
| **2** | Charge PV | PV-priority charging | `Xmax`: maximum grid power allowed to assist charging; `0 W` means PV-only charging | Manual only; deliberately not used for AC-coupled PV control |
| **3** | Discharge PV | PV + battery supply | `Xmax`: allowable battery discharge power while PV remains higher priority | Manual only |
| **4** | Import AC | Inverter import / AC charging | `Xset`: target grid purchase/import for inverter-level scheduling | Manual only |
| **5** | Export AC | Inverter export power | `Xset`: target grid sale/export for inverter-level scheduling | Manual only |
| **6** | Conserve | Reserve / Conserve | Not used; EnergyPilot writes `0 W` | Manual only; reserve/off-grid preparation behavior |
| **7** | Off-Grid | Off-grid | Not used; EnergyPilot writes `0 W` | Manual only; forces off-grid operation |
| **8** | Battery Standby | Battery Hold | Not used; EnergyPilot writes `0 W` | Automatic hold/deadband/EV/protective hold and manual pause |
| **9** | Buy Power | Grid import target | `Xset`: target import at the GoodWe smart-meter/PCC; battery may charge or discharge to hold it | Manual only; intentionally not automatic ownership |
| **10** | Sell Power | Grid export target | `Xset`: target export at the GoodWe smart-meter/PCC | Manual selector and Maximum export quick action |
| **11** | Charge Bat | Battery charge power | `Xset`: direct battery charging-power target | Main automatic charge mode and manual control |
| **12** | Discharge Bat | Battery discharge power | `Xset`: direct battery discharging-power target | Main automatic discharge mode and manual control |

The EnergyPilot labels above are the current stable labels from `const.py`. They are intentionally not renamed casually because the manual Home Assistant select exposes the label as part of its option string.

### Mode 1 — Auto / self-use

GoodWe controls battery charge/discharge from the smart-meter balance for normal self-consumption. `47512` does not define a power target.

EnergyPilot uses mode 1 when **Automatic Control is disabled**, returning control to the inverter with a `0 W` setpoint.

### Mode 2 — Charge PV / PV-priority charging

Purpose: keep the battery charging while **PV has first priority** and the grid may assist only up to the configured allowance.

```text
47512 = Xmax = maximum grid power allowed to assist charging
0 W   = charge from GoodWe-visible PV only
```

This is **not a direct battery charge-power target**. The actual battery charge can include PV plus permitted grid power and is still limited by BMS/inverter charge limits.

EnergyPilot deliberately does not use mode 2 for its AC-coupled-PV grid-neutral controller. External AC-coupled generation is visible at the grid meter but is not necessarily represented as GoodWe PV input, so mode 2 cannot be assumed to express the desired whole-site behavior.

### Mode 3 — Discharge PV / PV + battery supply

Purpose: keep supplying/exporting power with **PV preferred** and battery discharge available as the lower-priority source.

```text
47512 = Xmax = allowable battery discharge power
```

The value is a discharge limit, not the same direct battery target semantics as mode 12. PV remains the preferred source.

### Mode 4 — Import AC / inverter-level grid import

Purpose: use the inverter as a grid-scheduling unit where **grid import has priority** and PV is lower priority.

```text
47512 = Xset = target power purchased from the grid
```

GoodWe's mode description explicitly treats this as inverter-level scheduling and does **not** account for grid-side/site load in the same way as the smart-meter regional modes. Excess PV may be curtailed to satisfy the mode's internal priority behavior.

Therefore mode 4 must not be treated as equivalent to mode 9 or mode 11:

- mode 4 = inverter-level grid-purchase target;
- mode 9 = smart-meter/PCC grid-import target;
- mode 11 = direct battery charge-power target.

### Mode 5 — Export AC / inverter-level export

Purpose: schedule inverter AC export. **PV is preferred** and battery discharge can fill the remaining requested export.

```text
47512 = Xset = inverter-level grid sale/export target
```

Like mode 4, this mode is described without considering grid-side/site load. It is therefore not the same control primitive as mode 10.

### Mode 6 — Conserve / reserve

Purpose: reserve battery energy for off-grid use.

While on-grid, the battery is kept in a charging/reserve-oriented state and is not normally allowed to discharge for house self-use. PV is the normal charging source; battery discharge becomes relevant when the system is off-grid.

EnergyPilot treats mode 6 as a zero-setpoint mode and writes `0 W` to `47512`.

### Mode 7 — forced off-grid

Purpose: force off-grid operation. The battery then balances backup load against available PV.

```text
battery ~= backup load - PV
```

`47512` is not used by EnergyPilot in this mode and is forced to `0 W`.

This is not a normal grid-connected battery-control mode. Selecting it manually can materially change inverter operating topology and should only be done when the installation is designed and prepared for off-grid operation.

### Mode 8 — Battery Standby / Battery Hold

Purpose: battery neither charges nor discharges.

```text
battery power target ~= 0 W
```

EnergyPilot uses mode 8 extensively for:

- normal `P_batt` deadband;
- manual battery pause;
- EV charging hold;
- missing/unsafe grid-neutral feedback;
- the grid-neutral anti-flap dwell period.

EnergyPilot forces `47512 = 0 W`.

### Mode 9 — Buy Power / smart-meter grid-import target

Purpose: control **net grid import at the GoodWe smart-meter / point of common coupling**.

```text
47512 = Xset = desired grid import
```

The inverter may charge **or discharge** the battery to maintain that import target. If PV is excessive it may also limit PV; if load is high the battery may discharge to avoid exceeding the requested import.

This makes mode 9 fundamentally different from direct battery mode 11. Mode 9 owns battery direction as part of a grid target. EnergyPilot therefore does not currently use it for automatic EMHASS execution: `P_batt` remains the authoritative battery-direction request.

### Mode 10 — Sell Power / smart-meter grid-export target

Purpose: control **net export at the GoodWe smart-meter / point of common coupling**.

```text
47512 = Xset = desired grid export
```

PV is preferred and the battery may discharge when PV alone is insufficient. The inverter may limit PV to avoid exceeding the requested export target.

This is the correct GoodWe primitive when the intention is a net export target at the connection point. EnergyPilot currently exposes it through the manual EMS selector and the **Maximum export** quick action; it is not the normal EMHASS automatic-control primitive.

### Mode 11 — Charge Bat / direct battery charging power

Purpose: command the battery itself to charge at a requested power.

```text
47512 = Xset = battery charge-power target in W
```

PV has priority; if PV is insufficient, grid power may fill the remaining charging demand. The final achievable charge remains bounded by BMS/inverter limits.

This is EnergyPilot's normal automatic charging mode. During a planned near-zero-`P_grid` charge interval, EnergyPilot still uses mode 11 but treats the EMHASS `P_batt` value as a **maximum charge cap** and trims the actual `47512` value from smart-meter feedback.

### Mode 12 — Discharge Bat / direct battery discharging power

Purpose: command the battery itself to discharge at a requested power.

```text
47512 = Xset = battery discharge-power target in W
```

Battery discharge has high priority and is bounded by BMS/inverter discharge limits. GoodWe may limit PV under operating conditions where the requested battery discharge and PV together would exceed the applicable inverter/grid constraints.

This is EnergyPilot's normal automatic discharge mode.

### Similar-looking modes that must not be confused

| Pair | Difference |
|---|---|
| **2 vs 11** | Mode 2 controls a **grid-assist limit with PV priority**; mode 11 controls **battery charge power directly**. |
| **3 vs 12** | Mode 3 is **PV-priority supply with a battery-discharge allowance**; mode 12 is a **direct battery-discharge target**. |
| **4 vs 9** | Mode 4 is **inverter-level grid import scheduling**; mode 9 targets **net import at the smart meter/PCC** and may move the battery in either direction. |
| **5 vs 10** | Mode 5 is **inverter-level export scheduling**; mode 10 targets **net export at the smart meter/PCC**. |

These distinctions are why EnergyPilot keeps automatic strategy ownership explicit. Battery strategy maps EMHASS `P_batt` to modes **11/12/8**; Grid strategy maps signed `P_grid` to **9/10/1**. Hybrid first holds a neutral `P_batt` plan in mode **8**, then maps every non-neutral signed `P_grid` target to **9/10/1**. Disabling automatic ownership returns to **1**. Manual mode selections are never remapped.

### Manual mode selector

Home Assistant exposes all twelve values through the manual EMS mode select. Selecting any manual mode transfers ownership away from Automatic Control before the Modbus command is written.

The separate Manual power entity supplies `47512` for modes that require a non-zero setpoint. For modes `1`, `6`, `7` and `8`, EnergyPilot ignores that manual power and forces the setpoint to `0 W`.

### Evidence and naming source

The 12-mode behavior above follows the GoodWe **EMS Power Mode** table as represented by the maintained OpenEMS `EmsPowerMode` mapping and is cross-checked against maintained GoodWe integrations using registers `47511/47512`.

EnergyPilot's shorter UI names remain defined in `custom_components/gw_energypilot/const.py`; this document is the authoritative human-readable explanation of what those names mean electrically.

### Zero-power modes

Current zero-power handling includes modes:

```text
1, 6, 7, 8
```

When one of these modes is requested, the Modbus client forces the power setpoint to `0 W`.

## EMS write ordering

`GWModbusClient.async_set_mode()` currently writes:

1. EMS power register `47512`;
2. waits briefly;
3. EMS mode register `47511`.

Changing this order is a control-behaviour change and requires validation on real hardware.

The v0.18 `45356/45358` field-test writes use a separate client method and do not share or alter the EMS write sequence.

## Read blocks

The client reads contiguous holding-register blocks to reduce individual Modbus requests.

The canonical block definitions live together in `registers.py`:

```text
TELEMETRY_BLOCKS
OPTIONAL_TELEMETRY_BLOCKS
```

`client.py` imports those definitions and does not maintain a second copy.

The required runtime ranges are:

```text
35103 + 88 words
35212 + 10 words
35301 + 36 words
36003 + 55 words
37002 + 22 words
47509 + 4 words
```

The optional diagnostic/accounting ranges are:

```text
35206 + 6 words
36092 + 32 words
45356 + 1 word
45358 + 1 word
47000 + 1 word
47500 + 1 word
```

The client reconnects before each optional read because an unsupported optional range can cause the Modbus socket to close. One rejected Beta register therefore does not suppress later optional diagnostics or invalidate already successful required telemetry.

The first required blocks intentionally include every word of multi-register values:

```text
35189 is uint32 -> needs 35189 and 35190
35220 is uint32 -> needs 35220 and 35221
35335 is uint32 -> needs 35335 and 35336
```

The extended meter candidates are uint64 and therefore require four consecutive 16-bit words each.

Run:

```text
python scripts/validate_repo.py
```

The validator checks that every register definition is fully covered and that no read block exceeds the Modbus 125-register request limit.

## Register change policy

Any register change should include:

- exact address;
- read/write direction;
- holding/input register type where relevant;
- data width and signedness;
- byte/word order;
- scaling;
- unit;
- observed raw and decoded values;
- inverter model;
- firmware version if available;
- reason the previous interpretation was wrong or incomplete;
- whether the value is **Validated** or **Beta**.

Do not generalize behaviour from an older GoodWe generation to ETA-G20 without verification.
