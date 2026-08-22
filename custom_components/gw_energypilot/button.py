"""Button entities for GW EnergyPilot."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GWConfigEntry
from .entity import GWEnergyPilotEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GWConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up EnergyPilot button entities."""
    async_add_entities([GWOptimizeNowButton(entry)])


class GWOptimizeNowButton(GWEnergyPilotEntity, ButtonEntity):
    """Run one complete EMHASS optimization and publish cycle."""

    _attr_translation_key = "optimize_now"
    _attr_icon = "mdi:play-circle-outline"

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_optimize_now"

    async def async_press(self) -> None:
        """Start a manual optimization."""
        await self.entry.runtime_data.orchestrator.async_optimize(reason="manual_button")
