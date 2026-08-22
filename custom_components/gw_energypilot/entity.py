"""Base entity for GW EnergyPilot."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GWConfigEntry
from .const import DOMAIN, NAME
from .coordinator import GWEnergyPilotCoordinator


class GWEnergyPilotEntity(CoordinatorEntity[GWEnergyPilotCoordinator]):
    """Base coordinator entity."""

    _attr_has_entity_name = True

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self.entry = entry
        unique = f"{entry.data['host']}:{entry.data['slave']}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique)},
            name=NAME,
            manufacturer="GoodWe",
            model="ETA EMS Controller",
        )
