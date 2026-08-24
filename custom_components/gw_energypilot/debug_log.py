"""Bounded in-memory debug sessions for GW EnergyPilot."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

DEBUG_LOG_LIMIT = 1200
DEBUG_LOG_SCHEMA_VERSION = 1


def _utcnow_iso() -> str:
    """Return a stable UTC timestamp for support records."""
    return datetime.now(timezone.utc).isoformat()


class GWEnergyPilotDebugLog:
    """Keep one opt-in, bounded, non-persistent diagnostic session.

    Debug capture is deliberately disabled by default. Stopping a session keeps
    its events available for copy/export until the user clears the buffer or the
    integration is unloaded/restarted.
    """

    def __init__(self, limit: int = DEBUG_LOG_LIMIT) -> None:
        self.limit = max(10, int(limit))
        self.enabled = False
        self.started_at: str | None = None
        self.stopped_at: str | None = None
        self.dropped_events = 0
        self._events: deque[dict[str, Any]] = deque(maxlen=self.limit)

    def clear(self) -> None:
        """Clear captured events without changing the enabled state."""
        self._events.clear()
        self.dropped_events = 0
        if not self.enabled:
            self.started_at = None
            self.stopped_at = None

    def enable(self, baseline: Mapping[str, Any] | None = None) -> None:
        """Start a fresh debug session and optionally record its baseline."""
        self._events.clear()
        self.dropped_events = 0
        self.enabled = True
        self.started_at = _utcnow_iso()
        self.stopped_at = None
        self.record(
            "session",
            "started",
            {
                "schema_version": DEBUG_LOG_SCHEMA_VERSION,
                "baseline": dict(baseline or {}),
            },
        )

    def disable(self, final_snapshot: Mapping[str, Any] | None = None) -> None:
        """Stop capture while retaining the completed session in memory."""
        if not self.enabled:
            return
        self.record(
            "session",
            "stopped",
            {"final_snapshot": dict(final_snapshot or {})},
        )
        self.enabled = False
        self.stopped_at = _utcnow_iso()

    def record(
        self,
        category: str,
        event: str,
        data: Mapping[str, Any] | None = None,
    ) -> None:
        """Append one event only while debug capture is enabled."""
        if not self.enabled:
            return
        if len(self._events) >= self.limit:
            self.dropped_events += 1
        self._events.append(
            {
                "timestamp": _utcnow_iso(),
                "category": str(category),
                "event": str(event),
                "data": dict(data or {}),
            }
        )

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serializable copy of the current debug session."""
        return {
            "schema_version": DEBUG_LOG_SCHEMA_VERSION,
            "enabled": self.enabled,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "limit": self.limit,
            "event_count": len(self._events),
            "dropped_events": self.dropped_events,
            "events": [dict(item) for item in self._events],
        }
