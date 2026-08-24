"""WebSocket API for GW EnergyPilot optimization history."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .optimization_log import GWEnergyPilotOptimizationLog, OPTIMIZATION_LOG_LIMIT


def _resolve_entry(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry | None:
    """Resolve an EnergyPilot config entry, defaulting to the first entry."""
    if entry_id:
        entry = hass.config_entries.async_get_entry(entry_id)
        return entry if entry and entry.domain == DOMAIN else None
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "gw_energypilot/optimization_log/get",
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def websocket_get_optimization_log(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the bounded optimization history for one EnergyPilot entry."""
    entry = _resolve_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(
            msg["id"], "not_found", "GW EnergyPilot config entry not found"
        )
        return

    history = await GWEnergyPilotOptimizationLog(
        hass, entry.entry_id
    ).async_history()
    connection.send_result(
        msg["id"],
        {
            "entry_id": entry.entry_id,
            "limit": OPTIMIZATION_LOG_LIMIT,
            "history": history,
        },
    )


@callback
def async_register_optimization_log_api(hass: HomeAssistant) -> None:
    """Register the EnergyPilot optimization-history WebSocket command."""
    websocket_api.async_register_command(hass, websocket_get_optimization_log)
