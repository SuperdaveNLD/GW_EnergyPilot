# EMHASS setup for GW EnergyPilot

EMHASS creates the battery/grid plan. GW EnergyPilot supplies live inputs, runs optimization/publish, validates the result and executes the current EMHASS targets on the GoodWe ETA-G20.

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

### Why v0.13+ uses register 35172 for load

On the tested GW15K-ETA-G20 without the external-AC-PV edge case:

```text
GoodWe load 35172 ≈ Load L1 + Load L2 + Load L3
```

EnergyPilot also calculates:

```text
PV - grid + battery
```

That second value is retained as a **system power balance** diagnostic. It is not substituted into the EMHASS house-load model because it can also contain inverter conversion/auxiliary differences and depends on the electrical measurement points.

Registers `35138` and `35140` are inverter-side power diagnostics and should not be treated as inverter self-consumption.

### External AC-coupled PV note

Field testing has confirmed an important edge case: when a separate PV inverter is AC-coupled elsewhere in the installation, the GoodWe's own PV inputs can correctly report `0 W` while the GoodWe smart meter still sees the external generation at the point of connection. In that layout register `35172` can also become negative while the external inverter exports.

The current load-forecast builder rejects negative/implausible `35172` values and can therefore fall back to the configured fallback load (for example 700 W). Correct reconstruction of gross house load with external AC-coupled PV is a **separate forecast/input problem**. v0.18 does not silently redefine `35172`; it addresses the independent runtime problem where an optimistic PV forecast could make a fixed mode-11 charge request import the missing power from the grid.

## 4. Recommended EMHASS settings

Use the actual battery and inverter limits for your installation. For a configuration without deferrable loads, all per-load arrays should be empty.

Recommended publishing setting:

```json
"continual_publish": false
```

EnergyPilot publishes only after a successful optimization. This prevents a stale plan from being republished after a failed run.

Normal EMHASS output entity IDs used by v0.18 are:

```text
sensor.p_batt_forecast
sensor.p_grid_forecast
sensor.optim_status
```

They can be entered in EnergyPilot before EMHASS creates them.

EMHASS output conventions relevant to the controller are:

```text
P_batt < 0  = charge battery
P_batt > 0  = discharge battery
P_grid > 0  = planned grid import
P_grid < 0  = planned grid export
```

Note that the GoodWe smart-meter telemetry uses the opposite grid sign convention in EnergyPilot:

```text
GoodWe meter 36008 < 0 = actual import
GoodWe meter 36008 > 0 = actual export
```

## 5. EnergyPilot orchestrator settings

Recommended starting values:

```text
Enable built-in EMHASS orchestrator   ON
EMHASS URL                            http://5b918bf2-emhass:5000
P_batt output entity                  sensor.p_batt_forecast
P_grid output entity                  sensor.p_grid_forecast
Optimization interval                 60 min
Target SOC at end                     10%
Fallback house load                   700 W
Use runtime Nord Pool prices          ON when a supported source exists
Optimize when tomorrow prices arrive  ON
Nord Pool area                        blank or required area such as NL
Nord Pool currency                    EUR
Import price addition                 contract dependent
Export price deduction                 contract dependent
```

From v0.17, these EnergyPilot-owned integration settings are also available under the dashboard gear → **EMHASS** page. v0.18 adds the configurable `P_grid` output entity there. The dedicated settings page writes the same Home Assistant config entry as the normal integration options flow; it does not replace EMHASS `config.json`.

## 6. EMHASS optimization strategy

EMHASS supports these `costfun` objectives:

```text
profit
cost
self-consumption
```

v0.16+ represents this correctly as **one persistent setting** rather than three independent modes. Home Assistant exposes a stateful **EMHASS optimization strategy** select with these user-facing choices:

```text
Profit
Cost
Self-consumption
```

The EnergyPilot dashboard shows the same three choices as quick-selection buttons, but the active strategy is visibly highlighted and labelled `ACTIVE`. The state comes from the select entity, which reads the actual `costfun` from EMHASS `/get-config`.

The select refreshes at startup, after EnergyPilot writes EMHASS configuration and periodically so a `costfun` change made directly in the EMHASS UI also appears in Home Assistant.

Changing the strategy performs this sequence:

```text
GET /get-config
      ↓
change only costfun
      ↓
POST /set-config with the complete configuration
      ↓
update the Home Assistant strategy state
      ↓
run a fresh day-ahead optimization
      ↓
publish fresh EMHASS output
```

EnergyPilot deliberately reads and writes the complete configuration so unrelated EMHASS settings are preserved.

If the config write succeeds but the fresh optimization fails, the selected `costfun` remains saved. EnergyPilot reports this explicitly instead of presenting the entire selection as if it failed.

The v0.15 button unique IDs remain available for backwards compatibility with existing automations. They are now configuration actions and their names explicitly say **Set EMHASS...**. New dashboard/UI logic should use the stateful select.

Changing `costfun` changes **what EMHASS optimizes**. The controller then uses both the published battery and grid intent where needed; the cost function itself does not directly write a GoodWe mode.

## 7. v0.18 grid-neutral charge execution

The field case that motivated v0.18 looked like this:

```text
EMHASS forecast:
PV       ≈ 5.1 kW
Load     ≈ 0.7 kW
P_batt   ≈ -4.42 kW
P_grid   ≈ 0 W

Actual installation:
external AC-coupled PV much lower
GoodWe PV inputs = 0 W
mode 11 setpoint = 4.42 kW
actual grid import ≈ 3.1 kW
```

EMHASS did **not** plan that grid import: its `P_grid` target was about 0 W. The problem was the execution primitive: fixed GoodWe mode 11 kept charging at the forecast-derived `P_batt` target and sourced any missing power from the grid.

v0.18 therefore applies a separate execution rule only when:

```text
P_batt < -deadband
abs(P_grid) <= deadband
optimization status is ready
EV hold is not active
```

In that state:

```text
abs(P_batt) = maximum permitted charge power
GoodWe meter 36008 = live feedback
GoodWe mode 11 = charge actuator while charge > 0
GoodWe mode 8 = hold when local surplus is insufficient
```

The feedback correction runs every **30 seconds** using the latest coordinator telemetry; it does not add a second 30-second Modbus poll. Normal GoodWe telemetry can remain at the recommended 10-second polling interval.

For an existing mode-11 charge, the basic correction is:

```text
new_charge ≈ current_charge + actual_goodwe_grid_power
```

Because GoodWe grid power is negative on import, observed import immediately reduces the charge request. The result is clamped between zero and the current EMHASS `abs(P_batt)` cap.

Example:

```text
current charge setpoint  4420 W
GoodWe meter             -3070 W  (import)
next charge              ≈1350 W
```

### Anti-flap behavior

The controller deliberately does not chase every small cloud or meter fluctuation:

- grid error inside the configured deadband causes no setpoint change;
- grid import outside the deadband reduces charge immediately;
- export can increase charge by at most **1 kW per 30-second feedback tick**;
- if the calculated charge falls into the battery deadband, EnergyPilot switches to **mode 8 Battery Hold**, never through zero into discharge;
- after such a stop, Battery Hold lasts at least **2 minutes**;
- after that dwell, EnergyPilot requires **2 consecutive 30-second samples** with clear export (restart threshold at least 600 W and at least twice the configured deadband) before mode 11 can restart;
- a normal Home Assistant state-change event cannot bypass that dwell/restart evidence;
- if live GoodWe meter feedback is unavailable, grid-neutral charging fails safe to Battery Hold.

This is intentionally asymmetric: protecting against unintended import is fast; increasing charge again is slower and requires persistent surplus.

### Intentional grid charging remains possible

When EMHASS publishes a meaningful non-zero `P_grid` target during a charge interval, EnergyPilot treats that as explicit planned grid flow and preserves the existing direct `P_batt` → mode 11 execution. For example, EMHASS can still deliberately charge hard from the grid during a cheap-price interval.

If a charge request exists but the configured `P_grid` output is unavailable, v0.18 holds the battery rather than guessing that grid charging was intended.

### Why this does not use GoodWe mode 2 or mode 9

Mode 2 is not the correct primitive for the validated external-AC-PV layout because the GoodWe PV inputs themselves report 0 W; the relevant generation is visible at the smart meter instead.

v0.18 also does not hand battery direction to bidirectional grid-target mode 9. EMHASS still decides whether the battery is meant to charge or discharge. The smart-meter loop only limits a **charge** request when EMHASS itself planned grid flow around zero.

## 8. Price sources

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

## 9. First optimization

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

Before enabling v0.18 Automatic Control, also verify that `sensor.p_grid_forecast` (or the configured replacement) is numeric.

## 10. Enable control

Confirm:

```text
P_batt forecast      numeric
P_grid forecast      numeric
Optimization status Optimal
Orchestrator         ready
GoodWe grid power    plausible and signed as documented
```

Then enable **Automatic Control** or press **AUTO**.

AUTO performs a fresh optimization first and enables Automatic Control only after success.

## Scheduling

```text
GoodWe telemetry                   normally every 10 seconds
Grid-neutral charge correction     every 30 seconds while active
Minimum hold after charge stop     2 minutes
Restart evidence after hold        2 consecutive 30-second export samples
Periodic optimization              every 60 minutes
Optimize now                       immediately
AUTO                               immediately
Strategy change                    immediately after saving costfun
Tomorrow prices available          immediately
EV charging stops                  immediately when configured
SOC limit changes                  3 seconds after the final change
Home Assistant startup             no optimization
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

v0.18 automatic execution is summarized as:

```text
P_batt > +deadband
    → GoodWe mode 12, direct discharge target

P_batt inside deadband
    → GoodWe mode 8, Battery Hold

P_batt < -deadband AND abs(P_grid) <= deadband
    → grid-neutral charge limiter
    → mode 11 with meter-limited target, or mode 8 hold

P_batt < -deadband AND meaningful non-zero P_grid
    → GoodWe mode 11, direct planned charge target
```

Default deadband:

```text
300 W
```

## Grid energy foundation

v0.13+ exposes the current canonical GoodWe smart-meter cumulative grid counters:

```text
36015 total export
36017 total import
```

They are Home Assistant `total_increasing` kWh sensors. Recorder can therefore calculate today, yesterday, month and year changes without repeatedly integrating every historical power sample.

The v0.16+ extended `36104/36120` counters remain read-only Beta diagnostics pending physical SEMS lifetime correlation; they are not promoted to Recorder-facing canonical entities.

The dashboard's Grid detail graph uses 5-minute Recorder power statistics only when the user opens the Grid card. Daily import/export values are cached for five minutes.

## Diagnostics

Use **Copy snapshot** when reporting an issue and include the inverter model/firmware. For Beta register validation also use **Copy beta diagnostics**.

Relevant v0.18 values include:

- GoodWe EMS mode and setpoint;
- register 35172 and load-phase sum;
- system power balance;
- signed GoodWe grid power;
- configured/current `P_batt` and `P_grid` outputs;
- grid-neutral active flag and charge cap;
- grid-neutral live meter feedback;
- remaining anti-flap hold time and restart sample count;
- inverter registers 35138 and 35140;
- battery SOH and optional battery charge/discharge energy accounting;
- Beta SOC diagnostics `45356`, `45358`, `47500`;
- Beta extended grid counters `36104`, `36120`;
- active EMHASS optimization strategy and raw `costfun`;
- controller command/target;
- EMHASS health/version and HTTP results;
- load and price point counts;
- other active `goodwe` config entries.

## Common failures

### `waiting_for_home_assistant`

Home Assistant startup is still in progress.

### `waiting_for_goodwe`

EnergyPilot has not completed a successful Modbus refresh. Verify inverter address, Modbus availability and whether another client is polling the same inverter.

### `waiting_for_p_grid`

EMHASS requests battery charging but the configured `P_grid` entity has no usable numeric state. v0.18 holds the battery because it cannot determine whether grid charging was intentionally planned.

### `grid_neutral_meter_unavailable`

EMHASS planned near-zero grid flow while charging, but EnergyPilot has no usable GoodWe smart-meter feedback. The battery is held instead of executing a blind charge target.

### `grid_neutral_hold` / `grid_neutral_waiting_for_surplus`

The grid-neutral limiter stopped charging because local surplus was insufficient. It is enforcing the minimum 2-minute dwell and/or waiting for persistent export evidence before restarting.

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
