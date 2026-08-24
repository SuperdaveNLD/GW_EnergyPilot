# GW EnergyPilot release notes

This page is the user-facing release index for GW EnergyPilot.

`CHANGELOG.md` remains the detailed technical history. This page records the validation status and operator-visible scope of each release.

## Status definitions

- **Validated** — no intentionally unconfirmed control/hardware semantics are introduced by that release and repository checks passed.
- **Beta** — functionality is intentionally available before broad field testing across installations/firmware is complete.
- **Validated + beta diagnostics** — release behavior is validated while optional diagnostics still need field correlation.
- **Historical** — older development milestone retained for release history.

## Version overview

| Version | Date | Status | Main release notes |
|---|---|---|---|
| **0.28** | 2026-08-24 | **Beta** | Corrects Hybrid control to mode-9 buying / mode-12 selling and repairs the Battery · Plan · Price chart: canonical EMHASS battery schedule, historical-plan continuity, visible plan overlays, active-interval clipping and stepwise market prices. |
| **0.27** | 2026-08-24 | **Beta** | Resizable Battery plan/actual/price chart, historical active `P_batt` targets plus current EMHASS future forecast, native GoodWe battery-day counters, compact support diagnostics and corrected Hybrid neutral hold behavior. |
| **0.26** | 2026-08-24 | **Beta** | Consolidated release: Home Assistant language-aware Dutch/English UI, Battery & Price chart, canonical backend price-series API/cache, and synchronized EMHASS/GoodWe on-grid minimum SOC through register 45356 with verified write/read-back and rollback protection. |
| **0.25** | 2026-08-24 | **Beta** | Three Automatic Control strategies including Hybrid, extended 15 kW+ daily grid-accounting source selection and persistent 50-run optimization history/LOG. |
| **0.24** | 2026-08-23 | **Beta** | Restores the backwards-compatible direct `P_batt` automatic-control default while preserving explicit PCC control. |
| **0.23** | 2026-08-23 | **Beta** | Persistent Today/Yesterday grid accounting, EV anti-discharge protection, persistent `last_success` and final flow-direction fix. |
| **0.22** | 2026-08-23 | **Beta** | Adds optional GoodWe smart-meter/PCC automatic control through modes 9/10/1 with direct 11/12/8 fallback. |
| **0.21** | 2026-08-23 | **Beta** | Adds the manual 12-mode EMS test pad, live mode highlight, tooltips and manual setpoint slider. |
| **0.20** | 2026-08-23 | **Beta** | Corrects SOC diagnostics and separates configured runtime final SOC from last-sent runtime evidence. |
| **0.19** | 2026-08-23 | **Beta** | Adds combined SOC/constraint diagnostics across GoodWe, EMHASS and EnergyPilot. |
| **0.18** | 2026-08-23 | **Beta** | Adds verified manual field-test writes for G20 minimum-SOC registers 45356/45358. |
| **0.17** | 2026-08-23 | **Beta** | Adds dashboard settings, stable device identity migration, stateful EMHASS strategy readback and Beta SOC diagnostics. |
| **0.16** | 2026-08-23 | **Beta** | Adds optional G20 SOC-protection and extended-meter diagnostics including UINT64 decoding. |
| **0.15** | 2026-08-23 | **Validated** | Adds stateful EMHASS profit/cost/self-consumption strategy controls. |
| **0.14** | 2026-08-23 | **Validated + beta diagnostics** | Adds optional battery SOH and charge/discharge energy diagnostics. |
| **0.13** | 2026-08-23 | **Validated** | Establishes ETA-G20 load semantics, grid energy counters, history and SOC guidance. |
| **0.12** | 2026-08-23 | **Historical** | Startup, EMHASS health and Nord Pool reliability improvements. |
| **0.11** | 2026-08-23 | **Historical** | EMHASS SOC controls, EV-stop optimization and diagnostics snapshot. |
| **0.10** | 2026-08-22 | **Historical** | Native EMHASS orchestrator, Optimize now and manual battery actions. |
| **0.09** | 2026-08-22 | **Historical** | EMHASS output defaults, Recorder load bootstrap and publish validation. |
| **0.08** | 2026-08-22 | **Historical** | Draggable dashboard, visibility/animation controls and Automatic Control restore behavior. |
| **0.07** | 2026-08-22 | **Historical** | Compact PV/Home/Grid/Battery live-flow widget. |
| **0.06** | 2026-08-22 | **Historical** | Dashboard branding and cache-busting fixes. |
| **0.05** | 2026-08-22 | **Historical** | Built-in Home Assistant sidebar dashboard. |
| **0.04** | 2026-08-22 | **Historical** | Branding and EMHASS setup documentation. |
| **0.03** | 2026-08-22 | **Historical** | English setup/options UI and static-IP guidance. |
| **0.02** | 2026-08-22 | **Historical** | Native GoodWe ETA telemetry over direct Modbus TCP. |
| **0.01** | 2026-08-22 | **Historical** | Initial HACS integration with EMS modes 1–12, manual control and EMHASS mapping. |

# v0.28 — Corrected Hybrid control and Battery chart repair

v0.28 combines the corrected meaning of the **Hybrid** Automatic Control strategy with fixes found during live v0.27 Battery · Plan · Price validation.

## Corrected Hybrid buy/sell control

The previous Hybrid implementation combined direct battery charging through mode 11 with PCC export control through mode 10. The intended strategy is asymmetric in the other direction:

```text
buy/import      -> GoodWe mode 9  -> target from EMHASS P_grid
sell/discharge  -> GoodWe mode 12 -> target from EMHASS P_batt
```

The complete decision order is:

```text
P_grid > +deadband -> mode 9 Grid import target
else P_batt > +deadband -> mode 12 Battery discharge power
else P_batt inside deadband -> mode 8 Battery Hold
otherwise -> mode 1 GoodWe Auto / self-use
```

The import branch is evaluated first because an explicit positive `P_grid` is the Hybrid buying signal. Mode 9 lets GoodWe regulate the PCC import target using the planned grid-import magnitude while local PV can be added by the inverter.

Selling is deliberately direct battery control. A positive `P_batt` request uses mode 12 at the planned battery-discharge magnitude instead of forcing a PCC export target through mode 10.

A Hybrid battery-charge request with no planned grid import falls through to mode 1/self-use. This allows available local PV surplus to charge the battery according to GoodWe's own fast control rather than limiting charging to the forecast-sized `P_batt` value. A neutral battery plan remains mode 8 Battery Hold.

## Battery · Plan · Price fixes

Live v0.27 validation showed that the chart's future-plan parser did not match current EMHASS output. Current EMHASS publishes the `P_batt` horizon through the **`battery_scheduled_power`** attribute. v0.28 uses that as the canonical schedule and keeps `forecasts` only as a conservative compatibility fallback for older/custom publishers.

The chart also corrects several timeline and presentation details:

- Home Assistant's start-time history state is retained at local 00:00 when the active `P_batt` state originated before midnight.
- A current EMHASS schedule interval that started just before NOW remains visible and is clipped at NOW instead of being discarded.
- Solid actual bars render below the dashed historical/future plan overlay so planned versus actual remains visible when values overlap.
- Near-zero actual samples are not rendered as false charge/discharge bars or zero-power discharge tooltips.
- Missing historical/future plan data displays `—` for planned energy instead of a fabricated `0.00 kWh`.
- Timestamped market prices are rendered as a step series because they represent intervals, not continuously interpolated measurements.
- The read-only chart payload is versioned as schema `3` and reports which schedule attribute was detected.
- The complete nested ES-module import chain uses v0.28 cache keys so a browser cannot keep a stale v0.27 data/view module underneath a new panel wrapper.

## Battery daily totals

The headline charged/discharged values continue to prefer the native GoodWe day counters:

```text
35208 = battery_charge_energy_today
35211 = battery_discharge_energy_today
```

The secondary graph figure remains a numerical integration of Recorder 5-minute mean samples from instantaneous battery power register `35182`.

Those values can differ because they are separate measurement paths. v0.28 clarifies that distinction and does **not** scale or calibrate the Recorder integral to force a match with the inverter's own day counter. The GoodWe counter remains the headline value.

## Safety and compatibility

- Battery strategy remains `P_batt -> 11/12/8`.
- Grid strategy remains `P_grid -> 9/10/1`.
- EV anti-discharge remains a higher-priority directional override.
- Manual EMS commands remain direct operator commands.
- No new or guessed GoodWe register definitions or Modbus read blocks.
- EMS registers remain `47511` / `47512` with the existing `47512 -> wait -> 47511` write order.
- Chart/API reads remain read-only and do not trigger optimization or write inverter state.
- No entity ID, unique ID, stable device identity, EMHASS optimization objective or persistent accounting/runtime/log store changes.

v0.28 remains **Beta** while the Hybrid 9/12 mapping and corrected real-world plan/actual chart receive live installation validation.

# v0.27 — Battery plan versus actual and dashboard refinement

v0.27 turns the v0.26 Battery & Price visualization into a planning and verification view while preserving the existing GoodWe/EMHASS ownership boundaries.

## Battery plan versus actual

- The card can be switched between **S**, **M** and **L** layouts with an Apple-style segmented control; the browser remembers the selected size.
- Solid bars remain actual GoodWe `battery_power` history from Home Assistant Recorder.
- Historical plan blocks use the configured EnergyPilot `P_batt` entity history, so the graph shows the target that was actually active at each time rather than rewriting the past with the newest optimization.
- Future plan blocks were introduced from the current EMHASS battery forecast payload; v0.28 later corrects the attribute contract to current `battery_scheduled_power`.
- EMHASS and GoodWe battery signs remain aligned: negative = charge, positive = discharge.
- The market-price line and NOW marker stay on the same local-day timeline.

The read-only `gw_energypilot/battery_price/get` response is extended with a versioned chart payload, native battery-day energy values and normalized battery-plan points. Dashboard reads never run an optimization or write a GoodWe register.

## Battery energy totals

The headline **charged today** and **discharged today** values now prefer the already-decoded GoodWe day counters `35208` and `35211`. The Recorder integration remains visible as a graph-derived comparison and clips the still-active final five-minute bucket at the current time.

No new GoodWe register or Modbus block is introduced.

## Hybrid neutral hold

Hybrid Automatic Control now treats a neutral `P_batt` plan as an explicit battery hold when there is no stronger export request:

```text
P_batt < -deadband  -> mode 11 battery charge
else P_grid < -deadband -> mode 10 grid export
else P_batt inside deadband -> mode 8 Battery Hold
otherwise -> mode 1 GoodWe Auto / self-use
```

The export branch remains higher priority so a planned export can still use mode 10 while `P_batt` is neutral. Battery and Grid strategies are unchanged.

## Support and SOC presentation

The legacy direct minimum-SOC field-test panel is removed from the normal dashboard. The synchronized on-grid minimum-SOC NumberEntity remains the supported operator path; the low-level Beta SOC API remains available for diagnostics/backwards-compatible tooling.

The Support card becomes a compact operational summary with GoodWe telemetry, control ownership, optimizer state and EMHASS/GoodWe minimum-SOC synchronization at a glance. Deep raw-register and lifetime diagnostics remain available through the support-report copy action.

## Safety and compatibility

- No guessed or new GoodWe register definitions.
- No Modbus read-block changes.
- EMS registers remain `47511` / `47512` with the existing write order.
- No entity ID, unique ID, device identity or persistent accounting-store change.
- No EMHASS optimization objective change.
- The new chart is read-only; financial accounting must continue to use backend accounting deltas rather than reconstructing money from frontend graph samples.

v0.27 remains **Beta** while the S/M/L layouts and plan-versus-actual overlays receive live installation exposure.

# v0.26 — Language, Battery & Price and synchronized minimum SOC

v0.26 consolidates the release-ready work after v0.25 into one Beta release. It does not change GoodWe EMS register addresses, the EMS write order, or the established Automatic Control strategy mappings.

## Home Assistant language-aware dashboard

The dashboard follows Home Assistant language through `hass.locale.language` / `hass.language`.

- Dutch and English are supported.
- English is the fallback.
- Dashboard, settings, optimization-log, strategy confirmations and the new chart use the same language selection.
- Existing entity IDs, unique IDs and configuration keys are unchanged.

## Battery & Price chart

The new full-width card compares actual battery operation with market price for the current local Home Assistant day.

- GoodWe battery charging (`battery_power < 0`) is shown below zero.
- Battery discharging (`battery_power > 0`) is shown above zero.
- Market price is a separate line with a currency/kWh axis.
- A NOW marker separates observed battery operation from later available price slots.
- Approximate charged/discharged summaries integrate the displayed Recorder 5-minute mean buckets; they are visualization aids, not accounting entities.
- The graph has an expandable read-only detail view and uses a five-minute frontend cache.

Battery history comes from the existing `battery_power` Home Assistant entity/Recorder statistics. No duplicate Modbus or battery entity path is introduced.

The read-only `gw_energypilot/battery_price/get` WebSocket API serves timestamped market, effective buy and effective sell series from the same EnergyPilot price path used for EMHASS. Dashboard reads do not start an optimization.

See `docs/BATTERY_PRICE_CHART.md`.

## Synchronized on-grid minimum SOC

Field validation confirmed that the GoodWe inverter-side on-grid minimum in register `45356` can remain more restrictive than EMHASS `battery_minimum_state_of_charge`. Lowering only the EMHASS value therefore does not necessarily allow discharge to the requested minimum.

The existing EMHASS minimum-SOC NumberEntity remains the single normal on-grid operator control. An explicit change now performs:

```text
validate requested minimum against EMHASS maximum
require current readable GoodWe 45356
write requested whole percentage to GoodWe 45356
verify same-register read-back
write the same percentage to EMHASS battery_minimum_state_of_charge
publish verified GoodWe value into coordinator state
schedule the existing debounced fresh optimization
```

If `45356` is unavailable, neither layer is changed. If the GoodWe write verifies but the following EMHASS write fails, EnergyPilot attempts to restore the previous `45356` value. A failed rollback is surfaced instead of hidden.

There is no startup/background synchronization. The cross-system write happens only after an explicit minimum-SOC NumberEntity change.

The direct on-grid `45356` dashboard field-test card is removed to avoid two competing controls. Off-grid register `45358` remains an independent manual Beta field test. Maximum SOC remains EMHASS-only. The existing `beta_soc` backend API remains available for diagnostics/backwards-compatible tooling.

## Safety and compatibility

- No new or guessed GoodWe register definitions.
- No Modbus read-block changes.
- EMS registers remain `47511` / `47512` with `47512 -> wait -> 47511` ordering.
- Battery/Grid/Hybrid Automatic Control mappings are unchanged.
- No EMHASS objective/cost-function change.
- No existing entity unique ID or stable device-identity change.
- Persistent grid-accounting, runtime `last_success` and optimization-log stores are unchanged.
- The Battery & Price graph is read-only and must not become the source for future persistent financial accounting.

v0.26 remains **Beta** because the Battery & Price visualization and synchronized cross-system SOC transaction still need broader multi-installation field exposure.
