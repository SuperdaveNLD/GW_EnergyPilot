"""Read-only battery/price/plan dashboard API for GW EnergyPilot."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .battery_plan import (
    emhass_schedule_attribute,
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
    """Return live P_batt plus the canonical persisted EMHASS horizon."""
    entity_id = str(
        entry.options.get(CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY)
        or DEFAULT_P_BATT_ENTITY
    )
    state = hass.states.get(entity_id)
    schedule_attribute = (
        emhass_schedule_attribute(state.attributes) if state is not None else None
    )
    live_points = (
        normalize_emhass_forecasts(entity_id, state.attributes)
        if state is not None
        else []
    )

    runtime_data = getattr(entry, "runtime_data", None)
    plan_runtime = getattr(runtime_data, "plan_runtime", None)
    cached_points = plan_runtime.points("p_batt") if plan_runtime is not None else []
    points = cached_points or live_points

    live_current = finite_number(state.state) if state is not None else None
    cached_current = (
        plan_runtime.current_p_batt() if plan_runtime is not None else None
    )
    diagnostics = dict(plan_runtime.diagnostics) if plan_runtime is not None else {}
    current_w = live_current if live_current is not None else cached_current
    forecast_source = (
        diagnostics.get("source")
        if cached_points
        else f"home_assistant_{schedule_attribute}"
        if live_points and schedule_attribute
        else None
    )

    return {
        "entity_id": entity_id,
        "available": current_w is not None or bool(points),
        "current_w": current_w,
        "current_source": (
            "home_assistant"
            if live_current is not None
            else "persistent_plan"
            if cached_current is not None
            else None
        ),
        "last_updated": state.last_updated.isoformat() if state is not None else None,
        "schedule_attribute": schedule_attribute,
        "forecast_source": forecast_source,
        "generated_at": diagnostics.get("generated_at"),
        "valid_until": diagnostics.get("valid_until"),
        "restored_from_store": diagnostics.get("restored_from_store", False),
        "points": points,
    }


def _battery_soc_plan_payload(entry: ConfigEntry) -> dict[str, Any]:
    """Return validated planned SOC percentages from the official plan mirror."""
    runtime_data = getattr(entry, "runtime_data", None)
    plan_runtime = getattr(runtime_data, "plan_runtime", None)
    points = plan_runtime.points("soc_opt") if plan_runtime is not None else []
    diagnostics = dict(plan_runtime.diagnostics) if plan_runtime is not None else {}
    source = diagnostics.get("source") if points else None
    return {
        "available": bool(points),
        "unit": "%",
        "source": source,
        "source_column": "SOC_opt" if source == "emhass_api_v1_plan" else None,
        "source_unit": "fraction_0_1" if source == "emhass_api_v1_plan" else None,
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
    plan_runtime = getattr(runtime_data, "plan_runtime", None)
    price_reader = getattr(orchestrator, "async_dashboard_price_payload", None)
    if not callable(price_reader):
        connection.send_error(
            msg["id"], "not_loaded", "GW EnergyPilot price runtime is not loaded"
        )
        return

    force = bool(msg.get("force", False))
    refresh_plan = bool(
        plan_runtime is not None and (force or not plan_runtime.has_current_plan())
    )
    if refresh_plan:
        price_payload, _plan_refreshed = await asyncio.gather(
            price_reader(force=force),
            plan_runtime.async_refresh(reason="dashboard"),
        )
    else:
        price_payload = await price_reader(force=force)

    connection.send_result(
        msg["id"],
        {
            "entry_id": entry.entry_id,
            "chart_schema_version": 5,
            "plan_revision": int(getattr(orchestrator, "plan_revision", 0) or 0),
            **price_payload,
            "battery_energy": _battery_energy_payload(runtime_data),
            "battery_plan": _battery_plan_payload(hass, entry),
            "battery_soc_plan": _battery_soc_plan_payload(entry),
        },
    )


@callback
def async_register_battery_price_api(hass: HomeAssistant) -> None:
    """Register the read-only EnergyPilot battery chart command."""
    websocket_api.async_register_command(hass, websocket_get_battery_price)
