# GW EnergyPilot v0.47 changelog

## Added

- Added administrator-editable **Custom / Aangepast** Battery Saver costs to the dashboard and Settings → EMHASS.
- Added one validated `battery_saver/custom_set` WebSocket transaction that preserves the complete unrelated EMHASS configuration, scalar/list value shapes and the existing first-optimization rollback boundary.
- Added the immutable Gold Rush field baseline under `docs/field_evidence/`.

## Changed

- Increased Battery Strategy and Battery Saver settings typography without changing stable-DOM or native touch-scroll ownership.
- Retuned Gold Rush to 6% × dynamic price reference anti-churn per direction and 1% power stress after field comparison.
- Applied the same 6% transaction floor to Balanced and Battery Saver; Mad-Steve remains at 2.25%.
- Set every managed profile hard maximum to 100% and introduced a shared soft red zone above 95% with 5% / 10% / 25% / 50% price-relative hourly surplus factors.
- Added `gw-energy-pilot-v047.js` and refreshed the active frontend dependency graph with `0.47-custom-battery1`.

## Safety and compatibility

- Custom editing is administrator-only and supports exactly one EMHASS battery model.
- Minimum/Maximum SOC number entities, battery efficiency, inverter topology and unrelated EMHASS configuration retain their existing ownership.
- No GoodWe register/write, EMS/Automatic Control, entity identity, persistent Store, plan-resilience, PV or accounting behavior changes.
