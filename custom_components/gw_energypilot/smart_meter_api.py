"""GoodWe smart-meter automatic-control strategy API."""

from __future__ import annotations

from math import isfinite
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_USE_GOODWE_SMART_METER,
    DEFAULT_USE_GOODWE_SMART_METER,
    DOMAIN,
)


def _resolve_entry(hass: HomeAssistant, entry_id: str) -> ConfigEntry | None:
    """Resolve one GW EnergyPilot config entry."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        return None
    return entry


def _meter_state(entry: ConfigEntry) -> tuple[bool, float | None]:
    """Return whether live GoodWe meter telemetry is available and finite."""
    runtime_data = getattr(entry, "runtime_data", None)
    coordinator = getattr(runtime_data, "coordinator", None)
    snapshot = getattr(coordinator, "data", None)
    values = getattr(snapshot, "values", {}) if snapshot is not None else {}
    raw = values.get("meter_total_power_fast") if isinstance(values, dict) else None
    try:
        meter_power = float(raw)
    except (TypeError, ValueError):
        return False, None
    if not isfinite(meter_power):
        return False, None
    return True, meter_power


def _payload(entry: ConfigEntry) -> dict[str, Any]:
    """Return current smart-meter control configuration and live status."""
    available, meter_power = _meter_state(entry)
    enabled = bool(
        entry.data.get(
            CONF_USE_GOODWE_SMART_METER,
            DEFAULT_USE_GOODWE_SMART_METER,
        )
    )
    return {
        "entry_id": entry.entry_id,
        "enabled": enabled,
        "meter_available": available,
        "meter_power": meter_power,
        "enabled_strategy": "P_grid -> GoodWe modes 9/10; mode 1 around zero",
        "disabled_strategy": "P_batt -> GoodWe modes 11/12; mode 8 around zero",
        "storage": "home_assistant_config_entry_data",
    }


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "gw_energypilot/smart_meter/get",
        vol.Required("entry_id"): str,
    }
)
@websocket_api.async_response
async def websocket_get_smart_meter(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the GoodWe smart-meter control setting."""
    entry = _resolve_entry(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(
            msg["id"], "not_found", "GW EnergyPilot config entry not found"
        )
        return
    connection.send_result(msg["id"], _payload(entry))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "gw_energypilot/smart_meter/set",
        vol.Required("entry_id"): str,
        vol.Required("enabled"): bool,
    }
)
@websocket_api.async_response
async def websocket_set_smart_meter(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Persist the automatic-control strategy and reevaluate when active."""
    entry = _resolve_entry(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(
            msg["id"], "not_found", "GW EnergyPilot config entry not found"
        )
        return

    enabled = bool(msg["enabled"])
    new_data = dict(entry.data)
    new_data[CONF_USE_GOODWE_SMART_METER] = enabled
    hass.config_entries.async_update_entry(entry, data=new_data)

    runtime_data = getattr(entry, "runtime_data", None)
    controller = getattr(runtime_data, "controller", None)
    if controller is not None and controller.enabled:
        await controller.async_evaluate()

    refreshed = hass.config_entries.async_get_entry(entry.entry_id) or entry
    connection.send_result(msg["id"], _payload(refreshed))


@callback
def async_register_smart_meter_api(hass: HomeAssistant) -> None:
    """Register GoodWe smart-meter settings WebSocket commands once."""
    websocket_api.async_register_command(hass, websocket_get_smart_meter)
    websocket_api.async_register_command(hass, websocket_set_smart_meter)
