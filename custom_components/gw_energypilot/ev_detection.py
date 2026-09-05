"""EV charging detection from the user-selected Home Assistant source."""

from __future__ import annotations

from math import isfinite
from typing import Any, Mapping

from .const import (
    CONF_EV_DETECTION_METHOD,
    CONF_EV_MODE_ENTITY,
    CONF_EV_POWER_ENTITY,
    EV_DETECTION_METHOD_POWER,
    EV_DETECTION_METHOD_STATE,
)

EV_ACTIVE_STATE_VALUES = frozenset(
    {
        "on",
        "true",
        "charging",
        "connected_charging",
    }
)


def detection_method(options: Mapping[str, Any]) -> str | None:
    """Return an explicit detection method, or None for legacy OR behavior."""
    configured = options.get(CONF_EV_DETECTION_METHOD)
    if configured in {EV_DETECTION_METHOD_POWER, EV_DETECTION_METHOD_STATE}:
        return str(configured)
    return None


def default_detection_method(options: Mapping[str, Any]) -> str:
    """Choose the least-surprising form default for a legacy config entry."""
    configured = detection_method(options)
    if configured is not None:
        return configured
    if options.get(CONF_EV_MODE_ENTITY) and not options.get(CONF_EV_POWER_ENTITY):
        return EV_DETECTION_METHOD_STATE
    return EV_DETECTION_METHOD_POWER


def source_entity_ids(options: Mapping[str, Any]) -> set[str]:
    """Return only the selected EV source, preserving legacy OR behavior."""
    method = detection_method(options)
    keys = (
        (CONF_EV_POWER_ENTITY,)
        if method == EV_DETECTION_METHOD_POWER
        else (CONF_EV_MODE_ENTITY,)
        if method == EV_DETECTION_METHOD_STATE
        else (CONF_EV_MODE_ENTITY, CONF_EV_POWER_ENTITY)
    )
    return {str(options[key]) for key in keys if options.get(key)}


def status_is_active(states: Any, entity_id: str | None) -> bool:
    """Interpret a selected charging boolean or status entity."""
    state = states.get(entity_id) if entity_id else None
    return str(getattr(state, "state", "")).strip().lower() in EV_ACTIVE_STATE_VALUES


def legacy_status_is_active(states: Any, entity_id: str | None) -> bool:
    """Preserve the exact pre-selector charging-mode interpretation."""
    state = states.get(entity_id) if entity_id else None
    return str(getattr(state, "state", "")).strip().lower() == "connected_charging"


def power_is_active(states: Any, entity_id: str | None, threshold_w: float) -> bool:
    """Interpret a selected charger power sensor in W, kW, MW or mW."""
    power = power_value_w(states, entity_id)
    return power is not None and power > threshold_w


def power_value_w(states: Any, entity_id: str | None) -> float | None:
    """Return finite measured charger power in watts, if available."""
    state = states.get(entity_id) if entity_id else None
    raw = str(getattr(state, "state", "")).strip().lower()
    if raw in {"", "none", "unknown", "unavailable"}:
        return None
    try:
        power = float(raw)
    except (TypeError, ValueError):
        return None
    if not isfinite(power):
        return None
    unit = (getattr(state, "attributes", {}) or {}).get("unit_of_measurement")
    if unit == "kW":
        power *= 1000
    elif unit == "MW":
        power *= 1_000_000
    elif unit == "mW":
        power /= 1000
    return power
