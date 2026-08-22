<p align="center">
  <img src="custom_components/gw_energypilot/brand/logo.png" alt="GW EnergyPilot" width="180">
</p>

# GW EnergyPilot

GW EnergyPilot is an unofficial Home Assistant integration for advanced EMS and battery control of GoodWe ETA hybrid inverters.

It provides direct Modbus TCP communication, native GoodWe ETA telemetry, manual EMS mode control, EMHASS `P_batt` mapping, battery hold logic, optional EV charging coordination, and a built-in EnergyPilot dashboard.

> This is an independent community project and is not affiliated with or endorsed by GoodWe.

## Current status

**Alpha - v0.08**

The project is being built from practical testing on a GoodWe ETA installation. Forced EMS modes can charge or discharge a battery at high power and can export energy to the grid. Verify your inverter, battery and grid limits before enabling automatic control.

### Version numbering

GW EnergyPilot uses simple incremental versions:

```text
v0.01
v0.02
v0.03
v0.04
v0.05
v0.06
v0.07
v0.08
...
```

# Installation order: EMHASS + GW EnergyPilot

A fresh installation has a bootstrap dependency: EMHASS must exist before EnergyPilot automatic control is used, but the preferred EMHASS source sensors are created by EnergyPilot. Therefore **do not try to fully configure EMHASS with final GoodWe sensor IDs before EnergyPilot has been installed**.

Use this order:

1. Install Home Assistant and HACS.
2. Install the EMHASS App/Add-on and make sure the EMHASS web interface starts correctly.
3. Configure the general EMHASS battery, inverter, PV model, optimization and price settings. EMHASS does not need to be controlling the inverter yet.
4. Install GW EnergyPilot through HACS.
5. Add the GW EnergyPilot integration and connect it to the GoodWe ETA over Modbus TCP. Keep **Automatic Control OFF** during this bootstrap stage.
6. Verify that EnergyPilot publishes valid GoodWe telemetry, especially battery SOC, battery power, PV power and load/grid data.
7. Return to the EMHASS configuration and replace the temporary/old GoodWe source entities with the EnergyPilot entities.
8. Restart/reload EMHASS if required after changing its configuration.
9. Run a successful EMHASS day-ahead optimization.
10. Publish the optimization result to Home Assistant.
11. Verify that `sensor.p_batt_forecast` exists, is numeric and updates, and verify `sensor.optim_status` when status validation is used.
12. Open GW EnergyPilot options and select the working EMHASS `P_batt` and optimization-status entities.
13. Only then enable **Automatic Control**.

The final data path should be:

```text
GoodWe ETA
    │
    │ Modbus TCP
    ▼
GW EnergyPilot
    │
    ├── Battery SOC / power
    ├── PV power
    ├── Grid / load telemetry
    │
    ▼
EMHASS
    │
    │ sensor.p_batt_forecast
    ▼
GW EnergyPilot controller
    │
    ▼
GoodWe EMS modes 8 / 11 / 12
```

EMHASS documentation:

- https://emhass.readthedocs.io/
- https://github.com/davidusb-geek/emhass

## Recommended EMHASS source mapping

The exact entity IDs can receive a suffix if Home Assistant already contains entities with the same name. Verify the actual IDs under **Settings -> Devices & services -> Entities** or **Developer tools -> States**.

A normal fresh EnergyPilot installation should map EMHASS approximately as follows:

| EMHASS setting | GW EnergyPilot source |
|---|---|
| `sensor_battery_state_of_charge` | `sensor.gw_energypilot_battery_state_of_charge` |
| `sensor_power_battery` | `sensor.gw_energypilot_battery_power` |
| `sensor_power_photovoltaics` | `sensor.gw_energypilot_pv_total_power` |
| `sensor_power_load_no_var_loads` | `sensor.gw_energypilot_total_load_power` after validating that register on your firmware |
| `sensor_power_photovoltaics_forecast` | usually `sensor.p_pv_forecast` after EMHASS publish |

EnergyPilot uses the same battery-power sign convention expected by the current controller mapping:

```text
negative battery power = charging
positive battery power = discharging
```

### Load-power warning

GoodWe `total_load_power` behavior can differ by firmware and operating mode. Validate the value against the phase measurements/power balance before using it as the EMHASS load source. If it is negative or implausible on your inverter, use a validated calculated load sensor instead.

### Additional AC-coupled PV

`PV total power` from EnergyPilot represents the PV connected to the ETA. If the property also has a separate AC-coupled solar inverter, EMHASS should normally use a combined PV sensor containing both sources instead of only the ETA PV value.

## Minimum EMHASS readiness check

Before enabling EnergyPilot automatic control, confirm at minimum:

```text
EMHASS App                    running
EnergyPilot telemetry         valid
EMHASS source sensors         valid and numeric
EMHASS optimization           successful
sensor.p_batt_forecast        exists and numeric
sensor.optim_status           Optimal (when used)
publish-data                  working
EnergyPilot P_batt option     points to the correct entity
```

A typical battery setup will publish:

```text
sensor.p_batt_forecast
sensor.soc_batt_forecast
sensor.p_load_forecast
sensor.p_pv_forecast
sensor.optim_status
```

The exact output entity IDs can differ if custom EMHASS publish IDs are used.

## Keep optimization separate from inverter control

EMHASS optimization/publishing should continue even when EnergyPilot **Automatic Control is OFF**. The Automatic Control switch determines whether EnergyPilot may physically command the GoodWe inverter; it should not stop the optimizer from producing a fresh plan.

Recommended behavior:

```text
EnergyPilot Automatic OFF
    ├── EMHASS optimization continues
    ├── EMHASS publishing continues
    └── GoodWe remains under GoodWe Auto / AI

EnergyPilot Automatic ON
    ├── EMHASS optimization continues
    ├── EMHASS publishing continues
    └── EnergyPilot applies the current P_batt target
```

Do not gate your recurring EMHASS optimization job behind an old EnergyPilot/GoodWe master `input_boolean` when migrating from a YAML-based setup.

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

For current EMHASS configurations, enabling:

```json
"continual_publish": true
```

allows EMHASS to keep publishing the current optimization result according to its configured optimization time step. It is still useful to perform one publish immediately after a new optimization so the Home Assistant output entities are available without waiting for the next continual-publish interval.

Common EMHASS endpoints are:

```text
/action/dayahead-optim
/action/publish-data
```

A Home Assistant restart is normally not required just to make successfully published EMHASS sensors appear.

## Migrating from older GoodWe YAML packages

EnergyPilot replaces the direct GoodWe Modbus control layer. Do not leave old automations/scripts actively writing the same EMS registers while EnergyPilot automatic control is enabled.

Typical migration order:

1. Install EnergyPilot and verify its telemetry.
2. Change EMHASS source sensor IDs to EnergyPilot entities.
3. Verify EMHASS optimization and published output entities.
4. Configure the EnergyPilot EMHASS output entities.
5. Disable/remove old GoodWe EMS execution automations and direct Modbus write scripts.
6. Only after no remaining templates/automations depend on the old GoodWe Modbus entities, remove the old Home Assistant `modbus:` sensor package.

Legacy files that only provided direct EMS mode/setpoint writes or duplicate GoodWe telemetry can normally be removed after migration. Files that calculate long-term energy counters, combine additional AC PV, or provide unrelated EV logic may still be useful until those functions have been migrated separately.

## Installation with HACS

1. Open HACS.
2. Open **Custom repositories**.
3. Add `https://github.com/SuperdaveNLD/GW_EnergyPilot`.
4. Select category **Integration**.
5. Install **GW EnergyPilot**.
6. Restart Home Assistant.
7. Go to **Settings -> Devices & services -> Add integration**.
8. Search for **GW EnergyPilot**.
9. Connect the GoodWe ETA but keep Automatic Control OFF until the EMHASS bootstrap steps above are complete.

## GoodWe ETA connection

The setup flow asks for:

- GoodWe ETA inverter IP address.
- Modbus TCP port, normally `502`.
- Modbus Unit ID, commonly `247` on ETA installations.

### Use a fixed inverter IP address

The GoodWe ETA inverter should have a **static IP address or DHCP reservation**.

EnergyPilot connects directly to the inverter over Modbus TCP. If the inverter receives a different IP address after a router or network restart, EnergyPilot will no longer be able to communicate with it.

## Built-in EnergyPilot dashboard

Starting with v0.05, the integration registers its own Home Assistant sidebar panel named **EnergyPilot**. No Lovelace YAML, manual JavaScript resource, or separate HACS frontend package is required.

The panel is served locally from the integration and uses Home Assistant's live `hass` object. It discovers EnergyPilot entities from the Home Assistant entity registry, so renamed entity IDs remain supported.

The dashboard includes:

- live PV total and PV1/PV2/PV3 string power;
- whole-home load;
- battery SOC, power, voltage, current and temperature;
- grid import/export and phase measurements;
- inverter power and temperatures;
- EMS mode, setpoint, EnergyPilot target and current command;
- EMHASS `P_batt`, optimization status and common published forecast sensors;
- a guarded Automatic Control toggle;
- responsive desktop, tablet and mobile layouts;
- a compact animated PV / house / grid / battery flow widget;
- a dashboard layout menu;
- per-card visibility toggles;
- drag-and-drop card ordering;
- persistent layout preferences stored in the browser;
- a flow-animation toggle and layout reset button.

The dashboard uses the tested GoodWe smart-meter sign convention used by EnergyPilot: positive meter power is shown as export and negative meter power as import.

When enabling Automatic Control from the dashboard, EnergyPilot shows a confirmation warning because automatic operation may command high battery power.

### Dashboard layout controls

Use the layout button in the dashboard header to open the mini menu.

Enable **Edit layout** to drag cards into a different order. The card order, visibility settings and animation preference are stored in browser local storage, so each browser/device can keep its own dashboard arrangement.

Use **Reset dashboard layout** to return to the default card order and visibility.

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

### Cleaner default entity set

EnergyPilot still exposes detailed register data, but lower-value or duplicate entities are disabled by default to keep the device page and recorder cleaner.

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

GoodWe `total_load_power` has proven firmware/mode dependent during testing. Validate it before using it as an optimizer source. The EnergyPilot dashboard can fall back to a power-balance calculation for presentation when the raw load value is clearly invalid; EMHASS itself should be pointed at a source you have validated for your installation.

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

### Automatic Control state after restart/reload

Starting with v0.08, the Automatic Control switch restores its previous Home Assistant state:

```text
Was ON before restart/reload  -> restore ON
Was OFF before restart/reload -> remain OFF
First installation            -> OFF
```

Restoring the switch to ON does not bypass EnergyPilot's input validation. If the configured `P_batt` value is unavailable/non-numeric, or a configured optimization-status entity is not ready, the controller waits instead of issuing a new EMS command.

Turning Automatic Control OFF always hands the inverter back to GoodWe Auto / AI mode 1 with a 0 W setpoint.

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

The built-in dashboard additionally uses an inline high-contrast SVG mark so the EnergyPilot logo remains visible on the dark dashboard background.

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
- [x] Restore Automatic Control state after reload/restart.
- [x] Basic EV charging coordination.
- [x] English setup flow and help text.
- [x] Cleaner default entity set.
- [x] Local integration branding.
- [x] Built-in responsive JavaScript dashboard.
- [x] Compact animated energy-flow overview.
- [x] Drag-and-drop dashboard layout and visibility menu.
- [ ] Setup-time EMHASS readiness validation.
- [ ] Advanced EV house-load compensation.
- [ ] Forecast timeline / price graph in dashboard.
- [ ] Diagnostics download.
- [ ] Automated tests.
- [ ] Stable v1.00 release.

## License

MIT
