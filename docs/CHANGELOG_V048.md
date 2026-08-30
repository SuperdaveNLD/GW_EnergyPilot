# GW EnergyPilot v0.48 changelog

## Fixed

- Evaluate Hybrid `P_batt` neutrality before any `P_grid` branch and select mode 8 Hold at both configured deadband boundaries.
- For non-neutral Hybrid plans, select mode 1 around zero `P_grid`, mode 9 for positive planned import and mode 10 for negative planned export.
- Send the complete absolute `P_grid` target to modes 9/10, capped only by configured maximum power; never subtract the deadband.
- Replace stale 9/12 Hybrid operator copy with current English and Dutch 8/1/9/10 guidance.

## Added

- Added controller regressions for neutral-plan import/export, zero-grid self-use in both battery directions, signed PCC targets, variable exact deadband boundaries and maximum-power clamping.
- Added v0.48 release wiring, frontend-copy and Chromium/WebKit browser entrypoint coverage.

## Safety and compatibility

- EV anti-discharge remains higher priority and keeps its existing explicit-charge handling.
- Battery/Grid automatic strategies, manual EMS ownership, mode numbers, registers, non-negative setpoints and setpoint-before-mode write order are unchanged.
- No entity identity, config-entry compatibility, Store, EMHASS objective/topology, Battery Saver, PV or accounting contract changes.
