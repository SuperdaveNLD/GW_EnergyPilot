# GW EnergyPilot

GW EnergyPilot is an unofficial Home Assistant integration for advanced EMS and battery control of GoodWe ETA hybrid inverters.

It provides direct Modbus TCP communication, native GoodWe ETA telemetry, manual EMS mode control, optional EMHASS `P_batt` mapping, battery hold logic, and optional EV charging coordination.

> This is an independent community project and is not affiliated with or endorsed by GoodWe.

## Current status

**Alpha - v0.02**

The project is being built from practical testing on a GoodWe ETA installation. Use it only if you understand the impact of forced charge, discharge, export and off-grid modes.

### Version numbering

GW EnergyPilot uses simple incremental versions:

```text
v0.01
v0.02
v0.03
...
```

## Important: installation order

For automatic battery control, **EMHASS must be installed, configured and working before EnergyPilot automatic control is enabled**.

Recommended order for a new Home Assistant installation:

1. Install Home Assistant and HACS.
2. Install GW EnergyPilot from HACS.
3. Connect GW EnergyPilot to the GoodWe ETA inverter and verify Modbus communication.
4. Verify that the native EnergyPilot telemetry entities are updating correctly.
5. Install and configure EMHASS.
6. Configure EMHASS to use suitable Home Assistant source entities.
7. Run a successful EMHASS day-ahead optimization.
8. Publish the EMHASS result to Home Assistant.
9. Verify that the selected EMHASS output entities exist and contain valid values.
10. Configure EnergyPilot automatic control using those EMHASS entities.
11. Only then enable EnergyPilot automatic control.

EMHASS documentation:

- https://emhass.readthedocs.io/
- https://github.com/davidusb-geek/emhass

## GoodWe ETA connection

The setup flow asks for:

- GoodWe ETA inverter IP address.
- Modbus TCP port, normally `502`.
- Modbus Unit ID, commonly `247` on ETA installations.

### Use a fixed inverter IP address

The inverter should have a **static IP address or DHCP reservation**.

EnergyPilot connects directly to the inverter over Modbus TCP. If the inverter receives a different IP address after a network or router restart, EnergyPilot will no longer be able to communicate with it.

## Native GoodWe ETA telemetry

Starting with v0.02, EnergyPilot reads a broad set of GoodWe ETA telemetry directly from Modbus TCP. A separate Home Assistant Modbus YAML package is no longer required for these native entities.

Current telemetry includes:

- PV1, PV2, PV3 and PV4 voltage, current and power.
- Total PV power.
- Inverter L1/L2/L3 voltage, current, frequency and power.
- Total inverter power and AC active power.
- Smart-meter L1/L2/L3 power, voltage and current.
- Smart-meter total active power and fast power values.
- Grid/meter frequency.
- Battery SOC and SOH.
- Battery voltage, current and power.
- Battery mode and number of strings.
- BMS status, protocol, software and hardware version values.
- BMS maximum charge and discharge current.
- Maximum and minimum cell voltage.
- Inverter air, module and radiator temperature.
- BMS package temperature.
- Maximum and minimum battery cell temperature.
- Load and backup-load registers.
- Work mode, operation mode, grid mode, warning and error registers.
- EMS mode and EMS setpoint.

Some GoodWe registers are model- and firmware-dependent. Raw diagnostic values are exposed where a reliable human-readable mapping has not yet been confirmed.

### Load power warning

The GoodWe `total_load_power` register is exposed as telemetry, but EnergyPilot does **not** currently assume that it is always suitable as the EMHASS house-load source. Validate this value on your own installation before using it for optimization.

## EMHASS prerequisite

EnergyPilot does not install or configure EMHASS for you.

Before enabling automatic control, EMHASS must be able to:

- read its configured Home Assistant input sensors;
- complete an optimization successfully;
- publish its optimization result back to Home Assistant;
- provide a numeric battery-power target such as `sensor.p_batt_forecast`;
- optionally provide an optimization status entity such as `sensor.optim_status`.

If these conditions are not met, do not enable EnergyPilot automatic control.

## Publishing EMHASS sensors to Home Assistant

Installing and starting EMHASS does not automatically guarantee that forecast entities are already present in Home Assistant.

The normal sequence is:

```text
EMHASS input sensors available
        ↓
Day-ahead optimization
        ↓
Successful optimization result
        ↓
Publish data
        ↓
Home Assistant forecast entities
```

Typical published entities include:

```text
sensor.p_batt_forecast
sensor.p_load_forecast
sensor.p_pv_forecast
sensor.soc_batt_forecast
sensor.optim_status
```

The exact entities depend on the EMHASS version and configuration.

### No Home Assistant restart is normally required

When EMHASS publishes data successfully, the entities are created or updated directly in Home Assistant. A Home Assistant restart is normally not required just to make forecast sensors appear.

If EMHASS is configured with:

```json
"continual_publish": false
```

results are not continuously published automatically. Run the publish action explicitly or create an automation that publishes after optimization.

Common EMHASS endpoints are:

```text
/action/dayahead-optim
/action/publish-data
```

After publishing, verify the entities under **Settings -> Developer tools -> States**.

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

- Negative `P_batt` outside the deadband -> mode 11, charge battery.
- `P_batt` inside the deadband -> mode 8, Battery Hold.
- Positive `P_batt` outside the deadband -> mode 12, discharge battery.
- Disabling automatic control -> mode 1, GoodWe Auto / AI.

The automatic control switch intentionally starts **off after a Home Assistant restart**.

## EnergyPilot control configuration

Optional controller settings include:

- EMHASS `P_batt` entity.
- Optimization status entity and required state.
- Maximum battery charge/discharge power.
- Power deadband.
- EV mode and power entities.

### Maximum battery charge/discharge power

This is the maximum battery-control power EnergyPilot may request from the inverter. The value is entered in watts.

Examples:

```text
5000 W  = 5 kW
10000 W = 10 kW
15000 W = 15 kW
```

Configure this according to the supported inverter and battery limits.

### Power deadband

The deadband prevents unnecessary switching between charging, Battery Hold and discharging when the EMHASS target is close to zero.

For example, with a deadband of `300 W`:

```text
P_batt < -300 W  -> charge battery
-300 W to +300 W -> Battery Hold
P_batt > +300 W  -> discharge battery
```

A lower deadband reacts more quickly but can cause more mode changes. A higher deadband is calmer but ignores larger small-power corrections.

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

## Installation with HACS

Until the repository is included in the default HACS store:

1. Open HACS.
2. Open **Custom repositories**.
3. Add `https://github.com/SuperdaveNLD/GW_EnergyPilot`.
4. Select category **Integration**.
5. Install **GW EnergyPilot**.
6. Restart Home Assistant.
7. Go to **Settings -> Devices & services -> Add integration**.
8. Search for **GW EnergyPilot**.

## Safety

Forced EMS modes can charge or discharge a battery at high power and can export energy to the grid. Verify inverter limits, battery limits, grid connection limits and local regulations before enabling automatic control.

Do not enable automatic control until:

- the GoodWe ETA connection is verified;
- the telemetry values have been checked for plausibility;
- the configured EMHASS input sensors are valid;
- EMHASS successfully completes an optimization;
- the selected `P_batt` entity is numeric and updates correctly;
- the configured maximum power matches the actual inverter and battery limits.

## Roadmap

- [x] HACS-ready custom integration structure.
- [x] Direct Modbus TCP connection.
- [x] EMS mode and setpoint sensors.
- [x] Manual EMS mode control.
- [x] EMHASS `P_batt` mapping to modes 8/11/12.
- [x] Automatic-control master switch with mode 1 fallback.
- [x] Basic EV charging coordination.
- [x] Native GoodWe ETA PV telemetry.
- [x] Native inverter and smart-meter telemetry.
- [x] Native battery/BMS telemetry.
- [x] Native inverter, BMS and cell temperature sensors.
- [x] Document EMHASS prerequisite and publish workflow.
- [ ] Setup-time EMHASS readiness validation.
- [ ] Fully English setup flow and help text.
- [ ] Advanced EV house-load compensation.
- [ ] Diagnostics download.
- [ ] Automated tests.
- [ ] Dashboard example.
- [ ] Stable v1.00 release.

## License

MIT
