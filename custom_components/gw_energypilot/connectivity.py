"""Canonical runtime connectivity status for GW EnergyPilot."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_state_change_event

from .connectivity_model import (
    ConnectivityEvent,
    EVConnectivityGuard,
    ev_source_online,
)
from .const import (
    CONF_ENABLE_EV_COORDINATION,
    CONF_EV_ONLINE_ENTITY,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class GWEnergyPilotConnectivity:
    """Observe existing signals without adding a second polling/control loop."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry,
        coordinator,
        debug_log,
        *,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self.debug_log = debug_log
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self._guard = EVConnectivityGuard()
        self._unsubs: list[Callable[[], None]] = []
        self._timer_cancel: Callable[[], None] | None = None
        self.last_modbus_success: datetime | None = None
        self.last_modbus_failure: datetime | None = None

    @property
    def signal(self) -> str:
        return f"{DOMAIN}_{self.entry.entry_id}_connectivity_update"

    @property
    def ev_online_entity(self) -> str | None:
        raw = self.entry.options.get(CONF_EV_ONLINE_ENTITY)
        value = str(raw).strip() if raw else ""
        return value or None

    @property
    def ev_coordination_requested(self) -> bool:
        return bool(self.entry.options.get(CONF_ENABLE_EV_COORDINATION, False))

    @property
    def ev_coordination_effective(self) -> bool:
        return self._guard.effective(self.ev_coordination_requested)

    def _modbus_status(self) -> str:
        if not self.coordinator.last_update_success:
            return "unreachable"
        return "online" if self.coordinator.data is not None else "checking"

    def _ev_online(self) -> bool | None:
        entity_id = self.ev_online_entity
        if entity_id is None:
            return None
        return ev_source_online(self.hass.states.get(entity_id))

    @property
    def state(self) -> str:
        modbus = self._modbus_status()
        ev_online = self._ev_online()
        if modbus == "unreachable" or ev_online is False or self._guard.suspended:
            return "issue"
        if modbus == "checking":
            return "checking"
        return "all_ok"

    @staticmethod
    def _iso(timestamp: datetime | None) -> str | None:
        return timestamp.isoformat() if timestamp is not None else None

    @property
    def attributes(self) -> dict[str, Any]:
        now = self._now_fn()
        ev_online = self._ev_online()
        last_exception = getattr(self.coordinator, "last_exception", None)
        return {
            "modbus_status": self._modbus_status(),
            "modbus_last_success": self._iso(self.last_modbus_success),
            "modbus_last_failure": self._iso(self.last_modbus_failure),
            "modbus_last_error": str(last_exception) if last_exception else None,
            "refresh_seconds": int(
                self.entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
            "ev_online_entity": self.ev_online_entity,
            "ev_status": (
                "not_configured"
                if ev_online is None
                else "online" if ev_online else "unreachable"
            ),
            "ev_coordination_requested": self.ev_coordination_requested,
            "ev_coordination_effective": self.ev_coordination_effective,
            "ev_coordination_suspended": self._guard.suspended,
            "ev_transition": self._guard.transition,
            "ev_transition_remaining_seconds": self._guard.remaining_seconds(now),
            "ev_offline_since": self._iso(self._guard.offline_since),
            "ev_online_since": self._iso(self._guard.online_since),
            "ev_grace_seconds": self._guard.grace_seconds,
        }

    async def async_start(self) -> None:
        """Subscribe to the coordinator and configured charger source."""
        self._unsubs.append(
            self.coordinator.async_add_listener(self._async_coordinator_updated)
        )
        if self.ev_online_entity is not None:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass,
                    [self.ev_online_entity],
                    self._async_ev_source_changed,
                )
            )
        now = self._now_fn()
        if self.coordinator.last_update_success and self.coordinator.data is not None:
            self.last_modbus_success = now
        elif not self.coordinator.last_update_success:
            self.last_modbus_failure = now
        self._evaluate()

    async def async_unload(self) -> None:
        """Remove listeners and the current stable-window timer."""
        if self._timer_cancel is not None:
            self._timer_cancel()
            self._timer_cancel = None
        while self._unsubs:
            self._unsubs.pop()()

    def _record_event(self, transition: ConnectivityEvent) -> None:
        data = {
            "entity_id": self.ev_online_entity,
            "occurred_at": transition.occurred_at.isoformat(),
            "ev_status": self.attributes["ev_status"],
            "ev_grace_seconds": self._guard.grace_seconds,
            "ev_coordination_requested": self.ev_coordination_requested,
            "ev_coordination_effective": self.ev_coordination_effective,
        }
        self.debug_log.log.record("connectivity", transition.event, data)
        message = {
            "ev_connectivity_lost": "EV charger connectivity lost",
            "ev_connectivity_restored": "EV charger connectivity restored",
            "ev_coordination_suspended": (
                "EV coordination suspended after the charger remained "
                f"unreachable for {self._guard.grace_seconds} seconds"
            ),
            "ev_coordination_resumed": (
                "EV coordination resumed after the charger remained online "
                f"for {self._guard.grace_seconds} seconds"
            ),
            "ev_resume_cancelled_by_user": (
                "Automatic EV coordination resume cancelled because the user "
                "setting is off"
            ),
        }.get(transition.event, transition.event)
        if transition.event in {
            "ev_connectivity_lost",
            "ev_coordination_suspended",
        }:
            _LOGGER.warning(
                "GW EnergyPilot %s: %s (%s)",
                self.entry.entry_id,
                message,
                self.ev_online_entity,
            )
        else:
            _LOGGER.info(
                "GW EnergyPilot %s: %s (%s)",
                self.entry.entry_id,
                message,
                self.ev_online_entity,
            )

    def _schedule_transition(self, now: datetime) -> None:
        if self._timer_cancel is not None:
            self._timer_cancel()
            self._timer_cancel = None
        remaining = self._guard.remaining_seconds(now)
        if remaining is None:
            return
        self._timer_cancel = async_call_later(
            self.hass,
            max(1, remaining),
            self._async_transition_deadline,
        )

    def _evaluate(self) -> None:
        now = self._now_fn()
        entity_id = self.ev_online_entity
        online = self._ev_online()
        transitions = self._guard.update(
            now=now,
            user_enabled=self.ev_coordination_requested,
            source_configured=entity_id is not None,
            online=bool(online),
        )
        for transition in transitions:
            self._record_event(transition)
        self._schedule_transition(now)
        async_dispatcher_send(self.hass, self.signal)

    @callback
    def _async_coordinator_updated(self) -> None:
        now = self._now_fn()
        if self.coordinator.last_update_success and self.coordinator.data is not None:
            self.last_modbus_success = now
        else:
            self.last_modbus_failure = now
        self._evaluate()

    @callback
    def _async_ev_source_changed(self, _event: Event) -> None:
        self._evaluate()

    async def _async_transition_deadline(self, _now: datetime) -> None:
        self._timer_cancel = None
        self._evaluate()
