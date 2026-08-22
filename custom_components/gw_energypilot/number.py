"""Number platform for GW EnergyPilot."""

from homeassistant.components.number import NumberEntity
from homeassistant.const import EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GWConfigEntry
from .const import CONF_MAX_POWER, DEFAULT_MAX_POWER
from .entity import GWEnergyPilotEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GWConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up manual power number."""
    async_add_entities([GWManualPowerNumber(entry)])


class GWManualPowerNumber(GWEnergyPilotEntity, NumberEntity):
    """Manual power used when selecting an EMS mode."""

    _attr_translation_key = "manual_power"
    _attr_native_min_value = 0
    _attr_native_step = 100
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_manual_power"
        self._attr_native_max_value = int(
            entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER)
        )

    @property
    def native_value(self) -> int:
        """Return currently selected manual power."""
        return self.entry.runtime_data.controller.manual_power

    async def async_set_native_value(self, value: float) -> None:
        """Set manual power."""
        self.entry.runtime_data.controller.manual_power = int(value)
        self.async_write_ha_state()
