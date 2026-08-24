"""Read-only battery/price/plan dashboard API for GW EnergyPilot."""

from __future__ import annotations

import asyncio
from typing import Any, Mapping

from aiohttp import ClientError
import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .battery_plan import (
    emhass_schedule_attribute,
    finite_number,
    nonnegative_number,
    normalize_emhass_api_plan,
    normalize_emhass_forecasts,
)
from .const import (
    CONF_EMHASS_URL,
    CONF_P_BATT_ENTITY,
    DEFAULT_EMHASS_URL,
    DEFAULT_P_BATT_ENTITY,
    DOMAIN,
)

_PLAN_TIMEOUT_SECONDS = 8


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


async def _async_official_emhass_plan(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Read the latest full optimization horizon from EMHASS.

    Modern EMHASS exposes the latest optimization result through the versioned
    read-only ``GET /api/v1/plan`` endpoint. This is the canonical forecast
    source for the dashboard because Home Assistant's published ``P_batt``
    entity is primarily the current control target and may not carry the full
    future horizon on every EMHASS version/configuration.
    """
    base_url = str(
        entry.options.get(CONF_EMHASS_URL, DEFAULT_EMHASS_URL) or DEFAULT_EMHASS_URL
    ).strip().rstrip("/")
    if not base_url:
        return {
            "points": [],
            "generated_at": None,
            "emhass_schema_version": None,
            "error": "EMHASS URL is empty",
        }

    session = async_get_clientsession(hass)
    try:
        async with asyncio.timeout(_PLAN_TIMEOUT_SECONDS):
            async with session.get(f"{base_url}/api/v1/plan") as response:
                if response.status != 200:
                    return {
                        "points": [],
                        "generated_at": None,
                        "emhass_schema_version": None,
                        "error": f"EMHASS plan HTTP {response.status}",
                    }
                payload = await response.json(content_type=None)
    except (TimeoutError, ClientError, ValueError) as err:
        return {
            "points": [],
            "generated_at": None,
            "emhass_schema_version": None,
            "error": str(err),
        }

    if not isinstance(payload, Mapping):
        return {
            "points": [],
            "generated_at": None,
            "emhass_schema_version": None,
            "error": "EMHASS plan response is not an object",
        }

    points = normalize_emhass_api_plan(payload)
    status = str(payload.get("status") or "")
    return {
        "points": points,
        "generated_at": payload.get("generated_at"),
        "emhass_schema_version": payload.get("emhass_schema_version"),
        "error": None if points or status == "no-run" else "EMHASS plan has no P_batt horizon",
    }


async def _async_battery_plan_payload(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return current target plus the best available full battery horizon."""
    entity_id = str(
        entry.options.get(CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY)
        or DEFAULT_P_BATT_ENTITY
    )
    state = hass.states.get(entity_id)
    schedule_attribute = (
        emhass_schedule_attribute(state.attributes) if state is not None else None
    )
    entity_points = (
        normalize_emhass_forecasts(entity_id, state.attributes)
        if state is not None
        else []
    )

    official = await _async_official_emhass_plan(hass, entry)
    official_points = official["points"]
    points = official_points or entity_points
    forecast_source = (
        "emhass_api_v1_plan"
        if official_points
        else f"home_assistant_{schedule_attribute}"
        if entity_points and schedule_attribute
        else None
    )

    return {
        "entity_id": entity_id,
        "available": (
            (state is not None and finite_number(state.state) is not None) or bool(points)
        ),
        "current_w": finite_number(state.state) if state is not None else None,
        "last_updated": state.last_updated.isoformat() if state is not None else None,
        "schedule_attribute": schedule_attribute,
        "forecast_source": forecast_source,
        "forecast_error": official["error"] if not official_points else None,
        "generated_at": official["generated_at"],
        "emhass_schema_version": official["emhass_schema_version"],
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

    price_payload, battery_plan = await asyncio.gather(
        price_reader(force=bool(msg.get("force", False))),
        _async_battery_plan_payload(hass, entry),
    )
    connection.send_result(
        msg["id"],
        {
            "entry_id": entry.entry_id,
            "chart_schema_version": 4,
            **price_payload,
            "battery_energy": _battery_energy_payload(runtime_data),
            "battery_plan": battery_plan,
        },
    )


@callback
def async_register_battery_price_api(hass: HomeAssistant) -> None:
    """Register the read-only EnergyPilot battery chart command."""
    websocket_api.async_register_command(hass, websocket_get_battery_price)
