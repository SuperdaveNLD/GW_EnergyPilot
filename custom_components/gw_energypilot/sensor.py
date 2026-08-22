"""Sensors for GW EnergyPilot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GWConfigEntry
from .const import MODE_NAMES
from .entity import GWEnergyPilotEntity


@dataclass(frozen=True, kw_only=True)
class GWSensorEntityDescription(SensorEntityDescription):
    """Describe a GoodWe ETA telemetry sensor."""

    diagnostic: bool = False


POWER = {
    "device_class": SensorDeviceClass.POWER,
    "native_unit_of_measurement": UnitOfPower.WATT,
    "state_class": SensorStateClass.MEASUREMENT,
}
VOLTAGE = {
    "device_class": SensorDeviceClass.VOLTAGE,
    "native_unit_of_measurement": UnitOfElectricPotential.VOLT,
    "state_class": SensorStateClass.MEASUREMENT,
}
CURRENT = {
    "device_class": SensorDeviceClass.CURRENT,
    "native_unit_of_measurement": UnitOfElectricCurrent.AMPERE,
    "state_class": SensorStateClass.MEASUREMENT,
}
FREQUENCY = {
    "device_class": SensorDeviceClass.FREQUENCY,
    "native_unit_of_measurement": UnitOfFrequency.HERTZ,
    "state_class": SensorStateClass.MEASUREMENT,
}
TEMPERATURE = {
    "device_class": SensorDeviceClass.TEMPERATURE,
    "native_unit_of_measurement": UnitOfTemperature.CELSIUS,
    "state_class": SensorStateClass.MEASUREMENT,
}


TELEMETRY_SENSORS: tuple[GWSensorEntityDescription, ...] = (
    # PV
    GWSensorEntityDescription(key="pv_total_power", name="PV total power", **POWER),
    GWSensorEntityDescription(key="pv1_power", name="PV1 power", **POWER),
    GWSensorEntityDescription(key="pv1_voltage", name="PV1 voltage", **VOLTAGE),
    GWSensorEntityDescription(key="pv1_current", name="PV1 current", **CURRENT),
    GWSensorEntityDescription(key="pv2_power", name="PV2 power", **POWER),
    GWSensorEntityDescription(key="pv2_voltage", name="PV2 voltage", **VOLTAGE),
    GWSensorEntityDescription(key="pv2_current", name="PV2 current", **CURRENT),
    GWSensorEntityDescription(key="pv3_power", name="PV3 power", **POWER),
    GWSensorEntityDescription(key="pv3_voltage", name="PV3 voltage", **VOLTAGE),
    GWSensorEntityDescription(key="pv3_current", name="PV3 current", **CURRENT),
    GWSensorEntityDescription(key="pv4_power", name="PV4 power", **POWER),
    GWSensorEntityDescription(key="pv4_voltage", name="PV4 voltage", **VOLTAGE),
    GWSensorEntityDescription(key="pv4_current", name="PV4 current", **CURRENT),

    # Inverter AC
    GWSensorEntityDescription(
        key="total_inverter_power", name="Total inverter power", **POWER
    ),
    GWSensorEntityDescription(key="ac_active_power", name="AC active power", **POWER),
    GWSensorEntityDescription(key="inverter_l1_power", name="Inverter L1 power", **POWER),
    GWSensorEntityDescription(
        key="inverter_l1_voltage", name="Inverter L1 voltage", **VOLTAGE
    ),
    GWSensorEntityDescription(
        key="inverter_l1_current", name="Inverter L1 current", **CURRENT
    ),
    GWSensorEntityDescription(
        key="inverter_l1_frequency", name="Inverter L1 frequency", **FREQUENCY
    ),
    GWSensorEntityDescription(key="inverter_l2_power", name="Inverter L2 power", **POWER),
    GWSensorEntityDescription(
        key="inverter_l2_voltage", name="Inverter L2 voltage", **VOLTAGE
    ),
    GWSensorEntityDescription(
        key="inverter_l2_current", name="Inverter L2 current", **CURRENT
    ),
    GWSensorEntityDescription(
        key="inverter_l2_frequency", name="Inverter L2 frequency", **FREQUENCY
    ),
    GWSensorEntityDescription(key="inverter_l3_power", name="Inverter L3 power", **POWER),
    GWSensorEntityDescription(
        key="inverter_l3_voltage", name="Inverter L3 voltage", **VOLTAGE
    ),
    GWSensorEntityDescription(
        key="inverter_l3_current", name="Inverter L3 current", **CURRENT
    ),
    GWSensorEntityDescription(
        key="inverter_l3_frequency", name="Inverter L3 frequency", **FREQUENCY
    ),

    # Inverter temperatures
    GWSensorEntityDescription(
        key="inverter_air_temperature", name="Inverter air temperature", **TEMPERATURE
    ),
    GWSensorEntityDescription(
        key="inverter_module_temperature",
        name="Inverter module temperature",
        **TEMPERATURE,
    ),
    GWSensorEntityDescription(
        key="inverter_radiator_temperature",
        name="Inverter radiator temperature",
        **TEMPERATURE,
    ),

    # Load / backup. These are exposed as raw GoodWe telemetry. Some ETA
    # installations report Total load power as zero, so do not assume this is
    # a reliable whole-home load source without validating it locally.
    GWSensorEntityDescription(key="load_l1_power", name="Load L1 power", **POWER),
    GWSensorEntityDescription(key="load_l2_power", name="Load L2 power", **POWER),
    GWSensorEntityDescription(key="load_l3_power", name="Load L3 power", **POWER),
    GWSensorEntityDescription(
        key="total_backup_load_power", name="Total backup load power", **POWER
    ),
    GWSensorEntityDescription(key="total_load_power", name="Total load power", **POWER),

    # Battery runtime
    GWSensorEntityDescription(
        key="battery_soc",
        name="Battery state of charge",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GWSensorEntityDescription(
        key="battery_soh",
        name="Battery state of health",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    GWSensorEntityDescription(key="battery_power", name="Battery power", **POWER),
    GWSensorEntityDescription(key="battery_voltage", name="Battery voltage", **VOLTAGE),
    GWSensorEntityDescription(key="battery_current", name="Battery current", **CURRENT),
    GWSensorEntityDescription(
        key="battery_mode", name="Battery mode", diagnostic=True
    ),
    GWSensorEntityDescription(
        key="battery_strings", name="Battery strings", diagnostic=True
    ),

    # BMS temperatures, limits and cell health
    GWSensorEntityDescription(
        key="bms_package_temperature", name="BMS package temperature", **TEMPERATURE
    ),
    GWSensorEntityDescription(
        key="battery_max_cell_temperature",
        name="Battery maximum cell temperature",
        **TEMPERATURE,
    ),
    GWSensorEntityDescription(
        key="battery_min_cell_temperature",
        name="Battery minimum cell temperature",
        **TEMPERATURE,
    ),
    GWSensorEntityDescription(
        key="battery_max_cell_voltage", name="Battery maximum cell voltage", **VOLTAGE
    ),
    GWSensorEntityDescription(
        key="battery_min_cell_voltage", name="Battery minimum cell voltage", **VOLTAGE
    ),
    GWSensorEntityDescription(
        key="bms_max_charge_current", name="BMS maximum charge current", **CURRENT
    ),
    GWSensorEntityDescription(
        key="bms_max_discharge_current", name="BMS maximum discharge current", **CURRENT
    ),
    GWSensorEntityDescription(key="bms_status", name="BMS status", diagnostic=True),
    GWSensorEntityDescription(key="bms_protocol", name="BMS protocol", diagnostic=True),
    GWSensorEntityDescription(
        key="bms_software_version", name="BMS software version", diagnostic=True
    ),
    GWSensorEntityDescription(
        key="bms_hardware_version", name="BMS hardware version", diagnostic=True
    ),
    GWSensorEntityDescription(key="bms_error_low", name="BMS error low", diagnostic=True),
    GWSensorEntityDescription(
        key="bms_warning_low", name="BMS warning low", diagnostic=True
    ),
    GWSensorEntityDescription(
        key="bms_error_high", name="BMS error high", diagnostic=True
    ),
    GWSensorEntityDescription(
        key="bms_warning_high", name="BMS warning high", diagnostic=True
    ),

    # Smart meter / grid
    GWSensorEntityDescription(
        key="meter_total_active_power", name="Meter total active power", **POWER
    ),
    GWSensorEntityDescription(
        key="meter_total_power_fast", name="Meter total active power fast", **POWER
    ),
    GWSensorEntityDescription(
        key="meter_l1_active_power", name="Meter L1 active power", **POWER
    ),
    GWSensorEntityDescription(
        key="meter_l2_active_power", name="Meter L2 active power", **POWER
    ),
    GWSensorEntityDescription(
        key="meter_l3_active_power", name="Meter L3 active power", **POWER
    ),
    GWSensorEntityDescription(key="meter_l1_power_fast", name="Meter L1 power fast", **POWER),
    GWSensorEntityDescription(key="meter_l2_power_fast", name="Meter L2 power fast", **POWER),
    GWSensorEntityDescription(key="meter_l3_power_fast", name="Meter L3 power fast", **POWER),
    GWSensorEntityDescription(key="meter_l1_voltage", name="Meter L1 voltage", **VOLTAGE),
    GWSensorEntityDescription(key="meter_l2_voltage", name="Meter L2 voltage", **VOLTAGE),
    GWSensorEntityDescription(key="meter_l3_voltage", name="Meter L3 voltage", **VOLTAGE),
    GWSensorEntityDescription(key="meter_l1_current", name="Meter L1 current", **CURRENT),
    GWSensorEntityDescription(key="meter_l2_current", name="Meter L2 current", **CURRENT),
    GWSensorEntityDescription(key="meter_l3_current", name="Meter L3 current", **CURRENT),
    GWSensorEntityDescription(key="meter_frequency", name="Meter frequency", **FREQUENCY),
    GWSensorEntityDescription(
        key="meter_communication", name="Meter communication", diagnostic=True
    ),
    GWSensorEntityDescription(
        key="meter_test_status", name="Meter test status", diagnostic=True
    ),

    # Inverter diagnostics
    GWSensorEntityDescription(key="work_mode", name="Work mode", diagnostic=True),
    GWSensorEntityDescription(
        key="operation_mode", name="Operation mode", diagnostic=True
    ),
    GWSensorEntityDescription(key="grid_mode", name="Grid mode", diagnostic=True),
    GWSensorEntityDescription(key="warning_code", name="Warning code", diagnostic=True),
    GWSensorEntityDescription(key="error_message", name="Error message", diagnostic=True),
    GWSensorEntityDescription(
        key="diagnose_result", name="Diagnose result", diagnostic=True
    ),
    GWSensorEntityDescription(
        key="warning_message_32bit", name="Warning message 32-bit", diagnostic=True
    ),
    GWSensorEntityDescription(
        key="error_message_extended_32bit",
        name="Extended error message 32-bit",
        diagnostic=True,
    ),
    GWSensorEntityDescription(
        key="warning_message_extended_32bit",
        name="Extended warning message 32-bit",
        diagnostic=True,
    ),
    GWSensorEntityDescription(
        key="feed_power_enable", name="Feed power enable", diagnostic=True
    ),
    GWSensorEntityDescription(
        key="feed_power_parameter",
        name="Feed power parameter",
        diagnostic=True,
        **POWER,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GWConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up EnergyPilot sensors."""
    entities: list[SensorEntity] = [
        GWEMSModeSensor(entry),
        GWEMSSetpointSensor(entry),
        GWControlCommandSensor(entry),
        GWTargetPowerSensor(entry),
        GWEVActiveSensor(entry),
    ]
    entities.extend(GWTelemetrySensor(entry, description) for description in TELEMETRY_SENSORS)
    async_add_entities(entities)


class GWTelemetrySensor(GWEnergyPilotEntity, SensorEntity):
    """Generic coordinator-backed GoodWe ETA telemetry sensor."""

    entity_description: GWSensorEntityDescription

    def __init__(
        self,
        entry: GWConfigEntry,
        description: GWSensorEntityDescription,
    ) -> None:
        super().__init__(entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        if description.diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> Any:
        """Return the latest decoded register value."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.values.get(self.entity_description.key)


class GWEMSModeSensor(GWEnergyPilotEntity, SensorEntity):
    """Current EMS mode."""

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
    """Current EMS power setpoint."""

    _attr_translation_key = "ems_setpoint"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_ems_setpoint"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.power if self.coordinator.data else None


class GWControlCommandSensor(GWEnergyPilotEntity, SensorEntity):
    """Current EnergyPilot control command."""

    _attr_translation_key = "control_command"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_control_command"

    @property
    def native_value(self) -> str:
        return self.entry.runtime_data.controller.last_command


class GWTargetPowerSensor(GWEnergyPilotEntity, SensorEntity):
    """Current EnergyPilot target power."""

    _attr_translation_key = "target_power"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_target_power"

    @property
    def native_value(self) -> int:
        return self.entry.runtime_data.controller.target_power


class GWEVActiveSensor(GWEnergyPilotEntity, SensorEntity):
    """Optional EV charging status."""

    _attr_translation_key = "ev_status"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_ev_status"

    @property
    def native_value(self) -> str:
        return "active" if self.entry.runtime_data.controller.ev_is_active() else "inactive"
