# Persistent runtime state

GW EnergyPilot keeps configuration and runtime history separate.

## Ownership

- `ConfigEntry.data` and `ConfigEntry.options` remain the source of integration configuration.
- GoodWe registers remain the source of inverter-stored settings and live hardware state.
- EMHASS remains the source of optimizer configuration and published plan outputs.
- Small EnergyPilot-owned runtime history that must survive an integration reload or Home Assistant restart is stored with Home Assistant's `Store` helper.

The runtime store is per GW EnergyPilot config entry:

```text
gw_energypilot.runtime.<config_entry_id>
```

It is not a second configuration database and must not contain user settings that belong in the config entry.

## Last successful optimization

Issue #24 exposed that `last_success` previously existed only in the in-memory orchestrator object. A config-entry reload created a new orchestrator and initialized the value to `None`, which made the dashboard display `Last success: Never` even after a previously successful EnergyPilot-owned optimization.

The runtime store now persists:

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

## Scope

Only durable runtime evidence belongs here. Current persisted state is intentionally limited to `last_success`. Future runtime fields may be added to the same versioned store when they have a clear persistence requirement.

This storage layer does not change GoodWe Modbus registers, EMS ownership, controller behavior, EMHASS optimization inputs, entity IDs or unique IDs.
