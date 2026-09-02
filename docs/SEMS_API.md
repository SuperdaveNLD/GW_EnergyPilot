# SEMS+ API Beta telemetry

GW EnergyPilot v1.2.0-beta.3 can use either local Modbus TCP or the GoodWe
SEMS/SEMS+ portal as its coordinator-backed telemetry source.

This is a **Beta telemetry option**, not a cloud control transport and not an
EMHASS replacement. EMHASS remains the external optimizer. Every GoodWe EMS
mode/setpoint write and its read-back still use the configured local Modbus
host, port and unit ID.

## Configure

Open the EnergyPilot dashboard as a Home Assistant administrator and select:

```text
Configuration -> GoodWe data & control -> Telemetry source
```

Choose **SEMS+ API · Beta** and provide:

- the SEMS/SEMS+ account email;
- the account password;
- a station ID when the account can see multiple stations;
- an inverter serial when the station contains multiple inverters;
- a cloud refresh interval from 60 to 300 seconds.

When exactly one station and one inverter are visible, EnergyPilot resolves and
stores both identities during validation. It never silently selects the first
item from a multi-station or multi-inverter account.

A read-only visitor account is recommended. Sign in once through the official
portal/app first so any current EULA can be accepted. The password is stored in
the Home Assistant config entry, is never returned by the settings API and is
excluded from EnergyPilot debug/runtime reports. Leaving the password field
blank on a later save preserves the existing secret.

## Runtime boundary

```text
SEMS/SEMS+ API
    -> selected fresh inverter record
    -> supported telemetry subset
    -> EnergyPilot coordinator/entities/dashboard/orchestrator inputs

Local Modbus TCP
    -> EMS mode + setpoint read-back
    -> optional 45356/45358 SOC-floor read-back
    -> all EMS and verified minimum-SOC writes
```

The cloud snapshot must contain a valid inverter `last_time` no more than 15
minutes old. An older or future-dated sample fails the telemetry refresh instead
of being presented as live. Authentication is renewed once after an expired
token response. SEMS rate-limit code `GY0429` creates a local five-minute
back-off so the normal coordinator cannot hammer the service.

Runtime and control health remain separate. A valid cloud snapshot is retained
when the small local control read-back fails, but the connectivity entity shows
the Modbus control route as unreachable. Conversely, a successful local
read-back cannot turn a failed/stale SEMS refresh into successful telemetry.

## Mapped telemetry

Only an explicit, bounded subset is translated into existing EnergyPilot keys:

- PV total and PV1–PV4 voltage/current when present;
- inverter AC power, phase voltage/current/frequency and radiator temperature;
- power-flow load;
- `pmeter` grid power with the existing EnergyPilot sign convention;
- battery SOC/SOH, voltage/current, BMS current limits and power-flow battery
  power when the station explicitly reports a battery.

The SEMS power-flow battery direction is converted to the EnergyPilot contract:

```text
EnergyPilot battery power
negative = charging
positive = discharging
```

Sentinel/out-of-range values are omitted. Cloud lifetime energy totals, EMS
mode/settings, meter phase currents and unverified fields are deliberately not
mapped as substitutes for canonical GoodWe registers.

The portal can briefly return `soc: 0` as a placeholder while battery data is
transitioning. EnergyPilot rejects that sentinel, tries the selected inverter's
SOC field next and otherwise makes battery SOC unavailable. An unavailable SOC
blocks an EnergyPilot-owned EMHASS solve instead of initializing it at 0%.

At a multi-inverter station, station-wide power-flow PV/load/battery aggregates
are not mixed with the explicitly selected inverter. PV falls back to that
inverter's own value; station-wide load and battery power remain unavailable.

Consequences while SEMS+ is selected:

- entities outside the mapped subset become unavailable;
- persistent daily grid accounting pauses because no canonical lifetime-counter
  pair is present; it re-baselines safely when a valid local pair returns;
- phase-aware EV load balancing fails without a charger-limit write because the
  required GoodWe L1/L2/L3 meter currents are unavailable;
- local EMS control, manual actions and verified minimum-SOC transactions remain
  on Modbus and keep their existing write/read-back contract.

## Supported portal shape

The Beta currently supports the station response that contains
`inverter[].invert_full` and the legacy monitor-detail power-flow object.
SEMS+ station type 2 payloads that do not expose that shape are rejected with an
explicit error. Adding another portal shape requires captured, redacted payload
evidence and mapping tests; it must not be guessed from similarly named fields.

The implementation was informed by the maintained
`TimSoethout/goodwe-sems-home-assistant` project, including its newer SEMS+
cross-login, regional API-host normalization, visitor-account guidance, token
renewal and rate-limit handling. EnergyPilot intentionally does not copy its
undocumented inverter downtime/control switch.

## Troubleshooting

For a redacted raw/mapped comparison, open dashboard settings -> **LOG**, start
debug logging, reproduce one SEMS refresh and copy the debug report. Each SEMS
poll contains only an explicit allowlist of power-flow/inverter values, the
mapped EnergyPilot values and mapping decisions such as the selected/rejected
SOC source. Account, password, API token and arbitrary portal fields are never
included. The same credential-free summary is emitted at debug level by
`custom_components.gw_energypilot.sems_api` when Home Assistant debug logging
is enabled.

- **Authentication rejected:** verify account/password and accept the latest
  EULA in the official portal/app.
- **Multiple power stations/inverters:** enter the exact station ID and inverter
  serial instead of relying on auto-detection.
- **Station type 2 unsupported:** switch back to Local Modbus TCP and provide a
  redacted portal response with model/firmware details for review.
- **SEMS sample stale:** confirm that SEMS+ itself shows a recently updated
  inverter. Configuration validation tolerates an asleep/offline sample, but
  runtime polling does not present it as live.
- **Control unreachable:** SEMS telemetry does not remove the local Modbus
  requirement for GoodWe EMS control. Check the configured host, port and unit
  ID.
