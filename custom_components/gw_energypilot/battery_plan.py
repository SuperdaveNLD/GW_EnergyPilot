"""Pure helpers for GW EnergyPilot battery-plan data."""

from __future__ import annotations

from datetime import datetime, timezone
import math
from statistics import median
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


def normalized_timestamp(value: Any) -> tuple[str, float] | None:
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
    """Return sorted forecast points from an EMHASS-published HA entity.

    Current EMHASS publishes battery-power horizons in the
    ``battery_scheduled_power`` attribute. ``forecasts`` remains accepted as a
    conservative compatibility fallback for older/custom publishers. The same
    helper also supports ``P_grid`` entities because those use ``forecasts``.
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
        parsed_timestamp = normalized_timestamp(raw_timestamp)
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


def normalize_emhass_api_plan(
    payload: Mapping[str, Any] | None,
) -> dict[str, list[dict[str, Any]]]:
    """Normalize the official ``GET /api/v1/plan`` battery/grid horizon.

    EMHASS schema 1.x defines ``timestamp``, ``P_batt``, ``P_grid`` and
    ``SOC_opt`` as canonical control columns. Its persisted plan can also
    expose the exact ``P_PV`` and ``P_Load`` forecast columns. They remain
    dashboard-only evidence and never feed the GoodWe controller. ``SOC_opt``
    is a fraction in the persisted plan, unlike the percentage published to
    Home Assistant, so it is accepted only inside the documented 0..1 range
    and normalized here. Unknown/missing rows are ignored rather than guessed
    from unrelated numeric columns.
    """
    if not isinstance(payload, Mapping) or payload.get("status") != "ok":
        return {
            "p_batt": [],
            "p_grid": [],
            "p_pv": [],
            "p_load": [],
            "soc_opt": [],
        }
    rows = payload.get("plan")
    if not isinstance(rows, list):
        return {
            "p_batt": [],
            "p_grid": [],
            "p_pv": [],
            "p_load": [],
            "soc_opt": [],
        }

    result: dict[str, list[dict[str, Any]]] = {
        "p_batt": [],
        "p_grid": [],
        "p_pv": [],
        "p_load": [],
        "soc_opt": [],
    }
    for result_key, column in (
        ("p_batt", "P_batt"),
        ("p_grid", "P_grid"),
        ("p_pv", "P_PV"),
        ("p_load", "P_Load"),
    ):
        by_timestamp: dict[float, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            parsed_timestamp = normalized_timestamp(row.get("timestamp"))
            value = finite_number(row.get(column))
            if parsed_timestamp is None or value is None:
                continue
            start, sort_key = parsed_timestamp
            by_timestamp[sort_key] = {
                "start": start,
                "value_w": round(value, 3),
            }
        result[result_key] = [by_timestamp[key] for key in sorted(by_timestamp)]

    by_timestamp: dict[float, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        parsed_timestamp = normalized_timestamp(row.get("timestamp"))
        fraction = finite_number(row.get("SOC_opt"))
        if (
            parsed_timestamp is None
            or fraction is None
            or not 0.0 <= fraction <= 1.0
        ):
            continue
        start, sort_key = parsed_timestamp
        by_timestamp[sort_key] = {
            "start": start,
            "value_pct": round(fraction * 100.0, 3),
        }
    result["soc_opt"] = [by_timestamp[key] for key in sorted(by_timestamp)]
    return result


def infer_plan_step_seconds(*point_sets: list[dict[str, Any]]) -> int | None:
    """Infer the plan timestep from adjacent timestamps without hardcoding it."""
    deltas: list[float] = []
    for points in point_sets:
        timestamps: list[float] = []
        for point in points:
            parsed = normalized_timestamp(point.get("start"))
            if parsed is not None:
                timestamps.append(parsed[1])
        timestamps.sort()
        for previous, current in zip(timestamps, timestamps[1:]):
            delta = current - previous
            if delta > 0:
                deltas.append(delta)
    if not deltas:
        return None
    return max(1, int(round(median(deltas))))


def plan_valid_until(
    points: list[dict[str, Any]],
    step_seconds: int | None,
) -> datetime | None:
    """Return the exclusive validity boundary of a stepwise plan."""
    if not points or step_seconds is None or step_seconds <= 0:
        return None
    parsed = [normalized_timestamp(point.get("start")) for point in points]
    timestamps = [item[1] for item in parsed if item is not None]
    if not timestamps:
        return None
    return datetime.fromtimestamp(max(timestamps) + step_seconds, tz=timezone.utc)


def plan_value_at(
    points: list[dict[str, Any]],
    when: datetime,
    step_seconds: int | None,
) -> float | None:
    """Return the plan value active at ``when`` without extrapolating stale data."""
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    target = when.timestamp()
    parsed_points: list[tuple[float, float]] = []
    for point in points:
        parsed = normalized_timestamp(point.get("start"))
        value = finite_number(point.get("value_w"))
        if parsed is not None and value is not None:
            parsed_points.append((parsed[1], value))
    parsed_points.sort(key=lambda item: item[0])
    for index, (start, value) in enumerate(parsed_points):
        next_start = (
            parsed_points[index + 1][0]
            if index + 1 < len(parsed_points)
            else start + step_seconds
            if step_seconds is not None and step_seconds > 0
            else None
        )
        if next_start is not None and start <= target < next_start:
            return value
    return None


def plan_percentage_at(
    points: list[dict[str, Any]],
    when: datetime,
    step_seconds: int | None,
) -> float | None:
    """Return the active validated percentage point without extrapolation."""
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    target = when.timestamp()
    parsed_points: list[tuple[float, float]] = []
    for point in points:
        parsed = normalized_timestamp(point.get("start"))
        value = finite_number(point.get("value_pct"))
        if parsed is not None and value is not None and 0.0 <= value <= 100.0:
            parsed_points.append((parsed[1], value))
    parsed_points.sort(key=lambda item: item[0])
    for index, (start, value) in enumerate(parsed_points):
        next_start = (
            parsed_points[index + 1][0]
            if index + 1 < len(parsed_points)
            else start + step_seconds
            if step_seconds is not None and step_seconds > 0
            else None
        )
        if next_start is not None and start <= target < next_start:
            return value
    return None
