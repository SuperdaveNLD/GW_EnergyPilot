# GW EnergyPilot release notes

This page gives a user-facing summary of every GW EnergyPilot version.

`CHANGELOG.md` remains the detailed technical history. This page is intentionally shorter and also records whether a release contains functionality that is still under limited field validation.

## Status definitions

- **Validated** — the release does not intentionally introduce unconfirmed hardware semantics. It has passed the repository Quality, HACS and hassfest checks. This does not mean the project has been tested across every ETA-G20 model or firmware version.
- **Beta** — the release intentionally includes functionality that has not yet been extensively field-tested. Beta hardware values normally remain read-only/optional. A narrowly scoped manual write test is allowed only when it is explicitly documented, limited to known canonical registers, guarded by validation/read-back, and kept outside automatic control.
- **Historical** — older development milestone retained for version history; current support and testing focus is on the latest release.

## Version overview

| Version | Date | Status | Main release notes |
|---|---|---|---|
| **0.23** | 2026-08-23 | **Beta** | Adds a persistent EnergyPilot accounting layer on top of the existing GoodWe `36017/36015` lifetime counters. Native daily import/export entities now own Today/Yesterday accounting, with optional Recorder bootstrap for existing history. This is the foundation for later interval-based import cost, export revenue and net profit without moving financial logic into the frontend. |
| **0.22** | 2026-08-23 | **Beta** | Promotes the hardware-validated GoodWe smart-meter/PCC modes into an optional automatic strategy. With **GoodWe smart meter active** enabled, EMHASS `P_grid` drives mode 9 import targets and mode 10 export targets, while near-zero grid flow uses mode 1 Auto/self-use. Disabling the setting restores direct `P_batt` control through modes 11/12/8. Also fixes live-flow particle direction at the active frontend layer. |
| **0.21** | 2026-08-23 | **Beta** | Adds a manual 12-mode EMS test pad to the Controller card. Automatic Control locks the pad while still highlighting the live GoodWe mode. With Automatic Control off, testers can select modes 1–12 and set a `0..max_power` manual setpoint using the existing Home Assistant manual-mode/manual-power entities. This is a UI/testing surface only; the Modbus write path, ownership rules and automatic controller are unchanged. |
| **0.20** | 2026-08-23 | **Beta** | Corrects v0.19 SOC diagnostics after second-tester field data: configured EnergyPilot final SOC is separated from the last value actually sent by EnergyPilot, and invalid raw EMHASS SOC config values are identified as raw diagnostics instead of being rendered as impossible percentages. No optimizer or GoodWe control behavior changes. |
| **0.19** | 2026-08-23 | **Beta** | Makes the separate SOC layers explicit: current SOC, runtime `soc_init`/`soc_final`, EMHASS minimum/target/deficit threshold and cost, and GoodWe on-grid minimum SOC are shown together. The existing EMHASS `/get-config` refresh is reused; optimization and GoodWe control behavior do not change. |
| **0.18** | 2026-08-23 | **Beta** | Adds manual, read-back-verified G20 field-test controls for the on-grid minimum SOC floor at `45356` and off-grid minimum SOC floor at `45358` inside GOODWE settings. No automatic control path uses these registers; `47500` remains read-only. |
| **0.17** | 2026-08-23 | **Beta** | Adds the administrator settings gear with EP, EMHASS and GOODWE pages, validates GoodWe connection changes before saving, migrates device identity from mutable `host:slave` to stable config-entry ID, exposes the three SOC Beta candidates as enabled Home Assistant Diagnostic sensors, and makes the active EMHASS optimization strategy stateful/readable from `/get-config`. |
| **0.16** | 2026-08-23 | **Beta** | Ships read-only G20 SOC-protection candidates `45356/45358/47500` and extended 15 kW+ meter candidates `36104/36120` to the active tester group. Adds UINT64 decoding, beta diagnostics UI and tests. No candidate value is used for control or canonical grid accounting. |
| **0.15** | 2026-08-23 | **Validated** | Adds EMHASS `profit`, `cost` and `self-consumption` strategy controls. Preserves unrelated EMHASS config and immediately re-optimizes after a strategy change. GoodWe `P_batt` control remains unchanged. |
| **0.14** | 2026-08-23 | **Validated + beta diagnostics** | Adds optional battery SOH/charge/discharge accounting diagnostics from `35206-35211`. Those accounting values remain field-validation diagnostics and are not used for synthetic cycle calculations. |
| **0.13** | 2026-08-23 | **Validated** | Establishes GW15K-ETA-G20 load semantics, grid cumulative counters, 24-hour grid history, daily import/export totals, refresh labels and SOC-limit guidance. |
| **0.12** | 2026-08-23 | **Historical** | Improves startup reliability, EMHASS health diagnostics, Nord Pool fallback handling and error visibility. |
| **0.11** | 2026-08-23 | **Historical** | Adds EMHASS minimum/maximum SOC controls, EV-stop optimization and diagnostics snapshot. |
| **0.10** | 2026-08-22 | **Historical** | Introduces the native EMHASS orchestrator, Optimize now, manual battery controls and validated fresh-`P_batt` gating. |
| **0.09** | 2026-08-22 | **Historical** | Adds default EMHASS output IDs, Recorder load bootstrap and publish validation. |
| **0.08** | 2026-08-22 | **Historical** | Adds draggable dashboard layout, visibility controls, animation control and Automatic Control restore behavior. |
| **0.07** | 2026-08-22 | **Historical** | Adds the compact PV / Home / Grid / Battery live-flow widget. |
| **0.06** | 2026-08-22 | **Historical** | Fixes dashboard branding and frontend cache busting. |
| **0.05** | 2026-08-22 | **Historical** | Adds the built-in Home Assistant sidebar dashboard. |
| **0.04** | 2026-08-22 | **Historical** | Adds GW EnergyPilot branding and improved EMHASS setup documentation. |
| **0.03** | 2026-08-22 | **Historical** | Improves English setup/options UI, static-IP guidance and controller descriptions. |
| **0.02** | 2026-08-22 | **Historical** | Adds native GoodWe ETA telemetry over direct Modbus TCP. |
| **0.01** | 2026-08-22 | **Historical** | Initial HACS-compatible integration with EMS modes 1–12, manual control, EMHASS `P_batt` mapping and EV coordination. |

## v0.23 — Persistent grid accounting foundation

v0.23 moves daily grid accounting out of the dashboard and into a dedicated EnergyPilot runtime component.

The physical source remains unchanged:

```text
36017 = lifetime grid import
36015 = lifetime grid export
```

EnergyPilot stores the last observed lifetime values and accumulates only positive deltas into its own daily counters. The first public accounting entities are:

```text
Grid energy imported today
Grid energy exported today
```

Both expose the completed previous day through `last_period` and use Home Assistant `total_increasing` energy semantics.

For an existing installation upgrading to v0.23, EnergyPilot can read the canonical counter state at the previous and current local-midnight boundaries from Recorder after the first fresh GoodWe poll. That allows the new accounting store to start with already-existing Today/Yesterday values rather than always beginning at zero at upgrade time.

Recorder is **not** part of the live accounting loop. If Recorder is disabled or the historical boundary states do not exist, EnergyPilot simply establishes the current lifetime counters as a baseline and continues accounting from live GoodWe data.

The dashboard now reads Today/Yesterday from these accounting entities. The 24-hour power graph still uses Recorder because that graph is historical visualization, but it no longer owns the daily energy calculation.

### Why this exists before financial counters

Future dynamic-price accounting needs to value energy at the time it crossed the grid connection, not multiply an end-of-day kWh total by one average price. The v0.23 runtime is therefore the intended insertion point for:

```text
import_cost += delta_import_kWh * effective_buy_price
export_revenue += delta_export_kWh * effective_sell_price
```

Those future calculations can consume exactly the same per-refresh energy deltas already used by the daily counters and the same effective buy/sell price configuration already used by EnergyPilot/EMHASS.

### Safety boundary

v0.23 does not change GoodWe Modbus definitions, read blocks, EMS writes, Automatic Control, or EMHASS optimization behavior. The existing lifetime energy entities and their unique IDs remain untouched. The new accounting path is **Beta** until it has been observed across multiple installations and midnight/restart scenarios.

## v0.22 — Smart-meter/PCC automatic control

v0.22 turns the mode-9/mode-10 field tests from v0.21 into an explicit, reversible Automatic Control strategy.

### Hardware behavior confirmed on the reference ETA-G20

The manual v0.21 tests showed that the meaning of `47512` depends strongly on the selected EMS mode:

```text
mode 9  = target net grid import at the GoodWe smart meter / PCC
mode 10 = target net grid export at the GoodWe smart meter / PCC
mode 11 = direct battery charge-power target
mode 12 = direct battery discharge-power target
```

Observed examples included:

```text
mode 10, setpoint 400 W  -> approximately 395 W grid export
mode 9,  setpoint 400 W  -> approximately 331 W grid import
mode 9,  setpoint 15 kW  -> approximately 15 kW grid import while DC PV was added on top
mode 11, setpoint 15 kW  -> battery stayed close to 15 kW charge while PV reduced required grid import
```

Mode 1 was also observed naturally sending available PV surplus into the battery while keeping the grid close to zero on the reference installation.

### GoodWe smart meter active

The GOODWE settings page now contains a dedicated **GoodWe smart meter active** switch.

With the setting **ON** — the v0.22 default — Automatic Control uses EMHASS `P_grid` as the site-level target:

```text
P_grid > +deadband  -> mode 9  Grid import target
P_grid < -deadband  -> mode 10 Grid export target
P_grid near 0 W     -> mode 1  GoodWe Auto / self-use
```

EMHASS convention remains:

```text
P_grid > 0 = planned import
P_grid < 0 = planned export
```

The GoodWe smart meter itself still reports the opposite telemetry sign in EnergyPilot:

```text
meter 36008 < 0 = actual import
meter 36008 > 0 = actual export
```

GoodWe therefore performs the fast closed-loop correction at its own PCC. EnergyPilot does not need to keep trimming a mode-11 battery target every 30 seconds when this strategy is enabled.

With the setting **OFF**, the previous direct battery execution remains available:

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt near 0 W    -> mode 8  Battery Hold
```

This fallback does not require a valid `P_grid` entity.

### Why this helps external PV

A separate AC-coupled PV inverter can be invisible on the GoodWe DC-PV inputs while still being visible to the GoodWe smart meter. Modes 9 and 10 regulate the net site flow at that meter, so they naturally include externally generated AC power in the same PCC balance.

Directly connected GoodWe PV keeps an efficiency advantage because it reaches the battery through the inverter's DC path. The control objective, however, is the same: the requested import/export value is enforced at the connection point rather than inferred from a forecasted battery-power target.

### Retired v0.18-v0.21 feedback loop

The old 30-second grid-neutral mode-11 correction is no longer scheduled in v0.22. Its diagnostic fields are retained as inactive compatibility values so older frontend/support layers do not break during the transition.

### Flow-direction correction

The live-flow labels already used the validated signs, but the animated particles were assembled through several historical CSS layers. v0.22 makes their direction authoritative in the active frontend layer using explicit **to hub / from hub** classes:

```text
PV production       -> hub
Grid import         -> hub
Grid export         <- hub
Battery charging    <- hub
Battery discharging -> hub
House load          <- hub
```

Here the arrow points in the direction energy travels relative to the central EnergyPilot hub.

### Beta boundary

v0.22 remains **Beta** because the new automatic strategy selection and mode-9/10 execution have only limited field exposure across installations. The manual 12-mode pad remains available when Automatic Control is off, and switching **GoodWe smart meter active** off restores the established direct mode-11/12/8 control path.

The EMS registers and write order are unchanged:

```text
write 47512 power
wait briefly
write 47511 mode
```

## v0.21 — Manual 12-mode EMS test pad

v0.21 makes the recently documented GoodWe EMS modes practical to test from the EnergyPilot Controller card without adding a second write path.

The Controller card now contains twelve compact square mode buttons with short hover descriptions. The button that matches the **live `47511` read-back** is highlighted even while Automatic Control is active.

When **Automatic Control is ON**:

- all manual mode buttons are visually greyed/locked;
- the manual power slider is disabled;
- the live active GoodWe mode remains highlighted so automatic behavior can still be observed.

When **Automatic Control is OFF**:

- all twelve manual modes become selectable;
- the slider controls the existing `manual_power` Home Assistant number entity;
- the slider range is `0 W` through the configured EnergyPilot `max_power` setting;
- clicking a mode uses the existing `manual_mode` select entity and therefore the existing controller/manual-ownership path;
- modes `1`, `6`, `7` and `8` continue to force `47512 = 0 W` exactly as before;
- mode `7` asks for an extra confirmation because forced off-grid operation can materially change inverter topology.

The primary field test requested for this release is:

```text
Automatic Control OFF
manual setpoint 0 W
mode 10 — Grid export target
```

This tests GoodWe's smart-meter/PCC export-target behavior at a `0 W` export target. Mode 1 can be compared alongside it, but v0.21 does **not** change automatic PV-only or grid-neutral logic based on one installation's observation.

No new Modbus command exists in v0.21. The UI still follows:

```text
manual slider -> existing number.manual_power
mode button   -> existing select.manual_mode
              -> controller.async_manual_command()
              -> existing GWModbusClient.async_set_mode()
```

The established EMS write order remains unchanged: power register `47512`, brief wait, then mode register `47511`.

## v0.20 — SOC diagnostics validity

v0.20 is a narrow diagnostics correction based on a second tester's v0.19 snapshot. That installation showed `orchestrator=manual_only`, `Last success=Never`, an EnergyPilot final-SOC setting of 10%, and raw EMHASS values that rendered as `-90%` and `-690%` in v0.19.

The field data exposed two separate presentation problems:

1. v0.19 displayed the **configured** EnergyPilot final-SOC setting as if it were the runtime `soc_final` used by the last EnergyPilot optimization. On a manual-only installation EnergyPilot may never have sent that value at all.
2. v0.19 multiplied any finite `/get-config` SOC value by 100. EMHASS documents SOC fractions in the `0..1` range, so finite values outside that range are invalid configuration data rather than valid percentages.

v0.20 therefore shows both concepts separately:

```text
Configured EnergyPilot final SOC target
Last sent runtime final SOC (soc_final)
```

The last-sent value remains blank until an **EnergyPilot-owned** optimization completes successfully. External/manual EMHASS publishing does not populate it.

For EMHASS configuration values, valid `0..1` SOC fractions continue to render as percentages. Invalid finite values are retained for support and shown explicitly, for example:

```text
EMHASS config target SOC (fallback)   invalid raw -0.9
EMHASS deficit threshold              invalid raw -6.9
```

EnergyPilot does not repair, clamp or write those values automatically. Their origin must be diagnosed in the tester's EMHASS configuration/version/migration path.

This release changes diagnostics only. It does not change EMHASS constraints, GoodWe EMS commands, grid-neutral charging, `P_batt` mapping, or the v0.18 `45356/45358` manual field-test path.

## v0.19 — SOC constraint clarity

v0.19 makes the different SOC concepts visible next to each other so an apparent SOC stop can be traced to the correct layer instead of guessing from a single percentage.

The Diagnostics snapshot now shows:

```text
Current battery SOC
Last optimization SOC init
Runtime final SOC target (soc_final)
EMHASS minimum SOC
EMHASS config target SOC (fallback)
EMHASS deficit threshold
EMHASS deficit cost
GoodWe on-grid minimum SOC 45356
```

The **Runtime final SOC target** is the EnergyPilot config-entry value sent as `soc_final` with every native optimization. EMHASS documents runtime battery parameters as overriding configured values for that run, so this value is intentionally shown separately from `battery_target_state_of_charge` in EMHASS `config.json`.

`battery_target_state_of_charge` remains visible as the EMHASS fallback used when a runtime final SOC is not supplied. The deficit threshold is also shown separately because it is not a hard floor: EMHASS applies `battery_soc_deficit_cost` as a virtual `currency/kWh/h` cost while the battery is below that threshold.

The existing stateful EMHASS strategy refresh already reads the complete `/get-config` payload. v0.19 reuses that same response for these SOC diagnostics, so no extra periodic EMHASS request is added.

The EMHASS settings label **Target final SOC** is clarified as **Runtime final SOC target**. This is a UI/diagnostics clarification only; the optimizer payload, GoodWe EMS mapping and v0.18 manual G20 SOC-floor field-test path are unchanged.

## v0.18 — Beta G20 minimum-SOC write validation

v0.18 adds a deliberately narrow manual test path for the two G20 SOC-limit registers that have now produced consistent read evidence on the reference **GW15K-ETA-G20**.

### Why `45356` is shown as minimum SOC

Current upstream GoodWe code stores register `45356` as the raw battery discharge-depth setting but exposes on-grid DoD as:

```text
DoD = 100 - register 45356
```

That means a raw register value of `10` corresponds to a 10% minimum SOC / 90% depth of discharge. This matches the reference G20 observation that the battery stopped discharging at approximately 10% while `45356` read `10`.

OpenEMS independently maps the same register to a minimum-SOC-under-limit concept. v0.18 therefore presents the **raw register value** directly as **On-grid minimum SOC** while retaining the existing internal entity key for backwards compatibility.

Register `45358` is treated as the corresponding **Off-grid minimum SOC** candidate.

### GOODWE settings field test

The GOODWE configuration page now contains a separate **G20 field test · direct inverter setting** block for:

```text
45356  On-grid minimum SOC
45358  Off-grid minimum SOC
```

These values are stored by the inverter, not in the Home Assistant `ConfigEntry`.

Each control:

- is available only when that register is already readable through the normal optional telemetry path;
- accepts a whole percentage from `0` to `100`;
- writes exactly one selected register per action;
- asks for an explicit dashboard confirmation;
- reads the same register back after the write;
- reports success only when the read-back equals the requested value;
- immediately updates the coordinator snapshot after a verified write.

### Safety boundary

This is **not** a new automatic SOC controller.

- Automatic Control does not read or write `45356/45358`.
- EMHASS does not change these values.
- No event trigger or scheduler changes these values.
- The existing `P_batt` → EMS mode `8/11/12` mapping is unchanged.
- Arbitrary Modbus register writes are not exposed; the client whitelist contains only the two canonical keys already defined in `registers.py`.
- `47500` remains read-only because its meaning varies by firmware and the reference G20 has returned `65535`, which is not treated as a valid percentage.

Field testing should change one setting at a time and record the previous value, requested value, verified read-back and observed battery stop behavior.

## v0.17 — Beta settings UI, stateful strategy and field diagnostics

v0.17 combines the current Beta G20 validation tools with a dedicated configuration experience and clearer EMHASS strategy state for the active installations.

### Settings gear

Home Assistant administrators can open a configuration view from the dashboard header with three sections:

- **EP** — controller power limit, deadband, telemetry cadence and EV coordination;
- **EMHASS** — EnergyPilot-owned EMHASS connection, optimization schedule/output mapping and Nord Pool runtime-price settings;
- **GOODWE** — inverter host, Modbus TCP port and unit ID.

The pages update the existing Home Assistant config entry rather than creating a second settings store. GoodWe connection changes are tested before they are stored, after which EnergyPilot reloads the existing config entry.

### Stateful EMHASS optimization strategy

`profit`, `cost` and `self-consumption` are one persistent EMHASS `costfun` setting, not three independent modes. v0.17 exposes a stateful **EMHASS optimization strategy** select and uses it to highlight the active option in the dashboard.

The state is read from EMHASS `/get-config`, refreshed after EnergyPilot config writes and periodically so changes made directly in EMHASS are reflected in Home Assistant.

Changing the select safely updates only `costfun` in the complete current EMHASS config, then requests a fresh optimization. If the save succeeds but that optimization fails, the selected strategy remains saved and EnergyPilot reports the distinction.

The three v0.15 strategy button unique IDs remain available for existing automations; new UI/state logic uses the select.

### Device identity migration

Older releases linked the Home Assistant device to `host:slave`. v0.17 migrates the owning device to the stable config-entry ID before entities are set up. This allows a future validated host/unit-ID change without intentionally creating a second EnergyPilot device.

Existing entity unique IDs already use the config-entry ID and are not intentionally renamed by this migration.

### Beta SOC Diagnostic sensors

The read-only candidates are now also visible directly under the Home Assistant device's Diagnostic entities:

```text
45356  Beta on-grid discharge depth (%)
45358  Beta off-grid discharge depth (%)
47500  Beta battery SOC protection (raw status/value)
```

They remain Beta and are not inputs to the controller or EMHASS.

### Why v0.17 is still Beta

- the settings UI and device migration have limited real-installation exposure;
- the G20 candidate registers are still being correlated with SolarGo/SEMS+ on the active installations;
- the extended `36104/36120` counters remain diagnostics and do not replace `36015/36017` for Recorder-facing grid energy.

The stateful EMHASS strategy feature itself has automated coverage and does not change the GoodWe actuator mapping.

No GoodWe EMS write behavior changes in this release.

## v0.16 — Beta G20 field diagnostics

v0.16 turned the small active installation base into useful validation data without expanding the write/control surface.

### Beta values

```text
45356  candidate on-grid battery discharge-depth / SOC limit
45358  candidate off-grid battery discharge-depth / reserve limit
47500  candidate battery SOC-protection status/enable value
36104  candidate extended lifetime grid export counter
36120  candidate extended lifetime grid import counter
```

Rules while these remain Beta:

- read-only;
- optional Modbus reads;
- failure of a beta read must not fail normal telemetry;
- no beta value may change EMS mode, setpoint or ownership;
- `36015/36017` remain the canonical Recorder-facing grid-energy source;
- beta values should be compared with SolarGo/SEMS+ and reported together with exact inverter model and firmware.

A dedicated **Copy beta diagnostics** action is included so testers can report the candidate values consistently.

## Release-note maintenance rule

Every version bump must update both:

1. `CHANGELOG.md` — detailed technical changes;
2. `docs/RELEASE_NOTES.md` — user-facing version summary and validation status.

If a release contains functionality that is not extensively tested, mark the relevant release or feature **Beta** here rather than presenting the data as confirmed hardware behavior.