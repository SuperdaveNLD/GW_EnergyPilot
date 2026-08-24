"""Read-only battery/price dashboard API for GW EnergyPilot."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN


def _resolve_entry(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry | None:
    """Resolve one EnergyPilot config entry, defaulting to the first entry."""
    if entry_id:
        entry = hass.config_entries.async_get_entry(entry_id)
        return entry if entry and entry.domain == DOMAIN else None
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


@websocket_api.websocket_command(
    {
        vol.Required("type"): "gw_energypilot/battery_price/get",
        vol.Optional("entry_id"): str,
        vol.Optional("force", default=False): bool,
    }
)
@websocket_api.async_response
async def websocket_get_battery_price(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the canonical timestamped runtime price series for the chart."""
    entry = _resolve_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(
            msg["id"], "not_found", "GW EnergyPilot config entry not found"
        )
        return

    runtime_data = getattr(entry, "runtime_data", None)
    orchestrator = getattr(runtime_data, "orchestrator", None)
    price_reader = getattr(orchestrator, "async_dashboard_price_payload", None)
    if not callable(price_reader):
        connection.send_error(
            msg["id"], "not_loaded", "GW EnergyPilot price runtime is not loaded"
        )
        return

    payload = await price_reader(force=bool(msg.get("force", False)))
    connection.send_result(msg["id"], {"entry_id": entry.entry_id, **payload})


@callback
def async_register_battery_price_api(hass: HomeAssistant) -> None:
    """Register the read-only EnergyPilot battery/price chart command."""
    websocket_api.async_register_command(hass, websocket_get_battery_price)
