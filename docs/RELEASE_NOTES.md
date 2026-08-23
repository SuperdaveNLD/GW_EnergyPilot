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
