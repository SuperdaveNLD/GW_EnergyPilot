# Battery Saver

GW EnergyPilot exposes the battery strategy directly on the customer-facing **Controller** card and keeps the detailed Battery Saver view under **Settings → EMHASS**. It is an EnergyPilot policy layer on top of EMHASS: selecting a managed profile changes the configuration used by the next EnergyPilot-owned EMHASS optimization, while EMHASS remains the canonical optimizer and published `P_batt` / `P_grid` remain the control inputs.

Battery Saver does **not** write a GoodWe EMS mode directly.

## Customer controller

The Controller card presents five managed strategies plus **Custom**:

- **Mad-Steve**
- **Gold Rush**
- **Chargegasm**
- **Balanced**
- **Battery Saver**
- **Custom**

Selecting a managed strategy is one transaction: EnergyPilot writes and verifies the profile minimum in GoodWe, stores the selected strategy, applies all ten owned EMHASS battery fields, runs a fresh optimization and publishes the resulting plan. If that first apply-and-optimize cycle fails, the previous strategy, GoodWe minimum and all owned EMHASS fields are restored.

Selecting **Custom** deliberately releases managed-profile ownership without resetting the currently effective EMHASS battery values. A fresh optimization is still run so the plan reflects that ownership transition immediately. Only Custom exposes the existing minimum/maximum SOC entities as sliders; managed modes replace them with a read-only hard range, comfort zone and cost summary. It does not create duplicate SOC entities or a second battery configuration path.

The low-level controller command (for example `hybrid_grid_export`) remains available in the Diagnostics snapshot rather than the customer-facing Controller metrics.

Every successful EnergyPilot optimization refreshes the persistent plan and advances `plan_revision`. The battery/price graph watches that revision and bypasses its normal cache when the active plan changes, so profile changes and SOC-limit optimizations are reflected in the graph after the new solve is published.

## Hard limits and ownership

The managed-profile contract is:

- **Minimum SOC** is part of the profile and is written to verified GoodWe register `45356` before EMHASS is changed.
- **Maximum SOC** is the matching EMHASS hard upper boundary.
- Runtime `soc_final` is clamped to the effective hard minimum/maximum before every EnergyPilot-owned solve.
- Direct writes to the two SOC NumberEntities are rejected while a managed profile is active; choose Custom first.
- Custom installations keep their existing hard limits and cost values.

An installation upgrading from v1.0 with an already active managed profile retains its existing GoodWe floor until that profile is explicitly selected again. This avoids a hardware write caused only by installing the beta. The Settings view shows that reselection is required before the new managed range is authoritative.

The hard range is absolute. The comfort zone is economic: EMHASS may enter the five-percentage-point lower/upper shoulder when forecast value exceeds the corresponding SOC cost, but it can never cross hard min/max.

## Two different battery costs

Battery Saver separates **whether a battery transaction is worth doing** from **how hard the battery should be driven**.

### Anti-churn transaction cost

Mad-Steve deliberately retains the established aggressive linear EMHASS charge/discharge weight:

```text
weight_battery_charge    = 2.25% × price reference
weight_battery_discharge = 2.25% × price reference
```

Gold Rush and Chargegasm use the field-tuned floor:

```text
weight_battery_charge    = 6% × price reference
weight_battery_discharge = 6% × price reference
```

At the captured Gold Rush price reference of `0.1215`, this gives `0.007290` currency/kWh per direction. It removed the low-value 765 W, 857 W and 426 W short reversals while preserving the profitable 15 kW evening dispatch. One 1847 W reversal across a `0.025`/kWh spread remains economically justified by the linear EMHASS model.

The original Gold Rush tuning was developed in two steps:

1. the shared 2.25% floor removed several low-value quarter-hour reversals while preserving high-value evening dispatch;
2. a captured standard Gold Rush plan still contained marginal one-slot reversals; 3.5% was insufficient, while 6% removed the low-value reversals and reduced the comparable modeled objective by only `0.026`.

The factor remains price-relative instead of being hard-coded in EUR. This keeps the virtual transaction cost proportional to the price magnitude/currency used by the active EMHASS forecast.

A charge/discharge round trip pays both weights. Mad-Steve remains the deliberately aggressive exception. Balanced raises the per-direction factor to 7% and Battery Saver to 9%, making progressively smaller spreads uneconomic as preservation becomes more important.

### Battery power-stress cost

`battery_stress_cost` is separate from the linear anti-churn weights. Current EMHASS models it as a piecewise-linear approximation of a quadratic power cost, so high instantaneous battery power becomes progressively more expensive.

This is why a profile can choose 9–12 kW instead of 15 kW even when the hardware allows 15 kW. If nearby timesteps have similar value, EMHASS can spread the same energy and reduce the stress penalty.

### High-SOC red-zone dwell cost

Each profile starts its high-SOC shoulder five percentage points below its hard maximum. EMHASS applies `battery_soc_surplus_cost` to every kWh above that threshold for every hour it remains there:

```text
surplus penalty
  = surplus cost × timestep hours
  × max(0, stored energy − energy at the profile threshold)
```

This is a soft economic shoulder inside the hard range. Charging into it early becomes more expensive than reaching it shortly before the energy is needed.

The hourly cost factors are:

```text
Mad-Steve       5% × dynamic price reference per kWh/hour
Gold Rush      12% × dynamic price reference per kWh/hour
Chargegasm     18% × dynamic price reference per kWh/hour
Balanced       25% × dynamic price reference per kWh/hour
Battery Saver  50% × dynamic price reference per kWh/hour
```

The charge/discharge efficiency settings remain installation-owned and are not used as a substitute for this explicit aging/risk policy.

## Managed profiles

| Mode | Hard min | Comfort zone | Hard max | Low-SOC cost | High-SOC cost | Power-stress cost | Anti-churn charge / discharge |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Mad-Steve** | **5%** | **10–95%** | **100%** | 2% × price ref | **5% × price ref / kWh/h** | 0% × price ref | **2.25% / 2.25% × price ref** |
| **Gold Rush** | **5%** | **10–95%** | **100%** | 2% × price ref | **12% × price ref / kWh/h** | 0% × price ref | **6% / 6% × price ref** |
| **Chargegasm** | **8%** | **13–91%** | **96%** | 2% × price ref | **18% × price ref / kWh/h** | 2% × price ref | **6% / 6% × price ref** |
| **Balanced** | **10%** | **15–88%** | **93%** | 5% × price ref | **25% × price ref / kWh/h** | 6% × price ref | **7% / 7% × price ref** |
| **Battery Saver** | **10%** | **20–80%** | **85%** | 10% × price ref | **50% × price ref / kWh/h** | 20% × price ref | **9% / 9% × price ref** |

All five profiles use `battery_stress_segments = 10`.

### Mad-Steve

Maximum economic freedom. Mad-Steve keeps the widest 5–100% hard range, no power-stress cost and the lightest 2.25% anti-churn factor. The small 2% low-SOC shoulder below 10% and 5% high-SOC shoulder above 95% still discourage unnecessary edge dwell without blocking a valuable trade.

A legacy all-zero EMHASS battery-cost configuration is still more aggressive than managed Mad-Steve because it has no anti-churn weight at all.

### Gold Rush

Profit remains the priority. Gold Rush retains the 5–100% range and no power-stress cost, but uses the field-tested 6% anti-churn factor and a 12% high-SOC dwell factor. It therefore rejects more marginal reversals than Mad-Steve while retaining full-power freedom.

### Chargegasm

Chargegasm sits deliberately between Gold Rush and Balanced. Its 8–96% hard range removes the most extreme SOC endpoints, while 2% power stress and 6% anti-churn retain strong dispatch when the spread is worthwhile. The 13–91% comfort zone targets a lower average SOC without reducing the usable window as far as Balanced.

### Balanced

The recommended general-purpose profile. Balanced uses a 10–93% hard range, a 15–88% comfort zone, 6% power stress and 7% anti-churn. It requires materially more value than Chargegasm before cycling near either edge or at high instantaneous power.

### Battery Saver

Battery preservation has the highest virtual value. Its hard maximum is 85%, with a 20–80% comfort zone, so it directly limits high average SOC instead of merely pricing the final few percent. The 10% lower shoulder, 50% upper dwell factor, 20% power stress and 9% anti-churn make it the most selective profile.

## Degradation rationale and limits

The ordering is guided by published cell-aging evidence, not presented as a calibrated lifetime prediction:

- Zsoldos et al. tested LFP/graphite cells across different SOC windows and found less capacity fade at lower average SOC, regardless of depth of discharge in the tested windows. This supports progressively lowering the upper comfort boundary and hard maximum from Gold Rush through Battery Saver: [Journal of The Electrochemical Society 171 (2024), 080527](https://doi.org/10.1149/1945-7111/ad6cbd).
- Naumann et al. modeled commercial LFP/graphite cycle aging across temperature, C-rate, depth of cycle and SOC range. This supports keeping power stress and throughput costs separate rather than treating SOC alone as battery wear: [Journal of Power Sources 451 (2020), 227666](https://doi.org/10.1016/j.jpowsour.2019.227666).
- Groot et al. found LFP/graphite calendar fade depends on both SOC and temperature in long-duration storage tests. EnergyPilot can influence SOC dwell but has no cell-temperature degradation model: [Journal of Power Sources 255 (2014), 450–458](https://doi.org/10.1016/j.jpowsour.2013.11.098).

Battery Saver uses 10%, not 20%, as its hard minimum because raising the lower bound also raises average SOC. Its stronger cost below 20% discourages unnecessary bottom-edge use while retaining a lower average operating window. The exact 2% / 5% / 10%, 5% / 12% / 18% / 25% / 50%, power-stress and anti-churn factors are transparent EnergyPilot policy choices. They are not derived from the tested GoodWe battery's cell temperature, C-rate, replacement cost or measured state of health and must not be interpreted as a promised cycle-life improvement.

EnergyPilot never overrides inverter/BMS safety limits. If the battery manufacturer requires periodic high-SOC calibration or balancing, the operator must use an appropriate profile or Custom for that maintenance procedure; the beta does not invent an automatic maintenance-charge schedule.

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
- Chargegasm, Balanced and Battery Saver require EMHASS 0.18.1 or newer when the version is known because they use non-zero power stress.
- A failed first profile+optimization transaction restores the previous EnergyPilot mode, verified GoodWe minimum and every owned EMHASS field.
- Both hard SOC limits participate in the same apply/rollback transaction as the economic profile values.

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

One **Save and optimize** action reads the current complete EMHASS configuration, merges only these five fields, releases managed-profile ownership, writes `/set-config` and builds a fresh plan. If the write or first optimization fails, EnergyPilot restores the previous mode, runtime profile state and all ten Battery Saver-owned EMHASS fields. Dashboard and settings caches are updated from the same returned payload.

The Custom editor is intentionally disabled for multi-battery configurations because one visible value cannot safely represent heterogeneous batteries. Selecting Custom itself remains available so a multi-battery installation can release EnergyPilot profile ownership without changing its EMHASS values.

Minimum and Maximum SOC retain their dedicated Home Assistant number-entity paths and are not duplicated by the five-cost transaction. Those sliders are hidden in the dashboard and reject service writes while a managed mode owns the range; they become editable after Custom is selected.

The EnergyPilot-owned fields are now:

```text
battery_minimum_state_of_charge
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

## EMHASS publication contract

For every EnergyPilot-owned optimization EnergyPilot continues to enforce:

```text
continual_publish = false
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
managed mode: verified profile minimum in GoodWe + EMHASS
Custom: preserved synchronized GoodWe/EMHASS minimum
        ↓
complete EMHASS config via /set-config when required
        ↓
runtime hard min/max + clamped soc_final
        ↓
EnergyPilot dayahead optimization
        ↓
initial /action/publish-data
        ↓
EnergyPilot wall-clock plan-step publication
        ↓
fresh P_batt / P_grid
        ↓
persistent plan refresh + plan_revision
        ↓
existing EnergyPilot Automatic Control + refreshed dashboard graph
        ↓
GoodWe EMS command
```

EMHASS remains the plan owner. EnergyPilot is the single schedule owner: it
publishes active plan steps from that EMHASS plan and keeps EMHASS
`continual_publish` disabled.

## Minimum SOC synchronization

The on-grid Minimum SOC NumberEntity keeps its existing entity ID and unique-ID contract.

1. read the canonical GoodWe on-grid minimum SOC;
2. mirror it to EMHASS when required;
3. on an explicit slider change, write and verify GoodWe first;
4. write the same percentage to EMHASS;
5. if the EMHASS write fails, attempt to restore the previous verified GoodWe value.

Before an EnergyPilot-owned optimization, the available GoodWe minimum is reasserted and checked against the effective managed-profile maximum.
