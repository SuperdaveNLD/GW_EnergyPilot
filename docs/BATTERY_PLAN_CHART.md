# Battery plan versus actual chart

This document defines the Battery · Plan · Price chart contract used by GW EnergyPilot v0.30 Beta.

## Purpose

The dashboard shows, on one local-day timeline:

- actual GoodWe battery charging and discharging;
- the EMHASS battery-power target that was active historically;
- the latest full EMHASS future battery schedule;
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

## Historical active plan

The configured EnergyPilot `P_batt` entity remains the canonical published battery target. EMHASS and GoodWe battery power use the same sign convention:

```text
P_batt < 0 W = planned charge
P_batt > 0 W = planned discharge
P_batt ~= 0 W = neutral battery target
```

For the elapsed part of the day, the chart reads Home Assistant history for that configured entity. Each state is treated as the published target that remained active until the next state change.

Home Assistant may return the state active at the requested start time with its original timestamp from before local midnight when `include_start_time_state` is enabled. EnergyPilot clamps that valid boundary state to local 00:00 instead of discarding it.

This layer is intentionally the **active historical plan**. It does not claim that an earlier complete forecast horizon remained unchanged after later re-optimizations.

Historical plan blocks are drawn as a dashed translucent overlay above the solid actual bars.

## Current future forecast

### Primary source: official EMHASS plan API

v0.30 reads the latest complete optimization horizon from the official read-only EMHASS endpoint:

```text
GET /api/v1/plan
```

The versioned EMHASS response contains one record per optimization timestep. EnergyPilot consumes only the documented fields needed by this chart:

```text
timestamp = UTC ISO-8601 instant
P_batt    = battery power in W
```

The EMHASS plan schema defines `P_batt > 0` as discharge and `P_batt < 0` as charge. EnergyPilot converts those records to the same timestamped `value_w` contract already used by the chart.

The API plan is preferred because the Home Assistant `P_batt` entity is primarily the currently published control target and, depending on EMHASS version/configuration, may not expose the complete future horizon as an entity attribute.

### Compatibility fallback

If `/api/v1/plan` is unavailable or contains no usable battery horizon, EnergyPilot falls back to the configured `P_batt` entity attributes:

1. `battery_scheduled_power`;
2. legacy/custom `forecasts`.

The dashboard remains usable when an older EMHASS instance has no `/api/v1/plan`; actual battery power and prices are not suppressed by a forecast failure.

Future plan blocks use the same dashed translucent style as the historical plan and are clipped at **NOW** when an interval began just before the current time.

If neither historical target data nor a future schedule is available, planned-energy summaries show `—` rather than a false `0.00 kWh`.

## Market-price series

Price data comes from the same EnergyPilot runtime price path used by EMHASS. The chart does not discover or calculate a second price source in the browser.

Market prices are interval values and are rendered as a step series: one value remains active until the next timestamp.

## Today energy totals

The headline daily battery totals use the existing decoded GoodWe current-day counters when available:

| Direction | Key | Register |
|---|---|---:|
| Charged today | `battery_charge_energy_today` | `35208` |
| Discharged today | `battery_discharge_energy_today` | `35211` |

The secondary graph value integrates Recorder 5-minute mean samples from instantaneous GoodWe battery power register `35182`. The final still-active bucket is clipped at the current time.

These values are separate measurement paths and are not expected to be mathematically identical. The native GoodWe counter remains the headline value; EnergyPilot does not scale the Recorder integral to force a match.

These battery counters are separate from grid import/export accounting and are not used to calculate financial profit.

## Card resizing and window controls

v0.30 keeps the three existing chart sizes internally:

- **Compact**;
- **Normal**;
- **Large**.

The visible S/M/L segmented selector is replaced by EnergyPilot card chrome. On the Battery · Plan · Price card:

- **red `×`** — hide the card;
- **cyan `−`** — cycle Compact → Normal → Large → Compact;
- **mint `↗`** — open the detailed graph.

The selection is stored in the existing browser-local dashboard preference object. No Home Assistant entity or config-entry field is added.

Every dashboard card with an existing `data-ep-card` identity receives a small red close control. Closing a card sets the same `hidden` preference already used by **Dashboard layout & visibility**, so the card can be restored there. No entity or data is deleted.

The detailed graph keeps Apple-inspired circular controls but uses EnergyPilot's own coral/cyan/mint palette instead of copying the macOS traffic-light colors.

## Read-only API

The existing Home Assistant command remains:

```text
gw_energypilot/battery_price/get
```

v0.30 uses chart schema version `4` and includes:

- `battery_energy` — current GoodWe charged/discharged day counters;
- `battery_plan.entity_id` — configured published target entity;
- `battery_plan.current_w` — current published target;
- `battery_plan.points` — normalized latest future horizon;
- `battery_plan.forecast_source` — official EMHASS plan API or HA-entity fallback;
- `battery_plan.generated_at` / `emhass_schema_version` when supplied by EMHASS;
- timestamped market/effective-price data from the existing EnergyPilot price runtime.

The dashboard read does not run an optimization, publish data, write an inverter register or modify controller ownership.

## Safety and compatibility

This chart/UI layer changes no:

- GoodWe register address or decoding definition;
- Modbus read block;
- EMS mode or write order;
- Automatic Control decision;
- EMHASS objective or optimization constraints;
- entity ID or unique ID;
- persistent grid-accounting store.

Future cost/revenue totals must still consume backend grid-energy deltas and effective buy/sell prices; they must not be derived from this battery visualization.
