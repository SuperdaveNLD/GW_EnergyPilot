# Battery Saver

GW EnergyPilot provides **Battery Saver** under **Settings → EMHASS**. It is an EnergyPilot policy layer on top of EMHASS: selecting a profile changes the configuration used by the next EnergyPilot-owned EMHASS optimization, while EMHASS remains the canonical optimizer and published `P_batt` / `P_grid` remain the control inputs.

Battery Saver does **not** write a GoodWe EMS mode directly.

## Hard limits and ownership

The managed-profile contract for the next release is:

- **Minimum SOC** remains the canonical GoodWe on-grid minimum SOC synchronized into EMHASS.
- **Maximum SOC** becomes part of the selected EnergyPilot Battery Saver profile.
- Runtime `soc_final` is clamped to the effective hard minimum/maximum before every EnergyPilot-owned solve.
- Unmanaged/custom installations keep their existing EMHASS maximum and battery-cost values until the user explicitly selects an EnergyPilot profile.

This removes the need to maintain one Battery Saver mode and a separate manual EMHASS maximum-SOC setting that can drift away from the intended profile.

The profile hard maxima are:

| Mode | Hard maximum SOC |
| --- | ---: |
| **Mad-Steve** | **100%** |
| **Gold Rush** | **96%** |
| **Balanced** | **95%** |
| **Battery Saver / Eco** | **90%** |

The GoodWe minimum is checked against the **effective profile maximum** after the profile is applied. This is important when moving from a lower-cap profile to Mad-Steve: an old lower EMHASS maximum must not reject a mode that intentionally raises the maximum.

## Two different battery costs

Battery Saver separates **whether a battery transaction is worth doing** from **how hard the battery should be driven**.

### Anti-churn transaction cost

All four managed profiles use the same linear EMHASS charge/discharge weight:

```text
weight_battery_charge    = 2.25% × price reference
weight_battery_discharge = 2.25% × price reference
```

At the field-test price reference of roughly `0.31`, this gives approximately `0.007` currency/kWh per direction.

The tuning was developed in two steps:

1. approximately `0.005` per direction removed several low-value quarter-hour reversals while preserving high-value evening dispatch;
2. a follow-up comparison around `0.007` per direction further reduced low-value churn while still allowing full-power battery operation when the price spread justified it.

The factor remains price-relative instead of being hard-coded in EUR. This keeps the virtual transaction cost proportional to the price magnitude/currency used by the active EMHASS forecast.

A charge/discharge round trip pays both weights. The common floor is intentional: even Mad-Steve should not reverse the battery for a negligible spread.

### Battery power-stress cost

`battery_stress_cost` is separate from the linear anti-churn weights. Current EMHASS models it as a piecewise-linear approximation of a quadratic power cost, so high instantaneous battery power becomes progressively more expensive.

This is why a profile can choose 9–12 kW instead of 15 kW even when the hardware allows 15 kW. If nearby timesteps have similar value, EMHASS can spread the same energy and reduce the stress penalty.

## Managed profiles

| Mode | Hard max | Low-SOC threshold | Low-SOC cost | High-SOC threshold | High-SOC cost | Power-stress cost | Anti-churn charge / discharge |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Mad-Steve** | **100%** | 5% | 0% × price ref | 100% | 0% × price ref | 0% × price ref | **2.25% / 2.25% × price ref** |
| **Gold Rush** | **96%** | 5% | 0% × price ref | 96% | 5% × price ref | 3% × price ref | **2.25% / 2.25% × price ref** |
| **Balanced** | **95%** | 10% | 5% × price ref | 95% | 10% × price ref | 8% × price ref | **2.25% / 2.25% × price ref** |
| **Battery Saver / Eco** | **90%** | 15% | 10% × price ref | 90% | 25% × price ref | 20% × price ref | **2.25% / 2.25% × price ref** |

All four profiles use `battery_stress_segments = 10`.

The current managed presets intentionally align the high-SOC threshold with the hard profile maximum. The hard maximum is therefore the binding upper boundary. The high-SOC cost fields remain part of the owned profile contract for compatibility and diagnostics, but the optimizer cannot intentionally operate above that profile maximum.

### Mad-Steve

Maximum economic freedom. Mad-Steve can use the full configured 0–100% EMHASS upper range and has no extra low-SOC, high-SOC or power-stress penalty. It still uses the common anti-churn cost so tiny price differences do not automatically justify needless battery throughput.

A legacy all-zero EMHASS battery-cost configuration is still more aggressive than managed Mad-Steve because it has no anti-churn weight at all.

### Gold Rush

Profit remains the priority. Gold Rush uses a 96% hard maximum, no extra low-SOC penalty and only light battery power stress. Large price spreads can still justify 15 kW battery operation or the full shared hybrid-inverter limit.

### Balanced

The recommended general-purpose profile. Balanced uses a 95% hard maximum and moderate low-SOC/power-stress penalties. It is intended to preserve most of the economic value of Gold Rush while reducing low-value high-power cycling.

### Battery Saver / Eco

Battery preservation has the highest virtual value. The hard maximum is 90%, the low-SOC zone begins at 15%, and the power-stress penalty is strongest. Full power can still occur when the optimizer finds enough economic value, but it is materially more expensive than in the other profiles.

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
- Multi-battery EMHASS configurations are rejected rather than guessed.
- Non-zero power-stress profiles require EMHASS 0.18.1 or newer when the version is known.
- A failed first profile+optimization transaction restores the previous EnergyPilot mode and every Battery Saver-owned EMHASS field.
- Maximum SOC participates in the same apply/rollback transaction as the economic profile values.

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
inverter_is_hybrid = true
```

`set_use_pv` remains installation-specific.

The runtime flow is:

```text
Battery Saver mode
        ↓
profile maximum SOC + price-relative virtual costs
        ↓
GoodWe-synchronized minimum SOC
        ↓
complete EMHASS config via /set-config
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
existing EnergyPilot Automatic Control
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
