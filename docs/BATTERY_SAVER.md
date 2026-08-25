# Battery Saver

GW EnergyPilot v0.31 adds **Battery Saver** to the dashboard **Settings → EMHASS** page.

Battery Saver is an EnergyPilot policy layer on top of EMHASS. It does **not** create a second battery controller and it does not directly write a GoodWe EMS mode when a profile is selected. The selected profile changes the economic preferences of the next EnergyPilot-owned EMHASS optimization; the existing published `P_batt` / `P_grid` outputs and Automatic Control path remain responsible for actual inverter control.

## Hard limits versus soft preferences

The distinction is intentional:

- **Minimum SOC** and **Maximum SOC** are hard optimizer limits.
- The GoodWe on-grid minimum SOC is the canonical EnergyPilot minimum-SOC source and is mirrored into EMHASS.
- Battery Saver thresholds are **soft** economic zones. They can make an action less attractive, but they do not replace the hard SOC limits.
- EnergyPilot clamps its runtime `soc_final` request to the effective EMHASS minimum/maximum SOC before every owned optimization.

For example, if the hard minimum SOC is 23%, the Battery Saver low-SOC soft thresholds of 5%, 10% or 15% are below the reachable operating range. EnergyPilot deliberately does not invent a second 35–45% reserve. The configured 23% remains the real lower operating limit.

## Modes

| Mode | Low-SOC threshold | Low-SOC cost | High-SOC threshold | High-SOC cost | Power-stress cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| **Mad-Steve** | 5% | 0% × price reference | 98% | 0% × price reference | 0% × price reference |
| **Gold Rush** | 5% | 0% × price reference | 96% | 5% × price reference | 3% × price reference |
| **Balanced** | 10% | 5% × price reference | 95% | 10% × price reference | 8% × price reference |
| **Battery Saver** | 15% | 10% × price reference | 90% | 25% × price reference | 20% × price reference |

All four profiles use `battery_stress_segments = 10`.

### Mad-Steve

Maximum economic freedom. EnergyPilot adds no extra low-SOC, high-SOC or high-power cost. EMHASS may use the complete configured hard SOC range and available battery power whenever the normal optimization objective finds that economical.

This is behaviorally equivalent to an existing EMHASS configuration where `battery_soc_deficit_cost`, `battery_soc_surplus_cost` and `battery_stress_cost` are all zero.

### Gold Rush

Profit remains the priority, while very small-value cycling is discouraged. There is no extra low-SOC cost, a light high-SOC cost above 96%, and a light quadratic power-stress cost. Large price spreads can still justify full battery power.

### Balanced

The recommended general-purpose profile. It applies moderate penalties for entering the final low-SOC region, dwelling above 95%, and using high battery power where a lower-power alternative has nearly the same economic result.

### Battery Saver

Battery preservation has a materially higher economic value. Marginal cycling, prolonged high SOC and high battery power are more likely to be skipped unless the forecasted financial advantage is large enough to compensate for the additional virtual costs.

## Price-relative costs

EMHASS penalty values use the optimizer's active currency. Hard-coding one absolute value would therefore behave differently in EUR, NOK or another currency.

EnergyPilot derives a positive **price reference** for every Battery Saver-managed optimization:

1. use the median of positive effective runtime import prices when EnergyPilot supplies a timestamped `load_cost_forecast`;
2. if runtime prices contain no positive values, use the median non-zero absolute price magnitude;
3. when EMHASS owns the price forecast, fall back to its configured peak/off-peak/sell price values;
4. use `0.20` only as a final safe fallback when no usable price value exists.

The profile percentages in the table are multiplied by this reference. This keeps the policy strength proportional to the market values seen by the optimizer instead of tying it to one currency.

## LFP design rationale

GW EnergyPilot does not claim that a particular profile extends battery life by a fixed percentage. Battery ageing depends on cell chemistry, temperature, depth of discharge, C-rate, calendar time and the battery-management system.

For the GoodWe LFP battery family used by the primary GW15K-ETA-G20 reference installation, the low-SOC zones are intentionally much lower than the first experimental Battery Saver proposal. GoodWe specifies deep-cycle operation for its LFP batteries; a normal low SOC inside the BMS operating window is not the same as cell over-discharge below the permitted voltage. EnergyPilot therefore leaves reserve ownership to the hard Minimum SOC control instead of manufacturing a high soft floor.

The profiles put relatively more weight on avoiding unnecessary high-SOC dwell and low-value high-power cycling. The stress cost remains a soft optimizer cost: it does not reduce the configured GoodWe/EMHASS maximum power and cannot prevent full power when the economic signal is strong enough.

## Ownership and compatibility

Battery Saver is opt-in for upgraded installations.

- An existing installation with zero penalties is reported as **Mad-Steve-like**, but EnergyPilot does not claim ownership until the user selects a mode.
- Existing non-zero/custom EMHASS penalty values are reported as **custom** and are not overwritten until the user explicitly selects an EnergyPilot Battery Saver mode.
- After a mode has been selected, EnergyPilot owns the six Battery Saver EMHASS fields for its own optimizations.
- If the first profile application or optimization fails, EnergyPilot restores the previous config-entry mode and the previous Battery Saver-owned EMHASS fields.
- Multi-battery EMHASS configurations are rejected by the Battery Saver selector because EnergyPilot cannot safely infer per-battery ownership from one GoodWe integration.
- Non-zero power-stress modes require EMHASS 0.18.1 or newer when the EMHASS version is known.

The standard Home Assistant options flow and EnergyPilot's generic settings pages preserve the separately managed `battery_saver_mode` option.

## EMHASS publication contract

EnergyPilot owns **when to perform a complete optimization**. EMHASS owns **which row of that plan is published at the current optimization timestep**.

For every EnergyPilot-owned optimization v0.31 enforces:

- `continual_publish = true`
- `method_ts_round = first`
- `set_use_battery = true`
- `inverter_is_hybrid = true`

`set_use_pv` is deliberately **not** forced. A battery installation without PV is valid. PV sensor and forecast mappings are synchronized only when the customer's EMHASS configuration has `set_use_pv = true`.

The runtime flow is therefore:

```text
Battery Saver mode
        ↓
EnergyPilot price reference + hard SOC limits
        ↓
Battery Saver EMHASS config fields via /set-config
        ↓
EnergyPilot dayahead optimization
        ↓
initial /action/publish-data
        ↓
EMHASS continual_publish at every optimization_time_step
        ↓
fresh P_batt / P_grid state
        ↓
existing EnergyPilot Automatic Control
        ↓
GoodWe EMS command
```

There is no second EnergyPilot timer that republishes the plan every 15 minutes.

## Minimum SOC synchronization

The on-grid Minimum SOC NumberEntity keeps the existing entity ID/unique ID contract. In v0.31 its startup direction is corrected:

1. wait for the canonical GoodWe on-grid minimum-SOC telemetry;
2. display that value on the EnergyPilot slider;
3. mirror the value to EMHASS `battery_minimum_state_of_charge` when different;
4. on an explicit slider change, write and verify GoodWe first, then write EMHASS;
5. if the EMHASS write fails, roll GoodWe back to the previous verified value.

EnergyPilot also reasserts the available GoodWe minimum SOC before its own optimization runs and clamps `soc_final` to the hard EMHASS range.
