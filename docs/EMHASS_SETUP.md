# EMHASS setup for GW EnergyPilot

EMHASS creates the battery/grid plan. GW EnergyPilot supplies live inputs, runs optimization/publish, validates the outputs and translates the current plan into GoodWe ETA-G20 EMS commands.

The primary tested development inverter is **GoodWe GW15K-ETA-G20**.

## 1. Install EMHASS first

Install the EMHASS App/Add-on, enable **Start on boot** and **Watchdog**, and start it.

Confirm that the EMHASS web interface opens before configuring EnergyPilot.

EnergyPilot defaults to the Home Assistant add-on hostname:

```text
http://5b918bf2-emhass:5000
```

Change it when your EMHASS installation uses another address. `localhost` is often not appropriate when Home Assistant Core must reach a separate add-on container.

## 2. Connect GW EnergyPilot

1. Add GW EnergyPilot under **Settings → Devices & services**.
2. Enter the fixed inverter IP address.
3. Use port `502` and Unit ID `247` unless your inverter uses different values.
4. Keep **Automatic Control OFF** during setup.
5. Verify battery SOC, battery power, PV power, GoodWe load and grid power.
6. Open the dashboard gear → **GOODWE** and confirm whether **GoodWe smart meter active** matches the installation.

When EnergyPilot replaces another direct GoodWe Modbus integration, avoid running two integrations that continuously poll/control the same inverter.

## 3. EMHASS input mapping

Use the actual entity IDs shown by Home Assistant.

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

EnergyPilot sends current battery SOC as runtime `soc_init` for every native optimization.

### Load register 35172

On the tested GW15K-ETA-G20:

```text
GoodWe load 35172 ≈ Load L1 + Load L2 + Load L3
```

EnergyPilot also calculates:

```text
PV - grid + battery
```

That is retained as a **system power balance** diagnostic. It is not substituted into the EMHASS house-load model because it depends on measurement topology and inverter conversion/auxiliary differences.

Registers `35138` and `35140` are inverter-side power diagnostics and should not be treated as house load.

## 4. Required EMHASS outputs

The normal output entities are:

```text
sensor.p_batt_forecast
sensor.p_grid_forecast
sensor.optim_status
```

They can be entered in EnergyPilot before EMHASS creates them.

EMHASS output conventions used by EnergyPilot are:

```text
P_batt < 0  = planned battery charge
P_batt > 0  = planned battery discharge

P_grid > 0  = planned grid import
P_grid < 0  = planned grid export
```

The GoodWe smart-meter telemetry uses the **opposite grid sign convention**:

```text
GoodWe meter 36008 < 0 = actual import
GoodWe meter 36008 > 0 = actual export
```

Do not mix these two conventions.

## 5. GoodWe automatic actuator strategy

GW EnergyPilot v0.22 supports two explicit automatic strategies.

The choice is under:

```text
Dashboard gear → GOODWE → GoodWe smart meter active
```

### Strategy A — GoodWe smart meter active = ON

This is the v0.22 default and the preferred strategy on a validated GoodWe smart-meter installation.

`P_grid` becomes the automatic actuator plan:

```text
P_grid > +deadband
    → GoodWe mode 9 · Grid import target
    → 47512 = planned import magnitude

P_grid < -deadband
    → GoodWe mode 10 · Grid export target
    → 47512 = planned export magnitude

P_grid inside deadband
    → GoodWe mode 1 · Auto / AI
    → 47512 = 0 W
```

GoodWe then closes the fast loop against its own smart meter/PCC.

This matters because a **mode-9 setpoint is grid import, not battery charge power**. Hardware testing showed:

```text
mode 9 = 15 kW
actual grid import ≈ 15 kW
available DC PV is added locally
battery charge can therefore exceed 15 kW
```

On the reference test point, about 3.9 kW PV plus 15 kW grid import resulted in roughly 16.9 kW battery charging after house load and losses.

Mode 10 is the corresponding site export target.

### Strategy B — GoodWe smart meter active = OFF

This preserves the direct battery-control fallback:

```text
P_batt < -deadband
    → GoodWe mode 11 · Battery charge power
    → 47512 = abs(P_batt)

P_batt > +deadband
    → GoodWe mode 12 · Battery discharge power
    → 47512 = P_batt

P_batt inside deadband
    → GoodWe mode 8 · Battery Hold
    → 47512 = 0 W
```

This strategy does not require a valid `P_grid` output.

Use it when the GoodWe smart meter is absent, unavailable, incorrectly installed or not yet validated for the inverter/firmware.

## 6. Why mode 1 is used around zero grid flow

Manual v0.21 testing on the reference ETA-G20 showed mode 1 naturally performing the desired self-use behavior:

- house load is served;
- available PV surplus goes to the battery;
- grid flow stays close to zero;
- GoodWe itself reacts to real-time PV/load changes.

That makes mode 1 a simpler zero-grid primitive than maintaining a second EnergyPilot feedback loop around mode 11.

BMS, inverter SOC limits and GoodWe/SEMS+ protection settings remain authoritative.

## 7. External AC-coupled PV

A separate PV inverter may be AC-coupled elsewhere in the installation. In that layout:

- GoodWe's own DC PV registers can show little or no power from the external inverter;
- the GoodWe smart meter still sees its effect at the point of common coupling;
- register `35172` can become misleading/negative depending on topology;
- mode 9/10 PCC control still sees the **net site flow**.

This is one of the main reasons v0.22 prefers PCC targets when the GoodWe smart meter is available.

Directly connected GoodWe PV has an efficiency advantage because it can reach the battery through the DC path. An external AC inverter can still produce the same site-level import/export result, but energy crosses the AC conversion path.

## 8. The old grid-neutral mode-11 loop

v0.18-v0.21 used a 30-second GoodWe meter feedback loop to reduce mode-11 charging when actual PV was lower than forecast.

That loop is **retired in v0.22** when Smart Meter control is enabled.

GoodWe modes 9/10 now own the fast meter regulation directly. The legacy `grid_neutral_*` support attributes remain present as inactive compatibility values for older frontend/support code.

See `docs/GRID_NEUTRAL_CHARGING.md` for the migration rationale.

## 9. Recommended EMHASS settings

Use the real battery and inverter limits for the installation. For a configuration without deferrable loads, all per-load arrays should be empty.

Recommended publishing setting:

```json
"continual_publish": false,
"method_ts_round": "first"
```

EnergyPilot owns both scheduled paths. It runs a full optimization on fixed
local wall-clock boundaries and event triggers, then performs the initial
publish only after that optimization succeeds. Between full optimizations it
advances the saved EMHASS plan through `/action/publish-data` on the inferred
plan timestep. `method_ts_round = first` selects the active plan row. EMHASS's
independent continual-publish loop stays disabled.

Recommended EnergyPilot starting values:

```text
Enable built-in EMHASS orchestrator   ON
EMHASS URL                            http://5b918bf2-emhass:5000
P_batt output entity                  sensor.p_batt_forecast
P_grid output entity                  sensor.p_grid_forecast
Optimization status                   sensor.optim_status
Optimization interval                 15 min recommended; 30/60 min available
Runtime final SOC target              installation dependent
Fallback house load                   installation dependent
Use runtime Nord Pool prices          ON when a supported source exists
Optimize when tomorrow prices arrive  ON
Nord Pool currency                    EUR
```

The Controller maximum power setting caps the commanded **mode-specific setpoint**. With Smart Meter control enabled it caps the requested PCC import/export magnitude; it is not a battery-power ceiling for mode 9 because local PV can be added on top.

## 10. Optimization strategy

EMHASS supports these `costfun` objectives:

```text
profit
cost
self-consumption
```

EnergyPilot exposes them as one stateful **EMHASS optimization strategy** selector.

Changing the strategy performs:

```text
GET /get-config
      ↓
change only costfun
      ↓
POST /set-config with the complete configuration
      ↓
run fresh optimization
      ↓
publish fresh outputs
```

Unrelated EMHASS settings are preserved.

Changing `costfun` changes what EMHASS optimizes. It does **not** silently change the GoodWe Smart Meter strategy setting.

## 11. Price sources

EnergyPilot tries runtime price sources in this order:

1. Home Assistant `nordpool.get_prices_for_date`;
2. a sensor with `raw_today` and `raw_tomorrow`;
3. EMHASS internal pricing when runtime pricing is disabled.

With runtime prices enabled EnergyPilot supplies:

```text
load_cost_forecast
prod_price_forecast
```

If runtime pricing is enabled but no compatible source exists, EnergyPilot reports an error rather than silently optimizing with unintended prices.

## 12. First optimization

For a manual-only configuration, wait until Home Assistant startup has finished and EnergyPilot telemetry is available. Then press **Optimize now**.

Successful flow:

```text
EMHASS health check
        ↓
current SOC + load forecast + optional prices
        ↓
POST /action/dayahead-optim
        ↓
HTTP 2xx
        ↓
POST /action/publish-data
        ↓
fresh numeric outputs + expected optimization state
        ↓
ready
```

EnergyPilot never blocks Home Assistant startup on an EMHASS solve. v0.48 retains the v0.44 background recovery behavior: one attempt 60 seconds after EnergyPilot setup when native orchestration is enabled. The normal Home Assistant-running, GoodWe-telemetry, EMHASS-health and finite-output gates still apply. A transient failure retries after 15, 30 and 60 seconds; any successful manual, event-driven or scheduled optimization after setup cancels the remaining startup sequence. After the bounded retries are exhausted, the normal wall-clock schedule remains active.

## 13. Enable Automatic Control

Before enabling control confirm:

```text
P_batt forecast      numeric
Optimization status ready
GoodWe telemetry     available
```

When **GoodWe smart meter active = ON**, also confirm:

```text
P_grid forecast      numeric
Grid power 36008     plausible
Grid sign            negative import / positive export
```

Then enable **Automatic Control** or press **AUTO**.

AUTO creates a fresh optimization first and enables Automatic Control only after that optimization succeeds.

## 14. Manual EMS testing

v0.21+ includes the twelve-mode manual pad in the Controller card.

Automatic Control ON:

- the manual mode grid and power slider are hidden from view and the
  accessibility tree;
- a compact ownership summary remains visible;
- live mode and setpoint read-back remain available in the Controller metrics.

Automatic Control OFF:

- the same stable manual-control nodes become visible and usable;
- modes 1–12 can be selected manually when the required entities are available;
- the power slider runs from 0 W to configured maximum control power;
- modes 1/6/7/8 force 0 W;
- mode 7 requires extra confirmation.

If the required manual mode or manual power entity is missing, EnergyPilot keeps
the compact summary visible with an explicit unavailable status instead of
showing unusable controls.

Manual commands are never remapped by the GoodWe smart-meter strategy setting.

See `docs/EMS_MODES.md` for the exact meaning of all twelve modes.

## 15. SOC limits

The dashboard EMHASS controls write:

```text
battery_minimum_state_of_charge
battery_maximum_state_of_charge
```

EnergyPilot reads the complete EMHASS config, updates the selected field and writes the complete config back.

For normal grid-connected cycling, a common starting range is approximately:

```text
minimum 5%
maximum 95%
```

This is an operating recommendation, not a hardware override.

GoodWe/SEMS+ and the battery BMS have separate protection limits. For example, a GoodWe on-grid minimum SOC can stop discharge even when EMHASS requests a lower SOC.

## 16. Scheduling

```text
GoodWe telemetry                   configured scan interval
Wall-clock optimization            15/30/60 min at the boundary +15 s; 15 recommended
Active plan-step publish           inferred plan timestep at the boundary +15 s
Optimize now                       immediately
AUTO                               fresh optimize, then enable control
Strategy change                    fresh optimize after save
Tomorrow prices available          immediate when enabled
EV charging stops                  immediate fresh optimization when configured
SOC limit changes                  debounced after final change
Post-restart recovery              after 60 s; transient retry 15/30/60 s
```

When optimization and plan-step publication are due together, optimization
runs first and its initial publish is reused. A failed due step places enabled
Automatic Control in Battery Hold unless a valid fallback step can be published.

There is no v0.22 30-second mode-11 grid-neutral feedback scheduler when Smart Meter control is enabled.

## 17. Diagnostics

Use **Copy snapshot** when reporting an issue and include inverter model/firmware.

For v0.22 control validation include:

- **GoodWe smart meter active** setting;
- `P_batt` and `P_grid` values;
- optimizer status;
- GoodWe EMS mode `47511`;
- GoodWe EMS setpoint `47512`;
- signed GoodWe grid power `36008`;
- battery power;
- PV total;
- house load `35172` and phase sum;
- controller command/target;
- relevant SOC limits.

For Beta register validation also use **Copy beta diagnostics**.
