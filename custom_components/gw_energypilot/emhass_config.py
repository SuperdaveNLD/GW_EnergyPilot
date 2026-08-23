"""Helpers for reading and writing selected EMHASS configuration values."""

from __future__ import annotations

import asyncio
from typing import Any

from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_EMHASS_URL, DEFAULT_EMHASS_URL


def _base_url(entry) -> str:
    """Return configured EMHASS base URL."""
    base_url = str(entry.options.get(CONF_EMHASS_URL, DEFAULT_EMHASS_URL)).strip()
    if not base_url:
        raise HomeAssistantError("EMHASS URL is empty")
    return base_url.rstrip("/")


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


async def async_patch_emhass_config(
    hass: HomeAssistant,
    entry,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Safely merge selected values into the current complete EMHASS config.

    EMHASS /set-config reconstructs and persists config.json. Always fetching
    the current full config first prevents an EnergyPilot slider from replacing
    unrelated user settings with defaults.
    """
    config = await async_get_emhass_config(hass, entry)
    config.update(updates)
    await async_write_emhass_config(hass, entry, config)
    return config
