"""Switch platform for GW EnergyPilot."""

from typing import Any, override

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import restore_state
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


class GWAutomaticControlSwitch(
    GWEnergyPilotEntity,
    restore_state.RestoreEntity,
    SwitchEntity,
):
    """Master switch for EnergyPilot automatic control."""

    _attr_translation_key = "automatic_control"

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_automatic_control"

    @override
    async def async_added_to_hass(self) -> None:
        """Restore the previous automatic-control state."""
        await super().async_added_to_hass()

        previous = await self.async_get_last_state()
        if previous is not None and previous.state == STATE_ON:
            await self.entry.runtime_data.controller.async_enable()
        else:
            # First install and a previously disabled switch both start safely
            # in GoodWe Auto / AI.
            await self.entry.runtime_data.controller.async_disable()

        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return whether EnergyPilot automatic control is enabled."""
        return self.entry.runtime_data.controller.enabled

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable automatic control."""
        await self.entry.runtime_data.controller.async_enable()
        self.async_write_ha_state()

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable automatic control and restore GoodWe Auto."""
        await self.entry.runtime_data.controller.async_disable()
        self.async_write_ha_state()
