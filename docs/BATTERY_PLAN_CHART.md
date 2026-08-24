# Battery plan versus actual chart

This document defines the next Battery & Price chart layer prepared after v0.26.

## Purpose

The dashboard should show, on one local-day timeline:

- actual GoodWe battery charging and discharging;
- the EMHASS battery-power target that was active historically;
- the current EMHASS future battery forecast;
- the direction-neutral market-price line.

The chart is visualization only. It does not own GoodWe control, EMHASS optimization or persistent financial accounting.

## Actual battery series

Actual bars continue to use the existing `battery_power` entity backed by GoodWe register `35182`:

```text
battery_power < 0 W = charging
battery_power > 0 W = discharging
```

The dashboard requests Recorder 5-minute mean statistics. A solid turquoise/orange bar represents the actual mean battery power in that interval.

No duplicate battery-power entity, Modbus definition or poll is added.

## Historical plan

The configured EnergyPilot `P_batt` entity remains the canonical battery target. EMHASS uses the same sign convention as GoodWe battery power:

```text
P_batt < 0 W = planned charge
P_batt > 0 W = planned discharge
```

For the elapsed part of the day, the chart reads Home Assistant history for that configured entity. Each state is treated as the published target that remained active until the next state change. This is intentionally labelled as the **active historical plan**, not as a claim that an earlier full forecast remained unchanged after later re-optimizations.

## Future plan

EMHASS publishes the current horizon in the configured `P_batt` entity's `forecasts` attribute. The read-only Battery & Price WebSocket payload normalizes those rows into timestamped `value_w` points.

Future plan blocks are shown with a translucent dashed outline so they cannot be confused with actual battery power.

## Today energy totals

The v0.26 display integrated visible Recorder means and therefore produced an approximation. During a still-active 5-minute bucket the displayed total could also move between refreshes.

The enhanced chart uses the existing decoded GoodWe current-day counters as the headline values when available:

| Direction | Key | Register |
|---|---|---:|
| Charged today | `battery_charge_energy_today` | `35208` |
| Discharged today | `battery_discharge_energy_today` | `35211` |

The graph-derived integration remains visible as a secondary comparison. It clips the final mean bucket at the current time rather than treating a partial bucket as a complete five minutes.

These GoodWe battery counters are separate from grid import/export accounting. They are not used to calculate financial profit.

## Card sizes

The chart offers an Apple-style segmented size selector:

- **S / Compact** — half-width on sufficiently wide dashboards, reduced axes and concise legend;
- **M / Normal** — full-width standard chart;
- **L / Large** — full-width detailed chart with planned charge/discharge summaries.

The selection is stored in the existing browser-local dashboard preference object. It does not add a Home Assistant entity or configuration-entry field. On narrow screens Compact remains full width to preserve readability.

## Read-only API extension

The existing command remains:

```text
gw_energypilot/battery_price/get
```

Its schema is extended with:

- `battery_energy` — current GoodWe charged/discharged day counters;
- `battery_plan` — configured entity id, current target and normalized future forecast points;
- `chart_schema_version` — payload contract version.

The API does not run an optimization, write an inverter register or modify controller ownership.

## Safety and compatibility

This chart layer changes no:

- GoodWe register address or decoding definition;
- Modbus read block;
- EMS mode or write order;
- Automatic Control strategy;
- EMHASS objective;
- entity ID or unique ID;
- persistent grid-accounting store.

Future cost/revenue totals must still consume backend grid-energy deltas and effective buy/sell prices; they must not be derived from this battery visualization.
