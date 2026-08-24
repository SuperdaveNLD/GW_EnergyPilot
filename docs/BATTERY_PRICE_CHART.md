# Battery and price chart architecture

The GW EnergyPilot dashboard combines actual battery behavior and the runtime electricity price on one local-day timeline.

## Electrical series

The bars use the existing Home Assistant `battery_power` entity backed by GoodWe register `35182`.

GW EnergyPilot's established sign convention remains authoritative:

```text
battery_power < 0 W = charging
battery_power > 0 W = discharging
```

The frontend requests Home Assistant Recorder `5minute` mean statistics from local midnight through the current time. Charging is drawn below the zero line and discharging above it. No new battery-power entity or duplicate Modbus read path is introduced.

The **Charged today** and **Discharged today** summaries are approximate integrations of those same displayed 5-minute mean buckets. They are chart summaries, not replacement lifetime/daily accounting entities.

## Price series

The thin line shows the reconstructed wholesale/market price for the same local day.

EnergyPilot does not discover or calculate prices independently in the browser. The active orchestrator remains the canonical runtime price-source implementation:

```text
market price + configured buy adder = effective EMHASS load_cost
market price - configured sell deduction = effective EMHASS prod_price
```

The v0.26 orchestrator layer caches the exact effective timestamped maps supplied through the existing EnergyPilot price path and exposes a read-only WebSocket payload containing:

- market price;
- effective buy price;
- effective sell price;
- source, market area, currency and cache timestamp.

The chart draws the market-price line because it is the single direction-neutral price that can be compared with both charging and discharging. Effective buy/sell values remain in the payload for later tooltips and financial accounting.

## Read-only dashboard API

```text
gw_energypilot/battery_price/get
```

The command is read-only and does not start an EMHASS optimization. It uses a short in-memory price cache. If the cache is stale and no optimization is running, the command refreshes prices through the same orchestrator method used by optimization.

If runtime timestamped prices are unavailable, the battery bars remain usable and the dashboard explains why the line is absent.

## Time alignment

The compact card covers the current Home Assistant local day:

```text
00:00 local time -> 24:00 local time
```

Actual battery bars stop at the current time. Available runtime price points may continue through the rest of the day. A vertical `NOW` marker separates observed behavior from future price slots.

Timestamps retain their timezone offsets, so daylight-saving transitions use the actual local-day duration rather than assuming every day is exactly 24 elapsed hours.

## Dashboard ownership

The chart is a full-width dashboard card layered on the existing v0.26 frontend. It participates in the existing visibility menu under **Battery & price**, but it does not introduce a second dashboard-layout store or replace the current card ordering implementation.

An expand action opens the same data in a larger read-only graph.

## Future cost and revenue accounting

The chart is visualization only. Future persistent financial counters must use the accounting runtime's selected grid-energy deltas together with the effective buy/sell price series:

```text
import cost    += imported delta kWh * effective buy price
export revenue += exported delta kWh * effective sell price
```

Financial totals must not be reconstructed from chart pixels, battery-power bars or independent frontend calculations.
