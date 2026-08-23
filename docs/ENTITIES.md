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

The native GoodWe grid counters are exposed as Home Assistant energy sensors with `TOTAL_INCREASING` state class:

- grid energy imported total;
- grid energy exported total.

Preserve their units, device classes, state classes, and unique IDs to protect long-term statistics.

## Automatic Control switch

The Automatic Control switch represents controller ownership, not merely the last observed inverter mode.

Behaviour contract:

- ON: EnergyPilot automatic controller owns EMS decisions;
- OFF: EnergyPilot relinquishes automatic ownership and requests GoodWe Auto / AI (`mode 1`, `0 W`);
- state is restored over Home Assistant restarts.

Manual quick actions may switch the controller out of automatic ownership.

## Select entities

### Manual EMS mode

Allows explicit selection of a GoodWe EMS mode and transfers ownership to manual control.

### EMHASS optimization strategy

v0.16 exposes the active EMHASS `costfun` as one stateful select entity with stable unique-ID suffix:

```text
emhass_cost_function
```

User-facing options map to the native EMHASS values:

```text
Profit           -> profit
Cost             -> cost
Self-consumption -> self-consumption
```

The select reads the active value from EMHASS `/get-config` during startup, refreshes periodically so changes made in the EMHASS UI are picked up, and refreshes immediately after EnergyPilot writes EMHASS configuration.

Selecting another strategy:

1. reads the complete active EMHASS configuration;
2. changes only `costfun`;
3. writes the complete configuration back through `/set-config`;
4. updates the Home Assistant select state;
5. requests a fresh optimization and publish cycle.

If step 5 fails after the configuration write succeeded, EnergyPilot reports that distinction: the selected strategy remains saved even though the fresh plan could not be created.

The raw value is also exposed as the select attribute `emhass_costfun`.

## Manual power number

Defines the requested power used by manual EMS modes that need a non-zero setpoint.

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
- legacy EMHASS strategy shortcuts;
- Max export;
- Battery pause/hold;
- Max charge;
- Resume AUTO.

### Optimize now

Runs one complete EMHASS optimization/publish cycle and exposes runtime diagnostics as attributes.

### EMHASS strategy shortcut buttons

The three v0.15 button unique IDs remain available for backwards compatibility with automations and existing entity registries:

```text
emhass_costfun_profit
emhass_costfun_cost
emhass_costfun_self_consumption
```

They use the same canonical safe config-write path as the v0.16 select and are categorized as configuration actions. Their display names deliberately start with an action such as **Set EMHASS...** so they are not mistaken for three independent persistent modes.

New UI should prefer the stateful `emhass_cost_function` select because a button cannot represent which strategy is currently active.

These controls change the EMHASS optimization objective only. GoodWe Automatic Control remains `P_batt` driven and continues to use the validated mode 8/11/12 mapping. Any future `P_grid`/grid-target controller is a separate control-ownership change requiring hardware validation.

### Resume AUTO

Creates a fresh optimization first and enables automatic control only after optimization succeeds.

### Manual quick actions

Manual action buttons intentionally take manual ownership before issuing the EMS command.

## Diagnostic entities

Raw inverter, operating-mode, warning/error, meter-status, and similar sensors may be disabled by default.

Do not remove a diagnostic entity merely because it is disabled by default. It may be relied upon for field debugging and compatibility reports.

## Entity naming

Display names may improve over time, but changes should avoid changing stable unique IDs.

Entity IDs assigned by Home Assistant may differ between installations because users can rename entities or Home Assistant can resolve naming collisions. Documentation should therefore describe expected concepts and unique IDs rather than assuming every installation has exactly the same `entity_id`.

## Adding a new entity

Before adding one, check:

1. Does an existing entity already represent the same electrical value?
2. Is the underlying register semantics validated?
3. Should it be enabled by default or diagnostic/disabled by default?
4. What device class, state class, and unit are correct?
5. Is long-term statistics support appropriate?
6. Is its unique ID stable and deterministic?
7. Does it need a translation key?
8. Does the dashboard or documentation need updating?

Avoid duplicate representations of the same measurement unless the electrical measurement points are genuinely different and clearly named.
