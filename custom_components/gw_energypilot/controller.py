"""Automatic control logic for GW EnergyPilot."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
import logging
from math import isfinite
from typing import TYPE_CHECKING
from uuid import uuid4

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.event import async_track_state_change_event

from .client import GWModbusClient
from .control_decision import resolve_control_decision
from .const import (
    CONF_CONTROL_STRATEGY,
    CONF_DEADBAND,
    CONF_ENABLE_EMHASS_ORCHESTRATOR,
    CONF_ENABLE_EV_COORDINATION,
    CONF_ENABLE_EXTERNAL_PV,
    CONF_ENABLE_INTERNAL_PV,
    CONF_EV_DEADBAND,
    CONF_EV_MODE_ENTITY,
    CONF_EV_POWER_ENTITY,
    CONF_GOODWE_AUTO_DEADBAND,
    CONF_MAX_POWER,
    CONF_OPTIM_REQUIRED_STATE,
    CONF_OPTIM_STATUS_ENTITY,
    CONF_P_BATT_ENTITY,
    CONF_P_GRID_ENTITY,
    CONF_USE_GOODWE_SMART_METER,
    CONTROL_STRATEGIES,
    CONTROL_STRATEGY_BATTERY,
    CONTROL_STRATEGY_GRID,
    CONTROL_STRATEGY_HYBRID,
    DEFAULT_DEADBAND,
    DEFAULT_ENABLE_EXTERNAL_PV,
    DEFAULT_ENABLE_INTERNAL_PV,
    DEFAULT_EV_DEADBAND,
    DEFAULT_GOODWE_AUTO_DEADBAND,
    DEFAULT_MAX_POWER,
    DEFAULT_OPTIM_REQUIRED_STATE,
    DEFAULT_P_BATT_ENTITY,
    DEFAULT_P_GRID_ENTITY,
    DEFAULT_USE_GOODWE_SMART_METER,
    DOMAIN,
    EV_DETECTION_METHOD_POWER,
    EV_DETECTION_METHOD_STATE,
    EXTERNAL_PV_ENTITY_KEYS,
    MODE_AUTO,
    MODE_BATTERY_HOLD,
    MODE_CHARGE_BATTERY,
    MODES_ZERO_POWER,
)
from .coordinator import GWEnergyPilotCoordinator
from .ev_detection import (
    detection_method,
    legacy_status_is_active,
    power_is_active,
    source_entity_ids,
    status_is_active,
)
from .pv_insight import (
    external_sources_enabled,
    normalize_generation_power_w,
    sum_generation_power_w,
)

if TYPE_CHECKING:
    from .control_history import GWEnergyPilotControlHistory
    from .execution_history import GWEnergyPilotExecutionHistory


_LOGGER = logging.getLogger(__name__)


class GWEnergyPilotController:
    """Translate the current EMHASS plan into GoodWe EMS commands.

    Automatic Control supports three strategies:

    Battery control:
      P_batt < 0 = mode 11 direct battery charge target
      P_batt > 0 = mode 12 direct battery discharge target
      P_batt ~= 0 = mode 8 Battery Hold

    Grid control:
      P_grid > 0 = mode 9 import target at the PCC
      P_grid < 0 = mode 10 export target at the PCC
      P_grid ~= 0 = mode 1 GoodWe Auto / self-use balancing

    Hybrid control:
      P_batt ~= 0 = mode 8 Battery Hold
      otherwise P_grid ~= 0 = mode 1 GoodWe Auto / self-use balancing
      otherwise P_grid > 0 = mode 9 import target at the PCC
      otherwise P_grid < 0 = mode 10 export target at the PCC

    Hybrid gives an explicit neutral battery plan first priority. For every
    non-neutral battery plan it controls the PCC: GoodWe self-use owns a
    near-zero grid plan, and modes 9/10 own non-zero import/export targets.
    Separate configured deadbands classify neutral battery power and near-zero
    grid power. Neither is subtracted from a non-zero setpoint.

    Existing installations without an explicit strategy retain the legacy
    smart-meter boolean mapping for backwards compatibility.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry,
        client: GWModbusClient,
        coordinator: GWEnergyPilotCoordinator,
        control_history: GWEnergyPilotControlHistory | None = None,
        execution_history: GWEnergyPilotExecutionHistory | None = None,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client
        self.coordinator = coordinator
        self.control_history = control_history
        self.execution_history = execution_history
        self.execution_session_id = uuid4().hex
        self.enabled = False
        self.target_power = 0
        self.expected_mode = MODE_AUTO
        self.last_command = "goodwe_auto"
        self.last_ems_setpoint_updated_at = (
            control_history.last_ems_setpoint_updated_at
            if control_history is not None
            else None
        )
        self.last_ems_setpoint = (
            control_history.last_ems_setpoint
            if control_history is not None
            else None
        )
        self.last_ems_mode = (
            control_history.last_ems_mode
            if control_history is not None
            else None
        )
        self.last_ems_setpoint_command = (
            control_history.last_command
            if control_history is not None
            else None
        )
        self.manual_power = min(DEFAULT_MAX_POWER, int(entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER)))
        self.manual_charge_limit_soc: float | None = None
        self._unsubs: list[Callable[[], None]] = []
        self._ev_was_active = False
        self._ev_coordination_was_effective = True
        self._control_lock = asyncio.Lock()
        self._plan_update_suspensions = 0
        self.grid_neutral_active = False
        self.grid_neutral_charge_cap = 0
        self.grid_neutral_last_meter_power: float | None = None
        self.grid_neutral_export_samples = 0

    @property
    def signal(self) -> str:
        return f"{DOMAIN}_{self.entry.entry_id}_controller_update"

    @property
    def grid_neutral_hold_remaining(self) -> int:
        return 0

    @property
    def control_strategy(self) -> str:
        """Return configured strategy with legacy boolean fallback."""
        data = getattr(self.entry, "data", {}) or {}
        configured = data.get(CONF_CONTROL_STRATEGY)
        if configured in CONTROL_STRATEGIES:
            return str(configured)
        return CONTROL_STRATEGY_GRID if bool(data.get(CONF_USE_GOODWE_SMART_METER, DEFAULT_USE_GOODWE_SMART_METER)) else CONTROL_STRATEGY_BATTERY

    @property
    def use_goodwe_smart_meter(self) -> bool:
        """Compatibility property for older diagnostics/frontend layers."""
        return self.control_strategy != CONTROL_STRATEGY_BATTERY

    @property
    def ev_protection_state(self) -> str:
        """Return the presentation state of the EV anti-discharge guard.

        This is deliberately derived from the already selected controller
        command. It exposes control ownership without adding another control
        decision or write path.
        """
        if self.last_command == "waiting_for_ev_stop_optimization":
            return "waiting_for_fresh_plan"
        if not self.enabled or not self.ev_is_active():
            return "inactive"
        if self.last_command == "ev_anti_discharge_hold":
            return "blocking_discharge"
        if self.last_command in {
            "ev_battery_charge",
            "ev_charge_allowed",
            "ev_charge_fallback",
            "ev_grid_import_charge",
        }:
            return "allowing_charge"
        return "active_pending"

    def _notify_state(self) -> None:
        async_dispatcher_send(self.hass, self.signal)

    def _p_batt_entity_id(self) -> str:
        return str(self.entry.options.get(CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY) or DEFAULT_P_BATT_ENTITY)

    def _p_grid_entity_id(self) -> str:
        return str(self.entry.options.get(CONF_P_GRID_ENTITY, DEFAULT_P_GRID_ENTITY) or DEFAULT_P_GRID_ENTITY)

    @property
    def ev_source_ids(self) -> set[str]:
        """Return the selected EV activity source."""
        return source_entity_ids(self.entry.options)

    async def async_setup(self) -> None:
        self._ev_coordination_was_effective = self._ev_coordination_effective()
        self._ev_was_active = self.ev_is_active()
        entity_ids = {self._p_batt_entity_id(), self._p_grid_entity_id(), self.entry.options.get(CONF_OPTIM_STATUS_ENTITY), *self.ev_source_ids}
        entity_ids.discard(None)
        entity_ids.discard("")
        if entity_ids:
            self._unsubs.append(async_track_state_change_event(self.hass, list(entity_ids), self._async_source_changed))
        add_listener = getattr(self.coordinator, "async_add_listener", None)
        if add_listener is not None:
            self._unsubs.append(add_listener(self._async_coordinator_updated))
        runtime_data = getattr(self.entry, "runtime_data", None)
        connectivity = getattr(runtime_data, "connectivity", None)
        if connectivity is not None:
            self._unsubs.append(
                async_dispatcher_connect(
                    self.hass,
                    connectivity.signal,
                    self._async_connectivity_updated,
                )
            )

    async def async_unload(self) -> None:
        while self._unsubs:
            self._unsubs.pop()()

    @callback
    def _async_source_changed(self, event: Event) -> None:
        if not self.enabled:
            return
        entity_id = str(event.data.get("entity_id") or "")
        if entity_id in self.ev_source_ids:
            ev_active = self.ev_is_active()
            ev_was_active = self._ev_was_active
            self._ev_was_active = ev_active
            if ev_active:
                self.hass.async_create_task(
                    self.async_evaluate(allow_suspended=True),
                    "gw-energypilot-ev-anti-discharge",
                )
                return
            if ev_was_active and self.entry.options.get(CONF_ENABLE_EMHASS_ORCHESTRATOR, False):
                self.target_power = 0
                self.expected_mode = MODE_BATTERY_HOLD
                self.last_command = "waiting_for_ev_stop_optimization"
                self._notify_state()
                return
        if self._plan_update_suspensions:
            return
        self.hass.async_create_task(self.async_evaluate(), "gw-energypilot-evaluate")

    @callback
    def _async_coordinator_updated(self) -> None:
        """Stop the Max charge quick action when its captured SOC limit is met."""
        if self.last_command != "manual_max_charge" or self.manual_charge_limit_soc is None:
            return
        battery_soc = self._battery_soc()
        if battery_soc is None or battery_soc < self.manual_charge_limit_soc:
            return
        self.hass.async_create_task(
            self._async_stop_manual_max_charge_at_limit(),
            "gw-energypilot-max-charge-soc-limit",
        )

    def _raw_state_float(self, entity_id: str | None) -> float | None:
        """Return only the finite live HA state, without plan fallback."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in {"unknown", "unavailable", "none", ""}:
            return None
        try:
            value = float(state.state)
        except (TypeError, ValueError):
            return None
        return value if isfinite(value) else None

    def _state_float(self, entity_id: str | None) -> float | None:
        return self._raw_state_float(entity_id)

    @staticmethod
    def _finite_value(value: object) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if isfinite(number) else None

    def _combined_pv_actual(self, values: dict[str, object]) -> tuple[float | None, dict[str, int | bool]]:
        """Return the same configured display-only PV aggregate used by the UI."""
        options = self.entry.options
        source_values: list[float | None] = []
        internal_enabled = bool(
            options.get(CONF_ENABLE_INTERNAL_PV, DEFAULT_ENABLE_INTERNAL_PV)
        )
        if internal_enabled:
            source_values.append(
                normalize_generation_power_w(values.get("pv_total_power"), "W")
            )

        external_enabled = external_sources_enabled(
            options,
            enable_key=CONF_ENABLE_EXTERNAL_PV,
            entity_keys=EXTERNAL_PV_ENTITY_KEYS,
            default=DEFAULT_ENABLE_EXTERNAL_PV,
        )
        configured_external = 0
        available_external = 0
        if external_enabled:
            seen: set[str] = set()
            for key in EXTERNAL_PV_ENTITY_KEYS:
                entity_id = str(options.get(key, "") or "").strip()
                if not entity_id or entity_id in seen:
                    continue
                seen.add(entity_id)
                configured_external += 1
                state = self.hass.states.get(entity_id)
                attributes = getattr(state, "attributes", {}) if state else {}
                power = normalize_generation_power_w(
                    getattr(state, "state", None),
                    attributes.get("unit_of_measurement"),
                )
                if power is not None:
                    available_external += 1
                source_values.append(power)

        return sum_generation_power_w(source_values), {
            "internal_enabled": internal_enabled,
            "external_enabled": external_enabled,
            "configured_external_sources": configured_external,
            "available_external_sources": available_external,
        }

    def _actual_snapshot(self) -> dict[str, object]:
        data = self.coordinator.data
        values = getattr(data, "values", {}) if data is not None else {}
        values = values if isinstance(values, dict) else {}
        pv_power, pv_topology = self._combined_pv_actual(values)
        return {
            "battery_soc_pct": self._finite_value(values.get("battery_soc")),
            "battery_power_w": self._finite_value(values.get("battery_power")),
            "pv_power_w": pv_power,
            "load_power_w": self._finite_value(values.get("total_load_power")),
            "grid_power_w": self._finite_value(values.get("meter_total_power_fast")),
            "ems_mode": getattr(data, "mode", None) if data is not None else None,
            "ems_setpoint_w": getattr(data, "power", None) if data is not None else None,
            "pv_topology": pv_topology,
        }

    @staticmethod
    def _state_reported_at(state: object | None) -> str | None:
        if state is None:
            return None
        timestamp = getattr(state, "last_reported", None) or getattr(
            state, "last_updated", None
        )
        return timestamp.isoformat() if timestamp is not None else None

    def _execution_context(self) -> dict[str, object]:
        p_batt_entity = self._p_batt_entity_id()
        p_grid_entity = self._p_grid_entity_id()
        p_batt_state = self.hass.states.get(p_batt_entity)
        p_grid_state = self.hass.states.get(p_grid_entity)
        live_p_batt = self._raw_state_float(p_batt_entity)
        live_p_grid = self._raw_state_float(p_grid_entity)
        p_batt = self._state_float(p_batt_entity)
        p_grid = self._state_float(p_grid_entity)
        runtime_data = getattr(self.entry, "runtime_data", None)
        plan_runtime = getattr(runtime_data, "plan_runtime", None)
        orchestrator = getattr(runtime_data, "orchestrator", None)
        diagnostics = (
            dict(plan_runtime.diagnostics) if plan_runtime is not None else {}
        )
        current_soc = getattr(plan_runtime, "current_soc_opt", None)
        configured_strategy = (getattr(self.entry, "data", {}) or {}).get(
            CONF_CONTROL_STRATEGY
        )
        return {
            "occurred_at": datetime.now(timezone.utc),
            "kind": "controller_decision",
            "runtime_session_id": self.execution_session_id,
            "owner": "automatic" if self.enabled else "manual",
            "plan": {
                "p_batt_w": p_batt,
                "p_grid_w": p_grid,
                "soc_opt_pct": current_soc() if callable(current_soc) else None,
                "p_batt_source": (
                    "home_assistant"
                    if live_p_batt is not None
                    else "persistent_plan"
                    if p_batt is not None
                    else None
                ),
                "p_grid_source": (
                    "home_assistant"
                    if live_p_grid is not None
                    else "persistent_plan"
                    if p_grid is not None
                    else None
                ),
                "p_batt_reported_at": self._state_reported_at(p_batt_state),
                "p_grid_reported_at": self._state_reported_at(p_grid_state),
                "mirror_source": diagnostics.get("source"),
                "generated_at": diagnostics.get("generated_at"),
                "valid_until": diagnostics.get("valid_until"),
                "revision": int(getattr(orchestrator, "plan_revision", 0) or 0),
            },
            "configuration": {
                "strategy": self.control_strategy,
                "strategy_source": (
                    "explicit"
                    if configured_strategy in CONTROL_STRATEGIES
                    else "legacy_smart_meter"
                ),
                "deadband_w": float(
                    self.entry.options.get(CONF_DEADBAND, DEFAULT_DEADBAND)
                ),
                "battery_hold_deadband_w": float(
                    self.entry.options.get(CONF_DEADBAND, DEFAULT_DEADBAND)
                ),
                "goodwe_auto_deadband_w": float(
                    self.entry.options.get(
                        CONF_GOODWE_AUTO_DEADBAND,
                        DEFAULT_GOODWE_AUTO_DEADBAND,
                    )
                ),
                "max_power_w": int(
                    self.entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER)
                ),
                "ev_active": self.ev_is_active(),
            },
            "actual": self._actual_snapshot(),
        }

    async def _async_record_execution(
        self,
        context: dict[str, object],
        *,
        command: str,
        expected_mode: int | None,
        expected_power: int | None,
        write_status: str,
        verification_status: str,
        write_completed_at: datetime | None = None,
        readback_at: datetime | None = None,
        error_type: str | None = None,
    ) -> None:
        if self.execution_history is None:
            return
        event = dict(context)
        event["actual"] = self._actual_snapshot()
        event["outcome"] = {
            "command": command,
            "expected_mode": expected_mode,
            "expected_setpoint_w": expected_power,
            "write_status": write_status,
            "write_completed_at": write_completed_at,
            "verification_status": verification_status,
            "readback_at": readback_at,
            "readback_mode": event["actual"].get("ems_mode"),
            "readback_setpoint_w": event["actual"].get("ems_setpoint_w"),
            "error_type": error_type,
        }
        try:
            await self.execution_history.async_append(event)
        except Exception:  # noqa: BLE001 - history never owns the actuator
            _LOGGER.exception("Unable to append EnergyPilot execution evidence")

    async def _async_record_waiting(self, command: str) -> None:
        await self._async_record_execution(
            self._execution_context(),
            command=command,
            expected_mode=None,
            expected_power=None,
            write_status="not_attempted",
            verification_status="not_applicable",
        )

    def _battery_soc(self) -> float | None:
        """Return the latest finite GoodWe battery SOC percentage."""
        if getattr(self.coordinator, "last_update_success", True) is False:
            return None
        data = self.coordinator.data
        values = getattr(data, "values", {}) if data is not None else {}
        raw = values.get("battery_soc") if isinstance(values, dict) else None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        if not isfinite(value) or not 0.0 <= value <= 100.0:
            return None
        return value

    def _ev_coordination_effective(self) -> bool:
        if not self.entry.options.get(CONF_ENABLE_EV_COORDINATION, False):
            return False
        runtime_data = getattr(self.entry, "runtime_data", None)
        connectivity = getattr(runtime_data, "connectivity", None)
        if connectivity is None:
            return True
        return bool(connectivity.ev_coordination_effective)

    def ev_is_active(self) -> bool:
        if not self._ev_coordination_effective():
            return False
        mode_entity = self.entry.options.get(CONF_EV_MODE_ENTITY)
        power_entity = self.entry.options.get(CONF_EV_POWER_ENTITY)
        ev_deadband = float(self.entry.options.get(CONF_EV_DEADBAND, DEFAULT_EV_DEADBAND))
        status_active = status_is_active(self.hass.states, mode_entity)
        power_active = power_is_active(self.hass.states, power_entity, ev_deadband)
        method = detection_method(self.entry.options)
        if method == EV_DETECTION_METHOD_STATE:
            return status_active
        if method == EV_DETECTION_METHOD_POWER:
            return power_active
        # Entries created before the selector existed retain their exact former
        # connected_charging-or-power behavior until an explicit choice is saved.
        return (
            legacy_status_is_active(self.hass.states, mode_entity)
            or power_active
        )

    @callback
    def _async_connectivity_updated(self) -> None:
        """Re-evaluate only when effective EV coordination changes."""
        effective = self._ev_coordination_effective()
        if effective == self._ev_coordination_was_effective:
            return
        self._ev_coordination_was_effective = effective
        self._ev_was_active = self.ev_is_active()
        self._notify_state()
        if self.enabled:
            self.hass.async_create_task(
                self.async_evaluate(),
                "gw-energypilot-ev-connectivity-change",
            )

    def _optim_is_ready(self) -> bool:
        entity_id = self.entry.options.get(CONF_OPTIM_STATUS_ENTITY)
        if not entity_id:
            return True
        state = self.hass.states.get(entity_id)
        if state is None:
            return False
        required = str(self.entry.options.get(CONF_OPTIM_REQUIRED_STATE, DEFAULT_OPTIM_REQUIRED_STATE))
        return state.state == required

    def _actual_command_matches(self, mode: int, power: int) -> bool:
        data = self.coordinator.data
        if data is None or getattr(data, "mode", None) != mode:
            return False
        actual_power = getattr(data, "power", None)
        return actual_power is not None and int(actual_power) == int(power)

    async def _async_apply_command(self, mode: int, power: int, command: str, *, skip_if_readback_matches: bool = False) -> None:
        context = self._execution_context()
        power = max(0, min(int(power), 15000))
        if mode in MODES_ZERO_POWER:
            power = 0
        self.target_power = power
        self.expected_mode = mode
        self.last_command = command
        self._notify_state()
        if skip_if_readback_matches and self._actual_command_matches(mode, power):
            await self._async_record_execution(
                context,
                command=command,
                expected_mode=mode,
                expected_power=power,
                write_status="skipped_matching_readback",
                verification_status="verified",
                readback_at=datetime.now(timezone.utc),
            )
            self._notify_state()
            return
        try:
            await self.client.async_set_mode(mode, power)
        except Exception as err:
            await self._async_record_execution(
                context,
                command=command,
                expected_mode=mode,
                expected_power=power,
                write_status="failed",
                verification_status="not_attempted",
                error_type=type(err).__name__,
            )
            self._notify_state()
            raise
        timestamp = datetime.now(timezone.utc)
        self.last_ems_setpoint_updated_at = timestamp
        self.last_ems_setpoint = power
        self.last_ems_mode = mode
        self.last_ems_setpoint_command = command
        if self.control_history is not None:
            self.control_history.record(
                timestamp,
                setpoint=power,
                mode=mode,
                command=command,
            )
            await self.control_history.async_save()
        self._notify_state()
        refresh_error: Exception | None = None
        try:
            refresh_control = getattr(
                self.coordinator,
                "async_refresh_control_readback",
                None,
            )
            if callable(refresh_control):
                await refresh_control()
            else:
                await self.coordinator.async_request_refresh()
        except Exception as err:  # preserve the established propagation contract
            refresh_error = err
        readback_at = datetime.now(timezone.utc)
        actual = self._actual_snapshot()
        readback_mode = actual.get("ems_mode")
        readback_power = actual.get("ems_setpoint_w")
        verification_status = (
            "verified"
            if readback_mode == mode and readback_power == power
            else "unavailable"
            if readback_mode is None or readback_power is None or refresh_error
            else "mismatch"
        )
        await self._async_record_execution(
            context,
            command=command,
            expected_mode=mode,
            expected_power=power,
            write_status="completed",
            verification_status=verification_status,
            write_completed_at=timestamp,
            readback_at=readback_at,
            error_type=type(refresh_error).__name__ if refresh_error else None,
        )
        self._notify_state()
        if refresh_error is not None:
            raise refresh_error

    async def async_enable(self) -> None:
        self.manual_charge_limit_soc = None
        self.enabled = True
        self._ev_was_active = self.ev_is_active()
        self._notify_state()
        await self.async_evaluate()

    async def async_disable(self) -> None:
        async with self._control_lock:
            self.manual_charge_limit_soc = None
            self.enabled = False
            await self._async_apply_command(MODE_AUTO, 0, "goodwe_auto")

    async def async_hold_for_plan_step(self, command: str) -> None:
        """Fail safe to Battery Hold when a scheduled plan step is unavailable."""
        async with self._control_lock:
            if not self.enabled:
                return
            await self._async_apply_command(
                MODE_BATTERY_HOLD,
                0,
                command,
                skip_if_readback_matches=True,
            )

    def suspend_plan_updates(self) -> None:
        """Defer ordinary plan-source events until publication is complete."""
        self._plan_update_suspensions += 1

    def resume_plan_updates(self) -> None:
        """Release one plan-publication suspension without going negative."""
        self._plan_update_suspensions = max(0, self._plan_update_suspensions - 1)

    async def async_manual_command(self, mode: int, power: int, command: str) -> None:
        async with self._control_lock:
            self.manual_charge_limit_soc = None
            self.enabled = False
            await self._async_apply_command(mode, power, command)

    async def async_manual_max_charge(self, power: int, maximum_soc: float) -> None:
        """Start Max charge with a telemetry-enforced EMHASS maximum-SOC ceiling."""
        try:
            limit_soc = float(maximum_soc)
        except (TypeError, ValueError) as err:
            raise ValueError("Maximum battery SOC is not numeric") from err
        if not isfinite(limit_soc) or not 0.0 <= limit_soc <= 100.0:
            raise ValueError("Maximum battery SOC must be between 0 and 100%")

        async with self._control_lock:
            battery_soc = self._battery_soc()
            if battery_soc is None:
                raise ValueError("Current GoodWe battery SOC is unavailable")

            self.enabled = False
            self.manual_charge_limit_soc = limit_soc
            if battery_soc >= limit_soc:
                await self._async_apply_command(
                    MODE_BATTERY_HOLD,
                    0,
                    "manual_max_charge_soc_limit",
                    skip_if_readback_matches=True,
                )
                return
            await self._async_apply_command(
                MODE_CHARGE_BATTERY,
                power,
                "manual_max_charge",
            )

    async def _async_stop_manual_max_charge_at_limit(self) -> None:
        """Recheck the SOC ceiling under the control lock and hold the battery."""
        async with self._control_lock:
            if self.last_command != "manual_max_charge" or self.manual_charge_limit_soc is None:
                return
            battery_soc = self._battery_soc()
            if battery_soc is None or battery_soc < self.manual_charge_limit_soc:
                return
            await self._async_apply_command(
                MODE_BATTERY_HOLD,
                0,
                "manual_max_charge_soc_limit",
                skip_if_readback_matches=True,
            )

    async def _async_apply_direct_battery_plan(
        self, p_batt: float, battery_deadband: float, max_power: int
    ) -> None:
        decision = resolve_control_decision(
            strategy=CONTROL_STRATEGY_BATTERY,
            p_batt=p_batt,
            p_grid=None,
            battery_deadband=battery_deadband,
            grid_deadband=DEFAULT_GOODWE_AUTO_DEADBAND,
            max_power=max_power,
        )
        await self._async_apply_command(
            int(decision.mode),
            int(decision.power),
            decision.command,
            skip_if_readback_matches=True,
        )

    async def _async_apply_ev_anti_discharge_plan(
        self,
        p_batt: float,
        battery_deadband: float,
        grid_deadband: float,
        max_power: int,
    ) -> None:
        decision = resolve_control_decision(
            strategy=CONTROL_STRATEGY_BATTERY,
            p_batt=p_batt,
            p_grid=None,
            battery_deadband=battery_deadband,
            grid_deadband=grid_deadband,
            max_power=max_power,
            ev_active=True,
        )
        command = (
            "ev_charge_allowed"
            if decision.command == "ev_battery_charge"
            else decision.command
        )
        await self._async_apply_command(
            int(decision.mode),
            int(decision.power),
            command,
            skip_if_readback_matches=True,
        )

    async def _async_apply_smart_meter_plan(
        self, p_grid: float, grid_deadband: float, max_power: int
    ) -> None:
        decision = resolve_control_decision(
            strategy=CONTROL_STRATEGY_GRID,
            p_batt=0,
            p_grid=p_grid,
            battery_deadband=DEFAULT_DEADBAND,
            grid_deadband=grid_deadband,
            max_power=max_power,
        )
        await self._async_apply_command(
            int(decision.mode),
            int(decision.power),
            decision.command,
            skip_if_readback_matches=True,
        )

    async def _async_apply_hybrid_plan(
        self,
        p_batt: float,
        p_grid: float,
        battery_deadband: float,
        grid_deadband: float,
        max_power: int,
    ) -> None:
        """Hold neutral battery plans, otherwise execute the signed PCC plan."""
        decision = resolve_control_decision(
            strategy=CONTROL_STRATEGY_HYBRID,
            p_batt=p_batt,
            p_grid=p_grid,
            battery_deadband=battery_deadband,
            grid_deadband=grid_deadband,
            max_power=max_power,
        )
        await self._async_apply_command(
            int(decision.mode),
            int(decision.power),
            decision.command,
            skip_if_readback_matches=True,
        )

    async def _async_evaluate_locked(self) -> None:
        if not self.enabled:
            return
        p_batt = self._state_float(self._p_batt_entity_id())
        if p_batt is None:
            self.last_command = "waiting_for_p_batt"
            self._notify_state()
            await self._async_record_waiting(self.last_command)
            return
        if not self._optim_is_ready():
            self.last_command = "waiting_for_optimization"
            self._notify_state()
            await self._async_record_waiting(self.last_command)
            return
        battery_deadband = float(
            self.entry.options.get(CONF_DEADBAND, DEFAULT_DEADBAND)
        )
        grid_deadband = float(
            self.entry.options.get(
                CONF_GOODWE_AUTO_DEADBAND,
                DEFAULT_GOODWE_AUTO_DEADBAND,
            )
        )
        max_power = int(self.entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER))
        if self.ev_is_active():
            await self._async_apply_ev_anti_discharge_plan(
                p_batt,
                battery_deadband,
                grid_deadband,
                max_power,
            )
            return
        strategy = self.control_strategy
        if strategy == CONTROL_STRATEGY_BATTERY:
            await self._async_apply_direct_battery_plan(
                p_batt, battery_deadband, max_power
            )
            return
        p_grid = self._state_float(self._p_grid_entity_id())
        if p_grid is None:
            self.last_command = "waiting_for_p_grid"
            self._notify_state()
            await self._async_record_waiting(self.last_command)
            return
        if strategy == CONTROL_STRATEGY_HYBRID:
            await self._async_apply_hybrid_plan(
                p_batt,
                p_grid,
                battery_deadband,
                grid_deadband,
                max_power,
            )
            return
        await self._async_apply_smart_meter_plan(p_grid, grid_deadband, max_power)

    async def async_evaluate(self, *, allow_suspended: bool = False) -> None:
        if self._plan_update_suspensions and not allow_suspended:
            return
        async with self._control_lock:
            await self._async_evaluate_locked()
