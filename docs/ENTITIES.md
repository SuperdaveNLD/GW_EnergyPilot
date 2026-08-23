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

## Power semantics

### Grid

Primary grid power uses `meter_total_power_fast` / register `36008`:

```text
negative = import
positive = export
```

### Battery

```text
negative = charging
positive = discharging
```

### Home/load

The primary Home/load telemetry is GoodWe register `35172` (`total_load_power`).

Do not substitute the calculated system balance as the Home/load entity without an intentional architecture change.

## Cumulative energy sensors

The current canonical GoodWe grid counters are exposed as Home Assistant energy sensors with `TOTAL_INCREASING` state class:

- grid energy imported total (`36017`);
- grid energy exported total (`36015`).

Preserve their units, device classes, state classes, and unique IDs to protect long-term statistics.

The v0.16+ extended `36104/36120` values remain Beta diagnostics and are deliberately **not** separate Recorder-facing canonical energy entities yet.

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

## Buttons

Current major actions include:

- Optimize now;
- EMHASS Profit;
- EMHASS Cost;
- EMHASS Self-consumption;
- Max export;
- Battery pause/hold;
- Max charge;
- Resume AUTO.

### Optimize now

Runs one complete EMHASS optimization/publish cycle and exposes runtime diagnostics as attributes.

### EMHASS cost-function buttons

The three strategy buttons correspond directly to the supported EMHASS `costfun` values:

```text
profit
cost
self-consumption
```

Each button:

1. reads the complete active EMHASS configuration through `/get-config`;
2. changes only the top-level `costfun` value;
3. writes the complete configuration through `/set-config`;
4. immediately runs and publishes a fresh optimization.

Stable unique-ID suffixes are:

```text
emhass_costfun_profit
emhass_costfun_cost
emhass_costfun_self_consumption
```

These controls change the EMHASS optimization objective. In v0.15+ they do **not** change the GoodWe actuator strategy: Automatic Control still executes the resulting `P_batt` target using the existing mode 8/11/12 mapping. Any future `P_grid`/grid-target controller must be introduced as a separate, validated control-ownership change.

### Resume AUTO

Creates a fresh optimization first and enables automatic control only after optimization succeeds.

### Manual quick actions

Manual action buttons intentionally take manual ownership before issuing the EMS command.

## Diagnostic entities

Raw inverter, operating-mode, warning/error, meter-status, and similar sensors may be disabled by default.

The three v0.17 SOC Beta entities are intentionally an exception: they are Diagnostic category **and enabled by default** because current field validation requires testers to compare the values directly with SolarGo/SEMS+.

Do not remove a diagnostic entity merely because it is disabled by default. It may be relied upon for field debugging and compatibility reports.

## Entity naming

Display names may improve over time, but changes should avoid changing stable unique IDs.

Entity IDs assigned by Home Assistant may differ between installations because users can rename entities or Home Assistant can resolve naming collisions. Documentation should therefore describe expected concepts and unique IDs rather than assuming every installation has exactly the same `entity_id`.

## Adding a new entity

Before adding one, check:

1. Does an existing entity already represent the same electrical value?
2. Is the underlying register semantics validated or explicitly marked Beta?
3. Should it be enabled by default or diagnostic/disabled by default?
4. What device class, state class, and unit are correct?
5. Is long-term statistics support appropriate?
6. Is its unique ID stable and deterministic?
7. Does it need a translation key?
8. Does the dashboard or documentation need updating?

Avoid duplicate representations of the same measurement unless the electrical measurement points are genuinely different and clearly named.
