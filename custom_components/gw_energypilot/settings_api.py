"""WebSocket settings API for the GW EnergyPilot dashboard."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry, OperationNotAllowed
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .config_flow import (
    CONF_EMHASS_SOC_FINAL_PCT,
    CONF_MAX_POWER_KW,
    CannotConnect,
    _async_validate_connection,
    _controller_schema,
    _optimization_interval_options,
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
    CONF_ENABLE_EV_LOAD_BALANCING,
    CONF_ENABLE_EXTERNAL_PV,
    CONF_ENABLE_INTERNAL_PV,
    CONF_EV_DEADBAND,
    CONF_EV_CHARGER_CURRENT_ENTITY,
    CONF_EV_CHARGER_MAX_CURRENT,
    CONF_EV_CHARGER_MIN_CURRENT,
    CONF_EV_GRID_CURRENT_ENTITY,
    CONF_EV_LOAD_BALANCE_WINDOW,
    CONF_EV_MODE_ENTITY,
    CONF_EV_ONLINE_ENTITY,
    CONF_EV_POWER_ENTITY,
    CONF_GRID_CONNECTION_PROFILE,
    CONF_GRID_CUSTOM_CURRENT,
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
    DEFAULT_ENABLE_EXTERNAL_PV,
    DEFAULT_ENABLE_INTERNAL_PV,
    DEFAULT_EV_DEADBAND,
    DEFAULT_ENABLE_EV_LOAD_BALANCING,
    DEFAULT_EV_CHARGER_MAX_CURRENT,
    DEFAULT_EV_CHARGER_MIN_CURRENT,
    DEFAULT_EV_LOAD_BALANCE_WINDOW,
    DEFAULT_GRID_CONNECTION_PROFILE,
    DEFAULT_GRID_CUSTOM_CURRENT,
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
    EMHASS_OPTIMIZATION_INTERVALS,
    EXTERNAL_PV_ENTITY_KEYS,
    EV_LOAD_BALANCE_WINDOW_OPTIONS,
    GRID_CONNECTION_CUSTOM_PROFILES,
    GRID_CONNECTION_PROFILES,
    NAME,
)
from .ev_load_balancing import EVLoadBalancingAudit, high_current_audit_record
from .pv_insight import external_sources_enabled

SECTION_ENERGYPILOT = "energypilot"
SECTION_EMHASS = "emhass"
SECTION_EV = "ev"
SECTION_GOODWE = "goodwe"
SECTION_PV = "pv"

ENERGYPILOT_KEYS = {
    CONF_MAX_POWER_KW,
    CONF_DEADBAND,
    CONF_SCAN_INTERVAL,
}
EV_KEYS = {
    CONF_ENABLE_EV_COORDINATION,
    CONF_EV_MODE_ENTITY,
    CONF_EV_POWER_ENTITY,
    CONF_EV_DEADBAND,
    CONF_ENABLE_EV_LOAD_BALANCING,
    CONF_GRID_CONNECTION_PROFILE,
    CONF_GRID_CUSTOM_CURRENT,
    CONF_EV_GRID_CURRENT_ENTITY,
    CONF_EV_CHARGER_CURRENT_ENTITY,
    CONF_EV_CHARGER_MIN_CURRENT,
    CONF_EV_CHARGER_MAX_CURRENT,
    CONF_EV_LOAD_BALANCE_WINDOW,
}
EV_LOAD_BALANCING_KEYS = EV_KEYS - {
    CONF_ENABLE_EV_COORDINATION,
    CONF_EV_MODE_ENTITY,
    CONF_EV_POWER_ENTITY,
    CONF_EV_ONLINE_ENTITY,
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
OPTIONAL_ENTITY_KEYS = {
    CONF_EV_MODE_ENTITY,
    CONF_EV_POWER_ENTITY,
    CONF_EV_ONLINE_ENTITY,
}
PV_KEYS = {
    CONF_ENABLE_INTERNAL_PV,
    CONF_ENABLE_EXTERNAL_PV,
    *EXTERNAL_PV_ENTITY_KEYS,
}

PV_ENTITY_ID = vol.All(
    str,
    str.strip,
    vol.Match(r"^[a-z0-9_]+\.[a-z0-9_]+$"),
)
PV_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_ENABLE_INTERNAL_PV,
            default=DEFAULT_ENABLE_INTERNAL_PV,
        ): bool,
        vol.Required(
            CONF_ENABLE_EXTERNAL_PV,
            default=DEFAULT_ENABLE_EXTERNAL_PV,
        ): bool,
        **{vol.Optional(key): PV_ENTITY_ID for key in EXTERNAL_PV_ENTITY_KEYS},
    },
    extra=vol.PREVENT_EXTRA,
)

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

ENTITY_ID = vol.All(str, str.strip, vol.Match(r"^[a-z0-9_]+\.[a-z0-9_]+$"))
EV_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_ENABLE_EV_LOAD_BALANCING,
            default=DEFAULT_ENABLE_EV_LOAD_BALANCING,
        ): bool,
        vol.Required(
            CONF_GRID_CONNECTION_PROFILE,
            default=DEFAULT_GRID_CONNECTION_PROFILE,
        ): vol.In([*GRID_CONNECTION_PROFILES, *GRID_CONNECTION_CUSTOM_PROFILES]),
        vol.Required(
            CONF_GRID_CUSTOM_CURRENT, default=DEFAULT_GRID_CUSTOM_CURRENT
        ): vol.All(vol.Coerce(float), vol.Range(min=6, max=100)),
        vol.Optional(CONF_EV_GRID_CURRENT_ENTITY): vol.All(
            ENTITY_ID, vol.Match(r"^sensor\.")
        ),
        vol.Optional(CONF_EV_CHARGER_CURRENT_ENTITY): vol.All(
            ENTITY_ID, vol.Match(r"^number\.")
        ),
        vol.Required(
            CONF_EV_LOAD_BALANCE_WINDOW,
            default=DEFAULT_EV_LOAD_BALANCE_WINDOW,
        ): vol.All(vol.Coerce(int), vol.In(EV_LOAD_BALANCE_WINDOW_OPTIONS)),
        vol.Required(
            CONF_EV_CHARGER_MIN_CURRENT,
            default=DEFAULT_EV_CHARGER_MIN_CURRENT,
        ): vol.All(vol.Coerce(float), vol.Range(min=6, max=16)),
        vol.Required(
            CONF_EV_CHARGER_MAX_CURRENT,
            default=DEFAULT_EV_CHARGER_MAX_CURRENT,
        ): vol.All(vol.Coerce(float), vol.Range(min=6, max=32)),
        vol.Required(CONF_ENABLE_EV_COORDINATION, default=False): bool,
        vol.Optional(CONF_EV_MODE_ENTITY): ENTITY_ID,
        vol.Optional(CONF_EV_POWER_ENTITY): ENTITY_ID,
        vol.Required(CONF_EV_DEADBAND, default=DEFAULT_EV_DEADBAND): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=3000)
        ),
    },
    extra=vol.PREVENT_EXTRA,
)


def _validate_ev_values(values: dict[str, Any]) -> dict[str, Any]:
    """Validate the dedicated EV ownership and safety settings."""
    cleaned = {
        key: value
        for key, value in values.items()
        if key
        not in {
            CONF_EV_MODE_ENTITY,
            CONF_EV_POWER_ENTITY,
            CONF_EV_GRID_CURRENT_ENTITY,
            CONF_EV_CHARGER_CURRENT_ENTITY,
        }
        or value not in (None, "")
    }
    validated = dict(EV_SCHEMA(cleaned))
    if (
        validated[CONF_EV_CHARGER_MIN_CURRENT]
        > validated[CONF_EV_CHARGER_MAX_CURRENT]
    ):
        raise vol.Invalid(
            "Minimum charger current cannot exceed maximum charger current"
        )
    if validated[CONF_ENABLE_EV_LOAD_BALANCING]:
        if not validated.get(CONF_EV_GRID_CURRENT_ENTITY):
            raise vol.Invalid("A measured phase-current entity is required")
        if not validated.get(CONF_EV_CHARGER_CURRENT_ENTITY):
            raise vol.Invalid("A charger maximum-current number entity is required")
    return validated


def _validate_ev_entity_contract(hass: HomeAssistant, values: dict[str, Any]) -> None:
    """Reject known entities whose units/ranges do not match current control."""
    source = hass.states.get(values.get(CONF_EV_GRID_CURRENT_ENTITY, ""))
    if source is not None and source.attributes.get("unit_of_measurement") not in {
        "A",
        "mA",
    }:
        raise vol.Invalid("The measured phase-current entity must use A or mA")

    charger = hass.states.get(values.get(CONF_EV_CHARGER_CURRENT_ENTITY, ""))
    if charger is None:
        return
    if charger.attributes.get("unit_of_measurement") != "A":
        raise vol.Invalid("The charger maximum-current entity must use A")
    try:
        entity_minimum = float(charger.attributes["min"])
        entity_maximum = float(charger.attributes["max"])
    except (KeyError, TypeError, ValueError):
        raise vol.Invalid("The charger entity must expose numeric min and max values")
    if values[CONF_EV_CHARGER_MIN_CURRENT] < entity_minimum:
        raise vol.Invalid(
            f"Charger minimum cannot be below the entity minimum of {entity_minimum:g} A"
        )
    if values[CONF_EV_CHARGER_MAX_CURRENT] > entity_maximum:
        raise vol.Invalid(
            f"Charger maximum cannot exceed the entity maximum of {entity_maximum:g} A"
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
)

EV_FIELD_SPECS: tuple[dict[str, Any], ...] = (
    {
        "key": CONF_ENABLE_EV_LOAD_BALANCING,
        "label": "Load balancing for EV charger",
        "type": "boolean",
        "default": DEFAULT_ENABLE_EV_LOAD_BALANCING,
        "description": (
            "Adjust only the charger's current limit; GoodWe is never controlled "
            "by this regulator."
        ),
    },
    {
        "key": CONF_GRID_CONNECTION_PROFILE,
        "label": "House connection",
        "type": "select",
        "default": DEFAULT_GRID_CONNECTION_PROFILE,
        "options": [
            {"value": key, "label": key.replace("x", " × ") + " A"}
            for key in GRID_CONNECTION_PROFILES
        ] + [
            {"value": "custom_1_phase", "label": "Custom · 1 phase"},
            {"value": "custom_3_phase", "label": "Custom · 3 phase"},
        ],
        "description": "The selected ampere value is the limit for the measured phase.",
    },
    {
        "key": CONF_GRID_CUSTOM_CURRENT,
        "label": "Custom connection current",
        "type": "number",
        "default": DEFAULT_GRID_CUSTOM_CURRENT,
        "unit": "A / phase",
        "min": 6,
        "max": 100,
        "step": 1,
        "description": "Used only for a custom one-phase or three-phase connection.",
    },
    {
        "key": CONF_EV_GRID_CURRENT_ENTITY,
        "label": "Measured phase current",
        "type": "entity",
        "domains": ["sensor"],
        "units": ["A", "mA"],
        "default": "",
        "description": "Current measurement for the one phase that guards the connection.",
    },
    {
        "key": CONF_EV_CHARGER_CURRENT_ENTITY,
        "label": "Charger maximum-current control",
        "type": "entity",
        "domains": ["number"],
        "default": "",
        "description": (
            "One Home Assistant number entity that sets all three charger phases "
            "together."
        ),
    },
    {
        "key": CONF_EV_LOAD_BALANCE_WINDOW,
        "label": "Sustained condition window",
        "type": "select",
        "default": DEFAULT_EV_LOAD_BALANCE_WINDOW,
        "options": [
            {
                "value": value,
                "label": f"{value} min"
                + (" · recommended" if value == 5 else ""),
            }
            for value in EV_LOAD_BALANCE_WINDOW_OPTIONS
        ],
        "description": (
            "The overload or headroom must persist for this entire period before "
            "each adjustment."
        ),
    },
    {
        "key": CONF_EV_CHARGER_MIN_CURRENT,
        "label": "Minimum charger current",
        "type": "number",
        "default": DEFAULT_EV_CHARGER_MIN_CURRENT,
        "unit": "A",
        "min": 6,
        "max": 16,
        "step": 1,
        "description": "EnergyPilot never commands the charger below this boundary.",
    },
    {
        "key": CONF_EV_CHARGER_MAX_CURRENT,
        "label": "Maximum charger current",
        "type": "number",
        "default": DEFAULT_EV_CHARGER_MAX_CURRENT,
        "unit": "A",
        "min": 6,
        "max": 32,
        "step": 1,
        "description": (
            "16 A is the safe default. Higher values require an explicit audited "
            "acknowledgement."
        ),
    },
    {
        "key": CONF_ENABLE_EV_COORDINATION,
        "label": "EV battery coordination",
        "type": "boolean",
        "default": False,
        "description": (
            "Observe charging for battery anti-discharge and re-optimize after "
            "charging ends."
        ),
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
        "type": "entity",
        "domains": ["sensor"],
        "default": "",
        "description": "Optional Home Assistant power entity for EV coordination.",
    },
    {
        "key": CONF_EV_ONLINE_ENTITY,
        "label": "EV online entity",
        "type": "text",
        "default": "",
        "description": (
            "Optional Home Assistant entity whose availability reports whether "
            "the charger is reachable. Binary sensors use on/off explicitly."
        ),
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
        "type": "select",
        "default": str(DEFAULT_EMHASS_OPTIMIZATION_INTERVAL),
        "unit": "min",
        "options": [
            {"value": str(value), "label": f"{value} minutes"}
            for value in EMHASS_OPTIMIZATION_INTERVALS
        ],
        "description": (
            "Runs at matching local wall-clock boundaries plus 15 seconds; "
            "event triggers can still optimize immediately."
        ),
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

PV_FIELD_SPECS: tuple[dict[str, Any], ...] = (
    {
        "key": CONF_ENABLE_INTERNAL_PV,
        "label": "Include internal GoodWe PV",
        "type": "boolean",
        "default": DEFAULT_ENABLE_INTERNAL_PV,
        "description": (
            "Include the existing canonical GoodWe PV total in the dashboard PV "
            "total. This is display-only and does not affect EMS control."
        ),
    },
    {
        "key": CONF_ENABLE_EXTERNAL_PV,
        "label": "Include external PV",
        "type": "boolean",
        "default": DEFAULT_ENABLE_EXTERNAL_PV,
        "description": (
            "Include the configured external Home Assistant PV sources in the "
            "dashboard PV total. This is display-only."
        ),
    },
    *(
        {
            "key": key,
            "label": f"External PV source {index}",
            "type": "entity",
            "default": "",
            "description": (
                "Optional Home Assistant power entity with non-negative PV "
                "generation in W, kW or MW."
            ),
        }
        for index, key in enumerate(EXTERNAL_PV_ENTITY_KEYS, start=1)
    ),
)


def _fields_from_specs(
    options: dict[str, Any], specs: tuple[dict[str, Any], ...]
) -> list[dict[str, Any]]:
    """Combine frontend field metadata with current config-entry values."""
    fields: list[dict[str, Any]] = []
    for spec in specs:
        field = {key: value for key, value in spec.items() if key != "default"}
        field["value"] = options.get(spec["key"], spec.get("default"))
        if spec["key"] == CONF_EMHASS_OPTIMIZATION_INTERVAL:
            current = field["value"]
            field["options"] = [
                {
                    "value": value,
                    "label": (
                        f"{value} minutes"
                        if int(value) in EMHASS_OPTIMIZATION_INTERVALS
                        else f"{value} minutes (existing setting)"
                    ),
                }
                for value in _optimization_interval_options(current)
            ]
        field["readonly"] = False
        fields.append(field)
    return fields


def _settings_payload(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Return all settings required by the dedicated frontend pages."""
    options = _options_for_form(dict(entry.options))
    # v0.45 stored external entity IDs without a separate master switch. Keep
    # those existing installations enabled until the operator explicitly saves
    # the new v0.46 switch; fresh configurations remain disabled by default.
    pv_options = dict(options)
    pv_options.setdefault(
        CONF_ENABLE_EXTERNAL_PV,
        external_sources_enabled(
            options,
            enable_key=CONF_ENABLE_EXTERNAL_PV,
            entity_keys=EXTERNAL_PV_ENTITY_KEYS,
            default=DEFAULT_ENABLE_EXTERNAL_PV,
        ),
    )
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
                "description": "GoodWe controller boundaries and telemetry cadence.",
                "fields": _fields_from_specs(options, EP_FIELD_SPECS),
            },
            SECTION_EV: {
                "title": "EV",
                "short_title": "EV",
                "description": (
                    "Soft house-connection load balancing and the existing EV "
                    "battery coordination. The load balancer controls only the "
                    "configured charger current entity, never GoodWe."
                ),
                "fields": _fields_from_specs(options, EV_FIELD_SPECS),
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
            SECTION_PV: {
                "title": "PV",
                "short_title": "PV",
                "description": (
                    "Choose which internal and external PV power sources are shown "
                    "in EnergyPilot. These values are never used for control."
                ),
                "fields": _fields_from_specs(pv_options, PV_FIELD_SPECS),
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
            [
                SECTION_ENERGYPILOT,
                SECTION_EV,
                SECTION_EMHASS,
                SECTION_GOODWE,
                SECTION_PV,
            ]
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
    elif section == SECTION_EV:
        confirmation = values.pop("_confirm_high_current", False) is True
        unknown = set(values) - EV_KEYS
        if unknown:
            connection.send_error(
                msg["id"],
                "invalid_settings",
                f"Unsupported EV settings: {', '.join(sorted(unknown))}",
            )
            return
        try:
            validated = _validate_ev_values(values)
            _validate_ev_entity_contract(hass, validated)
        except (vol.Invalid, TypeError, ValueError) as err:
            connection.send_error(msg["id"], "invalid_settings", str(err))
            return
        previous_maximum = float(
            entry.options.get(
                CONF_EV_CHARGER_MAX_CURRENT, DEFAULT_EV_CHARGER_MAX_CURRENT
            )
        )
        maximum = float(validated[CONF_EV_CHARGER_MAX_CURRENT])
        if maximum > 16 and maximum != previous_maximum and not confirmation:
            connection.send_error(
                msg["id"],
                "high_current_confirmation_required",
                "A charger current above 16 A requires explicit confirmation",
            )
            return

        stored_options = dict(entry.options)
        for key in EV_KEYS:
            stored_options.pop(key, None)
        stored_options.update(validated)
        if maximum > 16 and maximum != previous_maximum:
            runtime = getattr(entry, "runtime_data", None)
            audit = (
                runtime.ev_load_balancer.audit
                if runtime is not None
                else EVLoadBalancingAudit(hass, entry.entry_id)
            )
            user = getattr(connection, "user", None)
            await audit.async_append(
                high_current_audit_record(
                    user_id=getattr(user, "id", None),
                    maximum=maximum,
                    options=stored_options,
                )
            )
        hass.config_entries.async_update_entry(entry, options=stored_options)
    elif section == SECTION_PV:
        unknown = set(values) - PV_KEYS
        if unknown:
            connection.send_error(
                msg["id"],
                "invalid_settings",
                f"Unsupported PV settings: {', '.join(sorted(unknown))}",
            )
            return
        cleaned_values = {
            key: value
            for key, value in values.items()
            if key in {CONF_ENABLE_INTERNAL_PV, CONF_ENABLE_EXTERNAL_PV}
            or value not in (None, "")
        }
        try:
            validated = PV_SCHEMA(cleaned_values)
        except (vol.Invalid, TypeError, ValueError) as err:
            connection.send_error(msg["id"], "invalid_settings", str(err))
            return
        external_entities = [
            validated[key]
            for key in EXTERNAL_PV_ENTITY_KEYS
            if key in validated
        ]
        if len(external_entities) != len(set(external_entities)):
            connection.send_error(
                msg["id"],
                "invalid_settings",
                "Each external PV entity may only be configured once",
            )
            return
        registry = er.async_get(hass)
        for entity_id in external_entities:
            registry_entry = registry.async_get(entity_id)
            if (
                registry_entry is not None
                and registry_entry.platform == DOMAIN
                and registry_entry.unique_id.endswith("_pv_generation_power")
            ):
                connection.send_error(
                    msg["id"],
                    "invalid_settings",
                    "A combined EnergyPilot PV sensor cannot be used as a PV source",
                )
                return

        stored_options = dict(entry.options)
        for key in PV_KEYS:
            stored_options.pop(key, None)
        stored_options.update(validated)
        hass.config_entries.async_update_entry(entry, options=stored_options)
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
        for key in PV_KEYS:
            form_values.pop(key, None)
        preserved_ev_load_balancing = {
            key: form_values.pop(key)
            for key in EV_LOAD_BALANCING_KEYS
            if key in form_values
        }
        form_values.update(values)
        for key in OPTIONAL_ENTITY_KEYS:
            if form_values.get(key) in (None, ""):
                form_values.pop(key, None)

        try:
            validated = _controller_schema(
                orchestrator_default=bool(
                    form_values.get(CONF_ENABLE_EMHASS_ORCHESTRATOR, True)
                ),
                optimization_interval=form_values.get(
                    CONF_EMHASS_OPTIMIZATION_INTERVAL
                ),
            )(form_values)
            stored_options = _options_from_form(validated)
        except (vol.Invalid, TypeError, ValueError) as err:
            connection.send_error(msg["id"], "invalid_settings", str(err))
            return
        if CONF_BATTERY_SAVER_MODE in entry.options:
            stored_options[CONF_BATTERY_SAVER_MODE] = entry.options[
                CONF_BATTERY_SAVER_MODE
            ]
        for key in PV_KEYS:
            if key in entry.options:
                stored_options[key] = entry.options[key]
        stored_options.update(preserved_ev_load_balancing)
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
