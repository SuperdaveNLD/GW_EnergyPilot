"""GW EnergyPilot v0.44 startup optimization resilience."""

from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.core import CoreState
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later

from .orchestrator_v033 import GWEnergyPilotOrchestrator as _BaseOrchestrator

_LOGGER = logging.getLogger(__name__)

STARTUP_OPTIMIZE_INITIAL_DELAY = 60
STARTUP_OPTIMIZE_RETRY_DELAYS = (15, 30, 60)


class GWEnergyPilotOrchestrator(_BaseOrchestrator):
    """Recover the first post-restart plan while dependencies settle."""

    def __init__(self, hass, entry, coordinator) -> None:
        super().__init__(hass, entry, coordinator)
        self._startup_success_baseline: datetime | None = None
        self._startup_retry_index = 0

    async def async_setup(self) -> None:
        """Start orchestration, then schedule a non-blocking recovery attempt."""
        self._startup_retry_index = 0
        await super().async_setup()
        # v0.13 restores last_success inside the inherited setup chain. Capture
        # that value afterwards so restored history is not mistaken for a new
        # optimization completed during this Home Assistant session.
        self._startup_success_baseline = self.last_success
        if self.enabled and self.status == "scheduled":
            self._schedule_startup_attempt(STARTUP_OPTIMIZE_INITIAL_DELAY)

    def _schedule_startup_attempt(self, delay: int) -> None:
        """Schedule one cancellable startup recovery callback."""
        self._unsubs.append(
            async_call_later(
                self.hass,
                delay,
                self._async_initial_optimize,
            )
        )

    def _startup_already_refreshed(self) -> bool:
        """Return whether another optimization already succeeded after setup."""
        return self.last_success != self._startup_success_baseline

    def _schedule_startup_retry(self) -> None:
        """Schedule one bounded follow-up attempt after a startup failure."""
        if self._startup_retry_index >= len(STARTUP_OPTIMIZE_RETRY_DELAYS):
            return
        delay = STARTUP_OPTIMIZE_RETRY_DELAYS[self._startup_retry_index]
        self._startup_retry_index += 1
        self._schedule_startup_attempt(delay)

    async def _async_initial_optimize(self, _now: datetime) -> None:
        """Run one post-restart solve/publish cycle with bounded recovery."""
        if not self.enabled or self._startup_already_refreshed():
            return
        # Do not turn a slow Home Assistant startup into a persisted failed
        # optimization attempt. The bounded retry sequence remains responsible
        # for trying again after Core reaches RUNNING.
        if self.hass.state is not CoreState.running:
            self._schedule_startup_retry()
            return
        try:
            await self.async_optimize(reason="startup")
        except HomeAssistantError as err:
            _LOGGER.warning("Startup EMHASS optimization failed: %s", err)
            self._schedule_startup_retry()
