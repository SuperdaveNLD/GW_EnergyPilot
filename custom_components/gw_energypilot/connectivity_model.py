"""Pure connectivity-state helpers for GW EnergyPilot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .const import EV_CONNECTIVITY_GRACE_SECONDS

MISSING_STATES = {"", "none", "unknown", "unavailable"}


def ev_source_online(state: Any) -> bool:
    """Interpret one configured Home Assistant entity as charger reachability.

    A missing/unknown/unavailable state is unreachable. Binary sensors are
    explicit boolean connectivity inputs. For other domains, any usable state
    means the charger integration is reporting; an ``off`` charging switch is
    therefore still an online, idle charger.
    """
    if state is None:
        return False
    raw = str(getattr(state, "state", "")).strip().lower()
    if raw in MISSING_STATES:
        return False
    entity_id = str(getattr(state, "entity_id", ""))
    if entity_id.startswith("binary_sensor."):
        return raw == "on"
    return True


@dataclass(frozen=True, slots=True)
class ConnectivityEvent:
    """One state transition that should be logged exactly once."""

    event: str
    occurred_at: datetime


class EVConnectivityGuard:
    """Suspend and recover EV coordination after stable connectivity windows."""

    def __init__(self, grace_seconds: int = EV_CONNECTIVITY_GRACE_SECONDS) -> None:
        self.grace_seconds = max(1, int(grace_seconds))
        self.suspended = False
        self.offline_since: datetime | None = None
        self.online_since: datetime | None = None
        self.last_online: bool | None = None

    @property
    def transition(self) -> str | None:
        if self.suspended and self.online_since is not None:
            return "resume_pending"
        if not self.suspended and self.offline_since is not None:
            return "suspend_pending"
        return None

    def effective(self, user_enabled: bool) -> bool:
        """Return runtime EV coordination without rewriting user settings."""
        return bool(user_enabled and not self.suspended)

    def deadline(self) -> datetime | None:
        """Return the next stable-window deadline, if one is active."""
        started = self.online_since if self.suspended else self.offline_since
        if started is None:
            return None
        return started + timedelta(seconds=self.grace_seconds)

    def remaining_seconds(self, now: datetime) -> int | None:
        deadline = self.deadline()
        if deadline is None:
            return None
        return max(0, int((deadline - now).total_seconds() + 0.999))

    def update(
        self,
        *,
        now: datetime,
        user_enabled: bool,
        source_configured: bool,
        online: bool,
    ) -> tuple[ConnectivityEvent, ...]:
        """Apply one reachability observation and return new transitions."""
        events: list[ConnectivityEvent] = []

        if not source_configured:
            self.offline_since = None
            self.online_since = None
            self.last_online = None
            if self.suspended:
                self.suspended = False
            return ()

        if not user_enabled:
            if self.suspended or self.online_since is not None:
                events.append(ConnectivityEvent("ev_resume_cancelled_by_user", now))
            self.suspended = False
            self.offline_since = None
            self.online_since = None
            self.last_online = online
            return tuple(events)

        if self.last_online is not None and online != self.last_online:
            events.append(
                ConnectivityEvent(
                    "ev_connectivity_restored" if online else "ev_connectivity_lost",
                    now,
                )
            )
        elif self.last_online is None and not online:
            events.append(ConnectivityEvent("ev_connectivity_lost", now))
        self.last_online = online

        if online:
            self.offline_since = None
            if not self.suspended:
                self.online_since = None
                return tuple(events)
            if self.online_since is None:
                self.online_since = now
            if (now - self.online_since).total_seconds() >= self.grace_seconds:
                self.suspended = False
                self.online_since = None
                events.append(ConnectivityEvent("ev_coordination_resumed", now))
            return tuple(events)

        self.online_since = None
        if self.suspended:
            self.offline_since = None
            return tuple(events)
        if self.offline_since is None:
            self.offline_since = now
        if (now - self.offline_since).total_seconds() >= self.grace_seconds:
            self.suspended = True
            self.offline_since = None
            events.append(ConnectivityEvent("ev_coordination_suspended", now))
        return tuple(events)
