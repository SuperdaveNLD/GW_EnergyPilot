# GW EnergyPilot examples

## EMHASS orchestrator YAML - v0.09 reference

The tested local EMHASS orchestration package is retained here as a migration/reference example:

- [`energypilot_emhass_orchestrator.yaml`](energypilot_emhass_orchestrator.yaml)

Starting with **GW EnergyPilot v0.10**, normal installations should use the native EnergyPilot EMHASS orchestrator and the **Optimize now** button instead of copying this package into `/config/packages/`.

The old YAML reference demonstrated the design that was moved into the integration:

- recurring EMHASS day-ahead optimization;
- optimization independent from Automatic Control;
- current EnergyPilot battery SOC as `soc_init`;
- Recorder-based load forecast;
- HTTP response validation before publishing;
- publish only after a successful optimization;
- validation of a fresh numeric `sensor.p_batt_forecast`;
- no direct GoodWe Modbus writes.

Keep GW EnergyPilot as the only component that writes GoodWe EMS mode/setpoint registers.

### v0.10 migration

If this package is currently installed:

```text
1. Update GW EnergyPilot to v0.10
2. Keep Automatic Control OFF
3. Test the native Optimize now button
4. Verify P_batt + Optimal
5. Remove/disable this YAML package
6. Restart/reload Home Assistant
7. Enable the native EnergyPilot recurring orchestrator schedule
8. Test Optimize now again
9. Enable Automatic Control
```

Current EnergyPilot detects the enabled legacy
`automation.energypilot_emhass_orchestrator` and prevents its native recurring
schedule from starting next to it. The manual legacy optimize-now script alone
is not a scheduler, and a disabled automation does not compete.

### Price source

This historical YAML uses a price entity exposing `raw_today` and `raw_tomorrow` because that was the development setup.

The v0.10 native orchestrator can instead call Home Assistant's official `nordpool.get_prices_for_date` action directly and handles the returned timestamped intervals, including the market transition between hourly and 15-minute MTUs.

See [`../EMHASS_SETUP.md`](../EMHASS_SETUP.md) for the current setup and migration instructions.
