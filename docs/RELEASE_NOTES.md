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
| **0.27** | 2026-08-24 | **Beta** | Corrects Hybrid Automatic Control to its intended asymmetric mapping: buying/import uses GoodWe mode 9 from EMHASS `P_grid`, selling/discharging uses mode 12 from EMHASS `P_batt`, neutral battery plans use mode 8, and PV-only charging can fall back to GoodWe self-use. |
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

# v0.27 — Corrected Hybrid buy/sell control

v0.27 corrects the meaning of the **Hybrid** Automatic Control strategy. The previous implementation mixed direct battery charging (mode 11) with PCC export control (mode 10). The intended Hybrid strategy combines the opposite control domains for the two economic directions:

```text
buy/import   -> GoodWe mode 9  -> target comes from EMHASS P_grid
sell/discharge -> GoodWe mode 12 -> target comes from EMHASS P_batt
```

The complete mapping is:

```text
P_grid > +deadband -> mode 9 Grid import target
else P_batt > +deadband -> mode 12 Battery discharge power
else P_batt near 0 W -> mode 8 Battery Hold
otherwise -> mode 1 GoodWe Auto / self-use
```

The import branch is evaluated first because an explicit positive `P_grid` is the Hybrid buying signal. The mode-9 setpoint uses the planned grid-import magnitude; local PV can therefore be added by the inverter while GoodWe regulates the PCC import target.

Selling is deliberately direct battery control. A positive `P_batt` request uses mode 12 at the planned battery-discharge magnitude rather than trying to force an export target through mode 10.

A Hybrid charging request with no planned grid import falls through to GoodWe mode 1/self-use. This allows available local PV surplus to charge the battery according to GoodWe's own fast control rather than limiting charging to the forecast-sized `P_batt` value. A neutral battery plan remains mode 8 Battery Hold.

Battery and Grid strategies are unchanged. EV anti-discharge remains a higher-priority safety override. Manual EMS commands remain direct operator commands.

### Safety and compatibility

- No new or guessed GoodWe register definitions.
- No Modbus read-block changes.
- EMS registers remain `47511` / `47512` with `47512 -> wait -> 47511` ordering.
- Battery strategy remains `P_batt -> 11/12/8`.
- Grid strategy remains `P_grid -> 9/10/1`.
- Existing entity unique IDs, device identity, persistent accounting/runtime/log stores and EMHASS optimizer objective remain unchanged.

v0.27 remains **Beta** while the corrected Hybrid behavior receives field validation on real installations.

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
