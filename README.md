<p align="center">
  <img src="custom_components/gw_energypilot/brand/logo.png" alt="GW EnergyPilot" width="180">
</p>

# GW EnergyPilot

GW EnergyPilot is an unofficial Home Assistant integration for advanced EMS and battery control of GoodWe ETA hybrid inverters.

It provides direct Modbus TCP telemetry and control, native EMHASS orchestration, `P_batt` mapping, Battery Hold, manual EMS control, optional EV coordination, and a built-in EnergyPilot dashboard.

> This is an independent community project and is not affiliated with or endorsed by GoodWe.

## Current status

**Alpha - v0.10**

v0.10 moves the tested EMHASS optimization/publish workflow into EnergyPilot itself and adds a native **Optimize now** button to Home Assistant and the built-in dashboard.

Forced EMS modes can charge or discharge a battery at high power and can export energy to the grid. Verify inverter, battery and grid limits before enabling Automatic Control.

## Version numbering

GW EnergyPilot uses simple incremental versions:

```text
v0.01
v0.02
v0.03
...
v0.09
v0.10
```

# Recommended installation order

For a fresh Home Assistant installation use this sequence:

```text
1. Install Home Assistant + HACS
2. Install and start EMHASS
3. Install GW EnergyPilot
4. Connect EnergyPilot to the GoodWe ETA
5. Keep EnergyPilot Automatic Control OFF
6. Verify EnergyPilot telemetry
7. Change EMHASS source mappings to EnergyPilot entities
8. Restart/reload EMHASS
9. Configure the EnergyPilot built-in EMHASS orchestrator
10. Press Optimize now in the EnergyPilot dashboard
11. Verify sensor.p_batt_forecast and sensor.optim_status
12. Enable the recurring EnergyPilot orchestrator schedule
13. Enable EnergyPilot Automatic Control
```

The final data path is:

```text
GoodWe ETA
    │ Modbus TCP
    ▼
GW EnergyPilot telemetry
    │
    ├── current SOC
    ├── current load + Recorder history
    └── optional official Nord Pool prices
    │
    ▼
GW EnergyPilot EMHASS orchestrator
    │
    ▼
EMHASS optimization + publish
    │ sensor.p_batt_forecast
    ▼
GW EnergyPilot controller
    │
    ▼
GoodWe EMS modes 8 / 11 / 12
```

# Native EMHASS orchestrator in v0.10

EnergyPilot can now run the complete EMHASS optimization cycle itself. A normal v0.10 installation no longer needs the old `energypilot_emhass_orchestrator.yaml` package.

The native orchestrator:

- runs independently from the EnergyPilot Automatic Control switch;
- reads current battery SOC directly from EnergyPilot before every optimization;
- passes actual SOC as runtime `soc_init`;
- builds a 48-hour load forecast from current load plus Home Assistant Recorder history;
- can retrieve timestamped prices from Home Assistant's official Nord Pool integration;
- validates the EMHASS optimization HTTP result;
- calls `publish-data` only after a successful optimization;
- validates that a fresh numeric `sensor.p_batt_forecast` is available;
- exposes optimizer diagnostics on the native **Optimize now** button entity;
- never writes GoodWe registers itself.

Recommended starting values:

```text
EMHASS P_batt entity            sensor.p_batt_forecast
Optimization status             sensor.optim_status
Required optimization state     Optimal
Maximum inverter power          15.0 kW
Power deadband                  300 W
Modbus scan interval            10 s
EMHASS URL                      http://5b918bf2-emhass:5000
Optimization interval           15 min
Target final SOC                10%
Fallback house load             700 W
Nord Pool currency              EUR
EV coordination                 OFF
```

Existing v0.09 installations upgrade with the built-in recurring scheduler OFF so it cannot silently run next to an existing YAML scheduler. The native **Optimize now** button is still available for testing.

## Optimize now

v0.10 adds a native Home Assistant button entity named **GW EnergyPilot Optimize now**.

The same control is shown directly on the dashboard EMHASS card:

```text
EMHASS
P_batt target     +x.xx kW
Optimization      Optimal

[ Optimize now ]
```

Pressing it performs one complete transaction:

```text
current SOC + load forecast + optional prices
        ↓
POST /action/dayahead-optim
        ↓
HTTP 2xx?
   no -> stop
   yes
        ↓
POST /action/publish-data
        ↓
validate fresh P_batt + optimization status
        ↓
ready
```

The button works even when the recurring orchestrator schedule is disabled.

## Official Nord Pool support

When **Use official Nord Pool prices** is enabled and Home Assistant's Nord Pool integration is configured, EnergyPilot calls:

```text
nordpool.get_prices_for_date
```

EnergyPilot requests today and, when available, tomorrow, converts the returned currency/MWh values to currency/kWh, and sends timestamped `load_cost_forecast` and `prod_price_forecast` dictionaries to EMHASS.

The price model supports:

```text
Import price addition
Export price deduction
```

The validated Tibber setup used an export deduction of:

```text
0.0248 EUR/kWh
```

Disable official Nord Pool pricing in EnergyPilot when EMHASS should instead use its own configured price forecast method such as `hp_hc_periods`, `constant`, `csv`, etc.

# EMHASS source mappings after EnergyPilot installation

After EnergyPilot is connected and its telemetry entities exist, configure EMHASS to use the EnergyPilot entities.

Typical mapping:

| EMHASS setting | GW EnergyPilot entity |
|---|---|
| `sensor_battery_state_of_charge` | `sensor.gw_energypilot_battery_state_of_charge` |
| `sensor_power_battery` | `sensor.gw_energypilot_battery_power` |
| `sensor_power_photovoltaics` | `sensor.gw_energypilot_pv_total_power` |
| `sensor_power_load_no_var_loads` | `sensor.gw_energypilot_total_load_power` |
| `sensor_power_photovoltaics_forecast` | normally `sensor.p_pv_forecast` |

Battery power convention:

```text
negative = charging
positive = discharging
```

Before using `sensor.gw_energypilot_total_load_power` for optimization, validate that it behaves correctly on your GoodWe firmware and operating modes.

If the home also has separate AC-coupled PV, use a combined PV sensor for EMHASS instead of only the ETA-connected PV total.

## Recommended EMHASS publish setting with v0.10

When the EnergyPilot native orchestrator owns the optimization/publish transaction, use:

```json
"continual_publish": false,
"optimization_time_step": 15
```

This lets EnergyPilot decide whether `publish-data` is allowed after checking the optimization result instead of unconditionally republishing an older plan after a failed optimization.

# Keep optimization separate from inverter control

EMHASS optimization can continue even when EnergyPilot Automatic Control is OFF.

```text
Automatic OFF
├── EnergyPilot keeps optimizing
├── EnergyPilot keeps publishing valid plans
└── GoodWe stays in GoodWe Auto / AI

Automatic ON
├── EnergyPilot keeps optimizing
├── EnergyPilot keeps publishing valid plans
└── EnergyPilot applies the current P_batt target
```

# Installation with HACS

1. Open HACS.
2. Open **Custom repositories**.
3. Add `https://github.com/SuperdaveNLD/GW_EnergyPilot`.
4. Select category **Integration**.
5. Install **GW EnergyPilot**.
6. Restart Home Assistant.
7. Go to **Settings -> Devices & services -> Add integration**.
8. Search for **GW EnergyPilot**.
9. Enter the GoodWe ETA Modbus TCP details.

Use a static IP address or DHCP reservation for the inverter.

Typical connection settings:

```text
Port:    502
Unit ID: 247
```

# Built-in dashboard

EnergyPilot registers its own Home Assistant sidebar panel.

The dashboard includes:

- compact animated PV / Home / Grid / Battery flow overview;
- Solar and PV string power;
- home and inverter power;
- grid import/export and three-phase measurements;
- battery SOC, power, voltage, current and temperature;
- EMS mode, setpoint, target and command;
- EMHASS target/status/forecast information;
- native orchestrator state and last-success information;
- **Optimize now** button;
- inverter/BMS health values;
- Automatic Control switch;
- draggable card ordering;
- per-card visibility toggles;
- flow-animation toggle;
- persistent browser-specific dashboard layout.

Temperature presentation follows the current Home Assistant temperature unit setting.

# GoodWe EMS mapping

EnergyPilot uses:

```text
Register 47511 = EMS mode
Register 47512 = EMS power setpoint
```

Main automatic-control mapping:

```text
P_batt < -deadband  -> mode 11 -> battery charge
inside deadband     -> mode 8  -> Battery Hold
P_batt > +deadband  -> mode 12 -> battery discharge
```

Disabling Automatic Control returns the inverter to:

```text
Mode 1 - GoodWe Auto / AI
Setpoint 0 W
```

Automatic Control restores its previous Home Assistant state after a reload/restart. First-time installs default to OFF. When restored ON, EnergyPilot still waits for valid EMHASS inputs before issuing a command.

## Tested EMS modes

| Mode | Name | Target |
|---:|---|---|
| 1 | GoodWe Auto / AI | GoodWe internal control |
| 2 | PV-priority charging | PV-priority strategy |
| 3 | PV + battery supply | PV-priority strategy |
| 4 | Inverter import / AC charging | inverter AC power |
| 5 | Inverter export power | inverter AC power |
| 6 | Reserve / Conserve | special mode |
| 7 | Off-grid | special mode |
| 8 | Battery Hold | battery power = 0 W |
| 9 | Grid import target | point of common coupling |
| 10 | Grid export target | point of common coupling |
| 11 | Battery charge power | direct battery charging |
| 12 | Battery discharge power | direct battery discharge |

# Native GoodWe telemetry

EnergyPilot reads GoodWe ETA telemetry directly through Modbus TCP. A separate Home Assistant `modbus:` sensor package is not required for EnergyPilot itself.

Telemetry includes PV strings, inverter values, smart-meter phase measurements, battery/BMS data, temperatures, load registers, EMS registers and diagnostic registers.

Lower-value or duplicate diagnostic entities are disabled by default and can be enabled manually when troubleshooting.

# Migration from v0.09 YAML orchestration

Do not leave two recurring EMHASS schedulers active at the same time and do not leave two systems writing GoodWe EMS registers.

Recommended v0.09 -> v0.10 migration:

```text
1. Update EnergyPilot to v0.10
2. Keep Automatic Control OFF
3. Verify the native Optimize now button exists
4. Press Optimize now and verify P_batt + Optimal
5. Remove/disable packages/energypilot_emhass_orchestrator.yaml
6. Restart/reload Home Assistant
7. Enable the built-in EnergyPilot orchestrator schedule
8. Press Optimize now once more
9. Enable Automatic Control
```

If the legacy script or automation is still loaded while the native schedule is enabled, EnergyPilot reports:

```text
legacy_yaml_detected
```

and does not start its recurring scheduler.

Old GoodWe EMS write automations and direct Modbus write scripts must also remain disabled after migrating control to EnergyPilot.

Energy counters, separate AC-PV helpers and unrelated EV logic may still be needed until those functions are migrated separately.

# Documentation

- `docs/EMHASS_SETUP.md`
- `docs/examples/energypilot_emhass_orchestrator.yaml` (v0.09 reference / migration aid)
- `docs/examples/README.md`
- EMHASS: https://emhass.readthedocs.io/
- Home Assistant developer documentation: https://developers.home-assistant.io/

# License

See `LICENSE`.
