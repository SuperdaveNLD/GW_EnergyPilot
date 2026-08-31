"""Event-driven optimization triggers for GW EnergyPilot."""

from __future__ import annotations

from collections.abc import Callable
import logging

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later, async_track_state_change_event

from .const import (
    CONF_ENABLE_EMHASS_ORCHESTRATOR,
    CONF_ENABLE_EV_COORDINATION,
)

_LOGGER = logging.getLogger(__name__)

EV_STOP_OPTIMIZATION_RETRY_DELAYS = (5, 15, 30, 60)


def async_setup_event_triggers(hass: HomeAssistant, entry) -> list[Callable[[], None]]:
    """Set up event-driven optimizations for one config entry."""
    unsubs: list[Callable[[], None]] = []

    if not entry.options.get(CONF_ENABLE_EMHASS_ORCHESTRATOR, False):
        return unsubs
    if not entry.options.get(CONF_ENABLE_EV_COORDINATION, False):
        return unsubs

    controller = entry.runtime_data.controller
    entity_ids = controller.ev_source_ids
    if not entity_ids:
        return unsubs

    state = {
        "was_active": controller.ev_is_active(),
        "retry_index": 0,
        "retry_cancel": None,
    }

    def _cancel_retry(*, reset: bool) -> None:
        cancel = state["retry_cancel"]
        if callable(cancel):
            cancel()
        state["retry_cancel"] = None
        if reset:
            state["retry_index"] = 0

    @callback
    def _schedule_retry() -> None:
        if controller.ev_is_active():
            _cancel_retry(reset=True)
            return
        index = int(state["retry_index"])
        if index >= len(EV_STOP_OPTIMIZATION_RETRY_DELAYS):
            return
        delay = EV_STOP_OPTIMIZATION_RETRY_DELAYS[index]
        state["retry_index"] = index + 1
        state["retry_cancel"] = async_call_later(
            hass,
            delay,
            _async_retry_after_ev_stop,
        )

    async def _async_run_after_ev_stop() -> None:
        try:
            await entry.runtime_data.orchestrator.async_optimize(
                reason="ev_charging_stopped"
            )
        except HomeAssistantError as err:
            _LOGGER.warning("EV-stop EMHASS optimization failed: %s", err)
            _schedule_retry()
        except Exception:  # noqa: BLE001 - background recovery must not stall
            _LOGGER.exception("Unexpected EV-stop EMHASS optimization failure")
            _schedule_retry()
        else:
            _cancel_retry(reset=True)

    async def _async_retry_after_ev_stop(_now) -> None:
        state["retry_cancel"] = None
        if controller.ev_is_active():
            state["retry_index"] = 0
            return
        hass.async_create_task(
            _async_run_after_ev_stop(),
            "gw-energypilot-ev-stop-optimize-retry",
        )

    @callback
    def _async_ev_source_changed(_event: Event) -> None:
        active = controller.ev_is_active()
        was_active = bool(state["was_active"])
        state["was_active"] = active

        if active:
            _cancel_retry(reset=True)
            return

        if was_active and not active:
            _cancel_retry(reset=True)
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
    unsubs.append(lambda: _cancel_retry(reset=True))
    return unsubs
