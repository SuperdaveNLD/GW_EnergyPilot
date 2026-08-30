# Home Assistant entity contract

This document describes the stability rules and major entity groups exposed by GW EnergyPilot.

The live code remains authoritative. Entity definitions currently live mainly in:

- `sensor.py`
- `switch.py`
- `number.py`
- `select.py`
- `button.py`

## Stability rule

Existing `unique_id` values are part of the migration contract with Home Assistant.

Do not rename or regenerate them casually. Changing a unique ID can create duplicate entities, lose user customizations, and split Recorder history.

Current general pattern:

```text
{config_entry_id}_{entity_key}
```

If a unique ID must change, implement an explicit entity-registry migration.

### Device identity

Entity unique IDs and Home Assistant device identity are separate contracts.

v0.17 migrates the EnergyPilot device identifier from the legacy mutable connection key:

```text
{host}:{slave}
```

to the stable config-entry ID. The migration is performed before platform entities are set up so changing a validated GoodWe host or unit ID through the settings page does not intentionally create a second device.

## Core telemetry sensors

Important enabled-by-default telemetry includes concepts such as:

- PV total power;
- PV string power;
- GoodWe load power (`35172`);
- battery power;
- battery SOC/SOH;
- battery voltage/current;
- BMS limits and key temperatures;
- grid power (`36008`);
- cumulative grid import/export energy;
- grid phase voltage/current.

A number of raw or diagnostic values are intentionally disabled by default.

## Connectivity status sensor

The enabled diagnostic enum sensor uses stable unique-ID suffix:

```text
{config_entry_id}_connectivity_status
```

Its states are `checking`, `all_ok` and `issue`. It remains available when a GoodWe poll fails so it can report Modbus unreachability rather than disappearing with coordinator-backed telemetry. Attributes expose the coordinator-derived Modbus status and configured refresh interval, optional charger reachability, requested/effective EV coordination, five-minute transition state/countdown and last Modbus success/failure/error evidence.

The sensor does not poll or control either device. The dashboard header pill consumes this single entity and patches its existing DOM node on state changes.

## Combined PV insight sensor

The read-only PV insight feature adds one aggregate entity with stable unique-ID suffix:

```text
{config_entry_id}_pv_generation_power
```

The entity uses device class `power`, unit `W` and state class `MEASUREMENT`. By default it mirrors the existing canonical GoodWe `pv_total_power`. When **Include external PV** is enabled, it adds each currently valid selected non-negative W/kW/MW/mW reading. Disabling external PV preserves the selections but excludes them from the entity.

Attributes expose the internal contribution, external contribution, configured/available source counts and a per-source breakdown. The aggregate is `display_only`: it is not a controller input, EMHASS input, persistent energy counter or grid-accounting source. Selected external entities retain their own identity and Recorder history; EnergyPilot does not create a duplicate entity per source.

See `docs/PV_INSIGHT.md` for validation, availability and dashboard-topology behavior.

## Power semantics

### Grid

Primary GoodWe grid telemetry uses `meter_total_power_fast` / register `36008`:

```text
negative = import
positive = export
```

EMHASS `P_grid` uses the opposite sign convention:

```text
positive = planned import
negative = planned export
```

Do not interchange these two values without applying their documented conventions.

### Battery

GoodWe battery telemetry and EMHASS `P_batt` use:

```text
negative = charging
positive = discharging
```

### Home/load

The primary Home/load telemetry is GoodWe register `35172` (`total_load_power`).

Do not substitute the calculated system balance as the Home/load entity without an intentional architecture change.

Field testing with an external AC-coupled PV inverter has shown that `35172` can become negative while that inverter exports through the GoodWe measurement point. The current orchestrator rejects implausible/negative load values and can therefore fall back to its configured fallback load. Correct AC-coupled load reconstruction is a separate architecture issue from v0.18 grid-neutral charge execution.

## Cumulative energy sensors

The current canonical GoodWe grid counters are exposed as Home Assistant energy sensors with `TOTAL_INCREASING` state class:

- grid energy imported total (`36017`);
- grid energy exported total (`36015`).

Preserve their units, device classes, state classes, and unique IDs to protect long-term statistics.

The v0.16+ extended `36104/36120` values remain Beta diagnostics and are deliberately **not** separate Recorder-facing canonical energy entities yet.

### Persistent daily grid accounting

v0.23 adds two EnergyPilot-owned daily accounting entities derived from the canonical lifetime counters above:

| Stable unique-ID suffix | Display name | Unit | State class | Source |
|---|---|---|---|---|
| `grid_energy_imported_today` | Grid energy imported today | kWh | `TOTAL_INCREASING` | `meter_total_energy_import` / `36017` |
| `grid_energy_exported_today` | Grid energy exported today | kWh | `TOTAL_INCREASING` | `meter_total_energy_export` / `36015` |

These are **derived accounting entities**, not alternative GoodWe meter-register interpretations. They do not replace or duplicate the physical lifetime counters.

Contract:

- one persistent accounting runtime exists per GW EnergyPilot config entry;
- live values are accumulated from positive differences between consecutive canonical GoodWe lifetime-counter samples;
- a lifetime-counter decrease re-baselines the source and is not treated as negative energy;
- `last_period` exposes the previous completed local-day value when known;
- accounting state survives Home Assistant restarts through Home Assistant storage;
- Recorder may be used once to bootstrap an existing installation at local-midnight boundaries, but Recorder is not part of the live delta loop;
- the dashboard consumes these entities instead of implementing a second daily accounting algorithm;
- future import-cost/export-revenue accounting must consume the same accounting deltas rather than reconstructing energy independently.

See `docs/ACCOUNTING.md` for the full accounting and future financial-accounting contract.

## EV load-balancing Diagnostic entity

When EV load balancing is enabled, one diagnostic sensor with stable unique-ID
suffix `ev_load_balancing` reports states such as `balanced`,
`waiting_overload`, `waiting_headroom`, `command_sent`, `minimum_reached`,
`unavailable`, and `write_failed`. Attributes expose the configured connection
phases/per-phase limit, measured phase current, charger current boundary, last
action/error and the explicit `goodwe_control: false` ownership marker.

The sensor is diagnostic only. The sole actuator is the external NumberEntity
selected in Settings → EV; EnergyPilot does not create a duplicate charger
NumberEntity.

## Beta SOC Diagnostic entities

v0.17 exposes three read-only candidate values as enabled-by-default Home Assistant Diagnostic sensors so field testers can see them directly on the device page:

| Register | Key / stable unique-ID suffix | Display name | Unit | Status |
|---:|---|---|---|---|
| 45356 | `battery_discharge_depth_on_grid` | Beta on-grid discharge depth (45356) | % | Beta / read-only |
| 45358 | `battery_discharge_depth_off_grid` | Beta off-grid discharge depth (45358) | % | Beta / read-only |
| 47500 | `battery_soc_protection` | Beta battery SOC protection (47500) | raw | Beta / read-only |

Their unique IDs follow the normal pattern, for example:

```text
{config_entry_id}_battery_discharge_depth_on_grid
```

Beta here means **not yet extensively field-tested**. These entities exist for correlation against SolarGo/SEMS+ and firmware reports. They are not controller inputs, EMHASS constraints or write targets.

## Automatic Control switch

The Automatic Control switch represents controller ownership, not merely the last observed inverter mode.

Behaviour contract:

- ON: EnergyPilot automatic controller owns EMS decisions;
- OFF: EnergyPilot relinquishes automatic ownership and requests GoodWe Auto / AI (`mode 1`, `0 W`);
- state is restored over Home Assistant restarts.

Manual quick actions may switch the controller out of automatic ownership.

### EMHASS automatic-control inputs

Automatic Control uses configurable EMHASS outputs:

```text
P_batt  default sensor.p_batt_forecast
P_grid  default sensor.p_grid_forecast
```

`P_batt` remains the source of battery direction and maximum requested battery power. v0.18 additionally uses `P_grid` to distinguish a planned grid-neutral charge interval from intentional grid charging.

### v0.18 grid-neutral charging

When all of the following are true:

```text
P_batt < -deadband
abs(P_grid) <= deadband
optimization state is ready
EV hold is not active
```

EnergyPilot treats `abs(P_batt)` as a **charge cap**, not an unconditional mode-11 setpoint. The current mode-11 setpoint is adjusted from GoodWe smart-meter register `36008` every 30 seconds.

Rules:

- observed grid import reduces charge immediately;
- observed export may increase charge by at most 1 kW per 30-second feedback tick;
- charge never exceeds `abs(P_batt)` or the configured controller maximum;
- the limiter never crosses through zero into discharge;
- when charge must stop, EnergyPilot uses mode 8 Battery Hold;
- after a protective stop, hold lasts at least two minutes;
- after that dwell, two consecutive 30-second samples with clear export are required before mode 11 may restart;
- unavailable GoodWe meter feedback fails safe to Battery Hold;
- unavailable `P_grid` during an EMHASS charge request fails safe to Battery Hold;
- an explicit non-zero EMHASS `P_grid` target preserves the existing direct `P_batt`/mode-11 behavior so intentional grid charging remains possible.

This deliberately does **not** use GoodWe mode 2 for AC-coupled PV that is not visible on the GoodWe PV inputs, and it does not make bidirectional mode 9 the owner of the battery direction.

## Manual control entities

### Manual power number

Defines the requested power used by manual EMS modes that need a non-zero setpoint.

### Manual mode select

Allows explicit selection of a GoodWe EMS mode and transfers ownership to manual control.

## EMHASS SOC number entities

EnergyPilot exposes minimum and maximum battery SOC controls backed by the active EMHASS configuration.

They correspond to:

```text
battery_minimum_state_of_charge
battery_maximum_state_of_charge
```

The Home Assistant UI uses percentages; EMHASS configuration stores fractional values.

Rules:

- minimum cannot exceed maximum;
- maximum cannot fall below minimum;
- write the complete current EMHASS config, preserving unrelated settings;
- re-optimize after a short debounce instead of on every slider movement.

EnergyPilot's normal grid-connected operating recommendation is approximately 5–95%, but inverter/SEMS/BMS protection limits remain independent and may be more restrictive.

## EMHASS optimization strategy select

v0.17 exposes one stateful Config-category select with stable unique-ID suffix:

```text
emhass_cost_function
```

User-facing options are:

```text
Profit
Cost
Self-consumption
```

The underlying raw values are `profit`, `cost` and `self-consumption` from EMHASS `costfun`.

Contract:

- read the current value from EMHASS `/get-config` rather than inferring it from the last button press;
- refresh after EnergyPilot writes EMHASS configuration;
- periodically refresh so direct EMHASS UI changes can be reflected;
- validate supported values before writing;
- update only `costfun` through the existing full-config patch path;
- run a fresh optimization after saving;
- if saving succeeds but optimization fails, keep/report the saved strategy rather than pretending the config write failed.

The strategy changes the optimizer objective. The actuator contract is separately defined by Automatic Control above.

## Buttons

Current major actions include:

- Optimize now;
- legacy/backward-compatible EMHASS Profit configuration action;
- legacy/backward-compatible EMHASS Cost configuration action;
- legacy/backward-compatible EMHASS Self-consumption configuration action;
- Max export;
- Battery pause/hold;
- Max charge;
- Resume AUTO.

### Optimize now

Runs one complete EMHASS optimization/publish cycle and exposes runtime diagnostics as attributes.

From v0.18 those attributes also expose the configured/current `P_grid` target and grid-neutral runtime state (active flag, cap, live meter feedback, hold time and restart evidence) for support snapshots.

### Backward-compatible EMHASS cost-function buttons

The v0.15 strategy button unique IDs remain stable:

```text
emhass_costfun_profit
emhass_costfun_cost
emhass_costfun_self_consumption
```

They are retained so existing automations do not break. Their names now describe an explicit **Set EMHASS...** configuration action and they use the same canonical safe `costfun` write helper as the stateful select.

New dashboard/state logic should use `select.emhass_cost_function` (actual generated entity ID may differ), because a ButtonEntity cannot represent which strategy is currently active.

### Resume AUTO

Creates a fresh optimization first and enables automatic control only after optimization succeeds.

### Manual quick actions

Manual action buttons intentionally take manual ownership before issuing the EMS command.

## Diagnostic entities

The existing `control_command` diagnostic sensor retains its stable unique ID and state semantics. Its attributes also expose the latest successfully completed EMS setpoint update:

```text
last_ems_setpoint_updated_at
last_ems_setpoint
last_ems_mode
last_ems_setpoint_command
```

The timestamp changes only after an actual `47512 -> wait -> 47511` command succeeds. A controller evaluation that skips a duplicate write because live read-back already matches does not change it. The dashboard shows the localized timestamp below the live EMS setpoint, while Diagnose/LOG retains the raw ISO timestamp and command context.

Raw inverter, operating-mode, warning/error, meter-status, and similar sensors may be disabled by default.

The three v0.17 SOC Beta entities are intentionally an exception: they are Diagnostic category **and enabled by default** because current field validation requires testers to compare the values directly with SolarGo/SEMS+.

Do not remove a diagnostic entity merely because it is disabled by default. It may be relied upon for field debugging and compatibility reports.

## Entity naming

Display names may improve over time, but changes should avoid changing stable unique IDs.

Entity IDs assigned by Home Assistant may differ between installations because users can rename entities or Home Assistant can resolve naming collisions. Documentation should therefore describe expected concepts and unique IDs rather than assuming every installation has exactly the same `entity_id`.

## Adding a new entity

Before adding one, check:

1. Does an existing entity already represent the same electrical/configuration value?
2. Is the underlying register semantics validated or explicitly marked Beta?
3. Should it be enabled by default or diagnostic/disabled by default?
4. What device class, state class, entity category and unit are correct?
5. Is long-term statistics support appropriate?
6. Is its unique ID stable and deterministic?
7. Does it need a translation key?
8. Does the dashboard or documentation need updating?

Avoid duplicate representations of the same measurement unless the electrical measurement points are genuinely different and clearly named.
