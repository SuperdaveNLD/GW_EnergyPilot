"""GW EnergyPilot integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .client import GWModbusClient
from .const import CONF_SCAN_INTERVAL, CONF_SLAVE, DEFAULT_SCAN_INTERVAL
from .coordinator import GWEnergyPilotCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER, Platform.SELECT]


@dataclass(slots=True)
class GWRuntimeData:
    client: GWModbusClient
    coordinator: GWEnergyPilotCoordinator


type GWConfigEntry = ConfigEntry[GWRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: GWConfigEntry) -> bool:
    """Set up GW EnergyPilot from a config entry."""
    client = GWModbusClient(
        host=entry.data[CONF_HOST],
        port=int(entry.data[CONF_PORT]),
        slave=int(entry.data[CONF_SLAVE]),
    )

    coordinator = GWEnergyPilotCoordinator(
        hass,
        client,
        scan_interval=int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)),
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = GWRuntimeData(client=client, coordinator=coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GWConfigEntry) -> bool:
    """Unload GW EnergyPilot."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.client.async_close()
    return unload_ok
