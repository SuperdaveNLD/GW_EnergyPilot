# GoodWe Modbus contract

This document records the Modbus assumptions currently used by GW EnergyPilot.

The canonical machine-readable definitions live in:

```text
custom_components/gw_energypilot/registers.py
```

Do not treat this document as permission to invent or extrapolate unverified registers.

## Tested hardware

Primary development and validation inverter:

- **GoodWe GW15K-ETA-G20**

The integration is built around the ETA-G20 generation. Other models must be individually validated before their register behaviour is considered confirmed.

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
| 35206 | `battery_charge_energy_total` | uint32 | 0.1 | Cumulative battery charge energy in kWh; optional pending broader ETA-G20 field validation |
| 35208 | `battery_charge_energy_today` | uint16 | 0.1 | Battery charge energy today in kWh; optional pending broader ETA-G20 field validation |
| 35209 | `battery_discharge_energy_total` | uint32 | 0.1 | Cumulative battery discharge energy in kWh; optional pending broader ETA-G20 field validation |
| 35211 | `battery_discharge_energy_today` | uint16 | 0.1 | Battery discharge energy today in kWh; optional pending broader ETA-G20 field validation |
| 37007 | `battery_soc` | uint16 | 1 | Battery state of charge |
| 37008 | `battery_soh` | uint16 | 1 | Battery state of health |
| 36008 | `meter_total_power_fast` | int16 | 1 | Primary instantaneous grid power |
| 36015 | `meter_total_energy_export` | float32 | 0.001 | Cumulative exported grid energy in kWh |
| 36017 | `meter_total_energy_import` | float32 | 0.001 | Cumulative imported grid energy in kWh |
| 47511 | `ems_mode` | uint16 | 1 | EMS mode control/state |
| 47512 | `ems_setpoint` | uint16 | 1 | EMS power setpoint |

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

GoodWe cumulative grid energy is decoded as IEEE-754 big-endian float32 values and scaled by `0.001` to kWh:

```text
36015 = exported energy total
36017 = imported energy total
```

Home Assistant exposes these as `total_increasing` energy sensors so Recorder can derive daily/monthly/yearly deltas efficiently.

## Battery energy accounting

GoodWe-compatible ET register documentation and the maintained Python GoodWe implementation identify the battery charge/discharge counters at `35206-35211` as integer energy values with `0.1 kWh` scaling.

EnergyPilot keeps this block optional while it is being validated on additional ETA-G20 firmware revisions. The values are available internally and in the support diagnostics, but are not yet promoted as normal dashboard telemetry or used to calculate a synthetic cycle count.

Current mapping:

```text
35206-35207  lifetime battery charge energy   uint32 / 10 -> kWh
35208        battery charge energy today      uint16 / 10 -> kWh
35209-35210  lifetime battery discharge energy uint32 / 10 -> kWh
35211        battery discharge energy today   uint16 / 10 -> kWh
```

Do not derive equivalent full cycles until usable battery capacity/model semantics are available from a validated source or explicit configuration. The BMS SOH value from register `37008` remains a separate measurement and must not be treated as a cycle counter.

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

## Read blocks

The client reads contiguous holding-register blocks to reduce individual Modbus requests.

The canonical block definitions now live together in `registers.py`:

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
47000 + 1 word
```

These remain optional so an unavailable diagnostic/accounting block does not fail the normal telemetry refresh.

The first three required blocks intentionally extend one word beyond the last visible 32-bit register address in the block:

```text
35189 is uint32 -> needs 35189 and 35190
35220 is uint32 -> needs 35220 and 35221
35335 is uint32 -> needs 35335 and 35336
```

That extra word is required for correct decoding and must not be trimmed as apparently unused space.

Run:

```text
python scripts/validate_repo.py
```

The validator checks that every register definition is fully covered, including both words of uint32/int32/float32 values, and that no read block exceeds the Modbus 125-register request limit.

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
- reason the previous interpretation was wrong or incomplete.

Do not generalize behaviour from an older GoodWe generation to ETA-G20 without verification.
