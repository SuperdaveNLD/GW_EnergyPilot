# Persistent runtime state

GW EnergyPilot keeps configuration and runtime history separate.

## Ownership

- `ConfigEntry.data` and `ConfigEntry.options` remain the source of integration configuration.
- GoodWe registers remain the source of inverter-stored settings and live hardware state.
- EMHASS remains the source of optimizer configuration and published plan outputs.
- Small EnergyPilot-owned runtime history that must survive an integration reload or Home Assistant restart is stored with Home Assistant's `Store` helper.

Four per-config-entry stores are used for controller/orchestrator runtime evidence:

```text
gw_energypilot.runtime.<config_entry_id>
gw_energypilot.control.<config_entry_id>
gw_energypilot.optimization_log.<config_entry_id>
gw_energypilot.execution.<config_entry_id>
```

They are not configuration databases and must not contain user settings that belong in the config entry.

## Last successful optimization

Issue #24 exposed that `last_success` previously existed only in the in-memory orchestrator object. A config-entry reload created a new orchestrator and initialized the value to `None`, which made the dashboard display `Last success: Never` even after a previously successful EnergyPilot-owned optimization.

The runtime store persists:

```json
{
  "last_success": "2026-08-23T18:30:00+00:00"
}
```

Behavior contract:

- restore `last_success` before the active orchestrator starts;
- write it only after a complete EnergyPilot-owned optimize + publish cycle succeeds;
- a failed later optimization must not clear or replace the previous successful timestamp;
- dashboard/coordinator refreshes do not modify it;
- config-entry reloads and Home Assistant restarts preserve it;
- a newer successful run replaces the previous timestamp.

Malformed or timezone-less stored timestamps are ignored safely and do not block integration startup.

## Last successful EMS setpoint update

Issue #96 adds a separate controller-history store:

```json
{
  "last_ems_setpoint_updated_at": "2026-08-30T08:15:02+00:00",
  "last_ems_setpoint": 3750,
  "last_ems_mode": 9,
  "last_command": "grid_import_target"
}
```

The timestamp advances only after the existing complete EMS command returns without a Modbus error. That command still writes setpoint register `47512`, waits and then writes mode register `47511`. A command skipped because current mode/setpoint read-back already matches does not advance the timestamp. A failed or partial command also leaves the previous successful evidence intact.

The value is deliberately described as an **EMS setpoint update**, not verified read-back. The normal coordinator refresh still supplies live mode/setpoint telemetry separately. The persisted context is exposed through the existing `control_command` diagnostic entity, Optimize diagnostics, support report and opt-in LOG session. It survives config-entry reloads and Home Assistant restarts without changing Automatic Control ownership or reissuing a command.

## Optimization history

v0.25 adds a separate bounded optimization-history store owned by `optimization_log.py`.

The newest 50 EnergyPilot-owned optimization attempts are retained. Both successful and failed attempts are recorded so manual, periodic and event-triggered runs can be compared after the fact.

Each record contains diagnostic context available to EnergyPilot at run time, including:

```text
started_at / finished_at
duration_seconds
reason
success
soc_init / soc_final
current_load
price_source / price_area / price_points
load_forecast_points
p_batt
optimize_http_status / publish_http_status
error
```

The history is chronological, oldest first, and automatically drops the oldest entry when the 51st record is written. A failure to write diagnostic history is logged but must never turn an otherwise successful optimization into a control failure.

The optimization log is deliberately separate from `last_success`: failed runs are valuable diagnostic evidence, while `last_success` must continue to represent the most recent completed optimize + publish cycle only.

## EMHASS-to-GoodWe execution history

The v0.51 feature layer, promoted in v1.0.0, adds a bounded evidence ledger for issue #108. It is not a command queue
and never becomes a control input. Each event snapshots the information that
was available when Automatic Control evaluated a plan:

```text
UTC instant + monotonic sequence
Home Assistant runtime session ID
automatic/manual ownership
P_batt / P_grid / wanted SOC + live-or-mirror source
plan generation / validity / revision
strategy + legacy/explicit source + deadband + maximum + EV state
actual battery SOC/power, combined PV, load, grid, EMS mode/setpoint
expected command/mode/setpoint
write status + post-refresh verification/read-back
```

The ledger retains seven elapsed days and at most 4096 oldest-first records.
The public chart API returns only the last 48 elapsed hours. UTC persistence
keeps repeated DST wall-clock hours distinct; the dashboard formats instants
using Home Assistant's configured timezone.

Completed writes are followed by the established coordinator refresh. Matching
mode and setpoint become `verified`; a finite disagreement becomes `mismatch`;
missing/failing refresh evidence becomes `unavailable`. A matching pre-write
read-back is stored as `skipped_matching_readback` and `verified`. Write and
Store failures are distinct: execution-history persistence is best-effort and
must never change whether a GoodWe transaction succeeds or propagates its
existing error.

History is immutable snapshot evidence. A later plan, strategy, deadband,
maximum-power or PV-source configuration change affects only future records.
There is intentionally no retroactive reconstruction because Recorder does not
contain the exact decision, ownership and verification context.

The Store omits configured entity IDs, EMHASS URLs/tokens and arbitrary Home
Assistant attributes. It does retain local power/SOC/strategy evidence and
therefore remains private installation data. Existing installations need no
migration: the new Store starts empty. Malformed/out-of-retention records are
ignored or pruned on restore.

The in-memory sequence is exposed as an execution-history revision so the
dashboard can refresh only the affected evidence/chart regions. The revision
is not persistent control state. A random controller runtime session ID is
stored with every new event so verified EV protection spans never bridge a
Home Assistant restart merely because two retained records have compatible
commands.

## Scope

Only durable runtime evidence belongs in these stores. User configuration remains in the Home Assistant config entry.

These storage layers do not change GoodWe Modbus registers, EMS ownership, controller behavior, EMHASS optimization inputs, entity IDs or unique IDs.
