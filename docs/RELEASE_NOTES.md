# GW EnergyPilot release notes

This page gives a user-facing summary of every GW EnergyPilot version.

`CHANGELOG.md` remains the detailed technical history. This page is intentionally shorter and also records whether a release contains functionality that is still under limited field validation.

## Status definitions

- **Validated** — the release does not intentionally introduce unconfirmed hardware semantics. It has passed the repository Quality, HACS and hassfest checks. This does not mean the project has been tested across every ETA-G20 model or firmware version.
- **Beta** — the release intentionally includes functionality that has not yet been extensively field-tested. Beta hardware values stay read-only/optional until enough real-installation evidence exists to promote them.
- **Historical** — older development milestone retained for version history; current support and testing focus is on the latest release.

## Version overview

| Version | Date | Status | Main release notes |
|---|---|---|---|
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

## v0.16 — Beta G20 field diagnostics

The current beta release is intended to turn the small active installation base into useful validation data without expanding the write/control surface.

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
