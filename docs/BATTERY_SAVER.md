# Battery Saver

GW EnergyPilot exposes the battery strategy directly on the customer-facing **Controller** card and keeps the detailed Battery Saver view under **Settings → EMHASS**. It is an EnergyPilot policy layer on top of EMHASS: selecting a managed profile changes the configuration used by the next EnergyPilot-owned EMHASS optimization, while EMHASS remains the canonical optimizer and published `P_batt` / `P_grid` remain the control inputs.

Battery Saver does **not** write a GoodWe EMS mode directly.

## Customer controller

The Controller card presents the four managed strategies plus **Custom**:

- **Mad-Steve**
- **Gold Rush**
- **Balanced**
- **Battery Saver**
- **Custom**

Selecting a managed strategy is one transaction: EnergyPilot stores the selected strategy, applies its owned EMHASS battery fields, runs a fresh optimization and publishes the resulting plan. If that first apply-and-optimize cycle fails, the previous strategy and Battery Saver-owned EMHASS fields are restored.

Selecting **Custom** deliberately releases managed-profile ownership without resetting the currently effective EMHASS battery values. A fresh optimization is still run so the plan reflects that ownership transition immediately. The customer card exposes the existing minimum/maximum SOC entities as sliders and shows the remaining active EMHASS battery penalties for transparency. It does not create duplicate SOC entities or a second battery configuration path.

The low-level controller command (for example `hybrid_battery_discharge`) remains available in the Diagnostics snapshot rather than the customer-facing Controller metrics.

Every successful EnergyPilot optimization refreshes the persistent plan and advances `plan_revision`. The battery/price graph watches that revision and bypasses its normal cache when the active plan changes, so profile changes and SOC-limit optimizations are reflected in the graph after the new solve is published.

## Hard limits and ownership

The managed-profile contract is:

- **Minimum SOC** remains the canonical GoodWe on-grid minimum SOC synchronized into EMHASS.
- **Maximum SOC** is part of the selected EnergyPilot Battery Saver profile.
- Runtime `soc_final` is clamped to the effective hard minimum/maximum before every EnergyPilot-owned solve.
- Unmanaged/custom installations keep their existing EMHASS maximum and battery-cost values until the user explicitly selects an EnergyPilot profile.

This removes the need to maintain one Battery Saver mode and a separate manual EMHASS maximum-SOC setting that can drift away from the intended profile.

All profile hard maxima are 100%. The upper 5% is deliberately modeled as a soft red zone instead of being made unreachable:

| Mode | Hard maximum SOC |
| --- | ---: |
| **Mad-Steve** | **100%** |
| **Gold Rush** | **100%** |
| **Balanced** | **100%** |
| **Battery Saver / Eco** | **100%** |

The GoodWe minimum is checked against the **effective profile maximum** after the profile is applied. This also lets a managed profile safely replace a legacy or Custom lower EMHASS maximum with the current 100% boundary.

## Two different battery costs

Battery Saver separates **whether a battery transaction is worth doing** from **how hard the battery should be driven**.

### Anti-churn transaction cost

Mad-Steve deliberately retains the established aggressive linear EMHASS charge/discharge weight:

```text
weight_battery_charge    = 2.25% × price reference
weight_battery_discharge = 2.25% × price reference
```

Gold Rush, Balanced and Battery Saver use the field-tuned floor:

```text
weight_battery_charge    = 6% × price reference
weight_battery_discharge = 6% × price reference
```

At the captured Gold Rush price reference of `0.1215`, this gives `0.007290` currency/kWh per direction. It removed the low-value 765 W, 857 W and 426 W short reversals while preserving the profitable 15 kW evening dispatch. One 1847 W reversal across a `0.025`/kWh spread remains economically justified by the linear EMHASS model.

The tuning was developed in two steps:

1. the shared 2.25% floor removed several low-value quarter-hour reversals while preserving high-value evening dispatch;
2. a captured standard Gold Rush plan still contained marginal one-slot reversals; 3.5% was insufficient, while 6% removed the low-value reversals and reduced the comparable modeled objective by only `0.026`. Gold Rush power stress moved from 3% to 1% so valuable dispatch can still use high power.

The factor remains price-relative instead of being hard-coded in EUR. This keeps the virtual transaction cost proportional to the price magnitude/currency used by the active EMHASS forecast.

A charge/discharge round trip pays both weights. Mad-Steve remains the deliberately aggressive exception. Balanced and Battery Saver use the proven 6% floor as well, because their preservation-oriented policy should not accept a transaction that profit-first Gold Rush rejects.

### Battery power-stress cost

`battery_stress_cost` is separate from the linear anti-churn weights. Current EMHASS models it as a piecewise-linear approximation of a quadratic power cost, so high instantaneous battery power becomes progressively more expensive.

This is why a profile can choose 9–12 kW instead of 15 kW even when the hardware allows 15 kW. If nearby timesteps have similar value, EMHASS can spread the same energy and reduce the stress penalty.

### High-SOC red-zone dwell cost

Every profile uses `battery_soc_surplus_threshold = 0.95`. EMHASS applies `battery_soc_surplus_cost` to every kWh above that threshold for every hour it remains there:

```text
surplus penalty
  = surplus cost × timestep hours
  × max(0, stored energy − energy at 95% SOC)
```

This is a soft economic boundary, not a hard stop. EMHASS can charge to 100% when the forecast value exceeds the penalty, but charging into the red zone early becomes more expensive than reaching it shortly before the energy is needed.

The hourly cost factors are:

```text
Mad-Steve       5% × dynamic price reference per kWh/hour
Gold Rush      10% × dynamic price reference per kWh/hour
Balanced       25% × dynamic price reference per kWh/hour
Battery Saver  50% × dynamic price reference per kWh/hour
```

For a 33.2 kWh battery at the captured `0.1215` price reference, remaining at 100% costs approximately `0.0101`, `0.0202`, `0.0504` or `0.1008` currency per hour respectively. The charge/discharge efficiency settings remain installation-owned and are not used as a substitute for this explicit aging/risk policy.

## Managed profiles

| Mode | Hard max | Low-SOC threshold | Low-SOC cost | High-SOC threshold | High-SOC cost | Power-stress cost | Anti-churn charge / discharge |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Mad-Steve** | **100%** | 5% | 0% × price ref | 95% | **5% × price ref / kWh/h** | 0% × price ref | **2.25% / 2.25% × price ref** |
| **Gold Rush** | **100%** | 5% | 0% × price ref | 95% | **10% × price ref / kWh/h** | **1% × price ref** | **6% / 6% × price ref** |
| **Balanced** | **100%** | 10% | 5% × price ref | 95% | **25% × price ref / kWh/h** | 8% × price ref | **6% / 6% × price ref** |
| **Battery Saver / Eco** | **100%** | 15% | 10% × price ref | 95% | **50% × price ref / kWh/h** | 20% × price ref | **6% / 6% × price ref** |

All four profiles use `battery_stress_segments = 10`.

The hard maximum and high-SOC threshold are intentionally different. The 100% maximum is the physical optimization boundary; the 95% threshold starts the time-dependent economic red zone.

### Mad-Steve

Maximum economic freedom. Mad-Steve can use the full configured 0–100% EMHASS range and has no extra low-SOC or power-stress penalty. Its 5% high-SOC factor is the lightest red-zone price, and its 2.25% anti-churn floor keeps this profile deliberately more aggressive than the other managed modes.

A legacy all-zero EMHASS battery-cost configuration is still more aggressive than managed Mad-Steve because it has no anti-churn weight at all.

### Gold Rush

Profit remains the priority. Gold Rush can reach 100%, but pays a 10% per-kWh/hour factor above 95%. It has no extra low-SOC penalty, uses the field-tested 6% anti-churn floor and only 1% price-relative battery power stress. Large price spreads can still justify 15 kW operation and the complete red-zone capacity, while the dwell penalty discourages filling that last 5% too early.

### Balanced

The recommended general-purpose profile. Balanced can reach 100% when warranted, but its 25% red-zone factor and moderate low-SOC/power-stress penalties require more value than Gold Rush before using or dwelling in the last 5%.

### Battery Saver / Eco

Battery preservation has the highest virtual value. It still permits 100% for an exceptional opportunity, but the 50% red-zone factor makes prolonged high-SOC dwell most expensive. The low-SOC zone begins at 15% and the power-stress penalty remains strongest.

## Why battery power can be below 15 kW

A `P_batt` target below the configured 15 kW maximum is not automatically an optimizer error.

Three different constraints can bind:

1. **Battery power limit** — `battery_charge_power_max` / `battery_discharge_power_max`.
2. **Hybrid inverter AC limit** — PV and battery share the inverter path. `PV + P_batt` can already produce the 15 kW AC limit while `P_batt` itself is only 14–14.8 kW.
3. **Economic optimum** — when neither physical limit binds, EMHASS may reserve energy for a later timestep or reduce instantaneous power because of `battery_stress_cost`.

When reviewing a plan, compare `P_batt`, `P_PV`, `P_hybrid_inverter`, SOC and neighboring prices together.

## Price reference

EnergyPilot derives one positive price reference for every managed optimization:

1. median of positive runtime import prices when EnergyPilot supplies a timestamped `load_cost_forecast`;
2. otherwise median non-zero absolute runtime price magnitude;
3. otherwise configured EMHASS peak/off-peak/sell prices;
4. final fallback `0.20` when no usable price exists.

The profile percentages are multiplied by this reference.

## Ownership and rollback

Battery Saver remains opt-in.

- Existing/custom EMHASS values are untouched until a profile is explicitly selected.
- Multi-battery EMHASS configurations are rejected for managed profiles rather than guessed; Custom can still release managed ownership without rewriting the installation topology.
- Non-zero power-stress profiles require EMHASS 0.18.1 or newer when the version is known.
- A failed first profile+optimization transaction restores the previous EnergyPilot mode and every Battery Saver-owned EMHASS field.
- Maximum SOC participates in the same apply/rollback transaction as the economic profile values.

## Custom value editor

**Custom / Aangepast** is available in both the dashboard Battery Strategy card and **Settings → EMHASS → Battery Saver**. When Custom is active, an administrator can edit these five raw, non-negative EMHASS cost values:

```text
battery_soc_deficit_cost
battery_soc_surplus_cost
battery_stress_cost
weight_battery_charge
weight_battery_discharge
```

The editor deliberately does not reinterpret the values as profile percentages. It preserves the EMHASS single-battery storage contract: the three penalty costs remain scalars and the charge/discharge weights remain one-item lists.

One **Save and optimize** action reads the current complete EMHASS configuration, merges only these five fields, releases managed-profile ownership, writes `/set-config` and builds a fresh plan. If the write or first optimization fails, EnergyPilot restores the previous mode, runtime profile state and all nine Battery Saver-owned EMHASS fields. Dashboard and settings caches are updated from the same returned payload.

The Custom editor is intentionally disabled for multi-battery configurations because one visible value cannot safely represent heterogeneous batteries. Selecting Custom itself remains available so a multi-battery installation can release EnergyPilot profile ownership without changing its EMHASS values.

Minimum and Maximum SOC retain their dedicated synchronized Home Assistant number-entity paths and are not duplicated by the five-cost transaction.

The EnergyPilot-owned fields are now:

```text
battery_maximum_state_of_charge
battery_soc_deficit_threshold
battery_soc_deficit_cost
battery_soc_surplus_threshold
battery_soc_surplus_cost
battery_stress_cost
battery_stress_segments
weight_battery_charge
weight_battery_discharge
```

The minimum SOC is deliberately not in this list because it has separate GoodWe-synchronized ownership.

## EMHASS publication contract

For every EnergyPilot-owned optimization EnergyPilot continues to enforce:

```text
continual_publish = true
method_ts_round = first
set_use_battery = true
```

`set_use_pv` and `inverter_is_hybrid` remain installation-specific EMHASS settings and are preserved by EnergyPilot.

The runtime flow is:

```text
Battery Saver mode / Custom ownership
        ↓
managed profile values or preserved custom EMHASS values
        ↓
GoodWe-synchronized minimum SOC
        ↓
complete EMHASS config via /set-config when required
        ↓
runtime hard min/max + clamped soc_final
        ↓
EnergyPilot dayahead optimization
        ↓
initial /action/publish-data
        ↓
EMHASS continual_publish
        ↓
fresh P_batt / P_grid
        ↓
persistent plan refresh + plan_revision
        ↓
existing EnergyPilot Automatic Control + refreshed dashboard graph
        ↓
GoodWe EMS command
```

EMHASS remains the plan owner and EnergyPilot does not create a second 15-minute plan publisher.

## Minimum SOC synchronization

The on-grid Minimum SOC NumberEntity keeps its existing entity ID and unique-ID contract.

1. read the canonical GoodWe on-grid minimum SOC;
2. mirror it to EMHASS when required;
3. on an explicit slider change, write and verify GoodWe first;
4. write the same percentage to EMHASS;
5. if the EMHASS write fails, attempt to restore the previous verified GoodWe value.

Before an EnergyPilot-owned optimization, the available GoodWe minimum is reasserted and checked against the effective managed-profile maximum.
