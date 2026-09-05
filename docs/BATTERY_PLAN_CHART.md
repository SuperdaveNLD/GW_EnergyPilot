# Battery plan versus actual chart

This document defines the Battery · Plan · Price chart contract used by GW EnergyPilot **v1.3.0-beta.4** and retained from v1.0.0 Stable.

## Purpose

The dashboard shows, on one selectable Home Assistant-local timeline:

- actual GoodWe battery charging and discharging;
- the EMHASS battery-power target that was active historically;
- the latest validated EMHASS future battery schedule;
- actual GoodWe battery SOC and the historical/current wanted EMHASS SOC;
- actual combined PV production and the validated expected solar-production
  series in every chart size and expanded views;
- estimated solar/grid origin for battery charge and solar/battery origin for
  grid export in the detailed view;
- the direction-neutral market-price series;
- verified EV anti-discharge blocked and charge-permitted intervals derived
  from the canonical execution ledger.

The chart is visualization only. It does not own GoodWe control, EMHASS optimization or persistent financial accounting.

## Chart ranges and time contract

The connected chart header offers three independent range choices:

- **12h** — a rolling zoom from six elapsed hours before `NOW` through six elapsed hours after `NOW`;
- **24h** — the fixed Home Assistant-local day from 00:00 through the next 00:00;
- **36h** — the fixed Home Assistant-local window from today 00:00 through tomorrow 12:00.

`24h` remains the backwards-compatible default. The selected range is stored under `ranges.battery-price` in the existing browser-local `gw_energypilot_dashboard_v008` preference object. It adds no config-entry option, entity or Home Assistant Store.

The backend derives `NOW`, local-day boundaries and axis ticks from `hass.config.time_zone`. Absolute instants are serialized in UTC together with the configured IANA timezone and local calendar-day offsets. A spring DST day is therefore 23 elapsed hours and an autumn DST day 25 elapsed hours while both remain the fixed **24h / today** operator choice. The rolling 12h zoom always spans exactly twelve elapsed hours. Invalid timezone input fails safe to UTC.

One cached read covers the earliest possible history boundary — at most six hours before local midnight during the early morning — through tomorrow 12:00 for price and plan points. Range clicks filter this shared dataset locally and do not call Recorder or the plan API again. Compared with the former today-only request, Recorder/history load is unchanged after 06:00 and increases by at most six hours before 06:00. The existing five-minute data-cache and explicit `plan_revision` invalidation remain authoritative.

The visible horizon is bounded by available source data. EnergyPilot does not extrapolate an expired EMHASS plan or invent tomorrow prices when the upstream plan/price provider has not published them yet.

## Actual battery series

Actual bars use the existing `battery_power` entity backed by GoodWe register `35182`:

```text
battery_power < 0 W = charging
battery_power > 0 W = discharging
```

The dashboard requests Recorder 5-minute mean statistics. A solid turquoise/orange bar represents the actual mean battery power in that interval. Near-zero values below the chart display threshold are not drawn as charge/discharge bars.

No duplicate battery-power entity, Modbus definition or poll is added.

## Actual-flow source attribution

The v0.51 feature layer requests Recorder 5-minute means for the existing `battery_power`,
combined display-only `pv_generation_power`, `total_load_power` and
`meter_total_power_fast` entities in one statistics request. Large and expanded
views use a load-first balance estimate:

```text
charge = max(-battery_power, 0)
solar surplus = max(PV - load, 0)
solar -> battery = min(charge, solar surplus)
grid -> battery = min(remaining charge, measured grid import)

grid export = max(measured grid export, 0)
solar -> grid = min(grid export, solar surplus remaining after charge)
battery -> grid = min(remaining export, battery discharge)
```

Any remaining flow is drawn with a hatched unknown source. Missing PV, load or
grid samples reduce confidence and are never replaced with a fabricated source.
The colors are green for grid → battery, ochre for solar → battery, orange for
battery → grid and yellow/ochre for solar → grid. Compact and Normal retain the
existing battery charge/discharge bars.

This is an instantaneous visualization estimate. It is not settlement-grade
energy allocation and does not feed grid accounting, EMHASS, Automatic Control
or financial totals. Recorder remains optional; missing statistics suppress
only attribution.

## Actual and expected solar production

All chart sizes (S, M and L) and expanded views show the combined display-only
`pv_generation_power` series as a solid yellow **Actual solar production**
line. It is the same bounded Recorder 5-minute mean data already used for
actual-flow attribution. The yellow dashed **Forecast solar production** step
line comes only from non-negative `P_PV` values in the current validated
official EMHASS plan mirror:

```text
EMHASS GET /api/v1/plan P_PV
-> validated current plan mirror
-> pv_plan in battery_price/get
-> every chart size and expanded view
```

The forecast is not derived from a similarly named Home Assistant entity, is
not extrapolated past available plan rows, and is absent when the active plan
uses the Home Assistant schedule fallback or does not expose `P_PV`. Both
series share the chart's power axis with charge/discharge, but do not enter
Automatic Control, accounting or any EMS decision.

## Actual and forecast SOC

Actual SOC uses the existing `battery_soc` entity backed by GoodWe register `37007`. Its canonical Home Assistant entity contract is already percentage (`0..100%`) with measurement state class. The frontend resolves its current entity ID through the integration's stable unique-ID registry mapping and requests Recorder 5-minute means separately from battery power. It does not apply a `0..1` heuristic: a recorded value of `1` means 1%, not 100%.

Forecast SOC comes only from exact `SOC_opt` rows in the validated official EMHASS schema-1.x plan mirror:

```text
GET /api/v1/plan SOC_opt fraction 0..1
-> validate finite and inside 0..1
-> normalize once to value_pct 0..100
-> retain source start and derive target_at = start + validated plan timestep
-> battery_soc_plan in battery_price/get
```

EMHASS stores `SOC_opt` as a fraction in the plan and scales it by 100 only when publishing its separate Home Assistant forecast entity. EnergyPilot does not use that output entity for this chart because its runtime ID can be customized and EnergyPilot has no SOC-output entity option. This also prevents double-scaling.

EMHASS reconstructs each `SOC_opt` value after applying that row's battery
power over one optimization timestep. Its plan-row timestamp is therefore the
power-interval start, while the SOC value is the interval-end target. The
backend preserves the source `start` for evidence and exposes an explicit
`target_at` calculated from the mirrored plan's inferred timestep. The
frontend plots only `target_at`; it does not hardcode 15 minutes or shift
`P_batt`, price or actual Recorder data. For example, a 50% `SOC_opt` row at
19:00 in a 15-minute plan is drawn at 19:15.

For `number_of_batteries > 1`, EMHASS intentionally has no meaningful bare/fleet `SOC_opt`; it exposes per-battery `SOC_opt_<k>` values. EnergyPilot does not select a battery or fabricate an aggregate. Planned SOC therefore remains unavailable until an explicit battery-selection contract is designed.

The actual SOC line is solid and the **Wanted SOC** line remains dashed. For
elapsed time the v0.51 feature layer uses the `SOC_opt` snapshot stored with each execution event;
the current/future segment uses the latest validated official plan. This keeps
historical intent immutable when a later optimization changes the horizon. On
an upgraded installation before execution events exist, the previous current
plan fallback remains available. New snapshots persist `soc_opt_target_at`;
legacy snapshots without an evidenced interval end are not guessed and age out
under the existing seven-day retention policy.

Both lines use a fixed `0..100%` axis independent of the power and price axes.
Missing Recorder statistics, missing execution history, missing `SOC_opt` or
an out-of-range point suppresses only the affected segment.

## Historical active plan

The configured EnergyPilot `P_batt` entity remains the canonical **published** battery target. EMHASS uses the same sign convention as GoodWe battery power:

```text
P_batt < 0 W = planned charge
P_batt > 0 W = planned discharge
P_batt ~= 0 W = neutral battery target
```

For the elapsed part of the loaded history window, the chart reads Home Assistant history for that configured entity. Each state is treated as the published target that remained active until the next state change.

The Home Assistant history API can return the state active at the requested start time with its original earlier timestamp when `include_start_time_state` is enabled. EnergyPilot clamps that valid state to the requested history boundary — local 00:00 for the fixed views, or at most six hours earlier for the rolling early-morning view — instead of discarding it.

This layer is intentionally the **active historical plan**. It does not rewrite history using the newest complete optimization horizon.

Historical plan blocks are drawn as a dashed translucent overlay above the solid actual bars so planned and actual behavior remain distinguishable even when values overlap.

## Current future plan source order

EMHASS remains the canonical plan owner. Since v0.33 the chart no longer depends only on the current Home Assistant entity attributes for the future horizon.

Preferred source:

```text
EMHASS GET /api/v1/plan
-> GWEnergyPilotPlanRuntime validated mirror
-> battery_price/get payload
```

The per-entry mirror is stored in:

```text
gw_energypilot.plan.<entry_id>
```

It includes normalized timestamped `P_batt`/`P_grid` points, generated time, inferred timestep and an explicit `valid_until` boundary. See `docs/EMHASS_PLAN_RUNTIME.md`.

Compatibility fallback:

- current `battery_scheduled_power` on the configured `P_batt` entity;
- older/custom `forecasts` attribute.

When the persistent official plan exists, it is preferred over the Home Assistant attribute remainder. This gives the chart the same plan-resilience source as Automatic Control while keeping the live entity as the control system's first current-value source.

Future plan blocks use a stronger dashed translucent outline so they cannot be confused with actual battery power.

If neither historical target data nor a current future schedule is available, planned-energy summaries show `—` rather than a false `0.00 kWh`.

## Plan validity

The persistent plan mirror is stepwise. EnergyPilot infers the optimization timestep from adjacent timestamps and calculates the end of the final interval.

For control, no plan value is extrapolated after `valid_until`.

The chart may display the stored horizon for its timestamped future visualization, but that does not extend controller validity or turn old points into current commands.

## Market-price series

The price data continues to come from the same EnergyPilot runtime price path used by EMHASS. The chart does not discover or calculate a second price source in the browser.

Market prices are interval values, not continuously interpolated measurements. The price line remains a **step series**: one value remains active until the next timestamp.

## Today energy totals

The headline daily battery totals use the existing decoded GoodWe current-day counters when available:

| Direction | Key | Register |
|---|---|---:|
| Charged today | `battery_charge_energy_today` | `35208` |
| Discharged today | `battery_discharge_energy_today` | `35211` |

The secondary graph value integrates Recorder 5-minute mean samples from instantaneous GoodWe battery power register `35182`. The final still-active bucket is clipped at the current time.

These values are **not expected to be mathematically identical**. They are separate measurement paths. The native GoodWe counter remains the headline value; EnergyPilot does not scale or calibrate the Recorder integral to force a match.

These GoodWe battery counters are separate from grid import/export accounting and are not used to calculate financial profit.

Changing the visible chart range does not change these headline **today** totals. The Recorder comparison continues to integrate only the fixed Home Assistant-local day, while planned charge/discharge in L/expanded presentation is explicitly calculated for the selected visible window.

## Card sizes and window controls

The chart offers separate Apple-style segmented selectors for range (`12h / 24h / 36h`) and size:

- **S / Compact** — half-width on sufficiently wide dashboards, reduced axes and concise legend;
- **M / Normal** — full-width standard chart;
- **L / Large** — full-width detailed chart with planned charge/discharge summaries.

The selection is stored in the existing browser-local dashboard preference object. It does not add a Home Assistant entity or configuration-entry field.

On coarse-pointer and narrow displays, every range and size segment has a real
minimum 44 × 44 CSS-pixel button box. The visible segmented styling remains
compact, but the browser no longer has to land a touch inside the earlier
27-pixel-high target. The chart expand/footer actions and execution-history
open/close controls use the same minimum target size.

Traffic-light controls remain:

- **red** — hide/close;
- **yellow** — compact/restore compact;
- **green** — open/toggle detailed presentation.

Hiding the card uses the existing browser-local `hidden` preference and does not delete data or change Home Assistant configuration.

## Read-only API

The existing command remains:

```text
gw_energypilot/battery_price/get
```

The current command uses chart schema version **`7`** and includes:

- `plan_revision` — the EnergyPilot optimization generation currently owning the mirrored plan;
- `chart_time` — authoritative Home Assistant timezone, current instant, local-day/history/maximum boundaries and the rolling/fixed window ticks;
- `battery_energy` — current GoodWe charged/discharged day counters;
- `battery_plan` — configured entity id, current target/source, future points, persistent-plan source, `generated_at`, `valid_until` and restore diagnostics;
- `battery_soc_plan` — optional normalized `value_pct` points, original
  interval `start`, explicit interval-end `target_at`, inferred `step_seconds`,
  `interval_end` timestamp semantics, `%` unit and exact official
  source-column/unit evidence;
- `pv_plan` — optional, non-negative official-plan `P_PV` points in W with
  explicit source-column evidence; it is display-only and has no Home
  Assistant-entity fallback;
- timestamped market/effective-price data from the existing EnergyPilot price runtime.
- `execution` — UTC boundaries, Home Assistant timezone, retention metadata,
  exact 48-hour decision evidence, a conditional 24-hour projection and its
  explicit assumptions.

The future projection joins exact timestamped `P_batt`, `P_grid`, optional
`P_PV`, optional `P_Load` and `SOC_opt` rows from the current validated plan.
It uses the shared controller strategy mapping but does not predict manual/EV
ownership changes, write success or GoodWe read-back. Optional `P_PV` and
`P_Load` are dashboard-only and are never control sources. Its plan evidence
retains `soc_opt_target_at` separately from the projection command's interval
start.

When `force=true`, or no current plan mirror exists, the read-only API may request a bounded refresh from the official EMHASS plan endpoint. It does not run an optimization, write an inverter register or modify controller ownership.

## Live plan refresh and duplicate protection

The frontend normally keeps a short chart-data cache. v0.33 uses two independent freshness paths:

1. **EnergyPilot optimization revision.** Every successful call through the central orchestrator refreshes `GWEnergyPilotPlanRuntime`, advances `plan_revision` and emits the existing orchestrator dispatcher signal. The existing Optimize Now button entity already subscribes to that signal and exposes orchestrator attributes, so no new entity is added. The chart compares that live revision with the revision stored in its last `battery_price/get` payload and force-refreshes immediately when they differ.
2. **External EMHASS publication fallback.** The configured `P_batt` entity's `last_updated` is still compared with the timestamp in the cached chart payload. A plan changed outside EnergyPilot therefore also bypasses normal cache expiry.

After either freshness signal, the chart calls the read-only API with force refresh, rebuilds the data-dependent contents inside the one connected canonical `.ep-v027-battery-plan-card`, and removes any accidental duplicate card left by a prior layered-render regression. Its 12h/24h/36h and S/M/L selectors, expand action and window bar stay connected so a refresh between native press and release cannot swallow that interaction.

The duplicate-card guard must therefore **not** return permanently just because a canonical card already exists. It may skip rendering only when the render key is unchanged and no fresh plan evidence exists.

## Frontend cache contract

The active v1.3.0-beta.4 top-level panel URL is versioned and the static integration path disables cache headers. Nested historical modules remain part of the active import chain; do not delete or rename them without tracing that chain.

A live browser session also keeps already-evaluated ES modules in its module map. Changing only the top-level panel URL is therefore not sufficient when a historical nested module itself changes. v1.3.0-beta.4 loads its presentation wrapper and every inner feature import through `1.3.0-beta.4`, including the strategy, permanent controls, settings, scoped plan-refresh and execution-history owners. The older v1.0.0 and v0.33 cache/plan-refresh mechanisms remain historical compatibility context.

## EV protection underlays

The graph reuses `gw_energypilot.execution.<entry_id>`; it does not add a
second EV timeline Store or API. A solid underlay represents a verified
`ev_anti_discharge_hold` decision. A striped underlay represents a verified
explicit charging decision (`ev_charge_allowed`, `ev_battery_charge`,
`ev_grid_import_charge` or `ev_charge_fallback`). Unverified, mismatched,
waiting and failed records produce no interval.

Each record includes the current `runtime_session_id`. Adjacent events form an
interval only inside the same Home Assistant runtime session, and only the
current session can extend to the API response time. This deliberately leaves
a gap across restart instead of presenting an EV protection state that was not
observed. `execution_history_revision` is cache invalidation evidence only; it
does not affect control or Recorder data.

The optimization revision and `P_batt` freshness checks are independent of ordinary five-minute chart-data cache expiry, so a newly published plan does not intentionally remain stale for that full interval.

## Safety and compatibility

This chart layer changes no:

- GoodWe register address or decoding definition;
- Modbus read block;
- EMS mode or write order;
- Automatic Control decision policy;
- EMHASS optimizer objective;
- entity ID or unique ID;
- persistent grid-accounting store.

The new plan Store is a read-only resilience mirror of EMHASS plan output for EnergyPilot consumption; it is not a second configuration database.

Future cost/revenue totals must still consume backend grid-energy deltas and effective buy/sell prices; they must not be derived from this battery visualization.
