"""Persistent energy accounting for GW EnergyPilot."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import logging
import math
from typing import Any

from homeassistant.components.recorder import get_instance, history
from homeassistant.const import Platform
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .accounting_model import (
    LEGACY_EXPORT_KEY,
    LEGACY_IMPORT_KEY,
    SOURCE_EXTENDED,
    GridAccountingState,
    apply_meter_totals,
    roll_to_day,
    seed_daily_totals,
    select_meter_totals,
)
from .const import DOMAIN
from .coordinator import GWEnergyPilotCoordinator

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
SAVE_DELAY_SECONDS = 30
IMPORT_TOTAL_KEY = LEGACY_IMPORT_KEY
EXPORT_TOTAL_KEY = LEGACY_EXPORT_KEY
IMPORT_DAILY_KEY = "grid_energy_imported_today"
EXPORT_DAILY_KEY = "grid_energy_exported_today"


def _safe_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _history_boundary_value(
    hass: HomeAssistant,
    entity_id: str,
    boundary: datetime,
) -> float | None:
    """Return the cumulative state at a local-day boundary from Recorder."""
    rows = history.get_significant_states(
        hass,
        boundary,
        boundary + timedelta(seconds=1),
        [entity_id],
        None,
        True,
        False,
        False,
        True,
        False,
    ).get(entity_id, [])

    for row in rows:
        raw = getattr(row, "state", None)
        if raw is None and isinstance(row, dict):
            raw = row.get("state", row.get("s"))
        value = _safe_number(raw)
        if value is not None:
            return value
    return None


class GWEnergyPilotAccounting:
    """Own EnergyPilot accounting derived from GoodWe lifetime counters."""

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

    async def async_prepare(self) -> None:
        """Restore persisted accounting before sensor entities are created."""
        stored = await self._store.async_load()
        self.state = GridAccountingState.from_dict(stored)
        if roll_to_day(self.state, dt_util.now().date()):
            await self._store.async_save(self.state.as_dict())

    async def async_start(self) -> None:
        """Start consuming GoodWe lifetime-counter updates."""
        if self._coordinator_unsub is not None:
            return
        self._coordinator_unsub = self.coordinator.async_add_listener(
            self._handle_coordinator_update
        )
        if self.coordinator.data is not None:
            self._handle_coordinator_update()

    async def async_bootstrap_if_needed(self) -> None:
        """Seed first-release daily totals from existing Recorder boundaries."""
        if self.state.bootstrap_complete:
            return
        if self.coordinator.data is None:
            return

        values = self.coordinator.data.values
        selected = select_meter_totals(values, self.state.source_pair)
        if selected is None:
            return
        source_pair, current_import, current_export = selected

        # Extended 64-bit totals were not separate Recorder-facing entities.
        # Their first selected live sample is therefore the safe baseline.
        if source_pair == SOURCE_EXTENDED:
            self.state.bootstrap_complete = True
            await self._store.async_save(self.state.as_dict())
            self._notify_listeners()
            return

        if "recorder" not in self.hass.config.components:
            return

        registry = er.async_get(self.hass)
        import_entity_id = registry.async_get_entity_id(
            Platform.SENSOR,
            DOMAIN,
            f"{self.entry_id}_{IMPORT_TOTAL_KEY}",
        )
        export_entity_id = registry.async_get_entity_id(
            Platform.SENSOR,
            DOMAIN,
            f"{self.entry_id}_{EXPORT_TOTAL_KEY}",
        )
        if import_entity_id is None or export_entity_id is None:
            return

        now_local = dt_util.now()
        today_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start_local = today_start_local - timedelta(days=1)
        today_start = dt_util.as_utc(today_start_local)
        yesterday_start = dt_util.as_utc(yesterday_start_local)

        recorder = get_instance(self.hass)
        try:
            yesterday_import_start = await recorder.async_add_executor_job(
                _history_boundary_value,
                self.hass,
                import_entity_id,
                yesterday_start,
            )
            today_import_start = await recorder.async_add_executor_job(
                _history_boundary_value,
                self.hass,
                import_entity_id,
                today_start,
            )
            yesterday_export_start = await recorder.async_add_executor_job(
                _history_boundary_value,
                self.hass,
                export_entity_id,
                yesterday_start,
            )
            today_export_start = await recorder.async_add_executor_job(
                _history_boundary_value,
                self.hass,
                export_entity_id,
                today_start,
            )
        except Exception as err:  # Recorder bootstrap is optional, never fatal.
            _LOGGER.debug("Unable to bootstrap EnergyPilot accounting: %s", err)
            return

        today_import = (
            current_import - today_import_start
            if today_import_start is not None and current_import >= today_import_start
            else None
        )
        today_export = (
            current_export - today_export_start
            if today_export_start is not None and current_export >= today_export_start
            else None
        )
        yesterday_import = (
            today_import_start - yesterday_import_start
            if yesterday_import_start is not None
            and today_import_start is not None
            and today_import_start >= yesterday_import_start
            else None
        )
        yesterday_export = (
            today_export_start - yesterday_export_start
            if yesterday_export_start is not None
            and today_export_start is not None
            and today_export_start >= yesterday_export_start
            else None
        )

        if not seed_daily_totals(
            self.state,
            now_local.date(),
            today_import_kwh=today_import,
            today_export_kwh=today_export,
            yesterday_import_kwh=yesterday_import,
            yesterday_export_kwh=yesterday_export,
        ):
            return

        self.state.last_import_total_kwh = current_import
        self.state.last_export_total_kwh = current_export
        await self._store.async_save(self.state.as_dict())
        self._notify_listeners()

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
        selected = select_meter_totals(
            self.coordinator.data.values,
            self.state.source_pair,
        )
        if selected is None:
            return

        source_pair, import_total, export_total = selected
        before = self.state.as_dict()
        apply_meter_totals(
            self.state,
            dt_util.now().date(),
            import_total_kwh=import_total,
            export_total_kwh=export_total,
            source_pair=source_pair,
        )
        if self.state.as_dict() == before:
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
