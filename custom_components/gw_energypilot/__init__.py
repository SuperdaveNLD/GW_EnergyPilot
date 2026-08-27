"""GW EnergyPilot integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.frontend import async_panel_exists
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .accounting import GWEnergyPilotAccounting
from .battery_price_api import async_register_battery_price_api
from .battery_saver_api import async_register_battery_saver_api
from .beta_soc_api import async_register_beta_soc_api
from .client import GWModbusClient
from .const import CONF_SCAN_INTERVAL, CONF_SLAVE, DEFAULT_SCAN_INTERVAL, DOMAIN
from .controller_v033 import GWEnergyPilotController
from .coordinator import GWEnergyPilotCoordinator
from .debug_log_api import async_register_debug_log_api
from .debug_log_runtime import GWEnergyPilotDebugRuntime
from .emhass_sync_api import async_register_emhass_sync_api
from .event_triggers import async_setup_event_triggers
from .optimization_log_api import async_register_optimization_log_api
from .orchestrator_v033 import GWEnergyPilotOrchestrator
from .plan_runtime import GWEnergyPilotPlanRuntime
from .settings_api import async_register_settings_api
from .smart_meter_api import async_register_smart_meter_api

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BUTTON,
]

PANEL_URL = "gw-energypilot"
PANEL_COMPONENT = "gw-energypilot-panel"
PANEL_STATIC_URL = "/gw_energypilot_static"
PANEL_MODULE = f"{PANEL_STATIC_URL}/gw-energy-pilot-v0411.js?v=0.41.1-optimize-scroll1"
FRONTEND_DIR = Path(__file__).parent / "frontend"


@dataclass(slots=True)
class GWRuntimeData:
    """Runtime data for one EnergyPilot config entry."""

    client: GWModbusClient
    coordinator: GWEnergyPilotCoordinator
    controller: GWEnergyPilotController
    orchestrator: GWEnergyPilotOrchestrator
    accounting: GWEnergyPilotAccounting
    debug_log: GWEnergyPilotDebugRuntime
    plan_runtime: GWEnergyPilotPlanRuntime
    event_unsubs: list[Callable[[], None]] = field(default_factory=list)


type GWConfigEntry = ConfigEntry[GWRuntimeData]


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up integration-wide dashboard APIs."""
    async_register_settings_api(hass)
    async_register_beta_soc_api(hass)
    async_register_smart_meter_api(hass)
    async_register_optimization_log_api(hass)
    async_register_debug_log_api(hass)
    async_register_battery_price_api(hass)
    async_register_battery_saver_api(hass)
    async_register_emhass_sync_api(hass)
    return True


def _migrate_device_identifier(hass: HomeAssistant, entry: GWConfigEntry) -> None:
    """Move the legacy mutable host:slave device identifier to entry_id."""
    registry = dr.async_get(hass)
    stable_identifier = (DOMAIN, entry.entry_id)
    if registry.async_get_device_by_identifier(stable_identifier, entry.entry_id):
        return
    legacy_identifier = (DOMAIN, f"{entry.data[CONF_HOST]}:{entry.data[CONF_SLAVE]}")
    device = registry.async_get_device_by_identifier(legacy_identifier, entry.entry_id)
    if device is not None:
        registry.async_update_device(device.id, new_identifiers={stable_identifier})


async def _async_register_panel(hass: HomeAssistant) -> None:
    """Register the EnergyPilot sidebar panel once."""
    if async_panel_exists(hass, PANEL_URL):
        return
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_STATIC_URL, str(FRONTEND_DIR), cache_headers=False)]
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


async def _async_initial_refresh(
    coordinator: GWEnergyPilotCoordinator,
    accounting: GWEnergyPilotAccounting,
) -> None:
    """Refresh telemetry, then seed accounting from existing Recorder history."""
    await coordinator.async_refresh()
    await accounting.async_bootstrap_if_needed()


async def async_setup_entry(hass: HomeAssistant, entry: GWConfigEntry) -> bool:
    """Set up GW EnergyPilot from a config entry."""
    _migrate_device_identifier(hass, entry)
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
    controller = GWEnergyPilotController(hass, entry, client, coordinator)
    orchestrator = GWEnergyPilotOrchestrator(hass, entry, coordinator)
    accounting = GWEnergyPilotAccounting(hass, entry.entry_id, coordinator)
    debug_log = GWEnergyPilotDebugRuntime(hass, entry.entry_id)
    plan_runtime = GWEnergyPilotPlanRuntime(hass, entry)
    entry.runtime_data = GWRuntimeData(
        client=client,
        coordinator=coordinator,
        controller=controller,
        orchestrator=orchestrator,
        accounting=accounting,
        debug_log=debug_log,
        plan_runtime=plan_runtime,
    )

    await plan_runtime.async_restore()
    entry.async_create_background_task(
        hass,
        plan_runtime.async_startup_refresh(),
        f"GW EnergyPilot EMHASS plan refresh ({entry.entry_id})",
    )
    await debug_log.async_start(entry)
    await accounting.async_prepare()
    await controller.async_setup()
    await orchestrator.async_setup()
    entry.runtime_data.event_unsubs.extend(async_setup_event_triggers(hass, entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await accounting.async_start()
    await _async_register_panel(hass)
    entry.async_create_background_task(
        hass,
        _async_initial_refresh(coordinator, accounting),
        f"GW EnergyPilot initial refresh ({entry.entry_id})",
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GWConfigEntry) -> bool:
    """Unload GW EnergyPilot."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        while entry.runtime_data.event_unsubs:
            entry.runtime_data.event_unsubs.pop()()
        await entry.runtime_data.debug_log.async_unload()
        await entry.runtime_data.accounting.async_unload()
        await entry.runtime_data.orchestrator.async_unload()
        await entry.runtime_data.controller.async_unload()
        await entry.runtime_data.client.async_close()
    return unload_ok
