<p align="center">
  <img src="https://raw.githubusercontent.com/SuperdaveNLD/GW_EnergyPilot/main/custom_components/gw_energypilot/brand/logo.png" alt="GW EnergyPilot" width="180">
</p>

# GW EnergyPilot

GW EnergyPilot is an unofficial Home Assistant integration for local telemetry, GoodWe EMS control and EMHASS optimization.

> This project is independent and is not affiliated with or endorsed by GoodWe.

## Status

**Alpha — v0.15**

GW EnergyPilot is being developed specifically around the **new GoodWe ETA G20 generation**.

### Tested hardware

| Model | Status | Notes |
|---|---|---|
| **GoodWe GW15K-ETA-G20** | ✅ Tested | Primary development and validation inverter |

The broader ETA-G20 family uses closely related telemetry and EMS concepts, but the other models have not yet been individually validated by this project.

If GW EnergyPilot works on your inverter, please open a GitHub issue/discussion and report:

```text
Inverter model
Firmware version
Battery model
Whether telemetry works
Whether EMS modes 8 / 11 / 12 work
```

That feedback will be used to build a real tested-model compatibility list rather than assuming every GoodWe generation uses the same register behaviour.

## What it provides

- direct local Modbus TCP telemetry;
- GoodWe EMS mode and power control;
- native EMHASS optimization and publishing;
- one-touch EMHASS `profit`, `cost` and `self-consumption` strategy controls;
- optional Nord Pool runtime prices;
- automatic `P_batt` execution;
- one-touch battery controls;
- optional EV coordination;
- built-in EnergyPilot dashboard;
- native cumulative grid import/export energy counters;
- optional battery charge/discharge accounting diagnostics;
- interactive 24-hour Grid history and daily import/export totals;
- copyable diagnostics snapshot.

## Requirements

- Home Assistant 2026.8 or newer;
- HACS;
- GoodWe ETA-G20 reachable through Modbus TCP;
- fixed inverter IP address or DHCP reservation;
- EMHASS installed, started and configured;
- optional Nord Pool price source.

Typical GoodWe ETA-G20 connection values:

```text
Port:    502
Unit ID: 247
```

Use only one integration for continuous local polling where possible. If GW EnergyPilot replaces another Home Assistant `goodwe` integration, disable that integration. Two clients repeatedly polling an inverter can compete for the connection, especially when the inverter is sleeping or unavailable.

## Installation

1. Install and start EMHASS.
2. Add this repository to HACS as an **Integration**.
3. Install **GW EnergyPilot**.
4. Restart Home Assistant.
5. Open **Settings → Devices & services → Add integration**.
6. Add **GW EnergyPilot** and enter the inverter IP address, port and Unit ID.
7. Keep **Automatic Control OFF** during validation.
8. Verify PV, grid, battery and load values.
9. Map the EMHASS source sensors to EnergyPilot.
10. Restart EMHASS after changing its configuration.
11. Press **Optimize now** in the EnergyPilot dashboard.
12. Confirm `sensor.p_batt_forecast` is numeric and optimization status is `Optimal`.
13. Enable Automatic Control.

## EMHASS URL

EMHASS documentation commonly shows:

```text
http://localhost:5000
```

That is the normal exposed web-server port and is useful for browsers, shell commands and standalone Docker setups.

For a Home Assistant custom integration, however, the HTTP request originates from Home Assistant Core. On current HAOS installations `localhost:5000` is not guaranteed to resolve to the EMHASS add-on container. EnergyPilot therefore keeps the Home Assistant add-on hostname as its default:

```text
http://5b918bf2-emhass:5000
```

If your installation exposes EMHASS through another address, change **EMHASS URL** in EnergyPilot options.

## EMHASS source mappings

Use the actual entity IDs created on your installation.

| EMHASS setting | GW EnergyPilot entity |
|---|---|
| `sensor_power_photovoltaics` | `sensor.gw_energypilot_pv_total_power` |
| `sensor_power_load_no_var_loads` | `sensor.gw_energypilot_goodwe_load_power_35172` or the actual generated ID for GoodWe load power |
| `sensor_power_battery` | `sensor.gw_energypilot_battery_power` |
| `sensor_battery_state_of_charge` | `sensor.gw_energypilot_battery_state_of_charge` |
| `var_model` | the same validated load entity |
| `sensor_power_photovoltaics_forecast` | normally `sensor.p_pv_forecast` |

Entity IDs can differ when Home Assistant has already assigned a name. Always verify them under **Developer tools → States**.

Battery convention:

```text
negative battery power = charging
positive battery power = discharging
```

EnergyPilot passes live battery SOC to EMHASS as `soc_init` for every optimization.

## EMHASS strategy controls

v0.15 exposes three one-touch EMHASS objectives:

```text
profit
cost
self-consumption
```

Selecting one reads the complete current EMHASS configuration, changes only `costfun`, writes the complete configuration back, then immediately creates and publishes a fresh optimization. Unrelated EMHASS settings are preserved.

This changes the optimizer objective only. GoodWe Automatic Control remains `P_batt`-driven and keeps the existing mode 8/11/12 mapping.

## Power semantics on the tested GW15K-ETA-G20

Several GoodWe registers represent different electrical measurement points. They must not all be interpreted as household consumption.

### Grid

EnergyPilot uses GoodWe smart-meter register `36008` as the primary instantaneous grid value:

```text
negative = grid import
positive = grid export
```

The dashboard hides the minus sign in the large Grid number because the **Importing / Exporting** badge already shows direction. Diagnostics keeps the signed raw value.

### House / load

Register `35172` is GoodWe's load value. On the tested GW15K-ETA-G20 it closely matches:

```text
Load L1 + Load L2 + Load L3
```

For that reason v0.13+ uses `35172` as the Home/load value and for the EMHASS load model.

### System power balance

EnergyPilot also displays:

```text
PV - grid + battery
```

This is a **system power balance**, not a second house-load sensor. The difference between this balance and `35172` can include inverter conversion losses, inverter auxiliary consumption and measurement-point differences.

Registers `35138` and `35140` remain available as inverter-side diagnostics. In particular, **35138 must not be interpreted as inverter self-consumption**.

## Refresh frequencies

The dashboard shows the configured refresh cadence directly on the cards.

Defaults:

```text
GoodWe telemetry     every 10 seconds
EMHASS optimization  every 60 minutes + event triggers
Grid daily totals    cached for 5 minutes in the dashboard
Grid 24h graph       loaded only when the Grid card is opened
```

This keeps the normal dashboard lightweight.

## Grid history and energy totals

The Grid card is interactive. Click it to open:

- signed grid-power graph for the previous 24 hours;
- energy imported today;
- energy exported today;
- energy imported yesterday;
- energy exported yesterday;
- lifetime GoodWe smart-meter import/export counters.

EnergyPilot reads the GoodWe meter's native cumulative registers:

```text
36015 = total exported grid energy
36017 = total imported grid energy
```

They are exposed as `total_increasing` kWh sensors so Home Assistant Recorder can calculate daily/monthly/yearly changes efficiently. The dashboard does **not** continuously scan history. The 24-hour graph is requested only when opened and daily totals are cached.

After first installation, yesterday's value becomes complete after Recorder has observed the cumulative counters across a midnight boundary.

## Battery accounting diagnostics

v0.14+ reads the GoodWe battery charge/discharge accounting block `35206-35211` as optional diagnostics. These values are useful for support and later energy/cost accounting, but are deliberately not used for EMS control or synthetic cycle-count calculations.

The optional block cannot make required inverter telemetry unavailable when unsupported by another firmware/model.

## Future energy-cost accounting

The native cumulative import/export counters are also the foundation for future cost accounting. The intended design is incremental rather than recalculating months of history on every dashboard render:

```text
meter delta import × active buy price  → cumulative import cost
meter delta export × active sell price → cumulative export revenue
```

The buy/sell price will use the same Nord Pool source plus the EnergyPilot import/export adjustments already used by EMHASS. Persistent cumulative cost/revenue sensors can then let Recorder return today, yesterday, month and year totals with cheap `change` queries.

A separate Cost card should only appear when a usable runtime price source is configured.

## Battery SOC limits

The dashboard exposes EMHASS minimum and maximum battery SOC sliders.

EnergyPilot recommendation for **normal grid-connected cycling**:

```text
minimum SOC: about 5%
maximum SOC: about 95%
```

This is a conservative EnergyPilot operating recommendation, not a replacement for GoodWe or battery protection settings.

There are multiple limit layers:

```text
EMHASS min/max SOC     optimizer planning limits
GoodWe / SEMS+ limits  inverter protection / operating limits
Battery BMS limits     final battery protection
```

The most restrictive layer wins. Example: when the GoodWe/SEMS+ on-grid minimum is set to `10%`, EnergyPilot can request mode 12 below 10%, but the inverter/BMS may refuse further discharge around that threshold.

GoodWe's current G20 documentation also recommends a substantially higher reserve for off-grid operation; off-grid SOC protection should therefore be treated separately from the 5–95% normal grid-connected cycling recommendation.

The dashboard `i` button beside the SOC controls explains this distinction.

SOC slider changes are debounced for 3 seconds. Moving a slider through several percentages therefore produces one new optimization after the control has settled instead of starting an optimizer run for every intermediate step.

## Native EMHASS orchestrator

EnergyPilot performs:

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
Automatic Control applies target
```

Default scheduling:

```text
Periodic optimization             every 60 minutes
Optimize now                      immediately
AUTO                              optimize, then resume automatic control
Cost-function change              optimize immediately after saving costfun
Tomorrow prices available         immediately
EV charging stops                 immediately when configured
SOC limit changes                 3 seconds after final change
Home Assistant startup            no automatic optimization
```

Recommended EMHASS setting when EnergyPilot owns publishing:

```json
"continual_publish": false
```

## Automatic control

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

Main EMS registers:

```text
47511 = EMS mode
47512 = EMS power setpoint
```

Forced charge, discharge and export modes can move significant power. Verify inverter, battery, grid and contract limits before enabling Automatic Control.

## Dashboard

The sidebar dashboard includes:

- live PV / Home / Grid / Battery flow;
- visible telemetry refresh frequency;
- Solar, Home, Grid and Battery cards;
- Controller and EMHASS cards;
- one-touch EMHASS strategy controls;
- one-touch battery controls;
- EMHASS minimum/maximum SOC controls with guidance popup;
- interactive Grid detail;
- battery accounting diagnostics;
- thermal/BMS information;
- draggable ordering and per-card visibility;
- flow animation toggle;
- copyable diagnostics snapshot.

Dashboard layout is stored per browser.

## Troubleshooting startup

When Home Assistant logs:

```text
Waiting for integrations to complete setup: {('goodwe', ...)}
```

that refers to the separate integration whose domain is `goodwe`, not `gw_energypilot`.

If the inverter sleeps or becomes unreachable at night, a separate GoodWe integration can remain in retry/setup for a long time. EnergyPilot adds its entities first and performs the first Modbus refresh as a background task, so an unavailable inverter should not hold all of Home Assistant startup open.

If EnergyPilot replaces the old GoodWe integration, disable the old integration rather than letting both poll the same device.

For the separate SEMS/SEMS+ plugin interoperability issue, see `docs/KNOWN_ISSUES.md`.

## Diagnostics

Use **Copy snapshot** when reporting an issue. Include the inverter model and firmware with the snapshot.

Useful values include:

- EMS mode/setpoint;
- GoodWe load 35172 and load phase sum;
- system power balance;
- signed grid meter value;
- 35138/35140 inverter diagnostics;
- battery power/SOC/SOH, BMS limits and optional charge/discharge accounting;
- selected EMHASS entities;
- EMHASS health/version and HTTP results;
- price and load point counts;
- other active `goodwe` config entries.

## Documentation

- `docs/EMHASS_SETUP.md`
- `docs/KNOWN_ISSUES.md`
- `CHANGELOG.md`
- EMHASS documentation: https://emhass.readthedocs.io/
- Home Assistant developer documentation: https://developers.home-assistant.io/

## License

See `LICENSE`.
