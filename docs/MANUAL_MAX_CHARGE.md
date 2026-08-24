# Manual Max charge SOC guard

This document defines the runtime contract for the GW EnergyPilot **Max charge** quick action.

## Purpose

`Max charge` is a convenience action that takes manual controller ownership and requests GoodWe EMS mode `11` at the configured EnergyPilot maximum control power.

The action must not continue charging beyond the configured EMHASS maximum battery SOC.

## Configuration ownership

The maximum SOC setting remains owned by EMHASS:

```text
battery_maximum_state_of_charge
```

GW EnergyPilot does not invent or write a GoodWe maximum-SOC register for this feature. The configured EMHASS maximum is read through the existing `/get-config` path when the operator presses **Max charge**.

If the EMHASS maximum is missing, non-numeric or outside the valid `0..1` range, Max charge fails safe and does not start.

## Runtime behavior

When Max charge is pressed:

```text
read complete EMHASS config
-> decode battery_maximum_state_of_charge
-> require current finite GoodWe battery SOC
-> if SOC >= maximum: mode 8 Battery Hold
-> otherwise: mode 11 at configured maximum control power
```

While `manual_max_charge` remains active, the controller listens to normal GoodWe coordinator telemetry updates.

On the first telemetry update where:

```text
battery_soc >= captured maximum SOC
```

EnergyPilot writes:

```text
mode 8
setpoint 0 W
command manual_max_charge_soc_limit
```

The normal EMS write contract remains unchanged in `client.py`:

```text
47512 -> brief wait -> 47511
```

The stop is therefore software/telemetry driven. Its response time is bounded by the configured GoodWe telemetry refresh interval plus Modbus execution time. No claim is made that this creates a new inverter-side hardware SOC ceiling.

## Scope boundary

This guard applies only to the **Max charge** quick action.

The manual EMS test pad remains a direct operator interface. Selecting mode `11` there is not remapped or automatically limited by this convenience-action guard.

Automatic Control remains governed by its Battery/Grid/Hybrid strategy and EMHASS plan. Starting Automatic Control, disabling control, or issuing another manual command clears the active Max charge SOC guard.

## Diagnostics

The controller exposes the captured runtime ceiling as:

```text
manual_charge_limit_soc
```

The stopped state is identifiable through:

```text
controller command = manual_max_charge_soc_limit
expected EMS mode = 8
controller target = 0 W
```

## Failure behavior

Max charge does not start when either of these safety inputs cannot be validated:

- active EMHASS maximum SOC;
- current GoodWe battery SOC.

No GoodWe register definitions, entity IDs, unique IDs or persistent storage formats are changed by this feature.
