"""Pure helpers for GW EnergyPilot battery-plan chart data."""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any, Mapping


_TIMESTAMP_KEYS = ("date", "start", "timestamp", "time")
_SCHEDULE_ATTRIBUTE_KEYS = (
    # Current EMHASS power-publish contract (RetrieveHass type_var="batt").
    "battery_scheduled_power",
    # Backwards-compatible/custom payload fallback used by earlier chart code.
    "forecasts",
)
_VALUE_FALLBACK_KEYS = (
    "value",
    "state",
    "P_batt",
    "p_batt",
    "p_batt_forecast",
)


def finite_number(value: Any) -> float | None:
    """Return a finite float, otherwise None."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def nonnegative_number(value: Any) -> float | None:
    """Return a finite non-negative float, otherwise None."""
    number = finite_number(value)
    return number if number is not None and number >= 0 else None


def _timestamp(value: Any) -> tuple[str, float] | None:
    """Normalize an ISO timestamp while retaining its explicit offset."""
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat(), parsed.timestamp()


def emhass_schedule_attribute(attributes: Mapping[str, Any] | None) -> str | None:
    """Return the first supported EMHASS battery-schedule attribute name."""
    if not attributes:
        return None
    for key in _SCHEDULE_ATTRIBUTE_KEYS:
        if isinstance(attributes.get(key), list):
            return key
    return None


def normalize_emhass_forecasts(
    entity_id: str,
    attributes: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Return sorted ``P_batt`` forecast points from an EMHASS entity.

    Current EMHASS publishes battery-power horizons in the
    ``battery_scheduled_power`` attribute. ``forecasts`` remains accepted as a
    conservative compatibility fallback for older/custom publishers. Each row
    uses ``date`` plus a value key derived from the configured entity id.
    """
    schedule_attribute = emhass_schedule_attribute(attributes)
    if schedule_attribute is None or attributes is None:
        return []
    rows = attributes.get(schedule_attribute)
    if not isinstance(rows, list):
        return []

    entity_key = str(entity_id or "").split(".", 1)[-1]
    by_timestamp: dict[float, dict[str, Any]] = {}

    for row in rows:
        if not isinstance(row, Mapping):
            continue

        raw_timestamp = next(
            (row.get(key) for key in _TIMESTAMP_KEYS if row.get(key) is not None),
            None,
        )
        parsed_timestamp = _timestamp(raw_timestamp)
        if parsed_timestamp is None:
            continue
        start, sort_key = parsed_timestamp

        value = finite_number(row.get(entity_key))
        if value is None:
            for key in _VALUE_FALLBACK_KEYS:
                value = finite_number(row.get(key))
                if value is not None:
                    break
        if value is None:
            for key, candidate in row.items():
                if key in _TIMESTAMP_KEYS:
                    continue
                value = finite_number(candidate)
                if value is not None:
                    break
        if value is None:
            continue

        by_timestamp[sort_key] = {
            "start": start,
            "value_w": round(value, 3),
        }

    return [by_timestamp[key] for key in sorted(by_timestamp)]
