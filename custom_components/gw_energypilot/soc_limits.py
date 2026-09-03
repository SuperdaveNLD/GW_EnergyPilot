"""Shared helpers for the verified GoodWe on-grid minimum-SOC setting."""

from __future__ import annotations

from typing import Any

from homeassistant.exceptions import HomeAssistantError

from .client import GWETAData, GWModbusError

GOODWE_ON_GRID_MINIMUM_SOC_KEY = "battery_discharge_depth_on_grid"


def goodwe_minimum_soc_pct(entry: Any) -> int | None:
    """Return the current verified coordinator value as a whole percentage."""
    runtime = getattr(entry, "runtime_data", None)
    coordinator = getattr(runtime, "coordinator", None)
    snapshot = getattr(coordinator, "data", None)
    if snapshot is None:
        return None
    raw = snapshot.values.get(GOODWE_ON_GRID_MINIMUM_SOC_KEY)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if 0 <= value <= 100 else None


def publish_goodwe_minimum_soc(entry: Any, value: int) -> None:
    """Reflect verified register read-back in coordinator-backed entities."""
    coordinator = entry.runtime_data.coordinator
    snapshot = coordinator.data
    if snapshot is None:
        return
    values = dict(snapshot.values)
    values[GOODWE_ON_GRID_MINIMUM_SOC_KEY] = int(value)
    readback = GWETAData(
        values={GOODWE_ON_GRID_MINIMUM_SOC_KEY: int(value)},
    )
    publish_local = getattr(coordinator, "async_publish_local_readback", None)
    if callable(publish_local):
        publish_local(readback)
        return
    coordinator.async_set_updated_data(GWETAData(values=values))


async def async_set_goodwe_minimum_soc(entry: Any, value: int) -> int:
    """Write and verify the canonical GoodWe on-grid minimum SOC setting."""
    try:
        readback = await entry.runtime_data.client.async_set_beta_soc_floor(
            GOODWE_ON_GRID_MINIMUM_SOC_KEY,
            value,
        )
    except (GWModbusError, ValueError) as err:
        raise HomeAssistantError(
            f"Unable to set GoodWe on-grid minimum SOC to {value}%: {err}"
        ) from err
    publish_goodwe_minimum_soc(entry, readback)
    return readback
