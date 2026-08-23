# Known issues

This document records field issues that affect a GW EnergyPilot installation but are not necessarily caused by GW EnergyPilot itself.

## Negative GoodWe load register on a secondary tester

### Field observation

A secondary v0.19 tester reported a live state with approximately:

```text
GoodWe load 35172       -4.56 kW
Load phase sum          -4.56 kW
GoodWe PV                  0 W
Grid                    +2.15 kW export
Battery                 -2.18 kW charging
System power balance    -4.32 kW
```

This differs from the reference **GW15K-ETA-G20** installation, where register `35172` and the three load-phase values behave as positive total house/load demand.

The secondary observation is consistent with a different electrical topology or measurement boundary, for example generation behind the GoodWe meter that is not represented by the inverter's own PV inputs. That explanation is **not yet confirmed**; exact inverter model, firmware, meter topology and any AC-coupled/secondary PV equipment must be collected before changing the canonical register interpretation.

### Impact on native EMHASS load forecasting

The current native EnergyPilot load-forecast path rejects negative `35172` current/history values as invalid household demand and uses the configured fallback load when no usable positive value is available. In the observed snapshot the fallback was `700 W`.

A tester who sees sustained negative `35172` should therefore **not assume the native load forecast represents real household consumption** until the topology is understood. Keeping the EnergyPilot orchestrator in `manual_only` avoids using that fallback as an EnergyPilot-generated optimization input.

Do not invert, clamp or globally reinterpret register `35172` solely from this one installation. Report:

- exact inverter model and firmware;
- smart-meter model/topology;
- whether another/AC-coupled PV inverter or other generation source exists;
- GoodWe `35172`, load-phase values, grid power, battery power and PV power from the same timestamp.

## SEMS / SEMS+ with the official GoodWe plugin or integration

### Symptom

When SEMS / SEMS+ is in use, the official GoodWe plugin or integration can conflict with the inverter registration/session. In affected installations the inverter may repeatedly disappear from, or be removed from, the GoodWe/SEMS software environment.

This is treated as a GoodWe/SEMS integration issue rather than a GW EnergyPilot Modbus-register issue.

### Recommendation

If you depend on SEMS / SEMS+:

- do **not** use the official GoodWe plugin/integration for the SEMS connection;
- prefer a community/custom GoodWe integration that reads the inverter through the **SEMS API**;
- keep GW EnergyPilot's local Modbus TCP connection separate from the SEMS cloud/API integration;
- avoid running multiple integrations that continuously poll the same local Modbus TCP endpoint when that is not required.

GW EnergyPilot itself communicates locally with the inverter over Modbus TCP. A SEMS API integration is therefore complementary: it can provide SEMS/cloud information without taking over GW EnergyPilot's local EMS control path.

### Troubleshooting

If an inverter starts disappearing from GoodWe/SEMS software:

1. disable the official GoodWe plugin/integration first;
2. recover or re-add the inverter in SEMS / SEMS+ if necessary;
3. use a custom GoodWe integration based on the SEMS API for SEMS/cloud data;
4. keep only the integrations that are actually needed for continuous local polling.

When reporting this behaviour, mention that SEMS / SEMS+ is involved and list every active GoodWe-related integration. This helps separate a GoodWe/SEMS account or plugin problem from a GW EnergyPilot local Modbus problem.
