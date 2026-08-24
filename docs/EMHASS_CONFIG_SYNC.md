# EMHASS configuration synchronization

GW EnergyPilot requires EMHASS to be installed and configured separately. EnergyPilot does not install EMHASS.

## Restore recommended defaults

The EMHASS settings page exposes **Restore recommended defaults**. This only fills the GW EnergyPilot settings form with the current recommended values for review. It does not save automatically.

Canonical EnergyPilot outputs are:

- `sensor.p_batt_forecast`
- `sensor.p_grid_forecast`
- `sensor.optim_status`
- required optimization state `Optimal`

## Synchronize required config

**Synchronize required config** is an explicit administrator action. It reads the complete live EMHASS configuration, changes only the mappings required by EnergyPilot, writes the complete merged configuration, then reads it back for verification.

The runtime resolves the actual Home Assistant entity IDs for EnergyPilot PV total power, GoodWe load power, battery power and battery SOC from the entity registry. Renamed entity IDs are therefore respected.

Managed EMHASS values are the required input sensor mappings, compatible interpolation/zero-replacement lists, compatible `var_model`, `continual_publish = false`, `method_ts_round = first`, and the PV/battery/hybrid enable flags.

Unrelated EMHASS configuration is preserved. Existing custom PV forecast entities are preserved. Custom `var_model` values are preserved with a warning. Multi-battery power/SOC lists are not rewritten because EnergyPilot cannot safely infer per-battery ownership.

Synchronization does not write any GoodWe register and does not automatically launch an optimization. After a successful synchronization, run a fresh optimization before enabling Automatic Control.

## Flow animation regression guard

The v0.28 consolidated frontend also makes the geometry-specific v0.13 particle keyframes authoritative by forcing `animation-direction: normal` on the flow particles. Later semantic frontend layers must not reverse those already-correct direction keyframes a second time.
