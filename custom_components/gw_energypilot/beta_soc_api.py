"""Manual Beta GoodWe SOC-floor settings API."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .client import BETA_SOC_FLOOR_KEYS, GWETAData, GWModbusError
from .const import DOMAIN


def _resolve_entry(hass: HomeAssistant, entry_id: str) -> ConfigEntry | None:
    """Resolve one loaded GW EnergyPilot config entry."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        return None
    return entry


def _current_values(entry: ConfigEntry) -> dict[str, int | None]:
    """Return the currently coordinator-backed Beta SOC-floor values."""
    runtime_data = getattr(entry, "runtime_data", None)
    coordinator = getattr(runtime_data, "coordinator", None)
    snapshot = getattr(coordinator, "data", None)
    values = getattr(snapshot, "values", {}) if snapshot is not None else {}
    return {
        key: int(values[key]) if key in values else None
        for key in BETA_SOC_FLOOR_KEYS
    }


def _payload(entry: ConfigEntry) -> dict[str, Any]:
    """Return the manual Beta SOC-floor settings model."""
    values = _current_values(entry)
    return {
        "entry_id": entry.entry_id,
        "values": values,
        "available": {key: values[key] is not None for key in BETA_SOC_FLOOR_KEYS},
        "beta": True,
        "storage": "goodwe_inverter",
        "semantics": {
            "battery_discharge_depth_on_grid": (
                "Raw register 45356 is treated as the on-grid minimum SOC floor; "
                "equivalent DoD is 100 minus this value."
            ),
            "battery_discharge_depth_off_grid": (
                "Raw register 45358 is treated as the off-grid minimum SOC floor."
            ),
        },
    }


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "gw_energypilot/beta_soc/get",
        vol.Required("entry_id"): str,
    }
)
@websocket_api.async_response
async def websocket_get_beta_soc(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return current coordinator-backed Beta SOC-floor values."""
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
        vol.Required("type"): "gw_energypilot/beta_soc/set",
        vol.Required("entry_id"): str,
        vol.Required("key"): vol.In(BETA_SOC_FLOOR_KEYS),
        vol.Required("value"): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    }
)
@websocket_api.async_response
async def websocket_set_beta_soc(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Write exactly one manual Beta SOC-floor value and verify read-back."""
    entry = _resolve_entry(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(
            msg["id"], "not_found", "GW EnergyPilot config entry not found"
        )
        return

    key = msg["key"]
    value = int(msg["value"])
    before = _current_values(entry)
    if before.get(key) is None:
        connection.send_error(
            msg["id"],
            "beta_register_unavailable",
            "That Beta SOC register is not currently readable on this inverter",
        )
        return

    if before[key] == value:
        connection.send_result(
            msg["id"],
            {
                **_payload(entry),
                "changed": False,
                "key": key,
                "previous": before[key],
                "readback": before[key],
            },
        )
        return

    try:
        readback = await entry.runtime_data.client.async_set_beta_soc_floor(key, value)
    except (GWModbusError, ValueError) as err:
        connection.send_error(msg["id"], "beta_write_failed", str(err))
        return

    coordinator = entry.runtime_data.coordinator
    snapshot = coordinator.data
    if snapshot is not None:
        updated_values = dict(snapshot.values)
        updated_values[key] = readback
        coordinator.async_set_updated_data(GWETAData(values=updated_values))

    connection.send_result(
        msg["id"],
        {
            **_payload(entry),
            "changed": True,
            "key": key,
            "previous": before[key],
            "readback": readback,
        },
    )


@callback
def async_register_beta_soc_api(hass: HomeAssistant) -> None:
    """Register manual Beta SOC-floor WebSocket commands once."""
    websocket_api.async_register_command(hass, websocket_get_beta_soc)
    websocket_api.async_register_command(hass, websocket_set_beta_soc)
