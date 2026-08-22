"""Select platform for GW EnergyPilot."""

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GWConfigEntry
from .const import MODE_NAMES, MODES_ZERO_POWER
from .entity import GWEnergyPilotEntity

MODE_OPTIONS = [f"{mode}: {name}" for mode, name in MODE_NAMES.items()]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GWConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up manual EMS mode selector."""
    async_add_entities([GWEMSModeSelect(entry)])


class GWEMSModeSelect(GWEnergyPilotEntity, SelectEntity):
    """Manual EMS mode selector."""

    _attr_translation_key = "manual_mode"
    _attr_options = MODE_OPTIONS
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_manual_mode"

    @property
    def current_option(self) -> str | None:
        """Return current EMS mode as an option."""
        if not self.coordinator.data:
            return None
        mode = self.coordinator.data.mode
        name = MODE_NAMES.get(mode)
        return f"{mode}: {name}" if name else None

    async def async_select_option(self, option: str) -> None:
        """Apply the selected EMS mode and switch to manual ownership."""
        mode = int(option.split(":", 1)[0])
        power = (
            0
            if mode in MODES_ZERO_POWER
            else self.entry.runtime_data.controller.manual_power
        )
        await self.entry.runtime_data.controller.async_manual_command(
            mode,
            power,
            f"manual_mode_{mode}",
        )
