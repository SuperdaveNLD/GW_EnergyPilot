# GW EnergyPilot v0.49 changelog

## Added

- Added a single serialized wall-clock owner for full EMHASS optimization and due saved-plan publication (#98).
- Added opt-in soft EV charger load balancing, configuration profiles, diagnostic state and append-only high-current acknowledgement history (#94).
- Added compact Modbus/charger/coordination reachability presentation and the five-minute stale-charger EV safety guard (#95).
- Added persisted latest-successful EMS setpoint transaction evidence to existing Controller, entity and LOG/support diagnostics (#96).
- Added explicit Controller feedback for active EV anti-discharge decisions (#91).
- Added a v0.49 presentation entrypoint and one fresh cache key across the complete active frontend import graph.

## Fixed

- Distinguish a configured-but-unavailable Nord Pool source from a missing source (#93).
- Preserve the Battery · Plan · Price card shell, header, S/M/L controls and window bar during scoped data refresh (#97).
- Fall back to canonical live minimum/maximum SOC entities when cached EMHASS settings data is absent (#100).
- Stop ordinary telemetry from rebuilding and resizing the Hybrid strategy explanation; preserve node identity and height across Chromium and WebKit profiles (#101).

## Safety and compatibility

- Keep the established EV anti-discharge priority, GoodWe register semantics, EMS setpoint-before-mode write sequence and non-negative setpoint magnitude.
- Keep EV load balancing isolated from GoodWe, Automatic Control and EMHASS.
- Preserve existing entity unique IDs, device identity, plan/accounting stores and unrelated EMHASS settings.
- Leave #99 open/on hold without a speculative code change because the reported white-screen failure has not been reproduced.
