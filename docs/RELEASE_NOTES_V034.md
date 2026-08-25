# GW EnergyPilot v0.34 Beta

v0.34 consolidates the open post-v0.33 work into one release candidate: deterministic Battery Plan refresh, Battery Saver profile tuning and corrected EV anti-discharge charge pass-through.

## Battery Plan refresh after every optimization

Every successful EnergyPilot-owned optimization now advances an explicit `plan_revision` after the persistent EMHASS plan refresh attempt. That revision is published through the existing orchestrator state and returned by the Battery Plan API.

The dashboard compares the live optimization revision with its cached Battery · Plan · Price payload. A revision mismatch forces an immediate read-only refresh of the canonical card instead of waiting for the normal frontend cache interval. The existing `P_batt.last_updated` fallback remains available for plans changed outside EnergyPilot.

The active v0.34 frontend uses fresh module URLs for both the Battery Saver layer and the Battery Plan core, preventing an already-open Home Assistant browser from retaining pre-v0.34 nested ES modules.

## Battery Saver profile-owned hard maximum SOC

When a Battery Saver mode is explicitly managed by EnergyPilot, its EMHASS `battery_maximum_state_of_charge` is part of the profile transaction:

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

## EV anti-discharge: pause discharge, allow charge

EV coordination remains strictly an anti-discharge guard.

During an active EV charging session:

| EMHASS battery direction | EnergyPilot behavior |
| --- | --- |
| `P_batt > +deadband` — discharge | **Mode 8 Battery Hold** |
| `P_batt` inside deadband — neutral | **Mode 8 Battery Hold** |
| `P_batt < -deadband` — charge | Charging remains allowed |

For an explicit battery charge plan, the configured control strategy remains relevant:

- **Battery control** uses GoodWe mode `11` with the `P_batt` charge magnitude.
- **Grid control** uses GoodWe mode `9` when a positive planned `P_grid` import target is available.
- **Hybrid control** uses mode `9` when a positive planned `P_grid` import target is available; otherwise the explicit `P_batt` charge request falls back to mode `11` so EV protection does not unnecessarily pause legitimate home-battery charging.

Discharge or neutral plans still take priority through mode `8` while the EV is active. EV-stop stale-plan protection remains unchanged and waits for a fresh optimization when the native orchestrator owns optimization timing.

## Compatibility and safety

- No new or guessed GoodWe register definitions or Modbus read blocks.
- EMS remains on `47511/47512` with the existing `47512 -> wait -> 47511` ordering.
- No entity ID, unique ID or stable device identity changes.
- EMHASS remains the canonical optimizer and plan owner.
- Minimum SOC ownership through the verified GoodWe on-grid minimum remains separate from Battery Saver maximum-SOC ownership.
- Multi-battery Battery Saver ownership remains rejected rather than guessed.
- The EV change only blocks discharge while the EV is active; it does not control the EV charger or add a second power-control loop.
- The v0.33 persistent-plan fallback and optimizer-readiness gates remain intact.

v0.34 remains **Beta** while the combined chart-refresh, Battery Saver and EV-control behavior receives live installation validation.
