"""Button entities for GW EnergyPilot."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
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

    async def async_added_to_hass(self) -> None:
        """Subscribe to native orchestrator status updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self.entry.runtime_data.orchestrator.signal,
                self._async_orchestrator_updated,
            )
        )

    @callback
    def _async_orchestrator_updated(self) -> None:
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose current optimizer status on the same native entity."""
        orchestrator = self.entry.runtime_data.orchestrator
        return {
            "orchestrator_status": orchestrator.status,
            **orchestrator.attributes,
        }

    async def async_press(self) -> None:
        """Start a manual optimization."""
        await self.entry.runtime_data.orchestrator.async_optimize(reason="manual_button")
