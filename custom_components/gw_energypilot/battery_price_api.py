"""Read-only battery/price/plan dashboard API for GW EnergyPilot."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .battery_plan import (
    finite_number,
    nonnegative_number,
    normalize_emhass_forecasts,
)
from .const import (
    CONF_P_BATT_ENTITY,
    DEFAULT_P_BATT_ENTITY,
    DOMAIN,
)


def _resolve_entry(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry | None:
    """Resolve one EnergyPilot config entry, defaulting to the first entry."""
    if entry_id:
        entry = hass.config_entries.async_get_entry(entry_id)
        return entry if entry and entry.domain == DOMAIN else None
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


def _battery_energy_payload(runtime_data: Any) -> dict[str, Any]:
    """Return GoodWe's native current-day battery energy counters."""
    coordinator = getattr(runtime_data, "coordinator", None)
    data = getattr(coordinator, "data", None)
    values = getattr(data, "values", {}) if data is not None else {}
    return {
        "charged_today_kwh": nonnegative_number(
            values.get("battery_charge_energy_today")
        ),
        "discharged_today_kwh": nonnegative_number(
            values.get("battery_discharge_energy_today")
        ),
        "source": "goodwe_35208_35211",
    }


def _battery_plan_payload(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return the configured EMHASS battery entity and its current horizon."""
    entity_id = str(
        entry.options.get(CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY)
        or DEFAULT_P_BATT_ENTITY
    )
    state = hass.states.get(entity_id)
    if state is None:
        return {
            "entity_id": entity_id,
            "available": False,
            "current_w": None,
            "last_updated": None,
            "points": [],
        }

    points = normalize_emhass_forecasts(entity_id, state.attributes)
    return {
        "entity_id": entity_id,
        "available": finite_number(state.state) is not None or bool(points),
        "current_w": finite_number(state.state),
        "last_updated": state.last_updated.isoformat(),
        "points": points,
    }


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
    """Return canonical prices, native energy totals and the EMHASS plan."""
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

    price_payload = await price_reader(force=bool(msg.get("force", False)))
    connection.send_result(
        msg["id"],
        {
            "entry_id": entry.entry_id,
            "chart_schema_version": 2,
            **price_payload,
            "battery_energy": _battery_energy_payload(runtime_data),
            "battery_plan": _battery_plan_payload(hass, entry),
        },
    )


@callback
def async_register_battery_price_api(hass: HomeAssistant) -> None:
    """Register the read-only EnergyPilot battery chart command."""
    websocket_api.async_register_command(hass, websocket_get_battery_price)
