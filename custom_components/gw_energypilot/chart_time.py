"""Home Assistant-timezone chart windows for Battery · Plan · Price."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_ROLLING_HALF_WINDOW = timedelta(hours=6)
_ROLLING_TICK = timedelta(hours=3)


def _time_zone(name: str | None) -> ZoneInfo:
    """Resolve Home Assistant's configured timezone without guessing."""
    try:
        return ZoneInfo(str(name or "UTC"))
    except (ValueError, ZoneInfoNotFoundError):
        return ZoneInfo("UTC")


def _utc(value: datetime | None) -> datetime:
    """Normalize an optional instant to an aware UTC datetime."""
    if value is None:
        return datetime.now(UTC)
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _boundary(day: date, hour: int, zone: ZoneInfo) -> datetime:
    """Build a local wall-clock boundary, retaining DST offset semantics."""
    return datetime.combine(day, time(hour=hour), tzinfo=zone)


def _iso_utc(value: datetime) -> str:
    """Serialize one instant in the existing Home Assistant ISO convention."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _tick(value: datetime, local_day: date, zone: ZoneInfo) -> dict[str, Any]:
    """Return one absolute tick plus its local calendar-day offset."""
    local_value = value.astimezone(zone)
    return {
        "at": _iso_utc(value),
        "day_offset": (local_value.date() - local_day).days,
    }


def _fixed_ticks(
    local_day: date,
    zone: ZoneInfo,
    *,
    through_tomorrow_hour: int,
) -> list[dict[str, Any]]:
    """Build six-hour local-wall-clock ticks for one fixed chart window."""
    ticks: list[dict[str, Any]] = []
    tomorrow = local_day + timedelta(days=1)
    for hour in (0, 6, 12, 18):
        value = _boundary(local_day, hour, zone)
        ticks.append(_tick(value, local_day, zone))
    for hour in range(0, through_tomorrow_hour + 1, 6):
        value = _boundary(tomorrow, hour, zone)
        ticks.append(_tick(value, local_day, zone))
    return ticks


def build_chart_time_payload(
    time_zone: str | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return authoritative rolling/fixed windows in Home Assistant time."""
    zone = _time_zone(time_zone)
    now_utc = _utc(now)
    local_now = now_utc.astimezone(zone)
    local_day = local_now.date()
    tomorrow = local_day + timedelta(days=1)

    day_start = _boundary(local_day, 0, zone)
    day_end = _boundary(tomorrow, 0, zone)
    extended_end = _boundary(tomorrow, 12, zone)
    rolling_start = now_utc - _ROLLING_HALF_WINDOW
    rolling_end = now_utc + _ROLLING_HALF_WINDOW
    rolling_ticks = [
        _tick(rolling_start + index * _ROLLING_TICK, local_day, zone)
        for index in range(5)
    ]

    return {
        "time_zone": zone.key,
        "now": _iso_utc(now_utc),
        "day_start": _iso_utc(day_start),
        "day_end": _iso_utc(day_end),
        "history_start": _iso_utc(min(day_start, rolling_start)),
        "max_end": _iso_utc(extended_end),
        "windows": {
            "12h": {
                "start": _iso_utc(rolling_start),
                "end": _iso_utc(rolling_end),
                "ticks": rolling_ticks,
            },
            "24h": {
                "start": _iso_utc(day_start),
                "end": _iso_utc(day_end),
                "ticks": _fixed_ticks(
                    local_day,
                    zone,
                    through_tomorrow_hour=0,
                ),
            },
            "36h": {
                "start": _iso_utc(day_start),
                "end": _iso_utc(extended_end),
                "ticks": _fixed_ticks(
                    local_day,
                    zone,
                    through_tomorrow_hour=12,
                ),
            },
        },
    }
