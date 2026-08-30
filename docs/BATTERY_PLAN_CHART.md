# Battery plan versus actual chart

This document defines the Battery · Plan · Price chart contract used by GW EnergyPilot **v0.50 Beta**.

## Purpose

The dashboard shows, on one local-day timeline:

- actual GoodWe battery charging and discharging;
- the EMHASS battery-power target that was active historically;
- the latest validated EMHASS future battery schedule;
- actual GoodWe battery SOC and the latest validated EMHASS SOC forecast;
- the direction-neutral market-price series.

The chart is visualization only. It does not own GoodWe control, EMHASS optimization or persistent financial accounting.

## Actual battery series

Actual bars use the existing `battery_power` entity backed by GoodWe register `35182`:

```text
battery_power < 0 W = charging
battery_power > 0 W = discharging
```

The dashboard requests Recorder 5-minute mean statistics. A solid turquoise/orange bar represents the actual mean battery power in that interval. Near-zero values below the chart display threshold are not drawn as charge/discharge bars.

No duplicate battery-power entity, Modbus definition or poll is added.

## Actual and forecast SOC

Actual SOC uses the existing `battery_soc` entity backed by GoodWe register `37007`. Its canonical Home Assistant entity contract is already percentage (`0..100%`) with measurement state class. The frontend resolves its current entity ID through the integration's stable unique-ID registry mapping and requests Recorder 5-minute means separately from battery power. It does not apply a `0..1` heuristic: a recorded value of `1` means 1%, not 100%.

Forecast SOC comes only from exact `SOC_opt` rows in the validated official EMHASS schema-1.x plan mirror:

```text
GET /api/v1/plan SOC_opt fraction 0..1
-> validate finite and inside 0..1
-> normalize once to value_pct 0..100
-> battery_soc_plan in battery_price/get
```

EMHASS stores `SOC_opt` as a fraction in the plan and scales it by 100 only when publishing its separate Home Assistant forecast entity. EnergyPilot does not use that output entity for this chart because its runtime ID can be customized and EnergyPilot has no SOC-output entity option. This also prevents double-scaling.

For `number_of_batteries > 1`, EMHASS intentionally has no meaningful bare/fleet `SOC_opt`; it exposes per-battery `SOC_opt_<k>` values. EnergyPilot does not select a battery or fabricate an aggregate. Planned SOC therefore remains unavailable until an explicit battery-selection contract is designed.

The actual SOC line is solid and the forecast SOC line dashed. Both use a fixed `0..100%` axis independent of the power and price axes. Missing Recorder statistics, a failed SOC-only history request, missing `SOC_opt` or an out-of-range point suppresses only the affected SOC line.

## Historical active plan

The configured EnergyPilot `P_batt` entity remains the canonical **published** battery target. EMHASS uses the same sign convention as GoodWe battery power:

```text
P_batt < 0 W = planned charge
P_batt > 0 W = planned discharge
P_batt ~= 0 W = neutral battery target
```

For the elapsed part of the day, the chart reads Home Assistant history for that configured entity. Each state is treated as the published target that remained active until the next state change.

The Home Assistant history API can return the state active at the requested start time with its original timestamp from before local midnight when `include_start_time_state` is enabled. EnergyPilot clamps that valid boundary state to local 00:00 instead of discarding it.

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

## Card sizes and window controls

The chart offers an Apple-style segmented size selector:

- **S / Compact** — half-width on sufficiently wide dashboards, reduced axes and concise legend;
- **M / Normal** — full-width standard chart;
- **L / Large** — full-width detailed chart with planned charge/discharge summaries.

The selection is stored in the existing browser-local dashboard preference object. It does not add a Home Assistant entity or configuration-entry field.

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

The current command uses chart schema version **`5`** and includes:

- `plan_revision` — the EnergyPilot optimization generation currently owning the mirrored plan;
- `battery_energy` — current GoodWe charged/discharged day counters;
- `battery_plan` — configured entity id, current target/source, future points, persistent-plan source, `generated_at`, `valid_until` and restore diagnostics;
- `battery_soc_plan` — optional normalized `value_pct` points, `%` unit and exact official source-column/unit evidence;
- timestamped market/effective-price data from the existing EnergyPilot price runtime.

When `force=true`, or no current plan mirror exists, the read-only API may request a bounded refresh from the official EMHASS plan endpoint. It does not run an optimization, write an inverter register or modify controller ownership.

## Live plan refresh and duplicate protection

The frontend normally keeps a short chart-data cache. v0.33 uses two independent freshness paths:

1. **EnergyPilot optimization revision.** Every successful call through the central orchestrator refreshes `GWEnergyPilotPlanRuntime`, advances `plan_revision` and emits the existing orchestrator dispatcher signal. The existing Optimize Now button entity already subscribes to that signal and exposes orchestrator attributes, so no new entity is added. The chart compares that live revision with the revision stored in its last `battery_price/get` payload and force-refreshes immediately when they differ.
2. **External EMHASS publication fallback.** The configured `P_batt` entity's `last_updated` is still compared with the timestamp in the cached chart payload. A plan changed outside EnergyPilot therefore also bypasses normal cache expiry.

After either freshness signal, the chart calls the read-only API with force refresh, rebuilds the data-dependent contents inside the one connected canonical `.ep-v027-battery-plan-card`, and removes any accidental duplicate card left by a prior layered-render regression. Its S/M/L selector, expand action and window bar stay connected so a refresh between native press and release cannot swallow that interaction.

The duplicate-card guard must therefore **not** return permanently just because a canonical card already exists. It may skip rendering only when the render key is unchanged and no fresh plan evidence exists.

## Frontend cache contract

The active v0.50 top-level panel URL is versioned and the static integration path disables cache headers. Nested historical modules remain part of the active import chain; do not delete or rename them without tracing that chain.

A live browser session also keeps already-evaluated ES modules in its module map. Changing only the top-level panel URL is therefore not sufficient when a historical nested module itself changes. v0.50 loads every import in the active graph through `0.50-ev1`, including the scoped plan-refresh owner. The older v0.33 plan-refresh mechanism remains historical compatibility context.

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
