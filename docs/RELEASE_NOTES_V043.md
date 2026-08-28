# GW EnergyPilot v0.43 Beta

## Summary

v0.43 hardens Home Assistant restart recovery for the built-in EMHASS orchestrator.

EnergyPilot already waits 60 seconds after integration setup before requesting an initial EMHASS optimization. If that first startup optimization fails because GoodWe telemetry, EMHASS, Recorder, Nord Pool or another startup dependency is not ready yet, v0.43 now performs a bounded retry sequence after 15, 30 and 60 seconds.

The existing persistent EMHASS plan remains available as the restart resilience path while live `P_batt` / `P_grid` publication is rebuilding. The dashboard warning that live EMHASS output is not detected is intentionally unchanged; a successful startup optimize + publish causes the live output to return and the warning to disappear normally.

## Behavior

- The inherited initial startup optimization remains delayed by 60 seconds.
- Failed startup optimizations retry after 15, 30 and 60 seconds, then stop.
- Startup attempts use `reason=startup` in optimization diagnostics/logging.
- If another optimization succeeds before the startup callback runs, the startup optimization is skipped to avoid a duplicate solve/publish cycle.
- If Automatic EMHASS orchestration is disabled, no startup optimization is performed.
- The normal recurring optimization schedule and Nord Pool price-triggered optimization remain unchanged.

## Safety and compatibility

- No GoodWe Modbus register, EMS mode, setpoint mapping or write order changes.
- No Automatic Control strategy mapping changes.
- No entity ID, unique ID, device identifier, config-entry key or persistent Store key changes.
- No change to EMHASS plan ownership or persistent-plan stale-horizon protection.
- A failed startup retry does not clear a still-valid persistent EMHASS plan.
- Existing manual and scheduled optimization paths continue to use the same canonical `async_optimize()` implementation.

## Validation scope

Regression coverage includes:

- A failed startup optimization schedules the first retry.
- A successful startup optimization schedules no retry.
- A successful non-startup optimization before the startup callback suppresses the duplicate startup solve.
- Retry backoff is bounded to 15, 30 and 60 seconds.

Release validation requires the repository Quality workflow plus HACS and Hassfest on the final release head.
