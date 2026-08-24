"""Persistent energy accounting for GW EnergyPilot."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import logging
import math
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .accounting_model import GridAccountingState, roll_to_day
from .accounting_power import integrate_signed_power
from .const import DOMAIN
from .coordinator import GWEnergyPilotCoordinator

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 2
SAVE_DELAY_SECONDS = 30
GRID_POWER_KEY = "meter_total_power_fast"
IMPORT_DAILY_KEY = "grid_energy_imported_today"
EXPORT_DAILY_KEY = "grid_energy_exported_today"
MAX_SAMPLE_GAP_SECONDS = 120


def _finite_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


class GWEnergyPilotAccounting:
    """Own persistent EnergyPilot grid accounting from live PCC power."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        coordinator: GWEnergyPilotCoordinator,
    ) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.coordinator = coordinator
        self.state = GridAccountingState()
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.accounting.{entry_id}",
            atomic_writes=True,
        )
        self._listeners: set[Callable[[], None]] = set()
        self._coordinator_unsub: CALLBACK_TYPE | None = None
        self._save_handle = None
        self._previous_power_w: float | None = None
        self._previous_sample_at: datetime | None = None

    async def async_prepare(self) -> None:
        """Restore persisted accounting before sensor entities are created."""
        stored = await self._store.async_load()
        self.state = GridAccountingState.from_dict(stored)
        if roll_to_day(self.state, dt_util.now().date()):
            await self._store.async_save(self.state.as_dict())

    async def async_start(self) -> None:
        """Start consuming live signed GoodWe grid-power updates."""
        if self._coordinator_unsub is not None:
            return
        self._coordinator_unsub = self.coordinator.async_add_listener(
            self._handle_coordinator_update
        )
        if self.coordinator.data is not None:
            self._handle_coordinator_update()

    async def async_bootstrap_if_needed(self) -> None:
        """Retained as a compatibility no-op for the v0.23 setup call path."""
        return

    async def async_unload(self) -> None:
        """Persist and stop accounting."""
        if self._coordinator_unsub is not None:
            self._coordinator_unsub()
            self._coordinator_unsub = None
        if self._save_handle is not None:
            self._save_handle.cancel()
            self._save_handle = None
        await self._store.async_save(self.state.as_dict())
        self._listeners.clear()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        """Register an accounting-state listener."""
        self._listeners.add(listener)

        @callback
        def remove_listener() -> None:
            self._listeners.discard(listener)

        return remove_listener

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data is None:
            return

        power_w = _finite_number(self.coordinator.data.values.get(GRID_POWER_KEY))
        if power_w is None:
            self._previous_power_w = None
            self._previous_sample_at = None
            return

        now = dt_util.now()
        day_changed = roll_to_day(self.state, now.date())
        changed = day_changed

        if self._previous_power_w is not None and self._previous_sample_at is not None:
            elapsed = (now - self._previous_sample_at).total_seconds()
            same_day = self._previous_sample_at.date() == now.date()
            if 0 < elapsed <= MAX_SAMPLE_GAP_SECONDS and same_day:
                import_kwh, export_kwh = integrate_signed_power(
                    self._previous_power_w,
                    power_w,
                    elapsed,
                )
                if import_kwh > 0:
                    self.state.today_import_kwh = round(
                        self.state.today_import_kwh + import_kwh,
                        6,
                    )
                    changed = True
                if export_kwh > 0:
                    self.state.today_export_kwh = round(
                        self.state.today_export_kwh + export_kwh,
                        6,
                    )
                    changed = True
            elif elapsed > MAX_SAMPLE_GAP_SECONDS:
                _LOGGER.debug(
                    "Skipping EnergyPilot grid accounting across %.1fs telemetry gap",
                    elapsed,
                )

        self._previous_power_w = power_w
        self._previous_sample_at = now

        if not changed:
            return
        self._schedule_save()
        self._notify_listeners()

    @callback
    def _schedule_save(self) -> None:
        if self._save_handle is not None:
            return
        self._save_handle = self.hass.loop.call_later(
            SAVE_DELAY_SECONDS,
            self._start_scheduled_save,
        )

    @callback
    def _start_scheduled_save(self) -> None:
        self._save_handle = None
        self.hass.async_create_task(
            self._async_save(),
            f"GW EnergyPilot accounting save ({self.entry_id})",
        )

    async def _async_save(self) -> None:
        await self._store.async_save(self.state.as_dict())

    @callback
    def _notify_listeners(self) -> None:
        for listener in tuple(self._listeners):
            listener()
