"""Sensors for GW EnergyPilot."""

from __future__ import annotations

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
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GWConfigEntry
from .const import CONF_ENABLE_EV_COORDINATION, MODE_NAMES
from .entity import GWEnergyPilotEntity


POWER = {
    "device_class": SensorDeviceClass.POWER,
    "native_unit_of_measurement": UnitOfPower.WATT,
    "state_class": SensorStateClass.MEASUREMENT,
}
ENERGY_TOTAL = {
    "device_class": SensorDeviceClass.ENERGY,
    "native_unit_of_measurement": UnitOfEnergy.KILO_WATT_HOUR,
    "state_class": SensorStateClass.TOTAL_INCREASING,
    "suggested_display_precision": 3,
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
    "suggested_display_precision": 1,
}

DIAGNOSTIC_DISABLED = {
    "entity_category": EntityCategory.DIAGNOSTIC,
    "entity_registry_enabled_default": False,
}
DISABLED = {"entity_registry_enabled_default": False}


TELEMETRY_SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(key="pv_total_power", name="PV total power", **POWER),
    SensorEntityDescription(key="pv1_power", name="PV1 power", **POWER),
    SensorEntityDescription(key="pv1_voltage", name="PV1 voltage", **VOLTAGE, **DISABLED),
    SensorEntityDescription(key="pv1_current", name="PV1 current", **CURRENT, **DISABLED),
    SensorEntityDescription(key="pv2_power", name="PV2 power", **POWER),
    SensorEntityDescription(key="pv2_voltage", name="PV2 voltage", **VOLTAGE, **DISABLED),
    SensorEntityDescription(key="pv2_current", name="PV2 current", **CURRENT, **DISABLED),
    SensorEntityDescription(key="pv3_power", name="PV3 power", **POWER),
    SensorEntityDescription(key="pv3_voltage", name="PV3 voltage", **VOLTAGE, **DISABLED),
    SensorEntityDescription(key="pv3_current", name="PV3 current", **CURRENT, **DISABLED),
    SensorEntityDescription(key="pv4_power", name="PV4 power", **POWER, **DISABLED),
    SensorEntityDescription(key="pv4_voltage", name="PV4 voltage", **VOLTAGE, **DISABLED),
    SensorEntityDescription(key="pv4_current", name="PV4 current", **CURRENT, **DISABLED),

    # 35138 and 35140 are inverter-side diagnostic power registers. They are
    # intentionally not labelled as inverter self-consumption or site load.
    SensorEntityDescription(
        key="total_inverter_power",
        name="Inverter total power (35138)",
        **POWER,
        **DIAGNOSTIC_DISABLED,
    ),
    SensorEntityDescription(
        key="ac_active_power",
        name="Inverter active power (35140)",
        **POWER,
        **DIAGNOSTIC_DISABLED,
    ),
    SensorEntityDescription(key="inverter_l1_power", name="Inverter L1 power", **POWER, **DISABLED),
    SensorEntityDescription(key="inverter_l1_voltage", name="Inverter L1 voltage", **VOLTAGE, **DISABLED),
    SensorEntityDescription(key="inverter_l1_current", name="Inverter L1 current", **CURRENT, **DISABLED),
    SensorEntityDescription(key="inverter_l1_frequency", name="Inverter L1 frequency", **FREQUENCY, **DISABLED),
    SensorEntityDescription(key="inverter_l2_power", name="Inverter L2 power", **POWER, **DISABLED),
    SensorEntityDescription(key="inverter_l2_voltage", name="Inverter L2 voltage", **VOLTAGE, **DISABLED),
    SensorEntityDescription(key="inverter_l2_current", name="Inverter L2 current", **CURRENT, **DISABLED),
    SensorEntityDescription(key="inverter_l2_frequency", name="Inverter L2 frequency", **FREQUENCY, **DISABLED),
    SensorEntityDescription(key="inverter_l3_power", name="Inverter L3 power", **POWER, **DISABLED),
    SensorEntityDescription(key="inverter_l3_voltage", name="Inverter L3 voltage", **VOLTAGE, **DISABLED),
    SensorEntityDescription(key="inverter_l3_current", name="Inverter L3 current", **CURRENT, **DISABLED),
    SensorEntityDescription(key="inverter_l3_frequency", name="Inverter L3 frequency", **FREQUENCY, **DISABLED),

    SensorEntityDescription(key="inverter_air_temperature", name="Inverter air temperature", **TEMPERATURE, **DISABLED),
    SensorEntityDescription(key="inverter_module_temperature", name="Inverter module temperature", **TEMPERATURE, **DISABLED),
    SensorEntityDescription(key="inverter_radiator_temperature", name="Inverter radiator temperature", **TEMPERATURE),

    SensorEntityDescription(key="load_l1_power", name="Load L1 power", **POWER, **DISABLED),
    SensorEntityDescription(key="load_l2_power", name="Load L2 power", **POWER, **DISABLED),
    SensorEntityDescription(key="load_l3_power", name="Load L3 power", **POWER, **DISABLED),
    SensorEntityDescription(key="total_backup_load_power", name="Total backup load power", **POWER, **DISABLED),
    SensorEntityDescription(key="total_load_power", name="GoodWe load power (35172)", **POWER),

    SensorEntityDescription(
        key="battery_soc",
        name="Battery state of charge",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(
        key="battery_soh",
        name="Battery state of health",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SensorEntityDescription(key="battery_power", name="Battery power", **POWER),
    SensorEntityDescription(key="battery_voltage", name="Battery voltage", **VOLTAGE),
    SensorEntityDescription(key="battery_current", name="Battery current", **CURRENT),
    SensorEntityDescription(key="battery_mode", name="Battery mode", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="battery_strings", name="Battery strings", **DIAGNOSTIC_DISABLED),

    SensorEntityDescription(key="bms_package_temperature", name="BMS package temperature", **TEMPERATURE),
    SensorEntityDescription(key="battery_max_cell_temperature", name="Battery maximum cell temperature", **TEMPERATURE),
    SensorEntityDescription(key="battery_min_cell_temperature", name="Battery minimum cell temperature", **TEMPERATURE, **DISABLED),
    SensorEntityDescription(key="battery_max_cell_voltage", name="Battery maximum cell voltage", suggested_display_precision=3, **VOLTAGE, **DISABLED),
    SensorEntityDescription(key="battery_min_cell_voltage", name="Battery minimum cell voltage", suggested_display_precision=3, **VOLTAGE, **DISABLED),
    SensorEntityDescription(key="bms_max_charge_current", name="BMS maximum charge current", **CURRENT),
    SensorEntityDescription(key="bms_max_discharge_current", name="BMS maximum discharge current", **CURRENT),
    SensorEntityDescription(key="bms_status", name="BMS status", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="bms_protocol", name="BMS protocol", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="bms_software_version", name="BMS software version", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="bms_hardware_version", name="BMS hardware version", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="bms_error_low", name="BMS error low", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="bms_warning_low", name="BMS warning low", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="bms_error_high", name="BMS error high", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="bms_warning_high", name="BMS warning high", **DIAGNOSTIC_DISABLED),

    SensorEntityDescription(key="meter_total_active_power", name="Meter total active power", **POWER, **DISABLED),
    SensorEntityDescription(key="meter_total_power_fast", name="Grid power", **POWER),
    SensorEntityDescription(key="meter_l1_active_power", name="Meter L1 active power", **POWER),
    SensorEntityDescription(key="meter_l2_active_power", name="Meter L2 active power", **POWER),
    SensorEntityDescription(key="meter_l3_active_power", name="Meter L3 active power", **POWER),
    SensorEntityDescription(key="meter_l1_power_fast", name="Meter L1 power fast", **POWER, **DISABLED),
    SensorEntityDescription(key="meter_l2_power_fast", name="Meter L2 power fast", **POWER, **DISABLED),
    SensorEntityDescription(key="meter_l3_power_fast", name="Meter L3 power fast", **POWER, **DISABLED),
    SensorEntityDescription(
        key="meter_total_energy_import",
        name="Grid energy imported total",
        **ENERGY_TOTAL,
    ),
    SensorEntityDescription(
        key="meter_total_energy_export",
        name="Grid energy exported total",
        **ENERGY_TOTAL,
    ),
    SensorEntityDescription(key="meter_l1_voltage", name="Meter L1 voltage", **VOLTAGE),
    SensorEntityDescription(key="meter_l2_voltage", name="Meter L2 voltage", **VOLTAGE),
    SensorEntityDescription(key="meter_l3_voltage", name="Meter L3 voltage", **VOLTAGE),
    SensorEntityDescription(key="meter_l1_current", name="Meter L1 current", **CURRENT),
    SensorEntityDescription(key="meter_l2_current", name="Meter L2 current", **CURRENT),
    SensorEntityDescription(key="meter_l3_current", name="Meter L3 current", **CURRENT),
    SensorEntityDescription(key="meter_frequency", name="Meter frequency", **FREQUENCY, **DISABLED),
    SensorEntityDescription(key="meter_communication", name="Meter communication", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="meter_test_status", name="Meter test status", **DIAGNOSTIC_DISABLED),

    SensorEntityDescription(key="work_mode", name="Work mode", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="operation_mode", name="Operation mode", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="grid_mode", name="Grid mode", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="warning_code", name="Warning code", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="error_message", name="Error message", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="diagnose_result", name="Diagnose result", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="warning_message_32bit", name="Warning message 32-bit", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="error_message_extended_32bit", name="Extended error message 32-bit", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="warning_message_extended_32bit", name="Extended warning message 32-bit", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="feed_power_enable", name="Feed power enable", **DIAGNOSTIC_DISABLED),
    SensorEntityDescription(key="feed_power_parameter", name="Feed power parameter", **POWER, **DIAGNOSTIC_DISABLED),
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
    ]

    if entry.options.get(CONF_ENABLE_EV_COORDINATION, False):
        entities.append(GWEVActiveSensor(entry))

    entities.extend(GWTelemetrySensor(entry, description) for description in TELEMETRY_SENSORS)
    async_add_entities(entities)


class GWTelemetrySensor(GWEnergyPilotEntity, SensorEntity):
    """Generic coordinator-backed GoodWe ETA telemetry sensor."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        entry: GWConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

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
