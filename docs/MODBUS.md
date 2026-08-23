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

## EMS modes currently used

| Mode | EnergyPilot meaning |
|---:|---|
| 1 | GoodWe Auto / AI |
| 8 | Battery Hold |
| 10 | Grid export target |
| 11 | Battery charge power |
| 12 | Battery discharge power |

The complete descriptive map currently lives in `const.py`.

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
