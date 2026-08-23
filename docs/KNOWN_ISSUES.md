# Known issues

This document records field issues that affect a GW EnergyPilot installation but are not necessarily caused by GW EnergyPilot itself.

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
