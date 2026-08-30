"""Soft EV load balancing using the linked GoodWe meter currents."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
import math
from typing import Any

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.storage import Store

from .const import (
    CONF_ENABLE_EV_LOAD_BALANCING,
    CONF_EV_CHARGER_ALLOCATED_CURRENT_ENTITY,
    CONF_EV_CHARGER_CURRENT_ENTITY,
    CONF_EV_CHARGER_PHASE,
    CONF_EV_CHARGER_PHASES,
    CONF_EV_CHARGER_MAX_CURRENT,
    CONF_EV_CHARGER_MIN_CURRENT,
    CONF_EV_LOAD_BALANCE_WINDOW,
    CONF_GRID_CONNECTION_PROFILE,
    CONF_GRID_CUSTOM_CURRENT,
    DEFAULT_EV_CHARGER_PHASE,
    DEFAULT_EV_CHARGER_PHASES,
    DEFAULT_EV_CHARGER_MAX_CURRENT,
    DEFAULT_EV_CHARGER_MIN_CURRENT,
    DEFAULT_EV_LOAD_BALANCE_WINDOW,
    DEFAULT_GRID_CONNECTION_PROFILE,
    DEFAULT_GRID_CUSTOM_CURRENT,
    DOMAIN,
    EV_CHARGER_PHASE_OPTIONS,
    EV_FEEDBACK_TIMEOUT_SECONDS,
    EV_FEEDBACK_TOLERANCE,
    EV_LOAD_BALANCE_HYSTERESIS,
    GRID_CONNECTION_CUSTOM_PROFILES,
    GRID_CONNECTION_PROFILES,
)

AUDIT_STORE_VERSION = 1
AUDIT_STORE_KEY = f"{DOMAIN}.ev_load_balancing_audit"
GOODWE_PHASE_CURRENT_KEYS = {
    "l1": "meter_l1_current",
    "l2": "meter_l2_current",
    "l3": "meter_l3_current",
}


def grid_connection_limit(options: Mapping[str, Any]) -> float:
    """Return the configured per-phase service current."""
    profile = str(
        options.get(CONF_GRID_CONNECTION_PROFILE, DEFAULT_GRID_CONNECTION_PROFILE)
    )
    if profile in GRID_CONNECTION_PROFILES:
        return float(GRID_CONNECTION_PROFILES[profile][1])
    if profile in GRID_CONNECTION_CUSTOM_PROFILES:
        return float(options.get(CONF_GRID_CUSTOM_CURRENT, DEFAULT_GRID_CUSTOM_CURRENT))
    raise ValueError(f"Unsupported grid connection profile: {profile}")


def grid_connection_phases(options: Mapping[str, Any]) -> int:
    """Return the configured service phase count."""
    profile = str(
        options.get(CONF_GRID_CONNECTION_PROFILE, DEFAULT_GRID_CONNECTION_PROFILE)
    )
    if profile in GRID_CONNECTION_PROFILES:
        return GRID_CONNECTION_PROFILES[profile][0]
    if profile in GRID_CONNECTION_CUSTOM_PROFILES:
        return GRID_CONNECTION_CUSTOM_PROFILES[profile]
    raise ValueError(f"Unsupported grid connection profile: {profile}")


class EVLoadBalancingAudit:
    """Append-only audit history for acknowledged charger limits above 16 A."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store[dict[str, Any]](
            hass, AUDIT_STORE_VERSION, f"{AUDIT_STORE_KEY}.{entry_id}"
        )
        self._lock = asyncio.Lock()
        self._loaded = False
        self._history: list[dict[str, Any]] = []

    async def _async_load(self) -> None:
        if self._loaded:
            return
        stored = await self._store.async_load()
        history = stored.get("history", []) if isinstance(stored, dict) else []
        self._history = [dict(row) for row in history if isinstance(row, Mapping)]
        self._loaded = True

    async def async_append(self, record: Mapping[str, Any]) -> None:
        """Append without truncating or replacing earlier acknowledgements."""
        async with self._lock:
            await self._async_load()
            self._history.append(dict(record))
            await self._store.async_save({"history": list(self._history)})

    async def async_history(self) -> list[dict[str, Any]]:
        async with self._lock:
            await self._async_load()
            return [dict(row) for row in self._history]


class GWEnergyPilotEVLoadBalancer:
    """Adjust one charger current limit after sustained overload or headroom."""

    def __init__(self, hass: HomeAssistant, entry: Any) -> None:
        self.hass = hass
        self.entry = entry
        self.audit = EVLoadBalancingAudit(hass, entry.entry_id)
        self.signal = f"{DOMAIN}_{entry.entry_id}_ev_load_balancing"
        self.status = "disabled"
        self.last_action: str | None = None
        self.last_error: str | None = None
        self.measured_current: float | None = None
        self.phase_currents: dict[str, float | None] = {
            phase: None for phase in GOODWE_PHASE_CURRENT_KEYS
        }
        self.charger_limit: float | None = None
        self.allocated_current: float | None = None
        self.pending_target: float | None = None
        self.last_feedback_status = (
            "idle"
            if entry.options.get(CONF_EV_CHARGER_ALLOCATED_CURRENT_ENTITY)
            else "not_configured"
        )
        self.last_feedback_error: str | None = None
        self._condition: str | None = None
        self._timer_cancel: Callable[[], None] | None = None
        self._feedback_timer_cancel: Callable[[], None] | None = None
        self._unsub: Callable[[], None] | None = None
        self._coordinator_unsub: Callable[[], None] | None = None
        self._lock = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        return bool(self.entry.options.get(CONF_ENABLE_EV_LOAD_BALANCING, False))

    @property
    def connection_limit(self) -> float:
        return grid_connection_limit(self.entry.options)

    @property
    def charger_phases(self) -> int:
        """Return whether the charger draws on one or three phases."""
        return int(
            self.entry.options.get(
                CONF_EV_CHARGER_PHASES, DEFAULT_EV_CHARGER_PHASES
            )
        )

    @property
    def charger_phase(self) -> str:
        """Return the observed GoodWe meter phase for a one-phase charger."""
        phase = str(
            self.entry.options.get(CONF_EV_CHARGER_PHASE, DEFAULT_EV_CHARGER_PHASE)
        ).lower()
        return phase if phase in EV_CHARGER_PHASE_OPTIONS else DEFAULT_EV_CHARGER_PHASE

    @property
    def configured_minimum(self) -> float:
        return float(
            self.entry.options.get(
                CONF_EV_CHARGER_MIN_CURRENT, DEFAULT_EV_CHARGER_MIN_CURRENT
            )
        )

    @property
    def configured_maximum(self) -> float:
        return float(
            self.entry.options.get(
                CONF_EV_CHARGER_MAX_CURRENT, DEFAULT_EV_CHARGER_MAX_CURRENT
            )
        )

    async def async_setup(self) -> None:
        if not self.enabled:
            self._publish("disabled")
            return
        charger = str(
            self.entry.options.get(CONF_EV_CHARGER_CURRENT_ENTITY, "")
        ).strip()
        if not charger:
            self._publish("configuration_error", "Charger control entity missing")
            return
        observed_entities = [charger]
        feedback = self._feedback_entity_id
        if feedback:
            observed_entities.append(feedback)
        self._unsub = async_track_state_change_event(
            self.hass, observed_entities, self._async_state_changed
        )
        coordinator = self.entry.runtime_data.coordinator
        self._coordinator_unsub = coordinator.async_add_listener(
            self._async_goodwe_updated
        )
        self.entry.async_create_background_task(
            self.hass,
            self.async_evaluate(),
            f"GW EnergyPilot EV load balancing initial evaluation ({self.entry.entry_id})",
        )

    async def async_unload(self) -> None:
        self._cancel_timer()
        self._cancel_feedback_timer()
        if self._unsub:
            self._unsub()
            self._unsub = None
        if self._coordinator_unsub:
            self._coordinator_unsub()
            self._coordinator_unsub = None

    @callback
    def _async_state_changed(self, _event: Event) -> None:
        self._schedule_evaluation("state update")

    @callback
    def _async_goodwe_updated(self) -> None:
        self._schedule_evaluation("GoodWe telemetry update")

    def _schedule_evaluation(self, reason: str) -> None:
        self.entry.async_create_background_task(
            self.hass,
            self.async_evaluate(),
            f"GW EnergyPilot EV load balancing {reason} ({self.entry.entry_id})",
        )

    @property
    def _feedback_entity_id(self) -> str:
        return str(
            self.entry.options.get(CONF_EV_CHARGER_ALLOCATED_CURRENT_ENTITY, "")
        ).strip()

    @staticmethod
    def _state_number(state: Any, *, current: bool = False) -> float | None:
        if state is None or str(state.state).lower() in {"unknown", "unavailable"}:
            return None
        try:
            value = float(state.state)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value):
            return None
        if current:
            unit = state.attributes.get("unit_of_measurement")
            if unit == "mA":
                value /= 1000
            elif unit != "A":
                return None
        return value

    def _goodwe_measured_current(self) -> float | None:
        """Select the applicable current directly from GoodWe telemetry."""
        coordinator = getattr(self.entry.runtime_data, "coordinator", None)
        data = getattr(coordinator, "data", None)
        values = getattr(data, "values", {})
        currents: dict[str, float | None] = {}
        for phase, key in GOODWE_PHASE_CURRENT_KEYS.items():
            try:
                value = float(values.get(key))
            except (AttributeError, TypeError, ValueError):
                value = math.nan
            currents[phase] = value if math.isfinite(value) and value >= 0 else None
        self.phase_currents = currents
        if self.charger_phases == 1:
            return currents[self.charger_phase]
        if any(value is None for value in currents.values()):
            return None
        return max(value for value in currents.values() if value is not None)

    @staticmethod
    def _feedback_matches(value: float | None, target: float) -> bool:
        return value is not None and abs(value - target) <= EV_FEEDBACK_TOLERANCE

    async def async_evaluate(self) -> None:
        async with self._lock:
            charger_id = str(
                self.entry.options.get(CONF_EV_CHARGER_CURRENT_ENTITY, "")
            )
            charger_state = self.hass.states.get(charger_id)
            charger = self._state_number(charger_state, current=True)
            allocated = self._state_number(
                self.hass.states.get(self._feedback_entity_id), current=True
            )
            measured = self._goodwe_measured_current()
            self.measured_current = measured
            self.charger_limit = charger
            self.allocated_current = allocated
            if charger is None:
                self._cancel_timer()
                self._condition = None
                self._publish("unavailable", "A valid charger current value is required")
                return

            if charger > self.configured_maximum + 0.001:
                self._cancel_timer()
                await self._async_set_charger(
                    self.configured_maximum, "clamped_to_configured_maximum"
                )
                return

            if self.pending_target is not None:
                if self._feedback_matches(allocated, self.pending_target):
                    self._cancel_feedback_timer()
                    self.pending_target = None
                    self.last_feedback_status = "applied"
                    self.last_feedback_error = None
                    self._publish("applied")
                else:
                    self._publish(
                        "awaiting_feedback",
                        f"Waiting for allocated current {self.pending_target:g} A",
                    )
                    return

            if measured is None:
                self._cancel_timer()
                self._condition = None
                self._publish(
                    "unavailable",
                    "Required GoodWe meter phase-current telemetry is unavailable",
                )
                return

            delta = measured - self.connection_limit
            if delta > EV_LOAD_BALANCE_HYSTERESIS:
                condition = "overload"
            elif delta < -EV_LOAD_BALANCE_HYSTERESIS and charger < self.configured_maximum:
                condition = "headroom"
            else:
                self._cancel_timer()
                self._condition = None
                self._publish("balanced")
                return

            if condition != self._condition:
                self._cancel_timer()
                self._condition = condition
                minutes = int(
                    self.entry.options.get(
                        CONF_EV_LOAD_BALANCE_WINDOW, DEFAULT_EV_LOAD_BALANCE_WINDOW
                    )
                )
                self._timer_cancel = async_call_later(
                    self.hass, minutes * 60, self._async_window_elapsed
                )
            self._publish(f"waiting_{condition}")

    async def _async_window_elapsed(self, _now: datetime) -> None:
        self._timer_cancel = None
        condition = self._condition
        async with self._lock:
            charger_id = str(
                self.entry.options.get(CONF_EV_CHARGER_CURRENT_ENTITY, "")
            )
            measured = self._goodwe_measured_current()
            charger_state = self.hass.states.get(charger_id)
            charger = self._state_number(charger_state, current=True)
            self.measured_current = measured
            self.charger_limit = charger
            if measured is None or charger is None:
                self._condition = None
                self._publish("unavailable", "Values became unavailable during the wait")
                return
            delta = measured - self.connection_limit
            if condition == "overload" and delta > EV_LOAD_BALANCE_HYSTERESIS:
                target = max(self.configured_minimum, charger - math.ceil(delta))
                if target >= charger:
                    self._condition = None
                    self._publish("minimum_reached")
                    return
                await self._async_set_charger(target, "reduced_after_sustained_overload")
            elif condition == "headroom" and delta < -EV_LOAD_BALANCE_HYSTERESIS:
                target = min(self.configured_maximum, charger + math.floor(-delta))
                if target <= charger:
                    self._condition = None
                    self._publish("balanced")
                    return
                await self._async_set_charger(target, "increased_after_sustained_headroom")
            else:
                self._condition = None
                self._publish("balanced")

    async def _async_set_charger(self, target: float, reason: str) -> None:
        charger_id = str(self.entry.options.get(CONF_EV_CHARGER_CURRENT_ENTITY, ""))
        state = self.hass.states.get(charger_id)
        entity_min = self._attribute_number(state, "min", self.configured_minimum)
        entity_max = self._attribute_number(state, "max", self.configured_maximum)
        step = self._attribute_number(state, "step", 1.0)
        lower = max(self.configured_minimum, entity_min)
        upper = min(self.configured_maximum, entity_max)
        target = min(upper, max(lower, target))
        if step > 0:
            target = lower + round((target - lower) / step) * step
            target = min(upper, max(lower, target))
        try:
            await self.hass.services.async_call(
                "number",
                "set_value",
                {"entity_id": charger_id, "value": target},
                blocking=True,
            )
        except Exception as err:  # Home Assistant service failures are runtime input.
            self._condition = None
            self._publish("write_failed", str(err))
            return
        self.charger_limit = target
        self.last_action = reason
        self._condition = None
        if not self._feedback_entity_id:
            self.last_feedback_status = "not_configured"
            self._publish("command_sent_unverified")
            return
        self.pending_target = target
        self.allocated_current = self._state_number(
            self.hass.states.get(self._feedback_entity_id), current=True
        )
        if self._feedback_matches(self.allocated_current, target):
            self.pending_target = None
            self.last_feedback_status = "applied"
            self.last_feedback_error = None
            self._publish("applied")
            return
        self._cancel_feedback_timer()
        self._feedback_timer_cancel = async_call_later(
            self.hass,
            EV_FEEDBACK_TIMEOUT_SECONDS,
            self._async_feedback_timeout,
        )
        self.last_feedback_status = "awaiting"
        self.last_feedback_error = None
        self._publish(
            "awaiting_feedback",
            f"Waiting for allocated current {target:g} A",
        )

    async def _async_feedback_timeout(self, _now: datetime) -> None:
        self._feedback_timer_cancel = None
        async with self._lock:
            target = self.pending_target
            if target is None:
                return
            self.allocated_current = self._state_number(
                self.hass.states.get(self._feedback_entity_id), current=True
            )
            self.pending_target = None
            if self._feedback_matches(self.allocated_current, target):
                self.last_feedback_status = "applied"
                self.last_feedback_error = None
                self._publish("applied")
                return
            actual = (
                "unavailable"
                if self.allocated_current is None
                else f"{self.allocated_current:g} A"
            )
            error = f"Requested {target:g} A but allocated current is {actual}"
            self.last_feedback_status = "mismatch"
            self.last_feedback_error = error
            self._publish("feedback_mismatch", error)

    @staticmethod
    def _attribute_number(state: Any, key: str, default: float) -> float:
        try:
            value = float(state.attributes.get(key, default))
        except (AttributeError, TypeError, ValueError):
            return float(default)
        return value if math.isfinite(value) else float(default)

    def _cancel_timer(self) -> None:
        if self._timer_cancel:
            self._timer_cancel()
            self._timer_cancel = None

    def _cancel_feedback_timer(self) -> None:
        if self._feedback_timer_cancel:
            self._feedback_timer_cancel()
            self._feedback_timer_cancel = None

    def _publish(self, status: str, error: str | None = None) -> None:
        self.status = status
        self.last_error = error
        async_dispatcher_send(self.hass, self.signal)

    @property
    def diagnostics(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "status": self.status,
            "connection_limit_a": self.connection_limit,
            "connection_phases": grid_connection_phases(self.entry.options),
            "charger_phases": self.charger_phases,
            "charger_phase": self.charger_phase if self.charger_phases == 1 else None,
            "current_source": "goodwe_meter",
            "goodwe_phase_currents_a": dict(self.phase_currents),
            "measured_phase_current_a": self.measured_current,
            "charger_limit_a": self.charger_limit,
            "charger_allocated_current_a": self.allocated_current,
            "charger_feedback_entity_id": self._feedback_entity_id or None,
            "pending_target_a": self.pending_target,
            "last_feedback_status": self.last_feedback_status,
            "last_feedback_error": self.last_feedback_error,
            "configured_minimum_a": self.configured_minimum,
            "configured_maximum_a": self.configured_maximum,
            "last_action": self.last_action,
            "last_error": self.last_error,
            "goodwe_control": False,
        }


def high_current_audit_record(
    *, user_id: str | None, maximum: float, options: Mapping[str, Any]
) -> dict[str, Any]:
    """Build a durable acknowledgement record for a limit above 16 A."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "maximum_a": maximum,
        "charger_entity_id": options.get(CONF_EV_CHARGER_CURRENT_ENTITY),
        "connection_profile": options.get(
            CONF_GRID_CONNECTION_PROFILE, DEFAULT_GRID_CONNECTION_PROFILE
        ),
        "acknowledgement": "charger_current_above_16a",
    }
