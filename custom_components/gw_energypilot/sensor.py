"""Sensors for GW EnergyPilot."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GWConfigEntry
from .const import MODE_NAMES
from .entity import GWEnergyPilotEntity


async def async_setup_entry(hass: HomeAssistant, entry: GWConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    """Set up EnergyPilot sensors."""
    async_add_entities([
        GWEMSModeSensor(entry),
        GWEMSSetpointSensor(entry),
        GWControlCommandSensor(entry),
        GWTargetPowerSensor(entry),
        GWEVActiveSensor(entry),
    ])


class GWEMSModeSensor(GWEnergyPilotEntity, SensorEntity):
    _attr_translation_key = "ems_mode"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_ems_mode"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.mode if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        mode = self.native_value
        return {"mode_name": MODE_NAMES.get(mode, "Unknown")}


class GWEMSSetpointSensor(GWEnergyPilotEntity, SensorEntity):
    _attr_translation_key = "ems_setpoint"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_ems_setpoint"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.power if self.coordinator.data else None


class GWControlCommandSensor(GWEnergyPilotEntity, SensorEntity):
    _attr_translation_key = "control_command"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_control_command"

    @property
    def native_value(self) -> str:
        return self.entry.runtime_data.controller.last_command


class GWTargetPowerSensor(GWEnergyPilotEntity, SensorEntity):
    _attr_translation_key = "target_power"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_target_power"

    @property
    def native_value(self) -> int:
        return self.entry.runtime_data.controller.target_power


class GWEVActiveSensor(GWEnergyPilotEntity, SensorEntity):
    _attr_translation_key = "ev_status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_ev_status"

    @property
    def native_value(self) -> str:
        return "active" if self.entry.runtime_data.controller.ev_is_active() else "inactive"
