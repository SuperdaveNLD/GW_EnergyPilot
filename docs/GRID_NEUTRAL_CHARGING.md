# Grid-neutral charging feedback

GW EnergyPilot v0.19 includes the grid-neutral charging execution path originally developed in PR #15. The purpose is to prevent a forecast miss from turning a planned PV charge into unintended grid import.

## Root cause

EMHASS can legitimately produce a plan where:

```text
P_batt < 0       battery should charge
P_grid ~= 0      no meaningful grid import/export was planned
```

If forecast PV is higher than real PV, blindly applying `abs(P_batt)` as a fixed GoodWe mode-11 charge setpoint can make the inverter import the missing energy from the grid. This is especially visible with external AC-coupled PV that is not represented by the GoodWe PV input registers.

## Execution model

EnergyPilot keeps EMHASS as the source of battery direction and maximum requested charge power. When EMHASS requests charging and its configured `P_grid` output is near zero, the requested `abs(P_batt)` becomes a **charge cap** rather than an unconditional setpoint.

The controller then uses the already-polled GoodWe smart-meter power (`36008`) as slow feedback:

- feedback interval: 30 seconds;
- grid import causes an immediate reduction of the mode-11 charge setpoint;
- upward charge movement is limited to 1 kW per feedback tick;
- if charging must stop, the controller enters Battery Hold for at least 120 seconds;
- after that hold, two consecutive feedback samples with clear export are required before charging can restart;
- if the required `P_grid` or live meter feedback is unavailable, the grid-neutral path fails safe to Battery Hold.

Normal GoodWe telemetry keeps its configured polling cadence; the feedback loop reuses coordinator data and does not add a second Modbus polling stream.

## Intentional grid charging

A meaningful non-zero EMHASS `P_grid` target is treated as an intentional grid-flow plan. In that case EnergyPilot preserves the existing direct `P_batt` mode-11 execution instead of applying the grid-neutral limiter.

## Configuration

The EMHASS `P_grid` output entity is configurable. The default is:

```text
sensor.p_grid_forecast
```

The setting is stored in the existing GW EnergyPilot config entry and is available through the normal options/settings paths.

## Control boundary

Grid-neutral charging does **not** change the overall ownership model:

- EMHASS still determines charge/discharge direction;
- Automatic Control remains the only automatic GoodWe EMS writer;
- discharge execution remains unchanged;
- manual battery actions remain unchanged;
- EV hold behavior remains unchanged;
- no new GoodWe register definitions are introduced;
- GoodWe PV-priority mode 2 is not used;
- bidirectional grid-target mode 9 does not become the automatic owner;
- EMS mode/power registers remain `47511` and `47512` with the existing write ordering.

## Diagnostics

The support snapshot exposes the configured `P_grid` entity/value and grid-neutral runtime state, including charge cap, last meter power, hold time and restart evidence. The dashboard also shows a short notice while a grid-neutral command is active.

This behavior is intentionally separate from the G20 `45356/45358` minimum-SOC field-test controls and from the v0.19 SOC/constraint diagnostics.
