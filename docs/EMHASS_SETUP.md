# EMHASS setup for GW EnergyPilot

EMHASS creates the battery plan. GW EnergyPilot supplies live inputs, runs optimization/publish, validates the result and maps the current `P_batt` target to the GoodWe ETA.

## 1. Install EMHASS first

Install the EMHASS App/Add-on, enable **Start on boot** and **Watchdog**, and start it.

Confirm that the EMHASS web interface opens before installing GW EnergyPilot.

## 2. Install and connect GW EnergyPilot

1. Install GW EnergyPilot through HACS.
2. Restart Home Assistant.
3. Add **GW EnergyPilot** under **Settings → Devices & services**.
4. Enter the fixed inverter IP address, port `502` and Unit ID `247` unless your installation uses different values.
5. Keep **Automatic Control OFF** during setup.
6. Verify battery SOC, battery power, PV power and grid power.

Disable the separate Home Assistant `goodwe` integration when it polls the same inverter. Concurrent polling can occupy the GoodWe connection and delay startup or telemetry.

## 3. Map EMHASS inputs to EnergyPilot

Use the actual entity IDs created on your Home Assistant instance.

| EMHASS parameter | Suggested EnergyPilot source |
|---|---|
| `sensor_power_photovoltaics` | `sensor.gw_energypilot_pv_total_power` |
| `sensor_power_load_no_var_loads` | `sensor.gw_energypilot_total_load_power` or another validated whole-home sensor |
| `sensor_power_battery` | `sensor.gw_energypilot_battery_power` |
| `sensor_battery_state_of_charge` | `sensor.gw_energypilot_battery_state_of_charge` |
| `var_model` | the same validated whole-home load sensor |
| `sensor_power_photovoltaics_forecast` | normally `sensor.p_pv_forecast` |

Battery sign convention:

```text
negative battery power = charging
positive battery power = discharging
```

EnergyPilot sends the current battery SOC as runtime `soc_init` for every optimization.

### House-load source

GoodWe register `35172` is available as a raw diagnostic sensor. EnergyPilot also calculates whole-home demand as:

```text
PV - grid + battery
```

This calculated value is used by the native orchestrator when PV, grid and battery values are valid. It avoids depending solely on register `35172` where AC-coupled PV or firmware behaviour makes that register incomplete.

## 4. Recommended EMHASS settings

Use the battery and inverter limits that match the actual hardware. For an installation without deferrable loads, all per-load arrays should be empty.

Recommended publishing setting:

```json
"continual_publish": false
```

EnergyPilot publishes only after a successful optimization, preventing an old plan from being published after a failed run.

Normal output entities:

```text
sensor.p_batt_forecast
sensor.optim_status
```

These IDs are prefilled in EnergyPilot as text and can be saved before EMHASS creates the entities.

## 5. Configure the EnergyPilot orchestrator

Recommended starting values:

```text
Enable built-in EMHASS orchestrator   ON
EMHASS URL                            http://5b918bf2-emhass:5000
Optimization interval                 60 min
Target SOC at end                     10%
Fallback house load                   700 W
Use runtime Nord Pool prices          ON when a supported source exists
Optimize when tomorrow prices arrive  ON
Nord Pool area                        blank or the required area, e.g. NL
Nord Pool currency                    EUR
Import price addition                 contract dependent
Export price deduction                contract dependent
```

## 6. Price sources

EnergyPilot tries price sources in this order:

1. Home Assistant action `nordpool.get_prices_for_date`;
2. a sensor with `raw_today` and `raw_tomorrow` attributes;
3. EMHASS's internal price configuration when runtime prices are disabled.

With runtime prices enabled, EnergyPilot supplies:

```text
load_cost_forecast
prod_price_forecast
```

The configured import addition and export deduction are applied before the dictionaries are sent to EMHASS.

If runtime pricing is enabled but no compatible source exists, EnergyPilot stops with a clear `error_prices` status instead of running EMHASS with unintended fallback prices.

## 7. Run the first optimization

Wait until Home Assistant startup has finished and EnergyPilot telemetry is available.

Then press **Optimize now** in the EnergyPilot dashboard.

Successful flow:

```text
EMHASS health check
        ↓
current SOC + 24-hour load forecast + optional prices
        ↓
POST /action/dayahead-optim
        ↓
HTTP 2xx
        ↓
POST /action/publish-data
        ↓
fresh numeric P_batt + expected optimization status
        ↓
ready
```

The orchestrator intentionally does not run during Home Assistant startup.

## 8. Enable control

After the first successful run, confirm:

```text
sensor.p_batt_forecast   numeric
sensor.optim_status      Optimal
Orchestrator             ready
Expected EMS mode        matches the P_batt sign
```

Then enable **Automatic Control** or press **AUTO**.

The AUTO button performs a fresh optimization first and enables Automatic Control only after success.

## Scheduling and triggers

```text
Periodic optimization             every 60 minutes
Optimize now                      immediately
AUTO button                       immediately
Tomorrow prices become available immediately
EV charging stops                 immediately, when configured
Minimum/maximum SOC changes       immediately
Home Assistant startup            no optimization
```

## Minimum and maximum SOC

The dashboard sliders write:

```text
battery_minimum_state_of_charge
battery_maximum_state_of_charge
```

EnergyPilot reads the complete configuration with `/get-config`, changes only the selected field and writes the complete configuration through `/set-config`. A fresh optimization is requested afterwards.

## Output mapping

```text
P_batt < -deadband  → GoodWe mode 11 → battery charge
inside deadband     → GoodWe mode 8  → Battery Hold
P_batt > +deadband  → GoodWe mode 12 → battery discharge
```

Default deadband:

```text
300 W
```

## Diagnostics

Use **Copy snapshot** on the Diagnostics card. The snapshot includes:

- GoodWe EMS mode and setpoint;
- raw and calculated house power;
- controller command, target and expected mode;
- selected EMHASS entities and states;
- EMHASS health/version and HTTP results;
- load and price point counts;
- detected price source;
- other active `goodwe` config entries.

## Common failures

### `waiting_for_home_assistant`

Home Assistant startup is still in progress. Wait until startup is complete.

### `waiting_for_goodwe`

EnergyPilot has not completed a successful Modbus refresh. Verify the inverter address and disable another integration polling the same GoodWe.

### `error_prices`

Runtime pricing is enabled but no supported price source was found. Configure Nord Pool or disable runtime pricing.

### `error_optimization`

The EMHASS request failed. Copy the Diagnostics snapshot and inspect the concise error message. Verify EMHASS inputs, forecast settings and battery/inverter limits.

### `stale_output`

Optimization and publish returned successfully, but no fresh numeric `P_batt` entity became available.

## References

- EMHASS configuration: https://emhass.readthedocs.io/en/latest/config.html
- EMHASS runtime data: https://emhass.readthedocs.io/en/latest/passing_data.html
- Home Assistant Nord Pool: https://www.home-assistant.io/integrations/nordpool/
