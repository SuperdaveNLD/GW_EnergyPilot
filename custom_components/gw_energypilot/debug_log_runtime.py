"""Runtime capture hooks for opt-in GW EnergyPilot debug sessions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_DEADBAND,
    CONF_ENABLE_EMHASS_ORCHESTRATOR,
    CONF_ENABLE_EV_COORDINATION,
    CONF_EV_MODE_ENTITY,
    CONF_EV_POWER_ENTITY,
    CONF_MAX_POWER,
    CONF_OPTIM_REQUIRED_STATE,
    CONF_OPTIM_STATUS_ENTITY,
    CONF_P_BATT_ENTITY,
    CONF_P_GRID_ENTITY,
    CONF_SCAN_INTERVAL,
    DEFAULT_DEADBAND,
    DEFAULT_MAX_POWER,
    DEFAULT_OPTIM_REQUIRED_STATE,
    DEFAULT_OPTIM_STATUS_ENTITY,
    DEFAULT_P_BATT_ENTITY,
    DEFAULT_P_GRID_ENTITY,
    DEFAULT_SCAN_INTERVAL,
)
from .debug_log import GWEnergyPilotDebugLog
from .registers import REGISTER_DEFINITIONS


class GWEnergyPilotDebugRuntime:
    """Observe existing runtime signals without adding a second control path."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.log = GWEnergyPilotDebugLog()
        self._entry = None
        self._unsubs: list[Callable[[], None]] = []

    def _runtime(self):
        entry = self._entry
        return getattr(entry, "runtime_data", None) if entry is not None else None

    @staticmethod
    def _state_payload(state) -> dict[str, Any] | None:
        if state is None:
            return None
        return {
            "entity_id": state.entity_id,
            "state": state.state,
            "last_changed": state.last_changed.isoformat(),
            "last_updated": state.last_updated.isoformat(),
        }

    def _source_entity_ids(self) -> set[str]:
        entry = self._entry
        if entry is None:
            return set()
        options = entry.options
        entity_ids = {
            str(options.get(CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY) or DEFAULT_P_BATT_ENTITY),
            str(options.get(CONF_P_GRID_ENTITY, DEFAULT_P_GRID_ENTITY) or DEFAULT_P_GRID_ENTITY),
            str(
                options.get(CONF_OPTIM_STATUS_ENTITY, DEFAULT_OPTIM_STATUS_ENTITY)
                or DEFAULT_OPTIM_STATUS_ENTITY
            ),
        }
        for key in (CONF_EV_MODE_ENTITY, CONF_EV_POWER_ENTITY):
            value = options.get(key)
            if value:
                entity_ids.add(str(value))
        return entity_ids

    def _sources_snapshot(self) -> dict[str, Any]:
        return {
            entity_id: self._state_payload(self.hass.states.get(entity_id))
            for entity_id in sorted(self._source_entity_ids())
        }

    def _controller_snapshot(self) -> dict[str, Any]:
        runtime = self._runtime()
        controller = getattr(runtime, "controller", None)
        entry = self._entry
        if controller is None or entry is None:
            return {}
        options = entry.options
        return {
            "enabled": controller.enabled,
            "control_strategy": controller.control_strategy,
            "last_command": controller.last_command,
            "target_power": controller.target_power,
            "expected_mode": controller.expected_mode,
            "manual_power": controller.manual_power,
            "manual_charge_limit_soc": controller.manual_charge_limit_soc,
            "ev_active": controller.ev_is_active(),
            "deadband": float(options.get(CONF_DEADBAND, DEFAULT_DEADBAND)),
            "max_power": int(options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER)),
            "optim_required_state": str(
                options.get(CONF_OPTIM_REQUIRED_STATE, DEFAULT_OPTIM_REQUIRED_STATE)
            ),
        }

    def _orchestrator_snapshot(self) -> dict[str, Any]:
        runtime = self._runtime()
        orchestrator = getattr(runtime, "orchestrator", None)
        if orchestrator is None:
            return {}
        return {
            "status": orchestrator.status,
            "last_error": orchestrator.last_error,
            "attributes": dict(orchestrator.attributes),
        }

    def _coordinator_snapshot(self) -> dict[str, Any]:
        runtime = self._runtime()
        coordinator = getattr(runtime, "coordinator", None)
        client = getattr(runtime, "client", None)
        if coordinator is None:
            return {}
        data = coordinator.data
        values = dict(data.values) if data is not None else {}
        last_exception = getattr(coordinator, "last_exception", None)
        modbus_client = getattr(client, "_client", None)
        return {
            "last_update_success": bool(coordinator.last_update_success),
            "last_exception": str(last_exception) if last_exception else None,
            "client_connected": bool(getattr(modbus_client, "connected", False)),
            "values": values,
        }

    def current_snapshot(self) -> dict[str, Any]:
        """Return a sanitized current-state snapshot for problem analysis."""
        entry = self._entry
        runtime = self._runtime()
        if entry is None or runtime is None:
            return {"entry_id": self.entry_id, "loaded": False}
        state = getattr(self.hass, "state", None)
        state_value = getattr(state, "value", None) or str(state)
        options = entry.options
        return {
            "entry_id": entry.entry_id,
            "loaded": True,
            "home_assistant": {
                "core_state": state_value,
                "time_zone": self.hass.config.time_zone,
            },
            "runtime_config": {
                "scan_interval_seconds": int(
                    options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                ),
                "native_orchestrator_enabled": bool(
                    options.get(CONF_ENABLE_EMHASS_ORCHESTRATOR, False)
                ),
                "ev_anti_discharge_enabled": bool(
                    options.get(CONF_ENABLE_EV_COORDINATION, False)
                ),
            },
            "controller": self._controller_snapshot(),
            "orchestrator": self._orchestrator_snapshot(),
            "coordinator": self._coordinator_snapshot(),
            "sources": self._sources_snapshot(),
            "register_catalog": {
                definition.key: {
                    "address": definition.address,
                    "data_type": str(definition.data_type),
                    "scale": definition.scale,
                    "precision": definition.precision,
                }
                for definition in REGISTER_DEFINITIONS
            },
        }

    def enable(self) -> dict[str, Any]:
        """Start a fresh capture session with a complete baseline."""
        self.log.enable(self.current_snapshot())
        return self.snapshot()

    def disable(self) -> dict[str, Any]:
        """Stop capture and retain all captured events for export."""
        self.log.disable(self.current_snapshot())
        return self.snapshot()

    def clear(self) -> dict[str, Any]:
        """Clear captured events and preserve a new baseline if still active."""
        active = self.log.enabled
        baseline = self.current_snapshot() if active else None
        self.log.clear()
        if active:
            self.log.record(
                "session",
                "buffer_cleared",
                {"baseline": baseline or {}},
            )
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        """Return debug session metadata, events and current runtime state."""
        result = self.log.snapshot()
        result["current"] = self.current_snapshot()
        return result

    async def async_start(self, entry) -> None:
        """Subscribe to the existing coordinator/controller/orchestrator signals."""
        self._entry = entry
        runtime = entry.runtime_data
        self._unsubs.append(
            runtime.coordinator.async_add_listener(self._async_coordinator_updated)
        )
        self._unsubs.append(
            async_dispatcher_connect(
                self.hass,
                runtime.controller.signal,
                self._async_controller_updated,
            )
        )
        self._unsubs.append(
            async_dispatcher_connect(
                self.hass,
                runtime.orchestrator.signal,
                self._async_orchestrator_updated,
            )
        )
        source_ids = sorted(self._source_entity_ids())
        if source_ids:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass,
                    source_ids,
                    self._async_source_changed,
                )
            )

    async def async_unload(self) -> None:
        """Stop observers and discard the intentionally non-persistent buffer."""
        while self._unsubs:
            self._unsubs.pop()()
        self.log.clear()
        self.log.enabled = False
        self._entry = None

    @callback
    def _async_coordinator_updated(self) -> None:
        snapshot = self._coordinator_snapshot()
        event = "poll_success" if snapshot.get("last_update_success") else "poll_failed"
        self.log.record("goodwe", event, snapshot)

    @callback
    def _async_controller_updated(self) -> None:
        runtime = self._runtime()
        coordinator = getattr(runtime, "coordinator", None)
        data = getattr(coordinator, "data", None)
        self.log.record(
            "controller",
            "state_changed",
            {
                **self._controller_snapshot(),
                "sources": self._sources_snapshot(),
                "goodwe_readback": {
                    "mode": getattr(data, "mode", None),
                    "setpoint": getattr(data, "power", None),
                },
            },
        )

    @callback
    def _async_orchestrator_updated(self) -> None:
        self.log.record(
            "emhass",
            "orchestrator_state_changed",
            self._orchestrator_snapshot(),
        )

    @callback
    def _async_source_changed(self, event: Event) -> None:
        self.log.record(
            "source",
            "state_changed",
            {
                "entity_id": event.data.get("entity_id"),
                "old": self._state_payload(event.data.get("old_state")),
                "new": self._state_payload(event.data.get("new_state")),
            },
        )
