"""Helpers for reading and writing selected EMHASS configuration values."""

from __future__ import annotations

import asyncio
import math
from typing import Any

from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import CONF_EMHASS_URL, DEFAULT_EMHASS_URL, DOMAIN

EMHASS_COST_FUNCTIONS: tuple[str, ...] = (
    "profit",
    "cost",
    "self-consumption",
)


def emhass_config_update_signal(entry_id: str) -> str:
    """Return the dispatcher signal for EMHASS configuration updates."""
    return f"{DOMAIN}_{entry_id}_emhass_config_update"


def _base_url(entry) -> str:
    """Return configured EMHASS base URL."""
    base_url = str(entry.options.get(CONF_EMHASS_URL, DEFAULT_EMHASS_URL)).strip()
    if not base_url:
        raise HomeAssistantError("EMHASS URL is empty")
    return base_url.rstrip("/")


def emhass_cost_function_from_config(config: dict[str, Any]) -> str | None:
    """Return a supported EMHASS cost function from a complete config."""
    value = str(config.get("costfun", "")).strip()
    return value if value in EMHASS_COST_FUNCTIONS else None


def _finite_number(config: dict[str, Any], key: str) -> float | None:
    """Decode one finite numeric EMHASS config value."""
    try:
        value = float(config.get(key))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _soc_percentage(config: dict[str, Any], key: str) -> float | None:
    """Decode one valid EMHASS 0..1 SOC config value to a percentage."""
    value = _finite_number(config, key)
    if value is None or not 0.0 <= value <= 1.0:
        return None
    return round(value * 100.0, 2)


def emhass_soc_diagnostics_from_config(
    config: dict[str, Any],
) -> dict[str, float | None]:
    """Return SOC-related EMHASS config values with explicit semantics.

    Percentage fields are exposed only when the raw EMHASS value is inside the
    documented 0..1 SOC range. Selected raw values are retained separately so
    support diagnostics can identify invalid or stale EMHASS configuration
    instead of presenting it as a plausible percentage.

    These values come from EMHASS config.json. They are deliberately kept
    separate from EnergyPilot's runtime `soc_final` payload setting.
    """
    target_raw = _finite_number(config, "battery_target_state_of_charge")
    deficit_threshold_raw = _finite_number(
        config, "battery_soc_deficit_threshold"
    )
    return {
        "emhass_minimum_soc_pct": _soc_percentage(
            config, "battery_minimum_state_of_charge"
        ),
        "emhass_maximum_soc_pct": _soc_percentage(
            config, "battery_maximum_state_of_charge"
        ),
        "emhass_config_target_soc_pct": _soc_percentage(
            config, "battery_target_state_of_charge"
        ),
        "emhass_config_target_soc_raw": target_raw,
        "emhass_soc_deficit_threshold_pct": _soc_percentage(
            config, "battery_soc_deficit_threshold"
        ),
        "emhass_soc_deficit_threshold_raw": deficit_threshold_raw,
        "emhass_soc_deficit_cost": _finite_number(
            config, "battery_soc_deficit_cost"
        ),
    }


async def async_get_emhass_config(
    hass: HomeAssistant,
    entry,
    *,
    timeout_seconds: int = 20,
) -> dict[str, Any]:
    """Read the complete active EMHASS config through its supported API."""
    session = async_get_clientsession(hass)
    url = f"{_base_url(entry)}/get-config"

    try:
        async with asyncio.timeout(timeout_seconds):
            async with session.get(url) as response:
                if not 200 <= response.status < 300:
                    text = await response.text()
                    raise HomeAssistantError(
                        f"EMHASS get-config HTTP {response.status}: {text[:250]}"
                    )
                payload = await response.json(content_type=None)
    except (TimeoutError, ClientError) as err:
        raise HomeAssistantError(f"Unable to read EMHASS configuration: {err}") from err

    if not isinstance(payload, dict):
        raise HomeAssistantError("EMHASS get-config did not return a JSON object")
    return payload


async def async_get_emhass_cost_function(
    hass: HomeAssistant,
    entry,
) -> str | None:
    """Read the active supported EMHASS cost function."""
    config = await async_get_emhass_config(hass, entry)
    return emhass_cost_function_from_config(config)


async def async_write_emhass_config(
    hass: HomeAssistant,
    entry,
    config: dict[str, Any],
    *,
    timeout_seconds: int = 30,
) -> None:
    """Write a complete EMHASS config through /set-config."""
    session = async_get_clientsession(hass)
    url = f"{_base_url(entry)}/set-config"

    try:
        async with asyncio.timeout(timeout_seconds):
            async with session.post(url, json=config) as response:
                if not 200 <= response.status < 300:
                    text = await response.text()
                    raise HomeAssistantError(
                        f"EMHASS set-config HTTP {response.status}: {text[:250]}"
                    )
    except (TimeoutError, ClientError) as err:
        raise HomeAssistantError(f"Unable to save EMHASS configuration: {err}") from err

    async_dispatcher_send(hass, emhass_config_update_signal(entry.entry_id))


async def async_patch_emhass_config(
    hass: HomeAssistant,
    entry,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Safely merge selected values into the current complete EMHASS config.

    EMHASS /set-config reconstructs and persists config.json. Always fetching
    the current full config first prevents an EnergyPilot control from replacing
    unrelated user settings with defaults.
    """
    config = await async_get_emhass_config(hass, entry)
    config.update(updates)
    await async_write_emhass_config(hass, entry, config)
    return config


async def async_set_emhass_cost_function(
    hass: HomeAssistant,
    entry,
    cost_function: str,
) -> dict[str, Any]:
    """Safely persist one supported EMHASS cost function."""
    value = str(cost_function).strip()
    if value not in EMHASS_COST_FUNCTIONS:
        supported = ", ".join(EMHASS_COST_FUNCTIONS)
        raise HomeAssistantError(
            f"Unsupported EMHASS cost function '{value}'. Supported values: {supported}"
        )
    return await async_patch_emhass_config(hass, entry, {"costfun": value})
