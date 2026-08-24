"""Admin API for EnergyPilot defaults and required EMHASS config sync."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .config_flow import CONF_EMHASS_SOC_FINAL_PCT
from .const import (
    CONF_BUY_PRICE_ADDER,
    CONF_EMHASS_FALLBACK_LOAD,
    CONF_EMHASS_OPTIMIZATION_INTERVAL,
    CONF_EMHASS_URL,
    CONF_ENABLE_EMHASS_ORCHESTRATOR,
    CONF_NORDPOOL_AREA,
    CONF_NORDPOOL_CURRENCY,
    CONF_OPTIMIZE_ON_TOMORROW_PRICES,
    CONF_OPTIM_REQUIRED_STATE,
    CONF_OPTIM_STATUS_ENTITY,
    CONF_P_BATT_ENTITY,
    CONF_P_GRID_ENTITY,
    CONF_SELL_PRICE_DEDUCTION,
    CONF_USE_NORDPOOL_PRICES,
    DEFAULT_BUY_PRICE_ADDER,
    DEFAULT_EMHASS_FALLBACK_LOAD,
    DEFAULT_EMHASS_OPTIMIZATION_INTERVAL,
    DEFAULT_EMHASS_SOC_FINAL,
    DEFAULT_EMHASS_URL,
    DEFAULT_NORDPOOL_AREA,
    DEFAULT_NORDPOOL_CURRENCY,
    DEFAULT_OPTIMIZE_ON_TOMORROW_PRICES,
    DEFAULT_OPTIM_REQUIRED_STATE,
    DEFAULT_OPTIM_STATUS_ENTITY,
    DEFAULT_P_BATT_ENTITY,
    DEFAULT_P_GRID_ENTITY,
    DEFAULT_SELL_PRICE_DEDUCTION,
    DEFAULT_USE_NORDPOOL_PRICES,
    DOMAIN,
)
from .emhass_config import async_get_emhass_config, async_write_emhass_config
from .emhass_sync import build_emhass_sync_config, emhass_sync_changes

ENTITY_KEYS: dict[str, str] = {
    "pv": "pv_total_power",
    "load": "total_load_power",
    "battery": "battery_power",
    "soc": "battery_soc",
}
REQUIRED_ENTITY_PURPOSES = {"load", "battery", "soc"}


def _resolve_entry(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry | None:
    if entry_id:
        entry = hass.config_entries.async_get_entry(entry_id)
        return entry if entry and entry.domain == DOMAIN else None
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


def _recommended_emhass_options() -> dict[str, Any]:
    return {
        CONF_ENABLE_EMHASS_ORCHESTRATOR: True,
        CONF_EMHASS_URL: DEFAULT_EMHASS_URL,
        CONF_EMHASS_OPTIMIZATION_INTERVAL: DEFAULT_EMHASS_OPTIMIZATION_INTERVAL,
        CONF_EMHASS_SOC_FINAL_PCT: DEFAULT_EMHASS_SOC_FINAL * 100,
        CONF_EMHASS_FALLBACK_LOAD: DEFAULT_EMHASS_FALLBACK_LOAD,
        CONF_P_BATT_ENTITY: DEFAULT_P_BATT_ENTITY,
        CONF_P_GRID_ENTITY: DEFAULT_P_GRID_ENTITY,
        CONF_OPTIM_STATUS_ENTITY: DEFAULT_OPTIM_STATUS_ENTITY,
        CONF_OPTIM_REQUIRED_STATE: DEFAULT_OPTIM_REQUIRED_STATE,
        CONF_USE_NORDPOOL_PRICES: DEFAULT_USE_NORDPOOL_PRICES,
        CONF_OPTIMIZE_ON_TOMORROW_PRICES: DEFAULT_OPTIMIZE_ON_TOMORROW_PRICES,
        CONF_NORDPOOL_AREA: DEFAULT_NORDPOOL_AREA,
        CONF_NORDPOOL_CURRENCY: DEFAULT_NORDPOOL_CURRENCY,
        CONF_BUY_PRICE_ADDER: DEFAULT_BUY_PRICE_ADDER,
        CONF_SELL_PRICE_DEDUCTION: DEFAULT_SELL_PRICE_DEDUCTION,
    }


def _resolve_required_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> tuple[dict[str, str], list[str]]:
    """Resolve canonical entities, treating PV as optional until EMHASS enables it."""
    registry = er.async_get(hass)
    entity_ids: dict[str, str] = {}
    missing: list[str] = []
    for purpose, key in ENTITY_KEYS.items():
        entity_id = registry.async_get_entity_id(
            "sensor", DOMAIN, f"{entry.entry_id}_{key}"
        )
        if entity_id:
            entity_ids[purpose] = entity_id
        elif purpose in REQUIRED_ENTITY_PURPOSES:
            missing.append(key)
    return entity_ids, missing


def _payload_from_config(
    entry: ConfigEntry,
    config: dict[str, Any],
    entity_ids: dict[str, str],
    *,
    error: str | None = None,
) -> dict[str, Any]:
    synced, warnings = build_emhass_sync_config(config, entity_ids)
    changes = emhass_sync_changes(config, synced)
    managed_keys = (
        "sensor_power_photovoltaics",
        "sensor_power_load_no_var_loads",
        "sensor_power_battery",
        "sensor_battery_state_of_charge",
        "sensor_power_photovoltaics_forecast",
        "sensor_replace_zero",
        "sensor_linear_interp",
        "var_model",
        "continual_publish",
        "method_ts_round",
        "set_use_battery",
        "inverter_is_hybrid",
    )
    return {
        "entry_id": entry.entry_id,
        "available": error is None,
        "synchronized": error is None and not changes,
        "recommended_options": _recommended_emhass_options(),
        "energy_entities": entity_ids,
        "managed_values": [
            {
                "key": key,
                "current": config.get(key),
                "required": synced.get(key),
                "synchronized": config.get(key) == synced.get(key),
            }
            for key in managed_keys
        ],
        "changes": changes,
        "warnings": warnings,
        "error": error,
    }


async def _async_get_payload(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    entity_ids, missing = _resolve_required_entities(hass, entry)
    base = {
        "entry_id": entry.entry_id,
        "available": False,
        "synchronized": False,
        "recommended_options": _recommended_emhass_options(),
        "energy_entities": entity_ids,
        "managed_values": [],
        "changes": [],
        "warnings": [],
        "error": None,
    }
    if missing:
        base["error"] = (
            "Required EnergyPilot entities are not registered yet: "
            + ", ".join(missing)
        )
        return base
    try:
        config = await async_get_emhass_config(hass, entry)
        return _payload_from_config(entry, config, entity_ids)
    except (HomeAssistantError, ValueError) as err:
        base["error"] = str(err)
        return base


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "gw_energypilot/emhass_sync/get",
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def websocket_get_emhass_sync(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    entry = _resolve_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(
            msg["id"], "not_found", "GW EnergyPilot config entry not found"
        )
        return
    connection.send_result(msg["id"], await _async_get_payload(hass, entry))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "gw_energypilot/emhass_sync/apply",
        vol.Required("entry_id"): str,
    }
)
@websocket_api.async_response
async def websocket_apply_emhass_sync(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    entry = _resolve_entry(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(
            msg["id"], "not_found", "GW EnergyPilot config entry not found"
        )
        return
    entity_ids, missing = _resolve_required_entities(hass, entry)
    if missing:
        connection.send_error(
            msg["id"],
            "entities_not_ready",
            "Required EnergyPilot entities are not registered yet: "
            + ", ".join(missing),
        )
        return
    try:
        current = await async_get_emhass_config(hass, entry)
        synced, warnings = build_emhass_sync_config(current, entity_ids)
        requested_changes = emhass_sync_changes(current, synced)
        if requested_changes:
            await async_write_emhass_config(hass, entry, synced)
        verified = await async_get_emhass_config(hass, entry)
        payload = _payload_from_config(entry, verified, entity_ids)
        payload["applied_changes"] = requested_changes
        payload["warnings"] = list(
            dict.fromkeys([*warnings, *payload["warnings"]])
        )
    except (HomeAssistantError, ValueError) as err:
        connection.send_error(msg["id"], "sync_failed", str(err))
        return
    if not payload["synchronized"]:
        connection.send_error(
            msg["id"],
            "verification_failed",
            "EMHASS accepted the configuration write but required values did not verify",
        )
        return
    connection.send_result(msg["id"], payload)


@callback
def async_register_emhass_sync_api(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, websocket_get_emhass_sync)
    websocket_api.async_register_command(hass, websocket_apply_emhass_sync)
