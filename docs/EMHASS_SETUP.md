# EMHASS setup for GW EnergyPilot

EMHASS creates the battery plan. GW EnergyPilot supplies live inputs, runs optimization/publish, validates the result and maps the current `P_batt` target to the GoodWe ETA-G20.

The primary tested development inverter is **GoodWe GW15K-ETA-G20**.

## 1. Install EMHASS first

Install the EMHASS App/Add-on, enable **Start on boot** and **Watchdog**, and start it.

Confirm that the EMHASS web interface opens before configuring EnergyPilot.

EMHASS documentation commonly uses `http://localhost:5000`. For requests originating from Home Assistant Core, current HAOS networking can make `localhost` unsuitable for reaching another add-on container. EnergyPilot therefore defaults to the internal EMHASS add-on hostname:

```text
http://5b918bf2-emhass:5000
```

Change the URL in EnergyPilot options when your EMHASS installation uses another address.

## 2. Connect GW EnergyPilot

1. Add GW EnergyPilot under **Settings → Devices & services**.
2. Enter the fixed inverter IP address.
3. Use port `502` and Unit ID `247` unless your inverter uses different values.
4. Keep **Automatic Control OFF** during setup.
5. Verify battery SOC, battery power, PV power, GoodWe load and grid power.

If another Home Assistant integration with domain `goodwe` polls the same inverter, disable it when EnergyPilot replaces it. An unavailable/sleeping inverter can otherwise leave that separate integration in a long retry cycle during Home Assistant startup.

## 3. Map EMHASS inputs

Use the actual entity IDs shown by Home Assistant. Stable EnergyPilot unique keys are listed below; the generated entity ID can vary if Home Assistant has already assigned names.

| EMHASS parameter | EnergyPilot source |
|---|---|
| `sensor_power_photovoltaics` | PV total power (`pv_total_power`) |
| `sensor_power_load_no_var_loads` | GoodWe load register 35172 (`total_load_power`) |
| `sensor_power_battery` | Battery power (`battery_power`) |
| `sensor_battery_state_of_charge` | Battery SOC (`battery_soc`) |
| `var_model` | the same GoodWe load entity |
| `sensor_power_photovoltaics_forecast` | normally `sensor.p_pv_forecast` |

Battery sign convention:

```text
negative battery power = charging
positive battery power = discharging
```

EnergyPilot sends current battery SOC as runtime `soc_init` for every optimization.

### Why v0.13 uses register 35172 for load

On the tested GW15K-ETA-G20:

```text
GoodWe load 35172 ≈ Load L1 + Load L2 + Load L3
```

EnergyPilot also calculates:

```text
PV - grid + battery
```

That second value is retained as a **system power balance** diagnostic. It is not substituted into the EMHASS house-load model because it can also contain inverter conversion/auxiliary differences and depends on the electrical measurement points.

Registers `35138` and `35140` are inverter-side power diagnostics and should not be treated as inverter self-consumption.

## 4. Recommended EMHASS settings

Use the actual battery and inverter limits for your installation. For a configuration without deferrable loads, all per-load arrays should be empty.

Recommended publishing setting:

```json
"continual_publish": false
```

EnergyPilot publishes only after a successful optimization. This prevents a stale plan from being republished after a failed run.

Normal EMHASS output entity IDs are:

```text
sensor.p_batt_forecast
sensor.optim_status
```

They can be entered in EnergyPilot before EMHASS creates them.

## 5. EnergyPilot orchestrator settings

Recommended starting values:

```text
Enable built-in EMHASS orchestrator   ON
EMHASS URL                            http://5b918bf2-emhass:5000
Optimization interval                 60 min
Target SOC at end                     10%
Fallback house load                   700 W
Use runtime Nord Pool prices          ON when a supported source exists
Optimize when tomorrow prices arrive  ON
Nord Pool area                        blank or required area such as NL
Nord Pool currency                    EUR
Import price addition                 contract dependent
Export price deduction                contract dependent
```

## 6. Price sources

EnergyPilot tries runtime price sources in this order:

1. Home Assistant `nordpool.get_prices_for_date`;
2. a sensor with `raw_today` and `raw_tomorrow`;
3. EMHASS internal pricing when runtime pricing is disabled.

With runtime prices enabled EnergyPilot supplies:

```text
load_cost_forecast
prod_price_forecast
```

The configured import addition and export deduction are applied before the dictionaries are sent to EMHASS.

If runtime pricing is enabled but no compatible source exists, EnergyPilot stops with `error_prices` rather than silently optimizing with unintended prices.

## 7. First optimization

Wait until Home Assistant startup has finished and EnergyPilot telemetry is available. Then press **Optimize now**.

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
fresh numeric P_batt + expected optimization state
        ↓
ready
```

EnergyPilot intentionally does not create an EMHASS plan during Home Assistant startup.

## 8. Enable control

Confirm:

```text
P_batt forecast      numeric
Optimization status Optimal
Orchestrator         ready
Expected EMS mode    matches P_batt sign
```

Then enable **Automatic Control** or press **AUTO**.

AUTO performs a fresh optimization first and enables Automatic Control only after success.

## Scheduling

```text
Periodic optimization             every 60 minutes
Optimize now                      immediately
AUTO                              immediately
Tomorrow prices available         immediately
EV charging stops                 immediately when configured
SOC limit changes                 3 seconds after the final change
Home Assistant startup            no optimization
```

The SOC debounce prevents a slider movement such as 5% → 10% from starting optimizer jobs at every intermediate step.

## Minimum and maximum SOC

The dashboard controls write EMHASS parameters:

```text
battery_minimum_state_of_charge
battery_maximum_state_of_charge
```

EnergyPilot reads the complete EMHASS configuration through `/get-config`, modifies the selected field and writes the complete configuration back through `/set-config`.

For normal grid-connected cycling, EnergyPilot suggests approximately:

```text
minimum 5%
maximum 95%
```

This is an EnergyPilot operating recommendation, not a hardware override.

GoodWe/SEMS+ and the battery BMS have separate protection limits. Those limits remain authoritative. A GoodWe on-grid minimum SOC of 10% can therefore prevent further discharge at about 10% even when EMHASS requests a lower target.

Off-grid reserve should be configured separately. Current GoodWe ETA-G20 documentation recommends a much higher minimum reserve for off-grid operation.

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

## Grid energy foundation

v0.13 exposes the GoodWe smart-meter cumulative grid counters:

```text
36015 total export
36017 total import
```

They are Home Assistant `total_increasing` kWh sensors. Recorder can therefore calculate today, yesterday, month and year changes without repeatedly integrating every historical power sample.

The dashboard's Grid detail graph uses 5-minute Recorder power statistics only when the user opens the Grid card. Daily import/export values are cached for five minutes.

These counters are also the intended foundation for future Nord Pool cost/revenue sensors.

## Diagnostics

Use **Copy snapshot** when reporting an issue and include the inverter model/firmware.

Relevant values include:

- GoodWe EMS mode and setpoint;
- register 35172 and load-phase sum;
- system power balance;
- signed grid power;
- inverter registers 35138 and 35140;
- controller command/target;
- selected EMHASS output entities;
- EMHASS health/version and HTTP results;
- load and price point counts;
- other active `goodwe` config entries.

## Common failures

### `waiting_for_home_assistant`

Home Assistant startup is still in progress.

### `waiting_for_goodwe`

EnergyPilot has not completed a successful Modbus refresh. Verify inverter address, Modbus availability and whether another client is polling the same inverter.

### `error_prices`

Runtime pricing is enabled but no supported price source was found.

### `error_optimization`

EMHASS rejected or failed the optimization. Copy the Diagnostics snapshot and verify EMHASS inputs, forecast settings and constraints.

### `stale_output`

Optimization and publish returned successfully, but no fresh numeric `P_batt` became available.

## References

- EMHASS usage: https://emhass.readthedocs.io/en/latest/usage_guide.html
- EMHASS configuration: https://emhass.readthedocs.io/en/latest/config.html
- EMHASS runtime data: https://emhass.readthedocs.io/en/latest/passing_data.html
- Home Assistant developer documentation: https://developers.home-assistant.io/
