"""Persistent runtime state for GW EnergyPilot."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

RUNTIME_STORE_VERSION = 1
RUNTIME_STORE_KEY = f"{DOMAIN}.runtime"


class GWEnergyPilotRuntimeStore:
    """Persist small runtime status values per EnergyPilot config entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store[dict[str, Any]](
            hass,
            RUNTIME_STORE_VERSION,
            f"{RUNTIME_STORE_KEY}.{entry_id}",
        )
        self._data: dict[str, Any] = {}

    async def async_load_last_success(self) -> datetime | None:
        """Load the last successful EnergyPilot optimization timestamp."""
        stored = await self._store.async_load()
        self._data = dict(stored) if isinstance(stored, dict) else {}

        raw = self._data.get("last_success")
        if not isinstance(raw, str) or not raw:
            return None

        try:
            timestamp = datetime.fromisoformat(raw)
        except ValueError:
            _LOGGER.warning(
                "Ignoring invalid persisted EnergyPilot last_success value: %s",
                raw,
            )
            return None

        if timestamp.tzinfo is None:
            _LOGGER.warning(
                "Ignoring persisted EnergyPilot last_success without timezone: %s",
                raw,
            )
            return None
        return timestamp

    async def async_save_last_success(self, timestamp: datetime) -> None:
        """Persist a successful EnergyPilot optimization timestamp."""
        if timestamp.tzinfo is None:
            raise ValueError("EnergyPilot last_success timestamp must include a timezone")

        self._data["last_success"] = timestamp.isoformat()
        await self._store.async_save(dict(self._data))
