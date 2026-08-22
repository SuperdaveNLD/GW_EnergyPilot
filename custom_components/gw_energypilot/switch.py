"""Switch platform for GW EnergyPilot."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GWConfigEntry
from .entity import GWEnergyPilotEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GWConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up automatic control switch."""
    async_add_entities([GWAutomaticControlSwitch(entry)])


class GWAutomaticControlSwitch(GWEnergyPilotEntity, SwitchEntity):
    """Master switch for EnergyPilot automatic control."""

    _attr_translation_key = "automatic_control"

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_automatic_control"

    @property
    def is_on(self) -> bool:
        """Return whether EnergyPilot automatic control is enabled."""
        return self.entry.runtime_data.controller.enabled

    async def async_turn_on(self, **kwargs) -> None:
        """Enable automatic control."""
        await self.entry.runtime_data.controller.async_enable()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Disable automatic control and restore GoodWe Auto."""
        await self.entry.runtime_data.controller.async_disable()
        self.async_write_ha_state()
