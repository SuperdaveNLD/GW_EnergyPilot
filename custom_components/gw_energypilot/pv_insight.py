"""Pure helpers for read-only PV insight telemetry."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any


_POWER_UNIT_FACTORS = {
    "W": 1.0,
    "kW": 1_000.0,
    "MW": 1_000_000.0,
    "mW": 0.001,
    "watt": 1.0,
    "watts": 1.0,
    "kilowatt": 1_000.0,
    "kilowatts": 1_000.0,
    "megawatt": 1_000_000.0,
    "megawatts": 1_000_000.0,
}


def external_sources_enabled(
    options: Mapping[str, Any],
    *,
    enable_key: str,
    entity_keys: Iterable[str],
    default: bool = False,
) -> bool:
    """Resolve the v0.46 master switch without disabling v0.45 sources."""
    if enable_key in options:
        return bool(options[enable_key])
    return bool(
        default
        or any(str(options.get(key, "")).strip() for key in entity_keys)
    )


def normalize_generation_power_w(value: Any, unit: Any) -> float | None:
    """Return a finite, non-negative generation value normalized to watts."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0:
        return None

    unit_text = str(unit or "").strip()
    factor = _POWER_UNIT_FACTORS.get(unit_text)
    if factor is None:
        factor = _POWER_UNIT_FACTORS.get(unit_text.lower())
    if factor is None:
        return None

    normalized = number * factor
    return normalized if math.isfinite(normalized) else None


def sum_generation_power_w(values: list[float | None]) -> float | None:
    """Sum available normalized readings, or return unavailable when none exist."""
    available = [value for value in values if value is not None]
    return round(sum(available), 3) if available else None
