"""WebSocket settings API for the GW EnergyPilot dashboard."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry, OperationNotAllowed
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback

from .config_flow import (
    CONF_EMHASS_SOC_FINAL_PCT,
    CONF_MAX_POWER_KW,
    CannotConnect,
    _async_validate_connection,
    _controller_schema,
    _options_for_form,
    _options_from_form,
)
from .const import (
    CONF_BATTERY_SAVER_MODE,
    CONF_BUY_PRICE_ADDER,
    CONF_DEADBAND,
    CONF_EMHASS_FALLBACK_LOAD,
    CONF_EMHASS_OPTIMIZATION_INTERVAL,
    CONF_EMHASS_URL,
    CONF_ENABLE_EMHASS_ORCHESTRATOR,
    CONF_ENABLE_EV_COORDINATION,
    CONF_EV_DEADBAND,
    CONF_EV_MODE_ENTITY,
    CONF_EV_POWER_ENTITY,
    CONF_NORDPOOL_AREA,
    CONF_NORDPOOL_CURRENCY,
    CONF_OPTIMIZE_ON_TOMORROW_PRICES,
    CONF_OPTIM_REQUIRED_STATE,
    CONF_OPTIM_STATUS_ENTITY,
    CONF_P_BATT_ENTITY,
    CONF_P_GRID_ENTITY,
    CONF_SCAN_INTERVAL,
    CONF_SELL_PRICE_DEDUCTION,
    CONF_SLAVE,
    CONF_USE_NORDPOOL_PRICES,
    DEFAULT_BUY_PRICE_ADDER,
    DEFAULT_DEADBAND,
    DEFAULT_EMHASS_FALLBACK_LOAD,
    DEFAULT_EMHASS_OPTIMIZATION_INTERVAL,
    DEFAULT_EMHASS_SOC_FINAL,
    DEFAULT_EMHASS_URL,
    DEFAULT_EV_DEADBAND,
    DEFAULT_MAX_POWER,
    DEFAULT_NORDPOOL_AREA,
    DEFAULT_NORDPOOL_CURRENCY,
    DEFAULT_OPTIMIZE_ON_TOMORROW_PRICES,
    DEFAULT_OPTIM_REQUIRED_STATE,
    DEFAULT_OPTIM_STATUS_ENTITY,
    DEFAULT_P_BATT_ENTITY,
    DEFAULT_P_GRID_ENTITY,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SELL_PRICE_DEDUCTION,
    DEFAULT_SLAVE,
    DEFAULT_USE_NORDPOOL_PRICES,
    DOMAIN,
    NAME,
)

SECTION_ENERGYPILOT = "energypilot"
SECTION_EMHASS = "emhass"
SECTION_GOODWE = "goodwe"

ENERGYPILOT_KEYS = {
    CONF_MAX_POWER_KW,
    CONF_DEADBAND,
    CONF_SCAN_INTERVAL,
    CONF_ENABLE_EV_COORDINATION,
    CONF_EV_MODE_ENTITY,
    CONF_EV_POWER_ENTITY,
    CONF_EV_DEADBAND,
}
EMHASS_KEYS = {
    CONF_ENABLE_EMHASS_ORCHESTRATOR,
    CONF_EMHASS_URL,
    CONF_EMHASS_OPTIMIZATION_INTERVAL,
    CONF_EMHASS_SOC_FINAL_PCT,
    CONF_EMHASS_FALLBACK_LOAD,
    CONF_P_BATT_ENTITY,
    CONF_P_GRID_ENTITY,
    CONF_OPTIM_STATUS_ENTITY,
    CONF_OPTIM_REQUIRED_STATE,
    CONF_USE_NORDPOOL_PRICES,
    CONF_OPTIMIZE_ON_TOMORROW_PRICES,
    CONF_NORDPOOL_AREA,
    CONF_NORDPOOL_CURRENCY,
    CONF_BUY_PRICE_ADDER,
    CONF_SELL_PRICE_DEDUCTION,
}
OPTIONAL_ENTITY_KEYS = {CONF_EV_MODE_ENTITY, CONF_EV_POWER_ENTITY}

GOODWE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): vol.All(str, str.strip, vol.Length(min=1)),
        vol.Required(CONF_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Required(CONF_SLAVE): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=247)
        ),
    },
    extra=vol.PREVENT_EXTRA,
)

EP_FIELD_SPECS: tuple[dict[str, Any], ...] = (
    {
        "key": CONF_MAX_POWER_KW,
        "label": "Maximum control power",
        "type": "number",
        "default": DEFAULT_MAX_POWER / 1000,
        "unit": "kW",
        "min": 0.5,
        "max": 15,
        "step": 0.1,
        "description": "Maximum power EnergyPilot may request from the GoodWe EMS controller.",
    },
    {
        "key": CONF_DEADBAND,
        "label": "Battery deadband",
        "type": "number",
        "default": DEFAULT_DEADBAND,
        "unit": "W",
        "min": 0,
        "max": 2000,
        "step": 50,
        "description": "P_batt values inside this band hold the battery around zero watts.",
    },
    {
        "key": CONF_SCAN_INTERVAL,
        "label": "GoodWe telemetry refresh",
        "type": "number",
        "default": DEFAULT_SCAN_INTERVAL,
        "unit": "s",
        "min": 5,
        "max": 60,
        "step": 1,
        "description": "Polling cadence for local GoodWe Modbus telemetry.",
    },
    {
        "key": CONF_ENABLE_EV_COORDINATION,
        "label": "EV coordination",
        "type": "boolean",
        "default": False,
        "description": "Re-optimize after a configured EV charging session ends.",
    },
    {
        "key": CONF_EV_MODE_ENTITY,
        "label": "EV mode entity",
        "type": "text",
        "default": "",
        "description": "Optional Home Assistant entity used to determine EV charging state.",
    },
    {
        "key": CONF_EV_POWER_ENTITY,
        "label": "EV power entity",
        "type": "text",
        "default": "",
        "description": "Optional Home Assistant power entity for EV coordination.",
    },
    {
        "key": CONF_EV_DEADBAND,
        "label": "EV active threshold",
        "type": "number",
        "default": DEFAULT_EV_DEADBAND,
        "unit": "W",
        "min": 0,
        "max": 3000,
        "step": 50,
        "description": "Power threshold used when determining whether EV charging is active.",
    },
)

EMHASS_FIELD_SPECS: tuple[dict[str, Any], ...] = (
    {
        "key": CONF_ENABLE_EMHASS_ORCHESTRATOR,
        "label": "Native EMHASS orchestrator",
        "type": "boolean",
        "default": True,
        "description": "Let EnergyPilot schedule and publish EMHASS optimizations.",
    },
    {
        "key": CONF_EMHASS_URL,
        "label": "EMHASS URL",
        "type": "text",
        "default": DEFAULT_EMHASS_URL,
        "description": "Address Home Assistant Core uses to reach the EMHASS web server.",
    },
    {
        "key": CONF_EMHASS_OPTIMIZATION_INTERVAL,
        "label": "Optimization interval",
        "type": "number",
        "default": DEFAULT_EMHASS_OPTIMIZATION_INTERVAL,
        "unit": "min",
        "min": 5,
        "max": 60,
        "step": 5,
        "description": "Periodic cadence; event triggers can still optimize immediately.",
    },
    {
        "key": CONF_EMHASS_SOC_FINAL_PCT,
        "label": "Target final SOC",
        "type": "number",
        "default": DEFAULT_EMHASS_SOC_FINAL * 100,
        "unit": "%",
        "min": 0,
        "max": 100,
        "step": 1,
        "description": "Final SOC target sent to EMHASS for the optimization horizon.",
    },
    {
        "key": CONF_EMHASS_FALLBACK_LOAD,
        "label": "Fallback load",
        "type": "number",
        "default": DEFAULT_EMHASS_FALLBACK_LOAD,
        "unit": "W",
        "min": 100,
        "max": 20000,
        "step": 50,
        "description": "Used when a valid current/history load value is unavailable.",
    },
    {
        "key": CONF_P_BATT_ENTITY,
        "label": "P_batt output entity",
        "type": "text",
        "default": DEFAULT_P_BATT_ENTITY,
        "description": "Published battery-power target. It remains the direction and maximum battery-power request used by Automatic Control.",
    },
    {
        "key": CONF_P_GRID_ENTITY,
        "label": "P_grid output entity",
        "type": "text",
        "default": DEFAULT_P_GRID_ENTITY,
        "description": "Published EMHASS grid target. During charging, a target around 0 W activates live smart-meter limiting so forecast errors do not become unintended grid charging.",
    },
    {
        "key": CONF_OPTIM_STATUS_ENTITY,
        "label": "Optimization status entity",
        "type": "text",
        "default": DEFAULT_OPTIM_STATUS_ENTITY,
    },
    {
        "key": CONF_OPTIM_REQUIRED_STATE,
        "label": "Required optimization state",
        "type": "text",
        "default": DEFAULT_OPTIM_REQUIRED_STATE,
    },
    {
        "key": CONF_USE_NORDPOOL_PRICES,
        "label": "Use Nord Pool runtime prices",
        "type": "boolean",
        "default": DEFAULT_USE_NORDPOOL_PRICES,
        "description": "Use Home Assistant Nord Pool prices for EMHASS runtime forecasts.",
    },
    {
        "key": CONF_OPTIMIZE_ON_TOMORROW_PRICES,
        "label": "Optimize when tomorrow prices arrive",
        "type": "boolean",
        "default": DEFAULT_OPTIMIZE_ON_TOMORROW_PRICES,
    },
    {
        "key": CONF_NORDPOOL_AREA,
        "label": "Nord Pool area",
        "type": "text",
        "default": DEFAULT_NORDPOOL_AREA,
        "description": "Optional override; leave empty to use the configured source.",
    },
    {
        "key": CONF_NORDPOOL_CURRENCY,
        "label": "Nord Pool currency",
        "type": "text",
        "default": DEFAULT_NORDPOOL_CURRENCY,
    },
    {
        "key": CONF_BUY_PRICE_ADDER,
        "label": "Import price adder",
        "type": "number",
        "default": DEFAULT_BUY_PRICE_ADDER,
        "unit": "EUR/kWh",
        "min": -1,
        "max": 2,
        "step": 0.001,
    },
    {
        "key": CONF_SELL_PRICE_DEDUCTION,
        "label": "Export price deduction",
        "type": "number",
        "default": DEFAULT_SELL_PRICE_DEDUCTION,
        "unit": "EUR/kWh",
        "min": -1,
        "max": 2,
        "step": 0.001,
    },
)


def _fields_from_specs(
    options: dict[str, Any], specs: tuple[dict[str, Any], ...]
) -> list[dict[str, Any]]:
    """Combine frontend field metadata with current config-entry values."""
    fields: list[dict[str, Any]] = []
    for spec in specs:
        field = {key: value for key, value in spec.items() if key != "default"}
        field["value"] = options.get(spec["key"], spec.get("default"))
        field["readonly"] = False
        fields.append(field)
    return fields


def _settings_payload(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return all settings required by the dedicated frontend pages."""
    options = _options_for_form(dict(entry.options))
    goodwe_fields = [
        {
            "key": "hardware_target",
            "label": "Validated hardware target",
            "type": "text",
            "value": "GoodWe GW15K-ETA-G20 / ETA-G20 generation",
            "description": (
                "EnergyPilot is developed and validated primarily against the "
                "GoodWe ETA-G20 generation."
            ),
            "readonly": True,
        },
        {
            "key": CONF_HOST,
            "label": "Inverter host",
            "type": "text",
            "value": str(entry.data.get(CONF_HOST, "")),
            "description": "Local IP address or resolvable hostname of the inverter.",
            "readonly": False,
        },
        {
            "key": CONF_PORT,
            "label": "Modbus TCP port",
            "type": "number",
            "value": int(entry.data.get(CONF_PORT, DEFAULT_PORT)),
            "min": 1,
            "max": 65535,
            "step": 1,
            "readonly": False,
        },
        {
            "key": CONF_SLAVE,
            "label": "Modbus unit ID",
            "type": "number",
            "value": int(entry.data.get(CONF_SLAVE, DEFAULT_SLAVE)),
            "min": 1,
            "max": 247,
            "step": 1,
            "readonly": False,
        },
    ]

    return {
        "entry_id": entry.entry_id,
        "entries": [
            {
                "entry_id": candidate.entry_id,
                "title": candidate.title,
                "state": candidate.state.value,
            }
            for candidate in hass.config_entries.async_entries(DOMAIN)
        ],
        "sections": {
            SECTION_ENERGYPILOT: {
                "title": "EnergyPilot",
                "short_title": "EP",
                "description": "Controller, telemetry and optional EV coordination.",
                "fields": _fields_from_specs(options, EP_FIELD_SPECS),
            },
            SECTION_EMHASS: {
                "title": "EMHASS",
                "short_title": "EMHASS",
                "description": (
                    "Connection, orchestration, output entities and runtime price "
                    "integration."
                ),
                "fields": _fields_from_specs(options, EMHASS_FIELD_SPECS),
            },
            SECTION_GOODWE: {
                "title": "GoodWe",
                "short_title": "GOODWE",
                "description": (
                    "Local Modbus TCP connection. Changes are validated against the "
                    "inverter before saving."
                ),
                "fields": goodwe_fields,
            },
        },
    }


def _resolve_entry(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry | None:
    """Resolve an EnergyPilot config entry, defaulting to the first entry."""
    if entry_id:
        entry = hass.config_entries.async_get_entry(entry_id)
        return entry if entry and entry.domain == DOMAIN else None
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Reload an updated entry and return whether a restart is required."""
    try:
        success = await hass.config_entries.async_reload(entry.entry_id)
    except OperationNotAllowed:
        return True
    return not success


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "gw_energypilot/settings/get",
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def websocket_get_settings(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the current EnergyPilot settings model."""
    entry = _resolve_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(
            msg["id"], "not_found", "GW EnergyPilot config entry not found"
        )
        return
    connection.send_result(msg["id"], _settings_payload(hass, entry))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "gw_energypilot/settings/update",
        vol.Required("entry_id"): str,
        vol.Required("section"): vol.In(
            [SECTION_ENERGYPILOT, SECTION_EMHASS, SECTION_GOODWE]
        ),
        vol.Required("values"): dict,
    }
)
@websocket_api.async_response
async def websocket_update_settings(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Validate, save and reload one dedicated settings section."""
    entry = _resolve_entry(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(
            msg["id"], "not_found", "GW EnergyPilot config entry not found"
        )
        return

    section = msg["section"]
    values = dict(msg["values"])

    if section == SECTION_GOODWE:
        try:
            validated = GOODWE_SCHEMA(values)
            host = validated[CONF_HOST]
            port = validated[CONF_PORT]
            slave = validated[CONF_SLAVE]
            await _async_validate_connection(host, port, slave)
        except (vol.Invalid, CannotConnect) as err:
            connection.send_error(
                msg["id"],
                "cannot_connect"
                if isinstance(err, CannotConnect)
                else "invalid_settings",
                "Unable to validate the GoodWe Modbus connection"
                if isinstance(err, CannotConnect)
                else str(err),
            )
            return

        unique_id = f"{host}:{slave}"
        duplicate = next(
            (
                candidate
                for candidate in hass.config_entries.async_entries(DOMAIN)
                if candidate.entry_id != entry.entry_id
                and candidate.unique_id == unique_id
            ),
            None,
        )
        if duplicate is not None:
            connection.send_error(
                msg["id"],
                "already_configured",
                "That GoodWe host and unit ID are already configured",
            )
            return

        new_data = dict(entry.data)
        new_data.update(
            {CONF_HOST: host, CONF_PORT: port, CONF_SLAVE: slave}
        )
        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            unique_id=unique_id,
            title=f"{NAME} ({host})",
        )
    else:
        allowed = (
            ENERGYPILOT_KEYS if section == SECTION_ENERGYPILOT else EMHASS_KEYS
        )
        unknown = set(values) - allowed
        if unknown:
            connection.send_error(
                msg["id"],
                "invalid_settings",
                f"Unsupported {section} settings: {', '.join(sorted(unknown))}",
            )
            return

        form_values = _options_for_form(dict(entry.options))
        # Battery Saver is managed by its dedicated control, not by this generic
        # form schema. Remove it before validation and restore it after converting
        # the regular form values back to config-entry options.
        form_values.pop(CONF_BATTERY_SAVER_MODE, None)
        form_values.update(values)
        for key in OPTIONAL_ENTITY_KEYS:
            if form_values.get(key) in (None, ""):
                form_values.pop(key, None)

        try:
            validated = _controller_schema(
                orchestrator_default=bool(
                    form_values.get(CONF_ENABLE_EMHASS_ORCHESTRATOR, True)
                )
            )(form_values)
            stored_options = _options_from_form(validated)
        except (vol.Invalid, TypeError, ValueError) as err:
            connection.send_error(msg["id"], "invalid_settings", str(err))
            return
        if CONF_BATTERY_SAVER_MODE in entry.options:
            stored_options[CONF_BATTERY_SAVER_MODE] = entry.options[
                CONF_BATTERY_SAVER_MODE
            ]
        hass.config_entries.async_update_entry(entry, options=stored_options)

    require_restart = await _async_reload_entry(hass, entry)
    refreshed = hass.config_entries.async_get_entry(entry.entry_id) or entry
    connection.send_result(
        msg["id"],
        {
            "require_restart": require_restart,
            "settings": _settings_payload(hass, refreshed),
        },
    )


@callback
def async_register_settings_api(hass: HomeAssistant) -> None:
    """Register EnergyPilot settings WebSocket commands once."""
    websocket_api.async_register_command(hass, websocket_get_settings)
    websocket_api.async_register_command(hass, websocket_update_settings)
