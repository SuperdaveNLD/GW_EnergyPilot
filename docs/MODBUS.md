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
| 37007 | `battery_soc` | uint16 | 1 | Battery state of charge |
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

There is currently a known duplication:

- `registers.py` defines `TELEMETRY_BLOCKS`;
- `client.py` also defines `TELEMETRY_BLOCKS` and `OPTIONAL_TELEMETRY_BLOCKS`.

The ranges are not perfectly identical. Until this is deliberately refactored and tested, treat the blocks in `client.py` as the ranges actually used for runtime reads, while `registers.py` remains canonical for value definitions.

A future cleanup should:

1. define blocks in one place;
2. automatically verify that every register definition is covered;
3. ensure 32-bit/float values include both words;
4. preserve optional-register behaviour;
5. validate on the tested G20 inverter before release.

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
