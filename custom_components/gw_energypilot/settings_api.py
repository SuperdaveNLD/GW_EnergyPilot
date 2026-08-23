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
    CONF_SCAN_INTERVAL,
    CONF_SELL_PRICE_DEDUCTION,
    CONF_SLAVE,
    CONF_USE_NORDPOOL_PRICES,
    DEFAULT_PORT,
    DEFAULT_SLAVE,
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
    CONF_OPTIM_STATUS_ENTITY,
    CONF_OPTIM_REQUIRED_STATE,
    CONF_USE_NORDPOOL_PRICES,
    CONF_OPTIMIZE_ON_TOMORROW_PRICES,
    CONF_NORDPOOL_AREA,
    CONF_NORDPOOL_CURRENCY,
    CONF_BUY_PRICE_ADDER,
    CONF_SELL_PRICE_DEDUCTION,
}

GOODWE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): vol.All(str, vol.Strip, vol.Length(min=1)),
        vol.Required(CONF_PORT): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
        vol.Required(CONF_SLAVE): vol.All(vol.Coerce(int), vol.Range(min=1, max=247)),
    },
    extra=vol.PREVENT_EXTRA,
)


def _field(
    key: str,
    label: str,
    field_type: str,
    value: Any,
    *,
    description: str = "",
    unit: str | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    step: float | None = None,
    readonly: bool = False,
) -> dict[str, Any]:
    """Build one frontend-neutral field description."""
    result: dict[str, Any] = {
        "key": key,
        "label": label,
        "type": field_type,
        "value": value,
        "description": description,
        "readonly": readonly,
    }
    if unit is not None:
        result["unit"] = unit
    if minimum is not None:
        result["min"] = minimum
    if maximum is not None:
        result["max"] = maximum
    if step is not None:
        result["step"] = step
    return result


def _option_fields(entry: ConfigEntry) -> dict[str, list[dict[str, Any]]]:
    """Return settings fields backed by the existing config entry options."""
    options = _options_for_form(dict(entry.options))

    energypilot = [
        _field(
            CONF_MAX_POWER_KW,
            "Maximum control power",
            "number",
            options.get(CONF_MAX_POWER_KW),
            unit="kW",
            minimum=0.5,
            maximum=15,
            step=0.1,
            description="Maximum power EnergyPilot may request from the GoodWe EMS controller.",
        ),
        _field(
            CONF_DEADBAND,
            "Battery deadband",
            "number",
            options.get(CONF_DEADBAND, 300),
            unit="W",
            minimum=0,
            maximum=2000,
            step=50,
            description="P_batt values inside this band hold the battery around zero watts.",
        ),
        _field(
            CONF_SCAN_INTERVAL,
            "GoodWe telemetry refresh",
            "number",
            options.get(CONF_SCAN_INTERVAL, 10),
            unit="s",
            minimum=5,
            maximum=60,
            step=1,
            description="Polling cadence for local GoodWe Modbus telemetry.",
        ),
        _field(
            CONF_ENABLE_EV_COORDINATION,
            "EV coordination",
            "boolean",
            bool(options.get(CONF_ENABLE_EV_COORDINATION, False)),
            description="Re-optimize after a configured EV charging session ends.",
        ),
        _field(
            CONF_EV_MODE_ENTITY,
            "EV mode entity",
            "text",
            options.get(CONF_EV_MODE_ENTITY, ""),
            description="Optional Home Assistant entity used to determine EV charging state.",
        ),
        _field(
            CONF_EV_POWER_ENTITY,
            "EV power entity",
            "text",
            options.get(CONF_EV_POWER_ENTITY, ""),
            description="Optional Home Assistant power entity for EV coordination.",
        ),
        _field(
            CONF_EV_DEADBAND,
            "EV active threshold",
            "number",
            options.get(CONF_EV_DEADBAND, 500),
            unit="W",
            minimum=0,
            maximum=3000,
            step=50,
            description="Power threshold used when determining whether EV charging is active.",
        ),
    ]

    emhass = [
        _field(
            CONF_ENABLE_EMHASS_ORCHESTRATOR,
            "Native EMHASS orchestrator",
            "boolean",
            bool(options.get(CONF_ENABLE_EMHASS_ORCHESTRATOR, True)),
            description="Let EnergyPilot schedule and publish EMHASS optimizations.",
        ),
        _field(
            CONF_EMHASS_URL,
            "EMHASS URL",
            "text",
            options.get(CONF_EMHASS_URL, ""),
            description="Address Home Assistant Core uses to reach the EMHASS web server.",
        ),
        _field(
            CONF_EMHASS_OPTIMIZATION_INTERVAL,
            "Optimization interval",
            "number",
            options.get(CONF_EMHASS_OPTIMIZATION_INTERVAL, 60),
            unit="min",
            minimum=5,
            maximum=60,
            step=5,
            description="Periodic optimization cadence; event triggers can still run immediately.",
        ),
        _field(
            CONF_EMHASS_SOC_FINAL_PCT,
            "Target final SOC",
            "number",
            options.get(CONF_EMHASS_SOC_FINAL_PCT),
            unit="%",
            minimum=0,
            maximum=100,
            step=1,
            description="Final SOC target sent to EMHASS for the optimization horizon.",
        ),
        _field(
            CONF_EMHASS_FALLBACK_LOAD,
            "Fallback load",
            "number",
            options.get(CONF_EMHASS_FALLBACK_LOAD, 700),
            unit="W",
            minimum=100,
            maximum=20000,
            step=50,
            description="Used when a valid current/history load value is unavailable.",
        ),
        _field(
            CONF_P_BATT_ENTITY,
            "P_batt output entity",
            "text",
            options.get(CONF_P_BATT_ENTITY, "sensor.p_batt_forecast"),
            description="Published EMHASS battery-power target used by Automatic Control.",
        ),
        _field(
            CONF_OPTIM_STATUS_ENTITY,
            "Optimization status entity",
            "text",
            options.get(CONF_OPTIM_STATUS_ENTITY, "sensor.optim_status"),
        ),
        _field(
            CONF_OPTIM_REQUIRED_STATE,
            "Required optimization state",
            "text",
            options.get(CONF_OPTIM_REQUIRED_STATE, "Optimal"),
        ),
        _field(
            CONF_USE_NORDPOOL_PRICES,
            "Use Nord Pool runtime prices",
            "boolean",
            bool(options.get(CONF_USE_NORDPOOL_PRICES, True)),
            description="Use Home Assistant Nord Pool prices instead of only EMHASS price configuration.",
        ),
        _field(
            CONF_OPTIMIZE_ON_TOMORROW_PRICES,
            "Optimize when tomorrow prices arrive",
            "boolean",
            bool(options.get(CONF_OPTIMIZE_ON_TOMORROW_PRICES, True)),
        ),
        _field(
            CONF_NORDPOOL_AREA,
            "Nord Pool area",
            "text",
            options.get(CONF_NORDPOOL_AREA, ""),
            description="Optional area override; leave empty to use the available configured source.",
        ),
        _field(
            CONF_NORDPOOL_CURRENCY,
            "Nord Pool currency",
            "text",
            options.get(CONF_NORDPOOL_CURRENCY, "EUR"),
        ),
        _field(
            CONF_BUY_PRICE_ADDER,
            "Import price adder",
            "number",
            options.get(CONF_BUY_PRICE_ADDER, 0.0),
            unit="EUR/kWh",
            minimum=-1,
            maximum=2,
            step=0.001,
        ),
        _field(
            CONF_SELL_PRICE_DEDUCTION,
            "Export price deduction",
            "number",
            options.get(CONF_SELL_PRICE_DEDUCTION, 0.0248),
            unit="EUR/kWh",
            minimum=-1,
            maximum=2,
            step=0.001,
        ),
    ]
    return {SECTION_ENERGYPILOT: energypilot, SECTION_EMHASS: emhass}


def _settings_payload(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return all settings required by the dedicated frontend pages."""
    option_fields = _option_fields(entry)
    goodwe = [
        _field(
            "hardware_target",
            "Validated hardware target",
            "text",
            "GoodWe GW15K-ETA-G20 / ETA-G20 generation",
            readonly=True,
            description="EnergyPilot is developed and validated primarily against the GoodWe ETA-G20 generation.",
        ),
        _field(
            CONF_HOST,
            "Inverter host",
            "text",
            str(entry.data.get(CONF_HOST, "")),
            description="Local IP address or resolvable hostname of the inverter.",
        ),
        _field(
            CONF_PORT,
            "Modbus TCP port",
            "number",
            int(entry.data.get(CONF_PORT, DEFAULT_PORT)),
            minimum=1,
            maximum=65535,
            step=1,
        ),
        _field(
            CONF_SLAVE,
            "Modbus unit ID",
            "number",
            int(entry.data.get(CONF_SLAVE, DEFAULT_SLAVE)),
            minimum=1,
            maximum=247,
            step=1,
        ),
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
                "fields": option_fields[SECTION_ENERGYPILOT],
            },
            SECTION_EMHASS: {
                "title": "EMHASS",
                "short_title": "EMHASS",
                "description": "Connection, orchestration, output entities and runtime price integration.",
                "fields": option_fields[SECTION_EMHASS],
            },
            SECTION_GOODWE: {
                "title": "GoodWe",
                "short_title": "GOODWE",
                "description": "Local Modbus TCP connection. Changes are validated against the inverter before saving.",
                "fields": goodwe,
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
        connection.send_error(msg["id"], "not_found", "GW EnergyPilot config entry not found")
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
        connection.send_error(msg["id"], "not_found", "GW EnergyPilot config entry not found")
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
                "cannot_connect" if isinstance(err, CannotConnect) else "invalid_settings",
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
                if candidate.entry_id != entry.entry_id and candidate.unique_id == unique_id
            ),
            None,
        )
        if duplicate is not None:
            connection.send_error(
                msg["id"], "already_configured", "That GoodWe host and unit ID are already configured"
            )
            return

        new_data = dict(entry.data)
        new_data.update(
            {
                CONF_HOST: host,
                CONF_PORT: port,
                CONF_SLAVE: slave,
            }
        )
        hass.config_entries.async_update_entry(
            entry,
            data=new_data,
            unique_id=unique_id,
            title=f"{NAME} ({host})",
        )
    else:
        allowed = ENERGYPILOT_KEYS if section == SECTION_ENERGYPILOT else EMHASS_KEYS
        unknown = set(values) - allowed
        if unknown:
            connection.send_error(
                msg["id"],
                "invalid_settings",
                f"Unsupported {section} settings: {', '.join(sorted(unknown))}",
            )
            return

        form_values = _options_for_form(dict(entry.options))
        form_values.update(values)
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
