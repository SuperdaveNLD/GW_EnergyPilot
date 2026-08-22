# GW EnergyPilot examples

## EMHASS orchestrator

The tested local EMHASS orchestration package is available here:

- [`energypilot_emhass_orchestrator.yaml`](energypilot_emhass_orchestrator.yaml)

Copy the complete file to your Home Assistant configuration, for example:

```text
/config/packages/energypilot_emhass_orchestrator.yaml
```

The orchestrator:

- runs a new EMHASS day-ahead optimization every 15 minutes;
- remains independent from the EnergyPilot Automatic Control switch;
- uses the current EnergyPilot battery SOC as `soc_init`;
- builds a load forecast from Home Assistant Recorder statistics;
- validates the EMHASS HTTP response before publishing;
- publishes only after a successful optimization;
- validates that a fresh `sensor.p_batt_forecast` was created;
- never writes GoodWe Modbus registers directly.

Keep GW EnergyPilot as the only component that writes GoodWe EMS mode/setpoint registers.

### Price source

The validated reference YAML currently uses a price entity exposing `raw_today` and `raw_tomorrow` because that is the setup used during development. Change the `price_entity` variable when your installation uses another price source.

For new installations, Home Assistant's official Nord Pool integration is preferred. Its `nordpool.get_prices_for_date` action returns timestamped price intervals and is compatible with the transition to 15-minute market time units. A future EnergyPilot orchestrator revision can use that action directly.

See [`../EMHASS_SETUP.md`](../EMHASS_SETUP.md) for the required EnergyPilot-to-EMHASS entity mappings and installation order.
