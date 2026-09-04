# GW EnergyPilot user guide

This guide takes you from a safe first start to normal daily use. It is written
for the built-in EnergyPilot dashboard in Home Assistant.

[Nederlandse handleiding](HANDLEIDING_NL.md) · [Project overview](../README.md) ·
[Report a problem](https://github.com/SuperdaveNLD/GW_EnergyPilot/issues)

> GW EnergyPilot can command significant battery and grid power. Keep
> **Automatic Control OFF** until the live values, signs, EMHASS outputs and
> inverter response have all been checked for your installation.

## What EnergyPilot does

EnergyPilot connects four jobs that would otherwise be spread over different
screens and automations:

1. It reads GoodWe ETA-G20 telemetry locally, or optionally uses SEMS+ Beta for
   telemetry.
2. It asks an existing EMHASS installation to create and publish a plan.
3. It applies safety rules and the selected Battery, Grid or Hybrid strategy.
4. It sends the resulting EMS mode and setpoint to the inverter over local
   Modbus, then checks the inverter read-back.

SEMS+ is never used for control. EMHASS remains the plan owner and must be
installed separately.

## Before you begin

You need:

- Home Assistant 2026.8 or newer and HACS;
- a supported GoodWe ETA-G20 reachable over Modbus TCP;
- a fixed inverter IP address or DHCP reservation;
- EMHASS installed, running and configured if you want optimization;
- a price entity/source if you want price-aware planning.

The primary tested inverter is the **GoodWe GW15K-ETA-G20**. Other ETA-G20
models and firmware should be validated carefully.

Typical connection values are port `502` and Unit ID `247`. Use the actual
values for your inverter. Avoid running two integrations that continuously
poll or control the same Modbus interface.

## Install and connect

1. Install and start EMHASS first. Enable its start-on-boot and watchdog
   options.
2. Add this GitHub repository to HACS as an **Integration**, install GW
   EnergyPilot and restart Home Assistant.
3. In Home Assistant, go to **Settings → Devices & services → Add
   integration**, select **GW EnergyPilot** and enter the inverter connection.
4. Open **GW EnergyPilot** from the Home Assistant sidebar.
5. Leave **Automatic Control OFF**.
6. Open the dashboard gear and complete the **ENERGYPILOT**, **EMHASS** and
   **GOODWE** sections. Configure **EV** and **PV** only when needed.

The **?** in the dashboard header always returns to this guide. It follows the
Home Assistant language and opens the Dutch guide for Dutch sessions.

For the complete EMHASS parameter mapping, see [EMHASS setup](EMHASS_SETUP.md).

## Validate the installation safely

Do not enable automatic control until every item below is true.

### 1. Check live energy values

Compare the EnergyPilot dashboard with the inverter and electricity meter:

- PV production is plausible;
- Home load changes when a known appliance is switched on;
- Battery SOC matches the inverter;
- battery power is **negative while charging** and **positive while
  discharging**;
- GoodWe grid power is **negative while importing** and **positive while
  exporting**;
- phase currents and temperatures are plausible when available.

### 2. Check EMHASS output

Run **Optimize now** and confirm that:

- the optimizer reports ready/success;
- `P_batt` is finite and follows the battery sign convention;
- `P_grid` is finite when Grid or Hybrid control is selected;
- Battery · Plan · Price shows a current/future plan rather than invented zero
  values.

EMHASS grid power uses the opposite sign from the GoodWe meter:

```text
EMHASS P_grid: positive = planned import, negative = planned export
GoodWe meter:  negative = actual import, positive = actual export
```

### 3. Test one command manually

With automatic control still off, use a low, safe power value and one manual
EMS action. Confirm that the Controller card shows the expected mode, setpoint
and successful read-back. Stop if the inverter response does not match the
command.

### 4. Enable automatic control

Select the intended strategy, enable **Automatic Control** and watch the first
plan step. The Controller card should explain which plan value caused the
active GoodWe mode.

## Dashboard tour

- **Live energy flow** shows PV, home, grid and battery direction and power.
- **Battery** shows SOC, live battery power and the selected battery policy.
- **Controller** shows ownership, chosen strategy, GoodWe EMS mode, setpoint
  and read-back evidence.
- **Battery · Plan · Price** compares planned battery power, actual battery
  power and market price over 12, 24 or 36 hours.
- **Execution history** records plan decisions, safety overrides, writes and
  read-back evidence across the current runtime history.
- **Header connectivity** summarizes Modbus, EV charger and effective EV
  coordination health.
- **Layout & visibility** lets you reorder/hide cards and enable the optional
  live-flow particles. Reduced-motion preferences and the off setting stop
  those particles completely.
- **Gear** opens all configuration sections; **?** opens this manual.

## Choose an automatic-control strategy

### Battery

Use the planned battery power directly. Charge plans select GoodWe mode 11,
discharge plans mode 12 and a neutral plan mode 8 (Battery Hold). This is the
compatibility choice when a validated GoodWe smart meter is not available.

### Grid

Use the planned point-of-connection flow. Import plans select mode 9, export
plans mode 10 and a near-zero grid plan mode 1 (GoodWe Auto/self-use). Choose
this only with a working, correctly signed GoodWe smart meter.

### Hybrid

Hybrid first preserves an explicitly neutral battery plan with Battery Hold.
For non-neutral battery plans it follows the grid plan, using GoodWe Auto near
zero grid flow and modes 9/10 outside the grid deadband. This combines an
explicit battery-idle decision with GoodWe's fast local PCC control.

The two deadbands have different jobs: Battery Hold is evaluated against
`P_batt`; GoodWe Auto is evaluated against `P_grid`. The dashboard gear →
**GOODWE** section shows both settings.

## Battery profiles

EnergyPilot offers five managed policies:

- **Mad-Steve** — widest SOC use and most aggressive dispatch;
- **Gold Rush** — aggressive price response with more anti-churn resistance;
- **Chargegasm** — broad usable range with light preservation;
- **Balanced** — stronger SOC, throughput and power-stress protection;
- **Battery Saver** — lowest average SOC target and strongest preservation.

A managed profile applies its GoodWe minimum SOC and all owned EMHASS battery
settings as one rollback-safe transaction. **Custom** returns the SOC and cost
controls to you. Profiles are transparent optimizer preferences, not a battery
lifetime guarantee. Exact ranges and factors are in [Battery Saver](BATTERY_SAVER.md).

## Planning and prices

EnergyPilot runs full optimization on 15, 30 or 60-minute local wall-clock
boundaries; 15 minutes is recommended. It also publishes the due step from the
active plan. If both are due, the new optimization wins and supplies the only
publish for that boundary.

The last official EMHASS plan is mirrored for resilience. It is used only while
still valid and only when live publication is missing/unavailable. A reported
non-ready optimizer remains authoritative, and an expired last point is never
extended.

## EV features

**EV anti-discharge** prevents the home battery from discharging into an EV
that is currently charging. A legitimate home-battery charge plan remains
allowed. This feature does not control the charger.

Optional **EV load balancing** can adjust one charger current-limit entity to
softly protect the configured grid connection, using GoodWe phase currents and
a separate allocated-current feedback entity. It is best-effort coordination,
not fuse protection. Validate phase selection, connection rating, maximum
current and charger feedback before enabling it. See
[EV load balancing](EV_LOAD_BALANCING.md).

## Settings map

| Section | Main purpose |
|---|---|
| **ENERGYPILOT** | Core dashboard/orchestration and general integration choices |
| **EV** | Charging detection, anti-discharge health guard and optional load balancing |
| **EMHASS** | URL, schedule, output entities, pricing, load forecast and config check |
| **PV** | Display-only internal and external PV sources |
| **GOODWE** | Telemetry source, inverter identity and automatic-control/deadband choices |

Settings containing credentials never return the saved SEMS password to the
browser or diagnostic report.

## Daily operation

Normally, check three things:

1. Header connectivity is healthy.
2. Battery · Plan · Price contains a sensible upcoming plan.
3. Controller shows the expected ownership, mode and verified setpoint.

Use **Optimize now** after a meaningful price/configuration change when you do
not want to wait for the next boundary. Turn Automatic Control off before
testing hardware, changing metering topology or investigating an unexpected
sign/direction.

## Troubleshooting

| Symptom | What to check |
|---|---|
| No live values | Inverter IP, port/Unit ID, Modbus availability, selected telemetry source and duplicate pollers |
| SEMS+ unavailable | Internet access, station/inverter selection and timestamp freshness; local control health is separate |
| Optimize now fails | EMHASS is running, base URL is reachable from Home Assistant, required config is synchronized and SOC/prices are available |
| Plan visible but control waits | Optimizer readiness, fresh finite `P_batt`, and fresh finite `P_grid` for Grid/Hybrid |
| Unexpected import/export direction | Recheck the two different grid sign conventions before changing any control setting |
| EV coordination suspended | Charger-online source has been unavailable for the grace period; verify charger state and feedback |
| A setting will not save | Check the inline validation message; managed battery profiles intentionally lock their owned values |
| Dashboard looks stale after update | Reload the integration, clear/reload the Home Assistant frontend cache and confirm the installed version badge |

For support, open dashboard settings → **LOG**, start a debug session, reproduce
the problem briefly, stop it and copy the report. The buffer is memory-only and
credential-free. Attach the report together with Home Assistant version,
inverter model/firmware, battery model and smart-meter details to a
[GitHub issue](https://github.com/SuperdaveNLD/GW_EnergyPilot/issues).

## Safety and limitations

- GoodWe/BMS protections and configured hardware limits remain authoritative.
- Never infer or change register meanings without hardware/vendor evidence.
- Minimum-SOC changes are written and read back locally before the matching
  EMHASS value is accepted.
- Persistent accounting uses coherent GoodWe counter pairs; charts are not a
  billing meter.
- SEMS+ remains optional Beta telemetry and is not an EMS transport.
- EMHASS is an external prerequisite; EnergyPilot does not install or replace
  it.

For exact technical contracts, continue with [Architecture](ARCHITECTURE.md),
[EMS modes](EMS_MODES.md), [EMHASS plan resilience](EMHASS_PLAN_RUNTIME.md) and
[Settings/security](SETTINGS.md).
