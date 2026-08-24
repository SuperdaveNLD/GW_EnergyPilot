"""Admin-only WebSocket API for GW EnergyPilot debug sessions."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN


def _resolve_entry(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry | None:
    """Resolve a loaded EnergyPilot config entry, defaulting to the first one."""
    if entry_id:
        entry = hass.config_entries.async_get_entry(entry_id)
        return entry if entry and entry.domain == DOMAIN else None
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


def _debug_runtime(entry: ConfigEntry):
    runtime = getattr(entry, "runtime_data", None)
    return getattr(runtime, "debug_log", None)


def _send_not_found(connection, msg: dict[str, Any]) -> None:
    connection.send_error(
        msg["id"],
        "not_found",
        "Loaded GW EnergyPilot config entry not found",
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "gw_energypilot/debug_log/get",
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def websocket_get_debug_log(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the current bounded debug session and live runtime snapshot."""
    entry = _resolve_entry(hass, msg.get("entry_id"))
    debug = _debug_runtime(entry) if entry is not None else None
    if entry is None or debug is None:
        _send_not_found(connection, msg)
        return
    connection.send_result(msg["id"], debug.snapshot())


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "gw_energypilot/debug_log/set_enabled",
        vol.Required("enabled"): bool,
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def websocket_set_debug_log_enabled(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Start a fresh debug session or stop the active one."""
    entry = _resolve_entry(hass, msg.get("entry_id"))
    debug = _debug_runtime(entry) if entry is not None else None
    if entry is None or debug is None:
        _send_not_found(connection, msg)
        return
    result = debug.enable() if msg["enabled"] else debug.disable()
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "gw_energypilot/debug_log/clear",
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def websocket_clear_debug_log(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Clear captured events without changing capture state."""
    entry = _resolve_entry(hass, msg.get("entry_id"))
    debug = _debug_runtime(entry) if entry is not None else None
    if entry is None or debug is None:
        _send_not_found(connection, msg)
        return
    connection.send_result(msg["id"], debug.clear())


@callback
def async_register_debug_log_api(hass: HomeAssistant) -> None:
    """Register EnergyPilot debug-session WebSocket commands."""
    websocket_api.async_register_command(hass, websocket_get_debug_log)
    websocket_api.async_register_command(hass, websocket_set_debug_log_enabled)
    websocket_api.async_register_command(hass, websocket_clear_debug_log)
