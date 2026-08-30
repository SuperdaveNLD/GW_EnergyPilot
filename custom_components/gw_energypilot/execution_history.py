"""Bounded plan-to-command execution history for GW EnergyPilot."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import logging
from math import isfinite
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

EXECUTION_HISTORY_STORE_VERSION = 1
EXECUTION_HISTORY_STORE_KEY = f"{DOMAIN}.execution"
EXECUTION_HISTORY_RETENTION_DAYS = 7
EXECUTION_HISTORY_LIMIT = 4096


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _json_value(value: Any) -> Any:
    """Return bounded JSON-compatible evidence without arbitrary objects."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if isfinite(value) else None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return None
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return str(value)


def _sequence_value(value: object) -> int:
    """Return a non-negative persisted sequence without trusting Store data."""
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


class GWEnergyPilotExecutionHistory:
    """Persist a small append-only history of controller execution evidence."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        *,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = Store[dict[str, Any]](
            hass,
            EXECUTION_HISTORY_STORE_VERSION,
            f"{EXECUTION_HISTORY_STORE_KEY}.{entry_id}",
        )
        self._now = now_fn or _utc_now
        self._lock = asyncio.Lock()
        self._loaded = False
        self._sequence = 0
        self._history: list[dict[str, Any]] = []

    def _prune(self, now: datetime) -> None:
        cutoff = now.astimezone(timezone.utc) - timedelta(
            days=EXECUTION_HISTORY_RETENTION_DAYS
        )
        self._history = [
            event
            for event in self._history
            if (occurred := _timestamp(event.get("occurred_at"))) is not None
            and occurred >= cutoff
        ][-EXECUTION_HISTORY_LIMIT:]

    async def _async_ensure_loaded(self) -> None:
        if self._loaded:
            return
        try:
            stored = await self._store.async_load()
        except Exception:  # noqa: BLE001 - optional evidence cannot block setup
            _LOGGER.exception("Unable to restore EnergyPilot execution history")
            stored = None
        raw = stored.get("history", []) if isinstance(stored, Mapping) else []
        if isinstance(raw, list):
            self._history = [
                _json_value(dict(item))
                for item in raw
                if isinstance(item, Mapping)
                and _timestamp(item.get("occurred_at")) is not None
            ]
        self._sequence = max(
            (_sequence_value(item.get("sequence")) for item in self._history),
            default=0,
        )
        self._prune(self._now())
        self._loaded = True

    async def async_restore(self) -> None:
        """Restore and sanitize history without contacting any external source."""
        async with self._lock:
            await self._async_ensure_loaded()

    async def async_append(self, record: Mapping[str, Any]) -> dict[str, Any] | None:
        """Append one event; persistence failure must never break EMS control."""
        occurred = _timestamp(record.get("occurred_at")) or self._now()
        if occurred.tzinfo is None:
            raise ValueError("Execution-history timestamp must include a timezone")
        async with self._lock:
            await self._async_ensure_loaded()
            self._sequence += 1
            event = _json_value(dict(record))
            event["occurred_at"] = occurred.astimezone(timezone.utc).isoformat()
            event["sequence"] = self._sequence
            event["event_id"] = f"{event['occurred_at']}:{self._sequence}"
            self._history.append(event)
            self._prune(self._now())
            try:
                await self._store.async_save(
                    {
                        "retention_days": EXECUTION_HISTORY_RETENTION_DAYS,
                        "history": deepcopy(self._history),
                    }
                )
            except Exception:  # noqa: BLE001 - evidence must not own control
                _LOGGER.exception("Unable to persist EnergyPilot execution history")
            return deepcopy(event)

    async def async_history(
        self,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Return oldest-first events inside an optional UTC interval."""
        async with self._lock:
            await self._async_ensure_loaded()
            self._prune(self._now())
            start_utc = start.astimezone(timezone.utc) if start else None
            end_utc = end.astimezone(timezone.utc) if end else None
            result = []
            for event in self._history:
                occurred = _timestamp(event.get("occurred_at"))
                if occurred is None:
                    continue
                if start_utc is not None and occurred < start_utc:
                    continue
                if end_utc is not None and occurred >= end_utc:
                    continue
                result.append(deepcopy(event))
            return sorted(
                result,
                key=lambda event: (
                    _timestamp(event.get("occurred_at")),
                    _sequence_value(event.get("sequence")),
                ),
            )
