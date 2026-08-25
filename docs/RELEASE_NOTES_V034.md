# GW EnergyPilot v0.34 Beta

v0.34 is a focused Battery Saver optimization update based on controlled four-profile EMHASS comparisons on the primary reference installation.

## Profile-owned hard maximum SOC

When a Battery Saver mode is explicitly managed by EnergyPilot, its EMHASS `battery_maximum_state_of_charge` is now part of the profile transaction:

| Mode | Maximum SOC |
| --- | ---: |
| Mad-Steve | **100%** |
| Gold Rush | **96%** |
| Balanced | **95%** |
| Battery Saver / Eco | **90%** |

The GoodWe on-grid minimum SOC remains the canonical hard lower limit and is synchronized separately. EnergyPilot applies the selected profile maximum before checking that GoodWe minimum, so a stale lower EMHASS maximum cannot incorrectly reject a profile that intentionally raises the cap.

Maximum SOC participates in the existing Battery Saver apply/rollback behavior. Unmanaged/custom installations remain untouched until a profile is selected.

## Calmer anti-churn floor

The common linear EMHASS battery-throughput cost moves from:

```text
1.5% × dynamic price reference per direction
```

to:

```text
2.25% × dynamic price reference per direction
```

At the field-test reference around `0.31`, this is approximately `0.007` currency/kWh for charging and `0.007` for discharging. The follow-up comparison reduced low-value adjacent-quarter-hour reversals while preserving high-value operation up to the real battery/hybrid-inverter limits.

The factor remains common to all four profiles. Profile differentiation continues through hard maximum SOC, low-SOC penalties and battery power-stress cost rather than through different hidden transaction floors.

## Compatibility and safety

- No GoodWe register definitions or Modbus read blocks change.
- EMS remains on `47511/47512` with the existing `47512 -> wait -> 47511` ordering.
- No Automatic Control mode mapping changes.
- No entity ID, unique ID or stable device identity changes.
- EMHASS remains the canonical optimizer and plan owner.
- Minimum SOC ownership through the verified GoodWe on-grid minimum remains separate from Battery Saver maximum-SOC ownership.
- Multi-battery Battery Saver ownership remains rejected rather than guessed.
