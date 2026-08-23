# EnergyPilot accounting architecture

GW EnergyPilot keeps physical meter telemetry and derived accounting as two separate layers.

## Canonical physical sources

The GoodWe smart-meter lifetime counters remain the only physical source of truth for grid energy:

| Direction | EnergyPilot key | GoodWe register | Home Assistant state class |
|---|---|---:|---|
| Import | `meter_total_energy_import` | `36017` | `total_increasing` |
| Export | `meter_total_energy_export` | `36015` | `total_increasing` |

Do not introduce a second Modbus register map or a second competing lifetime-energy source for normal accounting.

## Persistent EnergyPilot accounting

v0.23 adds one per-config-entry accounting runtime. It listens to the decoded lifetime counters from the normal coordinator and persists its own accounting state in Home Assistant storage.

Initial outputs are:

- `grid_energy_imported_today`;
- `grid_energy_exported_today`.

Both are daily `total_increasing` energy sensors. Their `last_period` attribute contains the completed previous-day value when it is known.

The accounting state stores:

```text
accounting day
current-day imported kWh
current-day exported kWh
previous-day imported kWh
previous-day exported kWh
last observed GoodWe import lifetime total
last observed GoodWe export lifetime total
```

Each valid coordinator refresh contributes only the positive difference from the previously observed lifetime counter. A counter decrease is treated as a re-baseline; EnergyPilot does not invent reset semantics or negative consumption.

## Startup and Recorder bootstrap

The live accounting loop does not depend on Recorder.

For an existing installation upgrading to v0.23, EnergyPilot may use Recorder once after the first fresh GoodWe poll to recover the cumulative counter values at the current and previous local-midnight boundaries. If that history is available, the new daily counters can start with the already-consumed/imported values for the current day instead of starting at zero at upgrade time.

If Recorder is unavailable or boundary history does not exist, accounting remains functional. It establishes the current GoodWe lifetime values as its live baseline and continues from there.

## Day rollover

During normal operation, the first GoodWe sample after local midnight moves the previous `today` values into `last_period` and starts a new daily total. A normal telemetry interval that straddles midnight is attributed to the new day.

If Home Assistant was offline across an unknown multi-day period, EnergyPilot does not assign the entire unseen lifetime-counter difference to one day. It resets the live day baseline and uses Recorder bootstrap when possible.

## Future financial accounting

The accounting runtime is intentionally the future insertion point for costs and revenue.

The planned extension is interval based:

```text
import_cost += delta_import_kWh * effective_buy_price
export_revenue += delta_export_kWh * effective_sell_price
```

The effective prices should come from the same EnergyPilot/EMHASS price configuration already used by the optimizer, including configured buy-price adders and sell-price deductions. Financial accounting must consume the same per-refresh energy deltas as the daily kWh counters; it must not reconstruct costs independently in the frontend.

Expected future outputs include current-day import cost, export revenue and net grid cost/profit, while preserving the physical GoodWe lifetime counters unchanged.

## Compatibility boundary

The accounting layer does not change:

- GoodWe register definitions;
- Modbus polling blocks;
- EMS modes or writes;
- Automatic Control;
- EMHASS optimization behavior;
- the existing lifetime energy entity unique IDs.

The dashboard is a consumer of accounting entities, not a second accounting implementation.
