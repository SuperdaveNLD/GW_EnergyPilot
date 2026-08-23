"""Event-driven optimization triggers for GW EnergyPilot."""

from __future__ import annotations

from collections.abc import Callable
import logging

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_ENABLE_EMHASS_ORCHESTRATOR,
    CONF_ENABLE_EV_COORDINATION,
    CONF_EV_MODE_ENTITY,
    CONF_EV_POWER_ENTITY,
)

_LOGGER = logging.getLogger(__name__)


def async_setup_event_triggers(hass: HomeAssistant, entry) -> list[Callable[[], None]]:
    """Set up event-driven optimizations for one config entry."""
    unsubs: list[Callable[[], None]] = []

    if not entry.options.get(CONF_ENABLE_EMHASS_ORCHESTRATOR, False):
        return unsubs
    if not entry.options.get(CONF_ENABLE_EV_COORDINATION, False):
        return unsubs

    entity_ids = {
        entry.options.get(CONF_EV_MODE_ENTITY),
        entry.options.get(CONF_EV_POWER_ENTITY),
    }
    entity_ids.discard(None)
    entity_ids.discard("")
    if not entity_ids:
        return unsubs

    controller = entry.runtime_data.controller
    state = {"was_active": controller.ev_is_active()}

    async def _async_run_after_ev_stop() -> None:
        try:
            await entry.runtime_data.orchestrator.async_optimize(
                reason="ev_charging_stopped"
            )
        except HomeAssistantError as err:
            _LOGGER.warning("EV-stop EMHASS optimization failed: %s", err)

    @callback
    def _async_ev_source_changed(_event: Event) -> None:
        active = controller.ev_is_active()
        was_active = bool(state["was_active"])
        state["was_active"] = active

        if was_active and not active:
            hass.async_create_task(
                _async_run_after_ev_stop(),
                "gw-energypilot-ev-stop-optimize",
            )

    unsubs.append(
        async_track_state_change_event(
            hass,
            list(entity_ids),
            _async_ev_source_changed,
        )
    )
    return unsubs
