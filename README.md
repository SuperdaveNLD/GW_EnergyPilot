<p align="center">
  <img src="https://raw.githubusercontent.com/SuperdaveNLD/GW_EnergyPilot/main/custom_components/gw_energypilot/brand/logo.png" alt="GW EnergyPilot" width="180">
</p>

# GW EnergyPilot

GW EnergyPilot is an unofficial Home Assistant integration for local telemetry and EMS control of GoodWe ETA hybrid inverters.

It combines:

- direct Modbus TCP telemetry;
- GoodWe EMS modes and power setpoints;
- native EMHASS optimization and publishing;
- optional Nord Pool runtime prices;
- automatic `P_batt` execution;
- one-touch battery controls;
- optional EV coordination;
- a built-in dashboard and diagnostics snapshot.

> This project is independent and is not affiliated with or endorsed by GoodWe.

## Status

**Alpha — v0.12**

Forced charge, discharge and export modes can move significant power. Confirm inverter, battery, grid and contract limits before enabling Automatic Control.

## Requirements

- Home Assistant 2026.8 or newer;
- HACS;
- GoodWe ETA inverter reachable through Modbus TCP;
- fixed inverter IP address or DHCP reservation;
- EMHASS installed, started and configured;
- optional Nord Pool price source in Home Assistant.

Typical GoodWe connection values:

```text
Port:    502
Unit ID: 247
```

Use only one local integration for continuous GoodWe polling where possible. Disable the separate `goodwe` integration when GW EnergyPilot replaces it. Two integrations polling the same inverter can compete for the Modbus connection and delay Home Assistant startup or telemetry.

## Installation

1. Install and start EMHASS.
2. Add this repository to HACS as an **Integration**.
3. Install **GW EnergyPilot**.
4. Restart Home Assistant.
5. Open **Settings → Devices & services → Add integration**.
6. Add **GW EnergyPilot** and enter the inverter IP address, port and Unit ID.
7. Keep **Automatic Control OFF** during validation.
8. Verify PV, grid, battery and house-power values.
9. Map the EMHASS source sensors to the EnergyPilot entities below.
10. Restart EMHASS.
11. Open the EnergyPilot dashboard and press **Optimize now**.
12. Confirm that `sensor.p_batt_forecast` is numeric and the optimization status is `Optimal`.
13. Enable Automatic Control.

## EMHASS source mappings

Use the actual entity IDs created on your installation. The normal defaults are:

| EMHASS setting | GW EnergyPilot entity |
|---|---|
| `sensor_power_photovoltaics` | `sensor.gw_energypilot_pv_total_power` |
| `sensor_power_load_no_var_loads` | `sensor.gw_energypilot_total_load_power` or a validated combined house-load sensor |
| `sensor_power_battery` | `sensor.gw_energypilot_battery_power` |
| `sensor_battery_state_of_charge` | `sensor.gw_energypilot_battery_state_of_charge` |
| `var_model` | the same validated house-load entity |
| `sensor_power_photovoltaics_forecast` | normally `sensor.p_pv_forecast` |

Battery-power convention:

```text
negative = charging
positive = discharging
```

EnergyPilot passes the live battery SOC to every optimization as `soc_init`.

### House load

GoodWe register `35172` is retained as a raw diagnostic value. The dashboard also calculates whole-home demand from:

```text
PV - grid + battery
```

with EnergyPilot's sign conventions:

```text
grid positive     = export
grid negative     = import
battery positive  = discharge
battery negative  = charge
```

The calculated value is used for the dashboard and the native load forecast when all three inputs are valid. This is especially useful with AC-coupled PV or firmware where register `35172` does not represent the complete property load.

## Native EMHASS orchestrator

EnergyPilot performs the complete transaction:

```text
current SOC + load forecast + optional prices
        ↓
POST /action/dayahead-optim
        ↓
validate HTTP result
        ↓
POST /action/publish-data
        ↓
validate fresh numeric P_batt
        ↓
Automatic Control applies the new target
```

Default scheduling:

```text
Periodic optimization             every 60 minutes
Optimize now                      immediately
AUTO button                       optimize, then resume automatic control
Tomorrow prices become available immediately
EV charging stops                 immediately, when EV coordination is configured
Minimum/maximum SOC changes       immediately
Home Assistant startup            no automatic optimization
```

The startup run is intentionally omitted. EMHASS and other Home Assistant entities must be ready before a plan is created.

Recommended EMHASS setting when EnergyPilot owns publishing:

```json
"continual_publish": false
```

## Prices

With **Use official Nord Pool runtime prices** enabled, EnergyPilot first uses Home Assistant's `nordpool.get_prices_for_date` action.

It also supports a Nord Pool-style sensor with `raw_today` and `raw_tomorrow` attributes. EnergyPilot automatically detects the available source and passes timestamped runtime dictionaries to EMHASS:

```text
load_cost_forecast
prod_price_forecast
```

Available adjustments:

```text
Import price addition
Export price deduction
```

When runtime pricing is disabled, EMHASS uses the price method configured inside EMHASS.

## Battery controls

The Battery card contains four native controls:

| Button | Action |
|---|---|
| **Max export** | GoodWe mode 10 with the configured maximum grid-export target |
| **Pause** | GoodWe mode 8, Battery Hold around 0 W |
| **Max charge** | GoodWe mode 11 with the configured maximum charge power |
| **AUTO** | creates a fresh EMHASS plan and enables Automatic Control only after success |

Manual controls disable Automatic Control so a later state update cannot immediately overwrite the requested mode.

## EMHASS SOC controls

The dashboard exposes:

```text
EMHASS minimum battery SOC
EMHASS maximum battery SOC
```

EnergyPilot reads the complete current EMHASS configuration through `/get-config`, changes only the selected SOC field and writes the full configuration back through `/set-config`. A new optimization is then requested.

## Dashboard

The built-in sidebar dashboard provides:

- live PV, house, grid and battery flow;
- Solar, Home, Grid and Battery cards;
- Controller and EMHASS state;
- one-touch battery controls;
- minimum and maximum SOC sliders;
- system temperatures and BMS limits;
- draggable card ordering;
- per-card visibility toggles, including Diagnostics;
- flow-animation toggle;
- copyable diagnostics snapshot.

Dashboard layout is stored per browser.

## Diagnostics

Use **Copy snapshot** on the Diagnostics card when reporting an issue. It includes:

- EMS mode and setpoint;
- controller command, target and expected mode;
- raw and calculated house power;
- grid, PV, inverter and battery power;
- selected `P_batt` and optimization entities;
- EMHASS health/version and HTTP results;
- load and price point counts;
- detected price source;
- other active Home Assistant `goodwe` config entries.

## Troubleshooting

### Sensors remain unavailable after startup

1. Confirm the inverter responds on TCP port 502.
2. Confirm the Unit ID.
3. Disable the separate Home Assistant `goodwe` integration if it polls the same inverter.
4. Reload GW EnergyPilot.
5. Open the Diagnostics card.

EnergyPilot adds its entities before the first Modbus read completes, so they may briefly show unavailable without delaying all of Home Assistant startup.

### Optimization fails

Check the orchestrator message and copied snapshot. Common causes:

- EMHASS still starting;
- invalid EMHASS source entity;
- missing runtime price source while runtime pricing is enabled;
- incompatible forecast length or malformed EMHASS configuration;
- no fresh `P_batt` output after publishing.

### `P_batt` or optimization entity does not exist yet

The normal IDs are prefilled as text:

```text
sensor.p_batt_forecast
sensor.optim_status
```

They can be configured before EMHASS creates them. The entities appear after a successful optimization and publish.

## GoodWe EMS mapping

```text
P_batt < -deadband  → mode 11 → battery charge
inside deadband     → mode 8  → Battery Hold
P_batt > +deadband  → mode 12 → battery discharge
```

Disabling Automatic Control returns the inverter to:

```text
Mode 1 — GoodWe Auto / AI
Setpoint 0 W
```

Main control registers:

```text
47511 = EMS mode
47512 = EMS power setpoint
```

## Documentation

- `docs/EMHASS_SETUP.md`
- `CHANGELOG.md`
- EMHASS documentation: https://emhass.readthedocs.io/
- Home Assistant developer documentation: https://developers.home-assistant.io/

## License

See `LICENSE`.
