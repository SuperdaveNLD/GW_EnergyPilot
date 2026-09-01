# EnergyPilot accounting architecture

GW EnergyPilot keeps physical meter telemetry and derived accounting as two separate layers.

## Physical grid-energy sources

GoodWe exposes two known lifetime smart-meter layouts on ETA/ET hardware. Both layouts remain defined once in `registers.py`; accounting does not maintain a second register map.

| Priority | Direction | EnergyPilot key | GoodWe register | Format |
|---|---|---|---:|---|
| Preferred when the populated pair is available | Export | `meter_total_energy_export_extended` | `36104` | 64-bit energy total |
| Preferred when the populated pair is available | Import | `meter_total_energy_import_extended` | `36120` | 64-bit energy total |
| Fallback | Export | `meter_total_energy_export` | `36015` | legacy float total |
| Fallback | Import | `meter_total_energy_import` | `36017` | legacy float total |

Current upstream GoodWe ET handling enables the extended meter layout for platform 745 devices and for inverters with rated power of at least 15 kW. Field data from the reference GW15K-ETA-G20 also shows populated `36104/36120` totals while the v0.23/v0.24 daily accounting bound only to `36015/36017` did not advance.

The accounting source-selection contract is therefore:

1. prefer `36104/36120` when both decoded values are valid and the pair is populated;
2. if an optional extended block is readable but reports `0/0` while a usable legacy pair exists, keep `36015/36017` for compatibility;
3. otherwise use `36015/36017` when that pair is valid;
4. once extended accounting is active, a transient missing optional extended read does not make accounting fall back to the legacy pair for one sample.

A source change is always a **re-baseline**. EnergyPilot never subtracts the absolute total from one register layout from the absolute total of the other layout. This prevents a lifetime difference of hundreds or thousands of kWh from being recorded as current-day energy.

The existing Home Assistant lifetime entities backed by `36015/36017` keep their unique IDs and state classes for backwards compatibility. The accounting source policy changes the derived accounting input; it does not rename or replace those established entities.

## Persistent EnergyPilot accounting

v0.23 introduced one per-config-entry accounting runtime. It listens to decoded lifetime counters from the normal coordinator and persists its own accounting state in Home Assistant storage.

SEMS+ Beta telemetry deliberately does not map portal lifetime totals into these
canonical keys. While SEMS+ is selected, accounting receives no coherent source
pair and does not accumulate cloud-derived deltas. Returning to a valid local
pair follows the existing source/restart re-baseline rules; the Store is not
deleted and counters from different layouts/sources are never subtracted.

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
active lifetime-counter source pair
```

Each valid coordinator refresh contributes only the positive difference from the previously observed lifetime counter from the **same source pair**. A counter decrease is treated as a re-baseline; EnergyPilot does not invent reset semantics or negative consumption.

## Startup and Recorder bootstrap

The live accounting loop does not depend on Recorder.

For legacy `36015/36017` accounting, EnergyPilot may use Recorder after the first fresh GoodWe poll to recover cumulative values at the current and previous local-midnight boundaries. If that history is available, the daily counters can recover current-day and previous-day totals.

The extended `36104/36120` values were previously diagnostics rather than separate Recorder-facing lifetime entities. When an existing installation first switches to the extended pair, the first selected extended sample is therefore used as a safe baseline and accounting continues from the next counter change. EnergyPilot deliberately does **not** fabricate the part of the current day that occurred before that baseline.

If Recorder is unavailable or usable boundary history does not exist, accounting remains functional. It establishes the current selected GoodWe lifetime values as its live baseline and continues from there.

## Day rollover

During normal operation, the first GoodWe sample after local midnight moves the previous `today` values into `last_period` and starts a new daily total. A telemetry interval that straddles midnight is attributed to the new day only when the before/after samples use the same source pair.

If Home Assistant was offline across an unknown multi-day period, EnergyPilot does not assign the entire unseen lifetime-counter difference to one day. It resets the live day baseline and uses Recorder bootstrap when possible.

## Future financial accounting

The accounting runtime remains the insertion point for costs and revenue.

The planned extension is interval based:

```text
import_cost += delta_import_kWh * effective_buy_price
export_revenue += delta_export_kWh * effective_sell_price
```

The effective prices should come from the same EnergyPilot/EMHASS price configuration already used by the optimizer, including configured buy-price adders and sell-price deductions. Financial accounting must consume the **same selected-source per-refresh energy deltas** as the daily kWh counters; it must not reconstruct costs independently in the frontend.

Expected future outputs include current-day import cost, export revenue and net grid cost/profit while preserving the physical GoodWe lifetime telemetry entities.

## Compatibility boundary

The accounting source selection does not change:

- GoodWe register addresses or decoding definitions;
- Modbus polling blocks;
- EMS modes or writes;
- Automatic Control;
- EMHASS optimization behavior;
- existing lifetime or daily accounting entity unique IDs.

The dashboard is a consumer of accounting entities, not a second accounting implementation.
