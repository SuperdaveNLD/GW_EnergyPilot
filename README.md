<p align="center">
  <img src="custom_components/gw_energypilot/brand/logo.png" alt="GW EnergyPilot" width="180">
</p>

# GW EnergyPilot

GW EnergyPilot is an unofficial Home Assistant integration for advanced EMS and battery control of GoodWe ETA hybrid inverters.

It provides direct Modbus TCP communication, native GoodWe ETA telemetry, manual EMS mode control, EMHASS `P_batt` mapping, battery hold logic, and optional EV charging coordination.

> This is an independent community project and is not affiliated with or endorsed by GoodWe.

## Current status

**Alpha - v0.04**

The project is being built from practical testing on a GoodWe ETA installation. Forced EMS modes can charge or discharge a battery at high power and can export energy to the grid. Verify your inverter, battery and grid limits before enabling automatic control.

### Version numbering

GW EnergyPilot uses simple incremental versions:

```text
v0.01
v0.02
v0.03
v0.04
...
```

## Important: EMHASS comes first

For the supported automatic-control workflow, **EMHASS must already be installed, configured, tested and publishing its Home Assistant sensors before GW EnergyPilot is installed/configured for automatic control**.

Do not start with an empty or unconfigured EMHASS environment.

The required order is:

1. Install Home Assistant and HACS.
2. Install EMHASS.
3. Configure EMHASS for your installation.
4. Make sure every Home Assistant source sensor referenced by EMHASS exists, is enabled, and contains a valid numeric value.
5. Configure the battery, inverter, PV/load and optimization parameters in EMHASS.
6. Run a successful EMHASS day-ahead optimization.
7. Publish the optimization result to Home Assistant.
8. Verify that the required EMHASS output sensors exist, are enabled, and update correctly.
9. Only now install/add GW EnergyPilot.
10. Connect EnergyPilot to the GoodWe ETA inverter.
11. Select the already-working EMHASS output entities in EnergyPilot.
12. Verify GoodWe telemetry and EMS state.
13. Only then enable EnergyPilot automatic control.

EMHASS documentation:

- https://emhass.readthedocs.io/
- https://github.com/davidusb-geek/emhass

### Minimum EMHASS readiness check

Before installing/configuring EnergyPilot automatic control, confirm at minimum:

```text
EMHASS optimization            successful
sensor.p_batt_forecast         exists, enabled and numeric
sensor.optim_status            exists if status validation is used
EMHASS source sensors          exist, enabled and numeric
publish-data                   working
```

A typical battery setup will publish:

```text
sensor.p_batt_forecast
sensor.soc_batt_forecast
sensor.p_load_forecast
sensor.p_pv_forecast
sensor.optim_status
```

The exact entity IDs can differ if you use custom EMHASS publish IDs.

### EMHASS source sensors

EMHASS must be configured with working Home Assistant source sensors appropriate for your installation, for example:

```text
Battery state of charge
Battery power
PV power
House/load power
```

The actual entity IDs are installation-specific. Do not point EMHASS at entities that are disabled, `unknown`, `unavailable`, permanently zero when they should not be, or use the wrong sign convention.

### Fresh Home Assistant bootstrap note

If you intentionally want to use **EnergyPilot's native GoodWe telemetry as the EMHASS source data on a completely fresh Home Assistant installation**, there is one bootstrap exception:

1. Add EnergyPilot with automatic control kept **OFF**.
2. Use its telemetry entities as EMHASS source sensors.
3. Configure EMHASS completely, run an optimization and publish the results.
4. Confirm the EMHASS output sensors are enabled and valid.
5. Return to EnergyPilot options and select those working EMHASS output entities.
6. Enable automatic control only after validation.

This exception is only needed when the required source sensors do not exist before EnergyPilot is added.

## Publishing EMHASS sensors to Home Assistant

Installing and starting EMHASS does not by itself guarantee that forecast sensors already exist in Home Assistant.

The normal sequence is:

```text
Valid source sensors
        ↓
Day-ahead optimization
        ↓
Successful optimization result
        ↓
Publish data
        ↓
Home Assistant forecast sensors
```

When EMHASS is configured with:

```json
"continual_publish": false
```

results are not continuously published automatically. Run `publish-data` manually or automate it.

Common EMHASS endpoints are:

```text
/action/dayahead-optim
/action/publish-data
```

A Home Assistant restart is normally not required just to make successfully published EMHASS sensors appear.

## Installation with HACS

Once the EMHASS prerequisite above is complete:

1. Open HACS.
2. Open **Custom repositories**.
3. Add `https://github.com/SuperdaveNLD/GW_EnergyPilot`.
4. Select category **Integration**.
5. Install **GW EnergyPilot**.
6. Restart Home Assistant.
7. Go to **Settings -> Devices & services -> Add integration**.
8. Search for **GW EnergyPilot**.

## GoodWe ETA connection

The setup flow asks for:

- GoodWe ETA inverter IP address.
- Modbus TCP port, normally `502`.
- Modbus Unit ID, commonly `247` on ETA installations.

### Use a fixed inverter IP address

The GoodWe ETA inverter should have a **static IP address or DHCP reservation**.

EnergyPilot connects directly to the inverter over Modbus TCP. If the inverter receives a different IP address after a router or network restart, EnergyPilot will no longer be able to communicate with it.

## Native GoodWe ETA telemetry

EnergyPilot reads GoodWe ETA telemetry directly over Modbus TCP. A separate Home Assistant Modbus YAML package is not required for these native entities.

Telemetry currently includes:

- PV1/PV2/PV3/PV4 power, voltage and current.
- Total PV power.
- Inverter L1/L2/L3 power, voltage, current and frequency.
- Total inverter power and AC active power.
- Smart-meter L1/L2/L3 power, voltage and current.
- Smart-meter total power and fast power values.
- Battery SOC, SOH, voltage, current and power.
- BMS charge/discharge current limits.
- Maximum/minimum cell voltage and temperature.
- Inverter air, module and radiator temperatures.
- BMS package temperature.
- Load and backup-load registers.
- Work mode, operation mode, grid mode, warning and error registers.
- EMS mode and EMS setpoint.

### Cleaner default entity set in v0.04

EnergyPilot still exposes the detailed register data, but lower-value or duplicate entities are disabled by default to keep the device page and recorder cleaner.

Examples of entities disabled by default include:

- PV voltage/current detail.
- Unused PV4 detail.
- Per-phase inverter voltage/current/frequency.
- Duplicate smart-meter fast phase power values.
- Per-phase load detail.
- Secondary inverter temperatures.
- Raw BMS/inverter diagnostic registers.

You can enable any of these entities manually from the EnergyPilot device/entity page when troubleshooting.

### Primary telemetry kept enabled

The default visible set focuses on useful operational data such as:

```text
PV total power
PV1 / PV2 / PV3 power
Total inverter power
AC active power
Total load power
Battery SOC / SOH
Battery power / voltage / current
BMS max charge / discharge current
BMS package temperature
Battery maximum cell temperature
Inverter radiator temperature
Meter total active power fast
Meter L1 / L2 / L3 active power
Meter L1 / L2 / L3 voltage and current
```

### Meter power note

On the first clean-HA validation system, the fast total meter value matched the sum of the three phase values closely. The slower `meter_total_active_power` register did not always match at the same instant, so the fast total is currently the preferred real-time grid reference.

### Load power note

The `total_load_power` register matched the sum of the three load phase registers closely during initial clean-HA testing. Still validate this value on your own inverter/firmware before using it as an EMHASS load source.

## Tested EMS model

EnergyPilot uses:

- Register `47511`: EMS mode.
- Register `47512`: EMS power setpoint.

| Mode | EnergyPilot name | Control target |
|---:|---|---|
| 1 | GoodWe Auto / AI | GoodWe internal control |
| 2 | PV-priority charging | PV-priority strategy |
| 3 | PV + battery supply | PV-priority strategy |
| 4 | Inverter import / AC charging | Inverter AC power |
| 5 | Inverter export power | Inverter AC power |
| 6 | Reserve / Conserve | Special mode |
| 7 | Off-grid | Special mode |
| 8 | Battery Hold | Battery power = 0 W |
| 9 | Grid import target | Point of common coupling |
| 10 | Grid export target | Point of common coupling |
| 11 | Battery charge power | Battery power |
| 12 | Battery discharge power | Battery power |

## EMHASS mapping

When automatic control is enabled and a valid `P_batt` entity is configured:

```text
P_batt < -deadband  -> mode 11 -> battery charge
inside deadband     -> mode 8  -> Battery Hold
P_batt > +deadband  -> mode 12 -> battery discharge
```

Disabling automatic control returns the inverter to:

```text
Mode 1 - GoodWe Auto / AI
Setpoint 0 W
```

The automatic-control switch intentionally starts **OFF after a Home Assistant restart or integration reload**.

## EnergyPilot control configuration

### Maximum inverter power

This is the maximum battery-control power EnergyPilot may request from the inverter.

The setup value is entered in kW. EnergyPilot converts it internally to watts.

Example:

```text
15.0 kW = 15000 W
```

Never configure this above the safe inverter or battery limits.

### Power deadband

The deadband prevents unnecessary switching between charging, Battery Hold and discharging when the EMHASS target is close to zero.

With a `300 W` deadband:

```text
P_batt < -300 W  -> charge battery
-300 W .. 300 W  -> Battery Hold
P_batt > 300 W   -> discharge battery
```

Recommended starting range:

```text
200-500 W
```

Recommended default:

```text
300 W
```

## EV coordination

EV coordination is optional. In the current alpha it uses a conservative strategy: while the configured EV is actively charging, EnergyPilot puts the battery in mode 8 (Battery Hold).

An EV is considered active if either:

- its mode entity equals `connected_charging`, or
- its charging power is above the configured EV threshold.

More advanced house-load compensation is planned for a later version.

## Branding

GW EnergyPilot ships its own local Home Assistant brand assets in:

```text
custom_components/gw_energypilot/brand/
```

The v0.04 branding uses the new square GW EnergyPilot energy monogram for both `icon.png` and `logo.png`.

## Safety

Do not enable automatic control until:

- the GoodWe ETA Modbus connection is verified;
- telemetry values have been checked for plausibility;
- EMHASS is fully configured and working;
- all required EMHASS source/output sensors are enabled and valid;
- EMHASS has completed a successful optimization;
- EMHASS publish-data is working;
- the selected `P_batt` entity is numeric and updates correctly;
- the configured maximum inverter power matches the real installation limits.

## Roadmap

- [x] HACS-ready custom integration structure.
- [x] Direct Modbus TCP connection.
- [x] Native GoodWe ETA telemetry.
- [x] EMS mode and setpoint sensors.
- [x] Manual EMS mode control.
- [x] EMHASS `P_batt` mapping to modes 8/11/12.
- [x] Automatic-control master switch with mode 1 fallback.
- [x] Basic EV charging coordination.
- [x] English setup flow and help text.
- [x] Cleaner default entity set.
- [x] Local integration branding.
- [ ] Setup-time EMHASS readiness validation.
- [ ] Advanced EV house-load compensation.
- [ ] Diagnostics download.
- [ ] Automated tests.
- [ ] Dashboard example.
- [ ] Stable v1.00 release.

## License

MIT
