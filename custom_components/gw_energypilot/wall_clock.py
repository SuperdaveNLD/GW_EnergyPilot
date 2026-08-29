"""Wall-clock cadence helpers for EMHASS orchestration."""

from __future__ import annotations

from datetime import datetime

WALL_CLOCK_OFFSET_SECOND = 15
WALL_CLOCK_TICK_MINUTES = 5
PLAN_FAIL_SAFE_CHECK_MINUTES = 15


def cadence_is_due(now: datetime, minutes: int) -> bool:
    """Return whether a local wall-clock timestamp is on a cadence boundary."""
    if minutes <= 0:
        return False
    minute_of_day = now.hour * 60 + now.minute
    return minute_of_day % minutes == 0


def plan_step_minutes(step_seconds: int | None) -> int | None:
    """Return a scheduler-compatible plan step without guessing its cadence."""
    if step_seconds is None or step_seconds <= 0 or step_seconds % 60:
        return None
    minutes = step_seconds // 60
    if minutes < WALL_CLOCK_TICK_MINUTES or minutes % WALL_CLOCK_TICK_MINUTES:
        return None
    return minutes
