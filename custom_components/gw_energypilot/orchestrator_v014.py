"""GW EnergyPilot v0.25 startup recovery refinements."""

from __future__ import annotations

import math

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, Event, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later

from .const import CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY
from .orchestrator_v013 import GWEnergyPilotOrchestrator as _V013Orchestrator

STARTUP_RECOVERY_DELAY_SECONDS = 10
STARTUP_RECOVERY_RETRY_SECONDS = 20
STARTUP_RECOVERY_ATTEMPTS = 3


class GWEnergyPilotOrchestrator(_V013Orchestrator):
    """Recover a missing EMHASS plan once Home Assistant has fully started."""

    async def async_setup(self) -> None:
        """Start normal orchestration and arm one post-start recovery path."""
        await super().async_setup()
        if not self.enabled:
            return

        if self.hass.state is CoreState.running:
            self._schedule_startup_recovery(STARTUP_RECOVERY_DELAY_SECONDS, 1)
            return

        self._unsubs.append(
            self.hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED,
                self._async_home_assistant_started,
            )
        )

    @callback
    def _async_home_assistant_started(self, _event: Event) -> None:
        """Run recovery only after Home Assistant reaches RUNNING."""
        self._schedule_startup_recovery(STARTUP_RECOVERY_DELAY_SECONDS, 1)

    def _schedule_startup_recovery(self, delay: int, attempt: int) -> None:
        """Schedule one bounded recovery attempt without blocking startup."""
        self._unsubs.append(
            async_call_later(
                self.hass,
                delay,
                lambda _now: self.hass.async_create_task(
                    self._async_startup_recovery(attempt),
                    f"gw-energypilot-startup-recovery-{attempt}",
                ),
            )
        )

    def _has_valid_p_batt_plan(self) -> bool:
        """Return whether the configured P_batt output is finite and ready."""
        entity_id = str(
            self.entry.options.get(CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY)
            or DEFAULT_P_BATT_ENTITY
        )
        state = self.hass.states.get(entity_id)
        if state is None or state.state in {"unknown", "unavailable", "none", ""}:
            return False
        try:
            value = float(state.state)
        except (TypeError, ValueError):
            return False
        return math.isfinite(value) and self._optimization_ready()

    async def _async_startup_recovery(self, attempt: int) -> None:
        """Create one fresh plan when startup finished without a valid output."""
        if self.hass.state is not CoreState.running or self._has_valid_p_batt_plan():
            return

        if self.coordinator.data is None or not self.coordinator.last_update_success:
            if attempt < STARTUP_RECOVERY_ATTEMPTS:
                self._schedule_startup_recovery(
                    STARTUP_RECOVERY_RETRY_SECONDS,
                    attempt + 1,
                )
            return

        if self._lock.locked():
            if attempt < STARTUP_RECOVERY_ATTEMPTS:
                self._schedule_startup_recovery(
                    STARTUP_RECOVERY_RETRY_SECONDS,
                    attempt + 1,
                )
            return

        try:
            await self.async_optimize(reason="startup_recovery")
        except HomeAssistantError:
            if attempt < STARTUP_RECOVERY_ATTEMPTS:
                self._schedule_startup_recovery(
                    STARTUP_RECOVERY_RETRY_SECONDS,
                    attempt + 1,
                )

    @callback
    def _async_tomorrow_price_changed(self, event: Event) -> None:
        """Ignore restored price availability while Home Assistant is starting."""
        if self.hass.state is not CoreState.running:
            return
        super()._async_tomorrow_price_changed(event)
