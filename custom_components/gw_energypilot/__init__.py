"""GW EnergyPilot integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.frontend import async_panel_exists
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .client import GWModbusClient
from .const import CONF_SCAN_INTERVAL, CONF_SLAVE, DEFAULT_SCAN_INTERVAL
from .controller import GWEnergyPilotController
from .coordinator import GWEnergyPilotCoordinator

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
]

PANEL_URL = "gw-energypilot"
PANEL_COMPONENT = "gw-energypilot-panel"
PANEL_STATIC_URL = "/gw_energypilot_static"
PANEL_MODULE = f"{PANEL_STATIC_URL}/gw-energy-pilot-v007.js?v=0.07"
FRONTEND_DIR = Path(__file__).parent / "frontend"


@dataclass(slots=True)
class GWRuntimeData:
    """Runtime data for one EnergyPilot config entry."""

    client: GWModbusClient
    coordinator: GWEnergyPilotCoordinator
    controller: GWEnergyPilotController


type GWConfigEntry = ConfigEntry[GWRuntimeData]


async def _async_register_panel(hass: HomeAssistant) -> None:
    """Register the EnergyPilot sidebar panel once."""
    if async_panel_exists(hass, PANEL_URL):
        return

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                PANEL_STATIC_URL,
                str(FRONTEND_DIR),
                cache_headers=False,
            )
        ]
    )
    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name=PANEL_COMPONENT,
        sidebar_title="EnergyPilot",
        sidebar_icon="mdi:transmission-tower",
        module_url=PANEL_MODULE,
        embed_iframe=False,
        require_admin=False,
        handle_safe_area=True,
    )


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
        scan_interval=int(
            entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        ),
    )
    await coordinator.async_config_entry_first_refresh()

    controller = GWEnergyPilotController(hass, entry, client, coordinator)
    entry.runtime_data = GWRuntimeData(
        client=client,
        coordinator=coordinator,
        controller=controller,
    )
    await controller.async_setup()

    # Safety baseline: automatic control is intentionally not restored after
    # a Home Assistant restart. Every setup/reload hands the inverter back to
    # GoodWe Auto / AI (mode 1, setpoint 0). The user must explicitly enable
    # EnergyPilot automatic control again.
    await controller.async_disable()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_register_panel(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GWConfigEntry) -> bool:
    """Unload GW EnergyPilot."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.controller.async_unload()
        await entry.runtime_data.client.async_close()
    return unload_ok
