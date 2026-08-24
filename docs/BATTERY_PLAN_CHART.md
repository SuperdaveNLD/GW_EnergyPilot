# Battery plan versus actual chart

This document defines the Battery · Plan · Price chart contract used by GW EnergyPilot v0.28 Beta.

## Purpose

The dashboard shows, on one local-day timeline:

- actual GoodWe battery charging and discharging;
- the EMHASS battery-power target that was active historically;
- the current EMHASS future battery schedule;
- the direction-neutral market-price series.

The chart is visualization only. It does not own GoodWe control, EMHASS optimization or persistent financial accounting.

## Actual battery series

Actual bars continue to use the existing `battery_power` entity backed by GoodWe register `35182`:

```text
battery_power < 0 W = charging
battery_power > 0 W = discharging
```

The dashboard requests Recorder 5-minute mean statistics. A solid turquoise/orange bar represents the actual mean battery power in that interval. Near-zero values below the chart display threshold are not drawn as charge/discharge bars, preventing a zero-power sample from being labelled as discharging.

No duplicate battery-power entity, Modbus definition or poll is added.

## Historical active plan

The configured EnergyPilot `P_batt` entity remains the canonical published battery target. EMHASS uses the same sign convention as GoodWe battery power:

```text
P_batt < 0 W = planned charge
P_batt > 0 W = planned discharge
P_batt ~= 0 W = neutral battery target
```

For the elapsed part of the day, the chart reads Home Assistant history for that configured entity. Each state is treated as the published target that remained active until the next state change.

The Home Assistant history API can return the state active at the requested start time with its original timestamp from before local midnight when `include_start_time_state` is enabled. EnergyPilot clamps that valid boundary state to local 00:00 instead of discarding it, so the historical plan does not start late merely because no new `P_batt` state was published exactly at midnight.

This layer is intentionally labelled as the **active historical plan**. It does not claim that an earlier complete forecast horizon remained unchanged after later re-optimizations.

Historical plan blocks are drawn as a dashed translucent overlay above the solid actual bars so planned and actual behavior remain distinguishable even when their power values overlap.

## Current future plan

Current EMHASS publishes the battery-power horizon on the configured `P_batt` entity in the `battery_scheduled_power` attribute. EMHASS constructs rows with a `date` timestamp and the configured entity-name value key.

The read-only Battery & Price WebSocket payload normalizes those rows into timestamped `value_w` points. The older/custom `forecasts` attribute remains accepted as a conservative backwards-compatible fallback, but `battery_scheduled_power` is preferred when both exist.

Future plan blocks are shown with a stronger dashed translucent outline so they cannot be confused with actual battery power.

If neither historical target data nor a current future schedule is available, planned-energy summaries show `—` rather than a false `0.00 kWh`.

## Market-price series

The price data continues to come from the same EnergyPilot runtime price path used by EMHASS. The chart does not discover or calculate a second price source in the browser.

Market prices are interval values, not continuously interpolated measurements. v0.28 therefore renders the price line as a **step series**: one value remains active until the next timestamp. This avoids visually inventing diagonal prices between market intervals.

## Today energy totals

The headline daily battery totals use the existing decoded GoodWe current-day counters when available:

| Direction | Key | Register |
|---|---|---:|
| Charged today | `battery_charge_energy_today` | `35208` |
| Discharged today | `battery_discharge_energy_today` | `35211` |

The secondary graph value integrates Recorder 5-minute mean samples from instantaneous GoodWe battery power register `35182`. The final still-active bucket is clipped at the current time.

These values are **not expected to be mathematically identical**. They are separate measurement paths:

- `35208/35211` are inverter-owned daily energy counters;
- the graph value is a numerical integration of sampled/averaged instantaneous battery power.

The native GoodWe counter remains the headline value. EnergyPilot does not scale or calibrate the Recorder integral to force it to match the inverter counter.

These GoodWe battery counters are also separate from grid import/export accounting and are not used to calculate financial profit.

## Card sizes

The chart offers an Apple-style segmented size selector:

- **S / Compact** — half-width on sufficiently wide dashboards, reduced axes and concise legend;
- **M / Normal** — full-width standard chart;
- **L / Large** — full-width detailed chart with planned charge/discharge summaries.

The selection is stored in the existing browser-local dashboard preference object. It does not add a Home Assistant entity or configuration-entry field. On narrow screens Compact remains full width to preserve readability.

## Window controls

v0.28 also adds macOS-style traffic-light controls to the Battery · Plan · Price card:

- **red** — hide the card immediately;
- **yellow** — switch the card to Compact size;
- **green** — open the detailed graph window.

Hiding the card uses the same existing browser-local dashboard `hidden` preference as the Layout & visibility menu. It does not delete data or change Home Assistant configuration. A hidden Battery · Plan · Price card can be restored from the dashboard layout menu.

The detailed graph uses the same visual controls: red closes the window, yellow closes it and returns the dashboard card to Compact size, and green toggles the detailed window between its normal and maximized presentation. Escape and backdrop-click closing remain supported.

## Read-only API

The existing command remains:

```text
gw_energypilot/battery_price/get
```

v0.28 uses chart schema version `3` and includes:

- `battery_energy` — current GoodWe charged/discharged day counters;
- `battery_plan` — configured entity id, current target, detected schedule attribute and normalized current future schedule;
- timestamped market/effective-price data from the existing EnergyPilot price runtime.

The API does not run an optimization, write an inverter register or modify controller ownership.

## Frontend cache contract

The v0.28 panel wrapper, chart wrapper, chart core, data module and view module use a coordinated v0.28 cache-busting query. Updating only the outer panel URL is insufficient because browsers can cache nested ES modules independently.

## Safety and compatibility

This chart layer changes no:

- GoodWe register address or decoding definition;
- Modbus read block;
- EMS mode or write order;
- Automatic Control decision;
- EMHASS objective;
- entity ID or unique ID;
- persistent grid-accounting store.

Future cost/revenue totals must still consume backend grid-energy deltas and effective buy/sell prices; they must not be derived from this battery visualization.
