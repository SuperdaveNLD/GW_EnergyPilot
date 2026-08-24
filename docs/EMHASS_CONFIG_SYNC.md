# EMHASS configuration synchronization

GW EnergyPilot keeps two different configuration layers deliberately separate:

```text
EnergyPilot ConfigEntry options    connection, schedule and output entity mapping
EMHASS config.json                 optimizer input/model configuration
```

The EMHASS settings page provides two explicit administrator actions.

## Restore recommended EnergyPilot defaults

**Restore recommended defaults** fills the EMHASS settings form with the current EnergyPilot recommendations. It does not save immediately; the operator can review the values and then use the normal **Save changes** action.

Recommended output mapping:

```text
P_batt output entity          sensor.p_batt_forecast
P_grid output entity          sensor.p_grid_forecast
Optimization status entity    sensor.optim_status
Required optimization state   Optimal
```

The standard starting values also include the configured EMHASS add-on URL, a 60-minute optimization interval, 10% runtime final SOC target, 700 W fallback load, runtime Nord Pool pricing enabled, EUR currency, zero import-price adder and the canonical export deduction.

These are starting values, not universal battery/tariff limits. Installation-specific values still require operator review.

## Synchronize required EMHASS config

**Synchronize required config** reads the complete active EMHASS configuration through `/get-config`, calculates the minimal required patch, writes the complete merged configuration through `/set-config`, and reads the configuration back for verification.

No separate configuration file or EnergyPilot settings database is created.

The sync resolves current Home Assistant entity IDs from the EnergyPilot entity registry. Renamed entity IDs are therefore used instead of guessed defaults.

Managed values:

```text
sensor_power_photovoltaics
sensor_power_load_no_var_loads
sensor_power_battery
sensor_battery_state_of_charge
sensor_power_photovoltaics_forecast
sensor_replace_zero
sensor_linear_interp
var_model (only when it follows the primary load mapping)
continual_publish = false
method_ts_round = first
set_use_pv = true
set_use_battery = true
inverter_is_hybrid = true
```

The PV forecast entity is preserved when a non-empty custom value already exists. When it is missing, the normal EMHASS output `sensor.p_pv_forecast` is used.

Existing extra entries in `sensor_replace_zero` and `sensor_linear_interp` are preserved. References to the previous primary PV/load mapping are replaced with the current EnergyPilot entity IDs.

A custom `var_model` is preserved and reported as a warning. EnergyPilot does not overwrite an intentionally separate machine-learning model input.

When EMHASS is configured with more than one battery, EnergyPilot does not replace per-battery power/SOC sensor lists because one aggregate GoodWe telemetry source cannot safely be expanded into multiple battery inputs.

## Safety boundaries

- Administrator access is required.
- The complete current EMHASS configuration is fetched before every write.
- Unrelated EMHASS settings are preserved.
- The write is verified with a second `/get-config` read.
- No GoodWe register is written.
- No optimization is started automatically.
- After synchronization, run **Optimize now** and verify fresh numeric outputs before enabling Automatic Control.

This feature does not install EMHASS and does not replace installation-specific battery capacity, inverter limits, PV model, tariff or deferrable-load configuration.
