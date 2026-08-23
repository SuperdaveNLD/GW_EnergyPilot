# Development guide

This document defines the practical development workflow for GW EnergyPilot.

## Repository is authoritative

Before changing code, inspect the current repository. Do not reconstruct current runtime behavior from older chats or releases.

For AI-assisted work, also read `AGENTS.md` first.

## Current modules

```text
custom_components/gw_energypilot/
```

Important files:

```text
__init__.py          config-entry setup, device migration, APIs and sidebar panel
client.py            asynchronous GoodWe Modbus TCP I/O
registers.py         canonical register definitions and read blocks
coordinator.py       periodic telemetry polling
controller.py        automatic/manual EMS ownership and actuator strategy
orchestrator.py      base EMHASS orchestration
orchestrator_v012.py reliability/startup/price refinements
orchestrator_v013.py current G20 orchestration subclass
emhass_config.py     complete EMHASS config read/write helpers
settings_api.py      EP/EMHASS/GoodWe connection settings
smart_meter_api.py   v0.22 GoodWe smart-meter actuator strategy
beta_soc_api.py      manual verified 45356/45358 field-test writes
event_triggers.py    event-driven optimization hooks
sensor.py            telemetry/diagnostics
switch.py            Automatic Control ownership
number.py            manual power + EMHASS SOC controls
select.py            manual EMS mode + EMHASS strategy
button.py            optimize/strategy/manual/resume actions
frontend/            layered dashboard/settings assets
tests/               hardware-independent regression tests
```

Repository tooling:

```text
scripts/validate_repo.py
.github/workflows/quality.yml
.github/workflows/hacs.yml
.github/workflows/hassfest.yml
```

## Active orchestrator chain

```text
orchestrator_v013.py
    inherits orchestrator_v012.py
        inherits orchestrator.py
```

All three remain active runtime code. Check subclasses before modifying base behavior.

## Active frontend chain

v0.22 top level:

```text
gw-energy-pilot-v022.js
  -> gw-energy-pilot-v021.js        manual 12-mode EMS pad
       -> gw-energy-pilot-v020.js   SOC diagnostics validity
            -> earlier layered dashboard/settings assets
```

The older filenames are not dead assets. Trace imports before deleting/consolidating anything.

The v0.22 layer owns current Smart Meter strategy UI, PCC/battery target relabelling and authoritative particle direction.

## Automatic-control contract

v0.22 has two explicit actuator strategies.

### GoodWe smart meter active = ON

Default on v0.22:

```text
EMHASS P_grid > +deadband  -> mode 9  Grid import target
EMHASS P_grid < -deadband  -> mode 10 Grid export target
EMHASS P_grid near 0 W     -> mode 1  GoodWe Auto / AI
```

`P_grid` sign:

```text
positive = planned import
negative = planned export
```

GoodWe meter sign is opposite:

```text
36008 negative = actual import
36008 positive = actual export
```

Both `P_batt` and `P_grid` are validated as finite plan outputs. `P_grid` is the actuator request. GoodWe modes 9/10 close the fast loop at the PCC.

The former v0.18-v0.21 30-second mode-11 grid-neutral correction is not scheduled in this strategy. Do not add a competing feedback loop without an explicit redesign and new hardware evidence.

### GoodWe smart meter active = OFF

Fallback:

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt near 0 W    -> mode 8  Battery Hold
```

This fallback deliberately works without a valid `P_grid` entity.

### Manual ownership

Manual commands never inherit or reinterpret the automatic strategy. Manual mode 9 is mode 9, manual mode 11 is mode 11, etc.

Automatic Control OFF returns the inverter to mode 1 / 0 W.

EV coordination can temporarily take Battery Hold ownership.

## Hardware evidence behind v0.22

Reference GW15K-ETA-G20 field tests established:

```text
mode 10 setpoint 400 W -> ~395 W grid export
mode 9  setpoint 400 W -> ~331 W grid import
mode 9  setpoint 15 kW -> ~15 kW grid import + local DC PV; battery ~16.9 kW charge
mode 11 setpoint 15 kW -> battery ~15 kW charge; PV reduces required grid import
mode 1                 -> observed self-use / near-zero-grid with PV surplus charging
```

Therefore:

```text
9 / 10  = PCC/grid targets
11 / 12 = direct battery-power targets
```

Do not use a mode-9 setpoint as a battery-power limit.

## Modbus safety

`registers.py` is canonical for register definitions/read blocks.

Never guess GoodWe addresses, data widths, scales or sign conventions.

EMS contract:

```text
47511 = mode
47512 = non-negative mode-specific power/setpoint magnitude
```

Write order remains:

```text
write 47512
brief wait
write 47511
```

Do not reorder this without hardware validation.

## Dedicated settings architecture

Dashboard APIs are admin-only.

```text
gw_energypilot/settings/get
gw_energypilot/settings/update

gw_energypilot/smart_meter/get
gw_energypilot/smart_meter/set

gw_energypilot/beta_soc/get
gw_energypilot/beta_soc/set
```

Storage rules:

- EP/EMHASS integration options: `ConfigEntry.options`;
- GoodWe connection + smart-meter actuator choice: `ConfigEntry.data`;
- EMHASS SOC/cost-function config: EMHASS `/get-config` → `/set-config`;
- 45356/45358: GoodWe inverter registers.

Do not create a second settings database.

GoodWe connection changes require real connection validation before save.

Device identity remains `(DOMAIN, config_entry_id)`; do not revert to mutable host/unit-ID identity.

## Development workflow

For each change:

1. Inspect current code and documentation.
2. Trace runtime caller/listener/entity/settings paths.
3. Identify whether the issue is Modbus, Home Assistant state, controller ownership, EMHASS, settings API or frontend-only.
4. Use hardware evidence for control/register semantics.
5. Apply the smallest robust change.
6. Add focused regression coverage.
7. Check unavailable/invalid input behavior.
8. Preserve entity/device IDs and Recorder/statistics contracts.
9. Update docs/changelog/release notes when behavior changes.
10. Require Quality, HACS and hassfest before merge.

## Local/CI checks

```text
python -m compileall -q custom_components/gw_energypilot scripts tests
python -m unittest discover -s tests -v
python scripts/validate_repo.py
```

Quality runs these automatically.

The repository validator covers:

- Modbus register/read-block coverage including multi-word values;
- block length limits;
- unique register keys;
- JSON parsing;
- frontend relative-import resolution;
- active frontend existence/version match;
- changelog/release-notes version coverage.

Static checks prove repository consistency, not physical GoodWe behavior.

## Current test priorities

Existing tests should cover at least:

- smart-meter ON: P_grid → mode 9/10/1;
- smart-meter OFF: P_batt → mode 11/12/8;
- maximum setpoint clamp;
- invalid/non-finite optimizer outputs;
- optimizer readiness;
- manual ownership;
- Automatic Control disable → mode 1 / 0 W;
- EV hold and fresh-plan behavior;
- duplicate command suppression;
- EMHASS complete-config preservation;
- Modbus decode/register-block invariants.

Next useful coverage:

- smart-meter WebSocket API authorization/state change;
- full Home Assistant config-entry lifecycle;
- device-registry migration;
- settings API reload behavior;
- orchestrator HTTP success/failure;
- Recorder/statistics integration;
- frontend behavior in a browser test harness.

## Live-flow presentation contract

Frontend energy particles must follow live telemetry signs, not selected EMS mode:

```text
PV production         -> hub
Grid import           -> hub
Grid export           hub -> grid
Battery charging      hub -> battery
Battery discharging   battery -> hub
House consumption     hub -> house
```

If labels and particles disagree, fix the frontend direction layer; do not change Modbus sign semantics without hardware evidence.

## Beta hardware policy

Beta means **not extensively field-tested**.

For candidate registers:

- use optional reads;
- keep read-only unless a separately validated write path exists;
- never feed unconfirmed values into automatic control;
- label Beta visibly;
- collect model/firmware and SolarGo/SEMS+ correlation;
- promote only through an intentional code/docs release change.

The v0.22 mode-9/10 automatic strategy is Beta for a different reason: the underlying EMS modes/registers have strong reference-hardware evidence, but the new automatic usage has limited installation exposure. The direct 11/12/8 strategy remains a reversible fallback.

## Known technical debt

1. Layered orchestrator inheritance should eventually be consolidated after tests.
2. Layered frontend assets should eventually be consolidated after behavior coverage.
3. Full Home Assistant/runtime/browser testing remains limited.
4. Legacy `grid_neutral_*` diagnostic fields remain temporarily as inactive compatibility attributes after retirement of the old feedback loop.

## Release checklist

Before release verify:

- manifest version;
- active frontend + cache-buster + `VERSION`;
- controller strategy and fallback tests;
- no unintended `client.py`/register/write-order changes;
- README current behavior;
- `CHANGELOG.md`;
- `docs/RELEASE_NOTES.md` and Beta/Validated status;
- `docs/EMS_MODES.md` for control changes;
- `docs/SETTINGS.md` for settings changes;
- translations/standard HA option descriptions where relevant;
- Quality, HACS and hassfest;
- exact tested PR head before merge.

## Durable documentation map

- `AGENTS.md` — contributor/AI rules;
- `docs/ARCHITECTURE.md` — runtime structure;
- `docs/MODBUS.md` — register contract;
- `docs/EMS_MODES.md` — all 12 EMS modes/current automatic strategy;
- `docs/EMHASS_SETUP.md` — operator setup;
- `docs/GRID_NEUTRAL_CHARGING.md` — old loop → v0.22 PCC migration;
- `docs/SETTINGS.md` — settings ownership/security;
- `docs/ENTITIES.md` — entity/device contract;
- `docs/KNOWN_ISSUES.md` — field issues;
- `docs/RELEASE_NOTES.md` — release summaries/status;
- `CHANGELOG.md` — detailed history.
