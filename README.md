<p align="center">
  <img src="custom_components/gw_energypilot/brand/logo.png" alt="GW EnergyPilot" width="180">
</p>

# GW EnergyPilot

GW EnergyPilot is an unofficial Home Assistant integration for advanced EMS and battery control of GoodWe ETA hybrid inverters.

It provides direct Modbus TCP telemetry and control, EMHASS `P_batt` mapping, Battery Hold, manual EMS control, optional EV coordination, and a built-in EnergyPilot dashboard.

> This is an independent community project and is not affiliated with or endorsed by GoodWe.

## Current status

**Alpha - v0.09**

v0.09 adds the tested EMHASS orchestration reference, prefilled EMHASS controller entities, and the existing v0.08 dashboard/controller improvements.

Forced EMS modes can charge or discharge a battery at high power and can export energy to the grid. Verify inverter, battery and grid limits before enabling Automatic Control.

## Version numbering

GW EnergyPilot uses simple incremental versions:

```text
v0.01
v0.02
v0.03
...
v0.08
v0.09
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
8. Run EMHASS optimization + publish
9. Verify sensor.p_batt_forecast and sensor.optim_status
10. Enable EnergyPilot Automatic Control
```

The final data path is:

```text
GoodWe ETA
    │ Modbus TCP
    ▼
GW EnergyPilot telemetry
    │
    ▼
EMHASS optimization
    │ sensor.p_batt_forecast
    ▼
GW EnergyPilot controller
    │
    ▼
GoodWe EMS modes 8 / 11 / 12
```

## EMHASS controller defaults in v0.09

The EnergyPilot setup screen now pre-fills the standard EMHASS outputs:

```text
P_batt entity               sensor.p_batt_forecast
Optimization status         sensor.optim_status
Required optimization state Optimal
Maximum inverter power      15.0 kW
Power deadband              300 W
Modbus scan interval        10 s
EV coordination             OFF
```

If `sensor.p_batt_forecast` does not exist yet during first setup, EnergyPilot simply waits. It starts reacting automatically after EMHASS publishes a valid numeric value.

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

# v0.09 EMHASS orchestrator reference

v0.09 includes the tested local orchestration package used during development:

```text
docs/examples/energypilot_emhass_orchestrator.yaml
```

Documentation:

```text
docs/examples/README.md
docs/EMHASS_SETUP.md
```

The reference orchestrator:

- runs a fresh day-ahead optimization every 15 minutes;
- runs independently from the EnergyPilot Automatic Control switch;
- uses current EnergyPilot battery SOC as `soc_init`;
- builds a load forecast from Home Assistant Recorder statistics;
- validates the EMHASS HTTP response;
- only calls `publish-data` after a successful optimization;
- checks that a fresh `sensor.p_batt_forecast` was published;
- never writes GoodWe Modbus registers.

The tested reference currently uses a price entity with `raw_today` / `raw_tomorrow` attributes. For a public/general setup, prefer Home Assistant's official Nord Pool integration and its `nordpool.get_prices_for_date` action. The official integration can change automatically between hourly and 15-minute market time units, so price handling should not assume exactly 24 hourly values.

## Keep optimization separate from inverter control

EMHASS optimization must continue even when EnergyPilot Automatic Control is OFF.

```text
Automatic OFF
├── EMHASS keeps optimizing
├── EMHASS keeps publishing
└── GoodWe stays in GoodWe Auto / AI

Automatic ON
├── EMHASS keeps optimizing
├── EMHASS keeps publishing
└── EnergyPilot applies the current P_batt target
```

Do not gate recurring EMHASS optimization behind an old GoodWe/EMHASS master `input_boolean` when migrating from a YAML-based system.

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

# Migration from older YAML control

Do not leave two systems writing GoodWe EMS registers at the same time.

Recommended migration:

```text
1. Install EnergyPilot and validate telemetry
2. Change EMHASS source mappings to EnergyPilot
3. Validate optimization + publish
4. Let EnergyPilot consume p_batt_forecast
5. Disable old GoodWe EMS write automations/scripts
6. Remove old Modbus YAML only after nothing else depends on it
```

Energy counters, separate AC-PV helpers and unrelated EV logic may still be needed until those functions are migrated separately.

# Documentation

- `docs/EMHASS_SETUP.md`
- `docs/examples/energypilot_emhass_orchestrator.yaml`
- `docs/examples/README.md`
- EMHASS: https://emhass.readthedocs.io/
- Home Assistant developer documentation: https://developers.home-assistant.io/

# License

See `LICENSE`.
