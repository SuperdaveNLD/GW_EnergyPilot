# GW EnergyPilot

GW EnergyPilot is an unofficial Home Assistant integration for advanced EMS and battery control of GoodWe ETA hybrid inverters.

It provides direct Modbus TCP control of the GoodWe EMS registers, optional EMHASS `P_batt` mapping, battery hold logic, manual EMS mode control, and optional EV charging coordination.

> This is an independent community project and is not affiliated with or endorsed by GoodWe.

## Current status

**Early alpha - v0.1.0**

The project is being built from practical testing on a GoodWe ETA installation. Use it only if you understand the impact of forced charge, discharge, export and off-grid modes.

## Important: installation order

For automatic battery control, **EMHASS must be installed, configured and working before EnergyPilot automatic control is enabled**.

Recommended order for a new Home Assistant installation:

1. Install Home Assistant and HACS.
2. Install GW EnergyPilot from HACS.
3. Connect GW EnergyPilot to the GoodWe ETA inverter and verify basic Modbus communication.
4. Make sure the source sensors required by EMHASS exist in Home Assistant.
5. Install and configure EMHASS.
6. Run a successful EMHASS day-ahead optimization.
7. Publish the EMHASS result to Home Assistant.
8. Verify that the EMHASS output entities exist and contain valid values.
9. Configure EnergyPilot automatic control using the EMHASS output entities.
10. Only then enable EnergyPilot automatic control.

EMHASS documentation:

- https://emhass.readthedocs.io/
- https://github.com/davidusb-geek/emhass

### EMHASS must already be working

EnergyPilot does not install or configure EMHASS for you.

Before enabling automatic control, EMHASS must be able to:

- read its configured Home Assistant input sensors;
- complete an optimization successfully;
- publish its optimization result back to Home Assistant;
- provide a numeric battery-power target such as `sensor.p_batt_forecast`;
- optionally provide an optimization status entity such as `sensor.optim_status`.

If these entities do not exist yet, do not enable EnergyPilot automatic control.

## EMHASS input sensors

EMHASS normally needs existing Home Assistant entities for the values configured in EMHASS, for example:

```text
sensor.battery_state_of_charge
sensor.power_battery
sensor.power_photovoltaics
sensor.power_load_no_var_loads
```

The exact names depend on your own EMHASS configuration.

### Important for a fresh Home Assistant installation

At this stage, **GW EnergyPilot v0.1.0 only provides the EMS control layer and does not yet expose all GoodWe ETA telemetry required as EMHASS input**.

On a completely fresh Home Assistant installation, you must therefore make sure the required EMHASS source sensors already exist before expecting a useful optimization.

Full GoodWe ETA telemetry is planned for a future EnergyPilot release so a fresh installation will no longer require a separate Modbus sensor package for the EMHASS source data.

## Publishing EMHASS sensors to Home Assistant

Installing and starting EMHASS does **not** automatically mean that entities such as `sensor.p_batt_forecast` are already available in Home Assistant.

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

When EMHASS publishes data successfully, the entities are created or updated in Home Assistant directly. A Home Assistant restart is normally not required just to make the published forecast sensors appear.

If you use:

```json
"continual_publish": false
```

EMHASS does not continuously publish the results by itself. You must explicitly run the publish action, or create an automation that publishes after optimization.

The commonly used EMHASS endpoints are:

```text
/action/dayahead-optim
/action/publish-data
```

After publishing, verify the entities under:

**Settings -> Developer tools -> States**

Before configuring EnergyPilot automatic control, confirm at minimum that your selected battery forecast entity contains a numeric value.

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

## EV coordination

EV coordination is optional. In v0.1.0 it uses a conservative safety strategy: while the configured EV is actively charging, EnergyPilot puts the battery in mode 8 (Battery Hold). More advanced house-load compensation is planned for a later release.

An EV is considered active if either:

- its mode entity equals `connected_charging`, or
- its charging power is above the configured EV threshold.

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

## GoodWe ETA connection

The setup flow asks for:

- GoodWe ETA inverter IP address.
- Modbus TCP port, normally `502`.
- Modbus Unit ID, commonly `247` on ETA installations.

### Use a fixed inverter IP address

The GoodWe ETA inverter should have a **static IP address or DHCP reservation**.

EnergyPilot connects directly to the inverter over Modbus TCP. If the inverter receives a different IP address after a router or network restart, EnergyPilot will no longer be able to communicate with it.

## EnergyPilot control configuration

Optional controller settings include:

- EMHASS `P_batt` entity.
- Optimization status entity and required state.
- Maximum battery charge/discharge power.
- Power deadband.
- EV mode and power entities.

### Maximum battery charge/discharge power

This is the maximum battery-control power EnergyPilot may request from the inverter.

The value is entered in watts.

Examples:

```text
5000 W  = 5 kW
10000 W = 10 kW
15000 W = 15 kW
```

Configure this value according to the supported inverter and battery limits. EnergyPilot should never be configured above the safe limits of the actual installation.

### Power deadband

The deadband prevents unnecessary switching between battery charging, Battery Hold and battery discharging when the EMHASS target is close to zero.

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

## Safety

Forced EMS modes can charge or discharge a battery at high power and can export energy to the grid. Verify inverter limits, battery limits, grid connection limits and local regulations before enabling automatic control.

Do not enable automatic control until:

- the GoodWe ETA connection is verified;
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
- [x] Document EMHASS prerequisite and publish workflow.
- [ ] Full GoodWe ETA telemetry entities for fresh installations.
- [ ] Setup-time EMHASS readiness validation.
- [ ] Fully English setup flow and help text.
- [ ] Advanced EV house-load compensation.
- [ ] Diagnostics download.
- [ ] Automated tests.
- [ ] Dashboard example.
- [ ] Stable v1.0 release.

## License

MIT
