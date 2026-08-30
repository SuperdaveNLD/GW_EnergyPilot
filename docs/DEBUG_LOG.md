# Debug logging

GW EnergyPilot v0.31 adds an opt-in debug session to the dashboard **LOG** tab for problem analysis.

## Purpose

The existing optimization log remains a persistent, bounded history of EnergyPilot-owned EMHASS optimization attempts. It is useful for optimizer history, but it is intentionally not a general runtime trace.

The debug session is a separate support facility. It observes the existing runtime and correlates the information needed to diagnose control, telemetry and EMHASS problems without adding another control path.

## Operator workflow

1. Open the GW EnergyPilot dashboard settings and select **LOG**.
2. Select **Start debug logging**.
3. Reproduce the problem.
4. Select **Stop debug logging**.
5. Select **Copy debug report** and attach the copied JSON to the support issue.
6. Clear the captured data when it is no longer needed.

Starting debug logging always begins a fresh session. Stopping capture retains the completed session in memory so it can still be copied.

## Captured information

A session starts with a complete baseline and then records existing runtime signals:

- all decoded GoodWe telemetry values from the canonical `registers.py` definitions;
- canonical register address/type/scale metadata so support can map each decoded value back to its register definition;
- coordinator poll success/failure, latest exception and Modbus connection state;
- controller enabled state, configured strategy, command, requested target, expected mode and actual GoodWe mode/setpoint read-back;
- configured `P_batt`, `P_grid`, optimization-status and optional EV source state changes;
- canonical Modbus/charger reachability, requested/effective EV coordination and one-shot connectivity loss/restoration/suspension/resume transitions;
- EMHASS/orchestrator status transitions, HTTP result diagnostics already exposed by the orchestrator, pricing/load-forecast metadata and the latest optimizer error;
- current Home Assistant core state and configured time zone;
- the existing persistent optimization history when **Copy debug report** is used.

This design deliberately reuses the coordinator, controller dispatcher and orchestrator dispatcher. Debug logging does not poll the inverter separately and does not run an additional control loop.

Connectivity transitions are also written to the normal Home Assistant log even when the opt-in debug session is off. Loss and suspension use warning level; restoration, resume and user cancellation use info level.

## Storage and limits

Debug capture is **off by default** and administrator-only.

The event buffer is memory-only and bounded to the newest **1200 events**. When the buffer is full, the oldest event is discarded and `dropped_events` is incremented. Debug data is not written to Home Assistant `Store`, Recorder or the config entry.

The buffer is discarded when the integration unloads/reloads or Home Assistant restarts.

The existing optimization history remains independently persistent and keeps its current 50-run limit.

## Privacy and support scope

The debug report intentionally excludes the configured GoodWe host/IP address and the EMHASS base URL. It includes configured entity IDs and their diagnostic state values because those are required to identify incorrect mappings and stale/unavailable inputs.

No Home Assistant access tokens, passwords or arbitrary entity attributes are collected.

## Safety

Debug logging is observer-only:

- it does not add, remove or change GoodWe registers;
- it does not change the Modbus polling interval;
- it does not write EMS mode/setpoint registers;
- it does not change automatic/manual control ownership;
- it does not trigger an optimization;
- it does not change EMHASS configuration;
- it does not create new Home Assistant entities or unique IDs.

The canonical GoodWe register source remains `custom_components/gw_energypilot/registers.py`.
