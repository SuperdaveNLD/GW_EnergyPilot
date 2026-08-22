# EMHASS setup for GW EnergyPilot

GW EnergyPilot does not replace the EMHASS optimization engine. EMHASS creates the battery power plan; EnergyPilot v0.10 now runs the optimization/publish cycle natively and translates the current `P_batt` target into GoodWe ETA EMS modes and setpoints.

## Recommended installation order

1. Install Home Assistant and HACS.
2. Install the EMHASS App/Add-on, enable **Start on boot** and **Watchdog**, and start EMHASS.
3. Install GW EnergyPilot through HACS.
4. Add GW EnergyPilot under **Settings -> Devices & services** and connect it to the GoodWe ETA inverter.
5. Keep **Automatic Control OFF** during initial setup.
6. Verify EnergyPilot telemetry, especially battery SOC, battery power, PV power and total load power.
7. Open the EMHASS configuration and map its GoodWe source sensors to the EnergyPilot entities listed below.
8. Restart/reload EMHASS after changing its configuration.
9. In GW EnergyPilot options configure the built-in EMHASS orchestrator.
10. Press **Optimize now** in the EnergyPilot dashboard.
11. Verify that `sensor.p_batt_forecast` is numeric and `sensor.optim_status` is `Optimal` when status validation is enabled.
12. Remove/disable the legacy `energypilot_emhass_orchestrator.yaml` package if it was used before v0.10.
13. Enable the built-in recurring orchestrator schedule.
14. Only after the optimization path is validated, enable EnergyPilot **Automatic Control**.

Optimization remains independent from Automatic Control:

```text
Automatic Control OFF
    -> optimization continues
    -> publishing continues
    -> GoodWe remains in GoodWe Auto / AI

Automatic Control ON
    -> optimization continues
    -> publishing continues
    -> EnergyPilot applies the current P_batt target
```

## Required EMHASS source mappings

The default EnergyPilot entity IDs are:

| EMHASS parameter | EnergyPilot source | Default entity ID |
|---|---|---|
| `sensor_power_photovoltaics` | Total GoodWe ETA PV power | `sensor.gw_energypilot_pv_total_power` |
| `sensor_power_load_no_var_loads` | GoodWe ETA total load power | `sensor.gw_energypilot_total_load_power` |
| `sensor_power_battery` | Signed battery power | `sensor.gw_energypilot_battery_power` |
| `sensor_battery_state_of_charge` | Battery SOC | `sensor.gw_energypilot_battery_state_of_charge` |
| `var_model` | Household/load model source | `sensor.gw_energypilot_total_load_power` |

Home Assistant can generate a different entity ID after a rename or collision. Always verify the actual IDs.

EnergyPilot uses the tested GoodWe battery-power convention:

```text
negative battery power = charging
positive battery power = discharging
```

### Load-power warning

GoodWe `total_load_power` can differ by firmware and operating mode. Validate the EnergyPilot load value against the phase sum or your power balance before using it as the EMHASS load source.

### Additional AC-coupled PV

EnergyPilot `PV total power` represents PV connected to the ETA. If the property also has a separate AC-coupled solar inverter, EMHASS should normally use a validated combined PV sensor instead of only the ETA PV value.

## Current SOC / soc_init

The built-in v0.10 orchestrator reads the current GoodWe battery SOC directly from the EnergyPilot coordinator immediately before every optimization and passes it to EMHASS as `soc_init`.

Example:

```text
GoodWe SOC = 88%
      ↓
EnergyPilot orchestrator
      ↓
soc_init = 0.88
      ↓
EMHASS day-ahead optimization
```

This prevents a stale fixed `soc_init` from producing a plan for the wrong battery state.

## Load forecast

EnergyPilot v0.10 builds a timestamped load forecast before calling EMHASS:

- current EnergyPilot total load is used as the live fallback;
- up to seven days of Home Assistant Recorder hourly statistics are read;
- the same local hour from available history is averaged;
- invalid or implausible load samples are ignored;
- a configurable fallback load is used only when current/history data cannot provide a plausible value;
- the generated forecast spans 48 hours.

This also prevents a fresh Home Assistant installation from failing because the EMHASS `naive` method has fewer historical samples than the optimization horizon.

## Nord Pool prices

EnergyPilot v0.10 can use Home Assistant's official Nord Pool integration through:

```text
nordpool.get_prices_for_date
```

When enabled, EnergyPilot requests today and, after roughly 13:00 local time, tomorrow. Nord Pool returns currency/MWh; EnergyPilot converts this to currency/kWh before sending timestamped dictionaries to EMHASS.

Two runtime adjustments are available:

```text
Import price addition
Export price deduction
```

The validated Tibber setup used an export deduction of:

```text
0.0248 EUR/kWh
```

If **Use official Nord Pool prices** is disabled, EnergyPilot does not send runtime price dictionaries and EMHASS uses its own configured price forecast methods such as `hp_hc_periods`, `constant`, `csv`, etc.

## Continual publishing

When using the native EnergyPilot orchestrator, recommended:

```json
"continual_publish": false,
"optimization_time_step": 15
```

EnergyPilot performs this transaction itself:

```text
build current SOC + load forecast + optional prices
        ↓
POST /action/dayahead-optim
        ↓
HTTP 2xx?
   no -> stop, do not publish
   yes
        ↓
POST /action/publish-data
        ↓
validate fresh numeric P_batt
```

This prevents a failed optimization from being followed by an unconditional publish of an older plan.

## EnergyPilot orchestrator options

Recommended starting values:

```text
Enable built-in EMHASS orchestrator   OFF while testing, ON after validation
EMHASS URL                            http://5b918bf2-emhass:5000
Optimization interval                 15 min
Target SOC at end                     10%
Fallback house load                   700 W
Use official Nord Pool prices         ON when the HA Nord Pool integration is used
Nord Pool area                        blank for first configured area, or e.g. NL
Nord Pool currency                    EUR
Import price addition                 contract dependent
Export price deduction                0.0248 EUR/kWh for the validated Tibber case
```

Existing v0.09 installations upgrade with the recurring schedule OFF. This is intentional so EnergyPilot cannot silently run next to an existing YAML scheduler.

## Optimize now

v0.10 creates a native Home Assistant button:

```text
GW EnergyPilot Optimize now
```

The same control is available directly in the built-in EnergyPilot dashboard on the EMHASS card.

The button performs one complete cycle even when the recurring schedule is disabled. This makes it the preferred validation method after changing EMHASS settings.

The button entity also exposes orchestrator diagnostics as attributes, including:

```text
orchestrator_status
last_success
last_error
last_reason
last_p_batt
soc_init
price_area
price_points
load_forecast_points
optimize_http_status
publish_http_status
automatic_schedule
```

## Legacy YAML migration

Before v0.10 a reference package could provide:

```text
script.energypilot_emhass_optimize_now
automation.energypilot_emhass_orchestrator
```

Do not leave that recurring scheduler active together with the native v0.10 scheduler.

EnergyPilot detects these legacy entities during setup. If found while the built-in schedule is enabled, the native scheduler reports:

```text
legacy_yaml_detected
```

and does not start its own recurring timer.

Recommended migration:

```text
1. Update EnergyPilot to v0.10
2. Verify the native Optimize now button exists
3. Keep Automatic Control OFF
4. Run Optimize now once
5. Verify P_batt + Optimal
6. Remove/disable the old orchestrator YAML package
7. Restart/reload Home Assistant
8. Enable the built-in orchestrator schedule
9. Run Optimize now again
10. Enable Automatic Control
```

## EnergyPilot output mapping

The normal defaults are pre-filled:

```text
EMHASS P_batt entity:            sensor.p_batt_forecast
Optimization status entity:      sensor.optim_status
Required optimization status:    Optimal
```

EnergyPilot translates the target as follows:

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

If `number_of_deferrable_loads` is `0`, keep every per-deferrable-load array empty:

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

Before turning Automatic Control ON, verify:

```text
EnergyPilot PV power             numeric and plausible
EnergyPilot load power           numeric and plausible
EnergyPilot battery SOC          numeric
EnergyPilot battery power        numeric
Optimize now                     successful
orchestrator status              ready
sensor.p_batt_forecast           numeric and fresh
sensor.optim_status              Optimal when configured
EnergyPilot expected EMS mode    matches P_batt sign
```

References:

- Home Assistant Nord Pool: https://www.home-assistant.io/integrations/nordpool/
- Nord Pool price action: https://www.home-assistant.io/actions/nordpool.get_prices_for_date/
- EMHASS configuration: https://emhass.readthedocs.io/en/latest/config.html
- EMHASS runtime data: https://emhass.readthedocs.io/en/latest/passing_data.html
- EMHASS forecasts: https://emhass.readthedocs.io/en/latest/forecasts.html
