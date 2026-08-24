"""GoodWe automatic-control strategy API."""

from __future__ import annotations

from math import isfinite
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_CONTROL_STRATEGY,
    CONF_USE_GOODWE_SMART_METER,
    CONTROL_STRATEGIES,
    CONTROL_STRATEGY_BATTERY,
    CONTROL_STRATEGY_GRID,
    CONTROL_STRATEGY_HYBRID,
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


def _control_strategy(entry: ConfigEntry) -> str:
    """Return explicit strategy, falling back to the legacy boolean setting."""
    configured = entry.data.get(CONF_CONTROL_STRATEGY)
    if configured in CONTROL_STRATEGIES:
        return str(configured)
    return (
        CONTROL_STRATEGY_GRID
        if bool(
            entry.data.get(
                CONF_USE_GOODWE_SMART_METER,
                DEFAULT_USE_GOODWE_SMART_METER,
            )
        )
        else CONTROL_STRATEGY_BATTERY
    )


def _payload(entry: ConfigEntry) -> dict[str, Any]:
    """Return current automatic-control configuration and live meter status."""
    available, meter_power = _meter_state(entry)
    strategy = _control_strategy(entry)
    return {
        "entry_id": entry.entry_id,
        "strategy": strategy,
        "enabled": strategy != CONTROL_STRATEGY_BATTERY,
        "meter_available": available,
        "meter_power": meter_power,
        "strategies": {
            CONTROL_STRATEGY_BATTERY: "Battery control",
            CONTROL_STRATEGY_GRID: "Grid control",
            CONTROL_STRATEGY_HYBRID: "Hybrid control",
        },
        "battery_strategy": "P_batt -> GoodWe modes 11/12; mode 8 around zero",
        "grid_strategy": "P_grid -> GoodWe modes 9/10; mode 1 around zero",
        "hybrid_strategy": "P_batt charge -> mode 11; P_grid export -> mode 10; mode 1 otherwise",
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
    """Return the automatic-control strategy."""
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
        vol.Optional("strategy"): vol.In(CONTROL_STRATEGIES),
        vol.Optional("enabled"): bool,
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

    strategy = msg.get("strategy")
    if strategy is None:
        if "enabled" not in msg:
            connection.send_error(
                msg["id"], "invalid_format", "A control strategy is required"
            )
            return
        strategy = (
            CONTROL_STRATEGY_GRID if bool(msg["enabled"]) else CONTROL_STRATEGY_BATTERY
        )

    new_data = dict(entry.data)
    new_data[CONF_CONTROL_STRATEGY] = strategy
    # Keep the old boolean synchronized for older frontend layers and support
    # tooling. Hybrid needs meter telemetry for its export side.
    new_data[CONF_USE_GOODWE_SMART_METER] = strategy != CONTROL_STRATEGY_BATTERY
    hass.config_entries.async_update_entry(entry, data=new_data)

    runtime_data = getattr(entry, "runtime_data", None)
    controller = getattr(runtime_data, "controller", None)
    if controller is not None and controller.enabled:
        await controller.async_evaluate()

    refreshed = hass.config_entries.async_get_entry(entry.entry_id) or entry
    connection.send_result(msg["id"], _payload(refreshed))


@callback
def async_register_smart_meter_api(hass: HomeAssistant) -> None:
    """Register GoodWe control-strategy WebSocket commands once."""
    websocket_api.async_register_command(hass, websocket_get_smart_meter)
    websocket_api.async_register_command(hass, websocket_set_smart_meter)
