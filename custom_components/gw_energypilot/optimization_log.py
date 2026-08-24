"""Persistent optimization history for GW EnergyPilot."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

OPTIMIZATION_LOG_VERSION = 1
OPTIMIZATION_LOG_KEY = f"{DOMAIN}.optimization_log"
OPTIMIZATION_LOG_LIMIT = 50


class GWEnergyPilotOptimizationLog:
    """Keep a bounded per-entry history of EnergyPilot optimization attempts."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store = Store[dict[str, Any]](
            hass,
            OPTIMIZATION_LOG_VERSION,
            f"{OPTIMIZATION_LOG_KEY}.{entry_id}",
        )
        self._lock = asyncio.Lock()
        self._loaded = False
        self._history: list[dict[str, Any]] = []

    async def _async_ensure_loaded(self) -> None:
        """Load and sanitize stored history once."""
        if self._loaded:
            return

        stored = await self._store.async_load()
        raw_history = stored.get("history", []) if isinstance(stored, dict) else []
        if isinstance(raw_history, list):
            self._history = [
                dict(item) for item in raw_history if isinstance(item, Mapping)
            ][-OPTIMIZATION_LOG_LIMIT:]
        else:
            self._history = []
        self._loaded = True

    async def async_append(self, record: Mapping[str, Any]) -> None:
        """Append one optimization attempt and keep only the newest records."""
        async with self._lock:
            await self._async_ensure_loaded()
            self._history.append(dict(record))
            self._history = self._history[-OPTIMIZATION_LOG_LIMIT:]
            await self._store.async_save({"history": list(self._history)})

    async def async_history(self) -> list[dict[str, Any]]:
        """Return a copy of the stored optimization history, oldest first."""
        async with self._lock:
            await self._async_ensure_loaded()
            return [dict(item) for item in self._history]
