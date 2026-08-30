# GW EnergyPilot v0.50 changelog

## Changed

- Replaced the manual EV load-balancing phase-current entity with automatic linked GoodWe L1/L2/L3 coordinator telemetry.
- Added explicit one-phase L1/L2/L3 selection and highest-phase guarding for three-phase chargers.
- Separated the writable charger current-limit control from the read-only allocated-current feedback sensor.
- Added bounded applied-current confirmation with a 60-second timeout and 0.25 A tolerance.
- Changed the default load-balancing condition window for new or unset configurations to 15 minutes; explicitly stored existing values remain unchanged.
- Added a v0.50 presentation entrypoint and the `0.50-ev1` cache boundary across the complete active frontend import graph.

## Fixed

- Accept the EV Online entity in the dedicated EV settings API instead of rejecting `ev_online_entity` as unsupported.
- Auto-link unambiguous Zaptec current-limit controls and allocated-current feedback sensors through Home Assistant device and config-entry relations while leaving tied candidates for explicit selection.
- Reject read-only current sensors as charger actuators and require an ampere current sensor as feedback when load balancing is newly enabled or saved.

## Safety and compatibility

- Keep GoodWe telemetry read-only in this actuator path; the EV load balancer writes only the configured Home Assistant charger NumberEntity through `number.set_value`.
- Preserve all GoodWe register definitions, EMS mode mappings, setpoint-before-mode ordering, Automatic Control ownership, entity unique IDs, device identity and persistent accounting/plan stores.
- Remove the legacy manual phase-current option on EV settings save while continuing to load existing configurations safely.
