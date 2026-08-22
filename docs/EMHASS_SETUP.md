# EMHASS setup for GW EnergyPilot

GW EnergyPilot does not replace EMHASS. EMHASS creates the battery power plan; EnergyPilot translates the current `P_batt` target into GoodWe ETA EMS modes and setpoints.

## Recommended installation order on a fresh Home Assistant system

1. Install Home Assistant and HACS.
2. Install the EMHASS add-on, enable **Start on boot** and **Watchdog**, and start EMHASS.
3. Install GW EnergyPilot through HACS.
4. Add GW EnergyPilot under **Settings -> Devices & services** and connect it to the GoodWe ETA inverter.
5. Keep **Automatic Control OFF** during initial setup.
6. Verify that the EnergyPilot telemetry entities exist and contain plausible values.
7. Open the EMHASS configuration and replace the old/generic source sensors with the EnergyPilot entities listed below.
8. Save the EMHASS configuration and restart the EMHASS add-on.
9. Run a successful day-ahead optimization.
10. Publish the optimization result to Home Assistant.
11. Verify that `sensor.p_batt_forecast` is numeric and that the optimization status is `Optimal` if status validation is used.
12. Open the GW EnergyPilot options and select the published EMHASS `P_batt` and optimization-status entities.
13. Enable EnergyPilot **Automatic Control**.

EMHASS optimization should continue to run even when EnergyPilot Automatic Control is OFF. The EnergyPilot switch only decides whether the published EMHASS command may be sent to the GoodWe inverter.

## Required EMHASS source mappings after EnergyPilot installation

The following are the default entity IDs created by a fresh EnergyPilot installation. Home Assistant can generate a different entity ID if an entity was renamed or already existed, so always verify the actual entity IDs under **Developer tools -> States**.

| EMHASS parameter | EnergyPilot source | Default entity ID |
|---|---|---|
| `sensor_power_photovoltaics` | Total GoodWe ETA PV power | `sensor.gw_energypilot_pv_total_power` |
| `sensor_power_load_no_var_loads` | GoodWe ETA total load power | `sensor.gw_energypilot_total_load_power` |
| `sensor_power_battery` | Signed battery power | `sensor.gw_energypilot_battery_power` |
| `sensor_battery_state_of_charge` | Battery SOC | `sensor.gw_energypilot_battery_state_of_charge` |
| `var_model` | Household/load model source | `sensor.gw_energypilot_total_load_power` |

EnergyPilot battery power uses the tested GoodWe convention:

```text
negative battery power = charging
positive battery power = discharging
```

Current EMHASS versions auto-detect battery-power sign for the optional battery-identification function. With `set_use_battery_identification: false`, `sensor_power_battery` and `sensor_battery_state_of_charge` are not used to set the optimization start SOC automatically; see the `soc_init` section below.

### Interpolation and zero replacement

Recommended mappings:

```json
"sensor_linear_interp": [
  "sensor.gw_energypilot_pv_total_power",
  "sensor.gw_energypilot_total_load_power"
],
"sensor_replace_zero": [
  "sensor.gw_energypilot_pv_total_power",
  "sensor.p_pv_forecast"
]
```

`set_zero_min: true` remains recommended for the load series. EMHASS treats negative load samples as invalid and can interpolate them when the load entity is also listed in `sensor_linear_interp`.

## Important: current battery SOC must still be passed as `soc_init`

The configured `sensor_battery_state_of_charge` is currently used by EMHASS battery self-identification. It does not automatically replace the day-ahead optimization `soc_init` when battery identification is disabled.

For each optimization run, pass the current EnergyPilot SOC as a fraction between 0 and 1.

Example Home Assistant template:

```jinja
{% set soc = states('sensor.gw_energypilot_battery_state_of_charge') | float(10) %}
{{ (soc / 100) | round(4) }}
```

Example runtime fragment:

```json
{
  "soc_init": 0.80,
  "soc_final": 0.10
}
```

For an automation or script, calculate `soc_init` immediately before every optimization so the optimizer always starts from the actual battery state.

## Continual publishing

Recommended:

```json
"continual_publish": true,
"optimization_time_step": 15
```

After a successful optimization, EMHASS saves the published entities and republishes the current forecast values every `optimization_time_step` minutes. A separate five-minute `publish-data` automation is therefore normally unnecessary when continual publishing is enabled.

Continual publishing does **not** run a new optimization. Keep a separate Home Assistant automation that launches the optimization at the desired interval, for example every 15 minutes.

## Recommended EnergyPilot EMHASS configuration

For the tested single-battery GoodWe ETA installation, the relevant source section should look like this after EnergyPilot is installed:

```json
{
  "continual_publish": true,
  "optimization_time_step": 15,
  "historic_days_to_retrieve": 7,
  "method_ts_round": "first",
  "sensor_power_photovoltaics": "sensor.gw_energypilot_pv_total_power",
  "sensor_power_photovoltaics_forecast": "sensor.p_pv_forecast",
  "sensor_power_load_no_var_loads": "sensor.gw_energypilot_total_load_power",
  "sensor_power_battery": [
    "sensor.gw_energypilot_battery_power"
  ],
  "sensor_battery_state_of_charge": [
    "sensor.gw_energypilot_battery_state_of_charge"
  ],
  "sensor_linear_interp": [
    "sensor.gw_energypilot_pv_total_power",
    "sensor.gw_energypilot_total_load_power"
  ],
  "sensor_replace_zero": [
    "sensor.gw_energypilot_pv_total_power",
    "sensor.p_pv_forecast"
  ],
  "var_model": "sensor.gw_energypilot_total_load_power",
  "load_negative": false,
  "set_zero_min": true
}
```

Some EMHASS releases/configuration interfaces serialize the two battery sensor fields as a one-item list while the current core documentation describes the single-battery value as one entity name. Keep the shape produced by your installed EMHASS add-on and replace only the entity ID.

## EnergyPilot output mapping

After EMHASS has successfully optimized and published data, configure EnergyPilot with:

```text
EMHASS P_batt entity:            sensor.p_batt_forecast
Optimization status entity:      sensor.optim_status
Required optimization status:    Optimal
```

EnergyPilot then translates the published target as follows:

```text
P_batt < -deadband  -> GoodWe mode 11 -> battery charge
inside deadband     -> GoodWe mode 8  -> Battery Hold
P_batt > +deadband  -> GoodWe mode 12 -> battery discharge
```

With the default `300 W` deadband:

```text
P_batt < -300 W       charge
-300 W .. +300 W      hold
P_batt > +300 W       discharge
```

## Deferrable loads

If `number_of_deferrable_loads` is `0`, keep every per-deferrable-load array empty. Do not leave the two default EMHASS example loads in the configuration.

Recommended:

```json
"number_of_deferrable_loads": 0,
"cost_forecast_per_deferrable_load": [],
"def_minimum_off_time": [],
"def_minimum_on_time": [],
"deferrable_load_groups": [],
"deferrable_load_max_cost": [],
"end_timesteps_of_each_deferrable_load": [],
"is_electric_load": [],
"minimum_power_of_deferrable_loads": [],
"nominal_power_of_deferrable_loads": [],
"operating_hours_of_each_deferrable_load": [],
"set_deferrable_load_single_constant": [],
"set_deferrable_max_startups": [],
"set_deferrable_startup_penalty": [],
"start_timesteps_of_each_deferrable_load": [],
"treat_deferrable_load_as_semi_cont": []
```

## Final validation

Before turning EnergyPilot Automatic Control ON, verify all of the following:

```text
EnergyPilot PV power             numeric and plausible
EnergyPilot load power           numeric and normally >= 0
EnergyPilot battery SOC          numeric
EnergyPilot battery power        numeric
EMHASS optimization              successful
sensor.p_batt_forecast           numeric and current
sensor.optim_status              Optimal (when configured)
EnergyPilot expected EMS mode    matches P_batt sign
```

Official EMHASS documentation:

- https://emhass.readthedocs.io/en/latest/config.html
- https://emhass.readthedocs.io/en/latest/passing_data.html
- https://emhass.readthedocs.io/en/latest/forecasts.html
