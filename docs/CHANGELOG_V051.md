# GW EnergyPilot v0.51 changelog

## Added

- Added the bounded `gw_energypilot.execution.<config_entry_id>` Store with
  seven-day retention, a 4096-event hard limit, UTC event IDs and
  failure-isolation from EMS control.
- Added immutable per-decision snapshots of plan source/value, wanted SOC,
  strategy/deadband/maximum, EV state, actual battery/PV/load/grid values,
  expected command, write result and post-refresh GoodWe read-back.
- Added one stable-DOM EMHASS → GOODWE dashboard card with a compact ±6-hour
  view and a full 48-hour history plus 24-hour projection table.
- Added a shared pure Battery/Grid/Hybrid/EV decision resolver used by live
  Automatic Control and future read-only projections.
- Added optional exact official-plan `P_PV` and `P_Load` normalization for
  dashboard projections without making those values control inputs.
- Added Recorder-based load-first source attribution for grid/solar battery
  charging and battery/solar grid export, including an explicit unknown
  residual.
- Added immutable historical wanted-SOC rendering while retaining the dashed
  line and current/future official-plan continuation.

## Changed

- Advanced `gw_energypilot/battery_price/get` to chart schema 6 with an
  `execution` section containing 48-hour history, 24-hour conditional
  projection, timezone, retention metadata and stated projection assumptions.
- Refresh GoodWe coordinator telemetry after a completed EMS write before
  recording verified, mismatched or unavailable read-back evidence. The
  existing refresh error propagation contract remains intact.
- Show source attribution only in the Large and expanded graph; Compact and
  Normal retain existing battery charge/discharge bars.
- Added the v0.51 presentation wrapper and refreshed the complete frontend
  dependency graph with the `0.51-h1` cache key.

## Safety and compatibility

- Preserve GoodWe register definitions, setpoint-before-mode write ordering,
  controller branch semantics, manual/automatic ownership and EV priority.
- Preserve EMHASS as canonical plan owner and the current live-output → valid
  mirror → unavailable control source order.
- Keep optional `P_PV` and `P_Load` plan values display-only; do not feed them
  into EMS decisions.
- Keep source attribution explicitly approximate and separate from persistent
  grid accounting and financial totals.
- Store no configured entity IDs, EMHASS URL/token or arbitrary Home Assistant
  attributes in execution history. Existing installs start with empty history
  and require no migration.
