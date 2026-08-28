"""GW EnergyPilot startup optimization resilience."""

from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later

from .orchestrator_v033 import GWEnergyPilotOrchestrator as _BaseOrchestrator

_LOGGER = logging.getLogger(__name__)

STARTUP_OPTIMIZE_RETRY_DELAYS = (15, 30, 60)


class GWEnergyPilotOrchestrator(_BaseOrchestrator):
    """Retry the post-restart optimization while startup dependencies settle."""

    def __init__(self, hass, entry, coordinator) -> None:
        super().__init__(hass, entry, coordinator)
        self._startup_success_baseline: datetime | None = None
        self._startup_retry_index = 0

    async def async_setup(self) -> None:
        """Capture restored runtime state after the inherited scheduler setup."""
        self._startup_retry_index = 0
        await super().async_setup()
        self._startup_success_baseline = self.last_success

    def _startup_already_refreshed(self) -> bool:
        """Return whether another optimization already succeeded after setup."""
        return self.last_success != self._startup_success_baseline

    def _schedule_startup_retry(self) -> None:
        """Schedule one bounded follow-up attempt after a startup failure."""
        if self._startup_retry_index >= len(STARTUP_OPTIMIZE_RETRY_DELAYS):
            return
        delay = STARTUP_OPTIMIZE_RETRY_DELAYS[self._startup_retry_index]
        self._startup_retry_index += 1
        self._unsubs.append(
            async_call_later(
                self.hass,
                delay,
                self._async_initial_optimize,
            )
        )

    async def _async_initial_optimize(self, _now: datetime) -> None:
        """Run one startup solve/publish cycle and retry transient failures."""
        if not self.enabled or self._startup_already_refreshed():
            return
        try:
            await self.async_optimize(reason="startup")
        except HomeAssistantError as err:
            _LOGGER.warning("Startup EMHASS optimization failed: %s", err)
            self._schedule_startup_retry()
