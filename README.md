# GW EnergyPilot

GW EnergyPilot is an unofficial Home Assistant integration for advanced EMS and battery control of GoodWe ETA hybrid inverters.

It provides direct Modbus TCP control of the GoodWe EMS registers, optional EMHASS `P_batt` mapping, battery hold logic, manual EMS mode control, and optional EV charging coordination.

> This is an independent community project and is not affiliated with or endorsed by GoodWe.

## Current status

**Early alpha - v0.1.0**

The project is being built from practical testing on a GoodWe ETA installation. Use it only if you understand the impact of forced charge, discharge, export and off-grid modes.

## Tested EMS model

EnergyPilot uses:

- Register `47511`: EMS mode.
- Register `47512`: EMS power setpoint.

| Mode | EnergyPilot name | Control target |
|---:|---|---|
| 1 | GoodWe Auto / AI | GoodWe internal control |
| 2 | PV-priority charging | PV-priority strategy |
| 3 | PV + battery supply | PV-priority strategy |
| 4 | Inverter import / AC charging | Inverter AC power |
| 5 | Inverter export power | Inverter AC power |
| 6 | Reserve / Conserve | Special mode |
| 7 | Off-grid | Special mode |
| 8 | Battery Hold | Battery power = 0 W |
| 9 | Grid import target | Point of common coupling |
| 10 | Grid export target | Point of common coupling |
| 11 | Battery charge power | Battery power |
| 12 | Battery discharge power | Battery power |

## EMHASS mapping

When automatic control is enabled and a `P_batt` entity is configured:

- Negative `P_batt` outside the deadband -> mode 11, charge battery.
- `P_batt` inside the deadband -> mode 8, Battery Hold.
- Positive `P_batt` outside the deadband -> mode 12, discharge battery.
- Disabling automatic control -> mode 1, GoodWe Auto / AI.

The automatic control switch intentionally starts **off after a Home Assistant restart**.

## EV coordination

EV coordination is optional. In v0.1.0 it uses a conservative safety strategy: while the configured EV is actively charging, EnergyPilot puts the battery in mode 8 (Battery Hold). More advanced house-load compensation is planned for a later release.

An EV is considered active if either:

- its mode entity equals `connected_charging`, or
- its charging power is above the configured EV threshold.

## Installation with HACS

Until the repository is included in the default HACS store:

1. Open HACS.
2. Open **Custom repositories**.
3. Add `https://github.com/SuperdaveNLD/GW_EnergyPilot`.
4. Select category **Integration**.
5. Install **GW EnergyPilot**.
6. Restart Home Assistant.
7. Go to **Settings -> Devices & services -> Add integration**.
8. Search for **GW EnergyPilot**.

## Configuration

The setup flow asks for:

- GoodWe inverter host/IP.
- Modbus TCP port, normally `502`.
- Modbus Unit ID, commonly `247` on ETA installations.

Optional controller settings:

- EMHASS `P_batt` entity.
- Optimization status entity and required state.
- Maximum battery power.
- Deadband.
- EV mode and power entities.

## Safety

Forced EMS modes can charge or discharge a battery at high power and can export energy to the grid. Verify inverter limits, battery limits, grid connection limits and local regulations before enabling automatic control.

## Roadmap

- [x] HACS-ready custom integration structure.
- [x] Direct Modbus TCP connection.
- [x] EMS mode and setpoint sensors.
- [x] Manual EMS mode control.
- [x] EMHASS `P_batt` mapping to modes 8/11/12.
- [x] Automatic-control master switch with mode 1 fallback.
- [x] Basic EV charging coordination.
- [ ] Full ETA telemetry entities.
- [ ] Advanced EV house-load compensation.
- [ ] Diagnostics download.
- [ ] Automated tests.
- [ ] Dashboard example.
- [ ] Stable v1.0 release.

## License

MIT
