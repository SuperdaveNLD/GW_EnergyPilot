"""Persistent EMS command evidence for GW EnergyPilot."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CONTROL_HISTORY_STORE_VERSION = 1
CONTROL_HISTORY_STORE_KEY = f"{DOMAIN}.control"


class GWEnergyPilotControlHistory:
    """Persist the latest successfully completed EMS setpoint write."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store[dict[str, Any]](
            hass,
            CONTROL_HISTORY_STORE_VERSION,
            f"{CONTROL_HISTORY_STORE_KEY}.{entry_id}",
        )
        self.last_ems_setpoint_updated_at: datetime | None = None
        self.last_ems_setpoint: int | None = None
        self.last_ems_mode: int | None = None
        self.last_command: str | None = None

    @staticmethod
    def _timestamp(value: object) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            timestamp = datetime.fromisoformat(value)
        except ValueError:
            return None
        return timestamp if timestamp.tzinfo is not None else None

    async def async_restore(self) -> None:
        """Restore the latest successful setpoint-write evidence."""
        stored = await self._store.async_load()
        data = dict(stored) if isinstance(stored, dict) else {}
        timestamp = self._timestamp(data.get("last_ems_setpoint_updated_at"))
        if timestamp is None:
            return

        try:
            setpoint = int(data["last_ems_setpoint"])
            mode = int(data["last_ems_mode"])
        except (KeyError, TypeError, ValueError):
            _LOGGER.warning("Ignoring incomplete persisted EMS setpoint history")
            return
        if not 0 <= setpoint <= 15000 or not 1 <= mode <= 12:
            _LOGGER.warning("Ignoring invalid persisted EMS setpoint history")
            return

        command = data.get("last_command")
        self.last_ems_setpoint_updated_at = timestamp
        self.last_ems_setpoint = setpoint
        self.last_ems_mode = mode
        self.last_command = str(command) if command else None

    def record(
        self,
        timestamp: datetime,
        *,
        setpoint: int,
        mode: int,
        command: str,
    ) -> None:
        """Update in-memory evidence after one complete EMS write succeeds."""
        if timestamp.tzinfo is None:
            raise ValueError("EMS setpoint update timestamp must include a timezone")
        self.last_ems_setpoint_updated_at = timestamp
        self.last_ems_setpoint = int(setpoint)
        self.last_ems_mode = int(mode)
        self.last_command = str(command)

    async def async_save(self) -> None:
        """Persist current evidence without affecting EMS control on failure."""
        timestamp = self.last_ems_setpoint_updated_at
        if timestamp is None:
            return
        data = {
            "last_ems_setpoint_updated_at": timestamp.isoformat(),
            "last_ems_setpoint": self.last_ems_setpoint,
            "last_ems_mode": self.last_ems_mode,
            "last_command": self.last_command,
        }
        try:
            await self._store.async_save(data)
        except Exception:  # noqa: BLE001 - history must never break EMS control
            _LOGGER.exception("Unable to persist EMS setpoint update history")
