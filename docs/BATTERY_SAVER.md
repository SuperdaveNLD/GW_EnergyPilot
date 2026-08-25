# Battery Saver

GW EnergyPilot v0.31 introduced **Battery Saver** on **Settings → EMHASS**. v0.33 refines the four profiles using field-tested anti-churn costs and keeps the existing hard/soft ownership model.

Battery Saver is an EnergyPilot policy layer on top of EMHASS. It does **not** create a second battery controller and it does not directly write a GoodWe EMS mode when a profile is selected. The selected profile changes the economic preferences of the next EnergyPilot-owned EMHASS optimization; the published `P_batt` / `P_grid` outputs and Automatic Control path remain responsible for actual inverter control.

## Hard limits versus soft preferences

The distinction is intentional:

- **Minimum SOC** and **Maximum SOC** are hard optimizer limits.
- The GoodWe on-grid minimum SOC is the canonical EnergyPilot minimum-SOC source and is mirrored into EMHASS.
- Battery Saver thresholds are **soft** economic zones. They make an action less attractive but do not replace the hard SOC limits.
- EnergyPilot clamps its runtime `soc_final` request to the effective EMHASS minimum/maximum SOC before every owned optimization.

For example, if the hard maximum SOC is 96%, a Gold Rush soft high-SOC threshold of 96% does not create a second limit: the hard 96% setting already prevents the optimizer from moving higher. If another installation allows a higher hard maximum, Gold Rush starts applying its high-SOC dwell penalty above 96% while still allowing that region when the financial value is sufficient.

## Two different battery costs

v0.33 deliberately separates **whether a battery transaction is worth doing** from **how hard the battery should be driven**.

### Anti-churn transaction cost

All four EnergyPilot profiles now apply the same small EMHASS charge/discharge weight:

```text
weight_battery_charge    = 1.5% × price reference
weight_battery_discharge = 1.5% × price reference
```

These weights are linear costs on every charged or discharged kWh. A charge/discharge round trip therefore has to overcome both weights before a very small price spread is attractive.

This common floor is intentional. Even **Mad-Steve** should not reverse the battery merely because two adjacent quarter-hours differ by a fraction of a cent.

The factor is based on field comparison on the primary installation. A manual test with approximately `0.005` currency/kWh on both charge and discharge removed several low-value quarter-hour charge/discharge reversals while preserving the high-value evening dispatch up to the physical inverter/battery limits. With the observed EnergyPilot price reference of about `0.3105`, the v0.33 factor produces approximately `0.004658` per direction.

The factor is price-relative instead of being hard-coded in EUR so that the policy scales with the currency/magnitude used by the active EMHASS price forecast.

### Battery power-stress cost

`battery_stress_cost` is a different mechanism. Current EMHASS models it as a piecewise-linear approximation of a quadratic power cost. It therefore makes high instantaneous battery power progressively more expensive.

This explains why a plan can deliberately use 9–12 kW instead of 15 kW even when 15 kW is physically available: if several nearby timesteps have similar prices, EMHASS can spread the same energy over them and reduce the quadratic stress penalty.

The four EnergyPilot modes keep different power-stress factors so that the operator can choose how strongly this smoothing should influence the optimization.

## Modes

| Mode | Low-SOC threshold | Low-SOC cost | High-SOC threshold | High-SOC cost | Power-stress cost | Charge / discharge anti-churn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Mad-Steve** | 5% | 0% × price reference | 98% | 0% × price reference | 0% × price reference | 1.5% / 1.5% × price reference |
| **Gold Rush** | 5% | 0% × price reference | **96%** | 5% × price reference | 3% × price reference | 1.5% / 1.5% × price reference |
| **Balanced** | 10% | 5% × price reference | 95% | 10% × price reference | 8% × price reference | 1.5% / 1.5% × price reference |
| **Battery Saver** | 15% | 10% × price reference | 90% | 25% × price reference | 20% × price reference | 1.5% / 1.5% × price reference |

All four profiles use `battery_stress_segments = 10`.

### Mad-Steve

Maximum economic freedom, but no low-value micro-arbitrage. EnergyPilot adds only the shared anti-churn charge/discharge weights. There is no additional low-SOC, high-SOC or high-power stress cost.

A pre-v0.33 EMHASS configuration with all Battery Saver costs and both battery weights at zero is therefore **more aggressive than current Mad-Steve**. Upgraded unmanaged/custom values remain untouched until the user explicitly selects a profile.

### Gold Rush

Profit remains the priority. Gold Rush uses the shared anti-churn floor, no extra low-SOC cost, a light high-SOC cost above **96%**, and a light quadratic power-stress cost. Large price spreads can still justify high/full battery power, while the optimizer is slightly less willing to remain very near full SOC.

### Balanced

The recommended general-purpose profile. It combines the shared anti-churn floor with moderate penalties for entering the final low-SOC region, dwelling above 95%, and using high battery power where a lower-power alternative has nearly the same economic result.

### Battery Saver

Battery preservation has a materially higher economic value. The shared anti-churn floor remains, while prolonged high/low SOC and high instantaneous power receive the strongest virtual penalties. The optimizer can still use the hard operating range or full power when the forecasted benefit is large enough.

## Why battery power can be below 15 kW

A `P_batt` target below the configured 15 kW maximum is not automatically evidence of an optimizer error.

For the hybrid inverter model, three different constraints can bind:

1. **Battery limit** — `battery_charge_power_max` / `battery_discharge_power_max`.
2. **Hybrid inverter AC limit** — PV and battery share the same inverter path. During evening discharge, for example, `PV + P_batt` can already produce 15 kW AC while `P_batt` itself is only 14–14.8 kW.
3. **Economic optimum** — when neither physical limit binds, EMHASS may reserve energy for a later higher-price timestep or reduce instantaneous power because of `battery_stress_cost`.

This distinction is important when reviewing an optimization table: compare `P_batt`, `P_PV`, `P_hybrid_inverter`, SOC and the neighboring prices before concluding that available battery power was left unused.

## Price-relative costs

EMHASS penalty values use the optimizer's active currency. Hard-coding one absolute value would behave differently in EUR, NOK or another currency.

EnergyPilot derives a positive **price reference** for every Battery Saver-managed optimization:

1. use the median of positive effective runtime import prices when EnergyPilot supplies a timestamped `load_cost_forecast`;
2. if runtime prices contain no positive values, use the median non-zero absolute price magnitude;
3. when EMHASS owns the price forecast, fall back to its configured peak/off-peak/sell price values;
4. use `0.20` only as a final safe fallback when no usable price value exists.

The profile percentages in the table are multiplied by this reference. This keeps the policy strength proportional to the market values seen by the optimizer instead of tying it to one currency.

## LFP design rationale

GW EnergyPilot does not claim that a particular profile extends battery life by a fixed percentage. Battery ageing depends on cell chemistry, temperature, depth of discharge, C-rate, calendar time and the battery-management system.

For the GoodWe LFP battery family used by the primary GW15K-ETA-G20 reference installation, the low-SOC zones are intentionally much lower than the first experimental Battery Saver proposal. GoodWe specifies deep-cycle operation for its LFP batteries; a normal low SOC inside the BMS operating window is not the same as cell over-discharge below the permitted voltage. EnergyPilot therefore leaves reserve ownership to the hard Minimum SOC control instead of manufacturing a high soft floor.

The profiles put relatively more weight on avoiding unnecessary high-SOC dwell, low-value battery throughput and low-value high-power cycling. The stress cost remains a soft optimizer cost: it does not reduce the configured GoodWe/EMHASS maximum power and cannot prevent full power when the economic signal is strong enough.

## Ownership and compatibility

Battery Saver remains opt-in for unmanaged installations.

- Existing/custom EMHASS battery costs and weights are not overwritten until the user explicitly selects an EnergyPilot Battery Saver mode.
- An old zero-cost/zero-weight configuration is recognized as legacy unrestricted behavior; it is no longer described as behaviorally identical to current Mad-Steve because Mad-Steve now includes anti-churn weights.
- After a mode has been selected, EnergyPilot owns the eight Battery Saver EMHASS fields for its own optimizations.
- If the first profile application or optimization fails, EnergyPilot restores the previous config-entry mode and all previous Battery Saver-owned EMHASS fields.
- Multi-battery EMHASS configurations are rejected by the Battery Saver selector because EnergyPilot cannot safely infer per-battery ownership from one GoodWe integration.
- Non-zero power-stress modes require EMHASS 0.18.1 or newer when the EMHASS version is known.

The EnergyPilot-owned fields are:

```text
battery_soc_deficit_threshold
battery_soc_deficit_cost
battery_soc_surplus_threshold
battery_soc_surplus_cost
battery_stress_cost
battery_stress_segments
weight_battery_charge
weight_battery_discharge
```

The standard Home Assistant options flow and EnergyPilot's generic settings pages preserve the separately managed `battery_saver_mode` option.

## EMHASS publication contract

EnergyPilot owns **when to perform a complete optimization**. EMHASS owns **which row of that plan is published at the current optimization timestep**.

For every EnergyPilot-owned optimization EnergyPilot enforces:

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

The on-grid Minimum SOC NumberEntity keeps the existing entity ID/unique ID contract.

1. wait for the canonical GoodWe on-grid minimum-SOC telemetry;
2. display that value on the EnergyPilot slider;
3. mirror the value to EMHASS `battery_minimum_state_of_charge` when different;
4. on an explicit slider change, write and verify GoodWe first, then write EMHASS;
5. if the EMHASS write fails, roll GoodWe back to the previous verified value.

EnergyPilot also reasserts the available GoodWe minimum SOC before its own optimization runs and clamps `soc_final` to the hard EMHASS range.
