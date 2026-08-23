"""GoodWe ETA runtime Modbus register definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RegisterDataType(StrEnum):
    """Supported register data types."""

    UINT16 = "uint16"
    INT16 = "int16"
    UINT32 = "uint32"
    INT32 = "int32"
    FLOAT32 = "float32"


@dataclass(frozen=True, slots=True)
class RegisterDefinition:
    """Describe one GoodWe ETA register value."""

    key: str
    address: int
    data_type: RegisterDataType
    scale: float = 1.0
    precision: int | None = None


# Canonical runtime read layout. Keep the final word of every 32-bit/float
# definition inside its block. All ranges are holding registers and remain
# below the Modbus 125-register request limit.
TELEMETRY_BLOCKS: tuple[tuple[int, int], ...] = (
    (35103, 88),
    (35212, 10),
    (35301, 36),
    (36003, 55),
    (37002, 22),
    (47509, 4),
)

# Register 47000 is useful diagnostic information but is not available on every
# tested/related device, so a failure to read this block must not fail the main
# telemetry refresh.
OPTIONAL_TELEMETRY_BLOCKS: tuple[tuple[int, int], ...] = (
    (47000, 1),
)


REGISTER_DEFINITIONS: tuple[RegisterDefinition, ...] = (
    RegisterDefinition("grid_mode", 35136, RegisterDataType.UINT16),
    RegisterDefinition("warning_code", 35185, RegisterDataType.UINT16),
    RegisterDefinition("work_mode", 35187, RegisterDataType.UINT16),
    RegisterDefinition("operation_mode", 35188, RegisterDataType.UINT16),
    RegisterDefinition("error_message", 35189, RegisterDataType.UINT32),
    RegisterDefinition("diagnose_result", 35220, RegisterDataType.UINT32),

    RegisterDefinition("pv1_voltage", 35103, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("pv1_current", 35104, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("pv1_power", 35105, RegisterDataType.UINT32),
    RegisterDefinition("pv2_voltage", 35107, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("pv2_current", 35108, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("pv2_power", 35109, RegisterDataType.UINT32),
    RegisterDefinition("pv3_voltage", 35111, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("pv3_current", 35112, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("pv3_power", 35113, RegisterDataType.UINT32),
    RegisterDefinition("pv4_voltage", 35115, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("pv4_current", 35116, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("pv4_power", 35117, RegisterDataType.UINT32),
    RegisterDefinition("pv_total_power", 35301, RegisterDataType.UINT32),

    RegisterDefinition("inverter_l1_voltage", 35121, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("inverter_l1_current", 35122, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("inverter_l1_frequency", 35123, RegisterDataType.UINT16, 0.01, 2),
    RegisterDefinition("inverter_l1_power", 35125, RegisterDataType.INT16),
    RegisterDefinition("inverter_l2_voltage", 35126, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("inverter_l2_current", 35127, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("inverter_l2_frequency", 35128, RegisterDataType.UINT16, 0.01, 2),
    RegisterDefinition("inverter_l2_power", 35130, RegisterDataType.INT16),
    RegisterDefinition("inverter_l3_voltage", 35131, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("inverter_l3_current", 35132, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("inverter_l3_frequency", 35133, RegisterDataType.UINT16, 0.01, 2),
    RegisterDefinition("inverter_l3_power", 35135, RegisterDataType.INT16),
    RegisterDefinition("total_inverter_power", 35138, RegisterDataType.INT16),
    RegisterDefinition("ac_active_power", 35140, RegisterDataType.INT16),

    RegisterDefinition("load_l1_power", 35164, RegisterDataType.INT16),
    RegisterDefinition("load_l2_power", 35166, RegisterDataType.INT16),
    RegisterDefinition("load_l3_power", 35168, RegisterDataType.INT16),
    RegisterDefinition("total_backup_load_power", 35170, RegisterDataType.INT16),
    RegisterDefinition("total_load_power", 35172, RegisterDataType.INT16),

    RegisterDefinition("inverter_air_temperature", 35174, RegisterDataType.INT16, 0.1, 1),
    RegisterDefinition("inverter_module_temperature", 35175, RegisterDataType.INT16, 0.1, 1),
    RegisterDefinition("inverter_radiator_temperature", 35176, RegisterDataType.INT16, 0.1, 1),

    RegisterDefinition("battery_voltage", 35180, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("battery_current", 35181, RegisterDataType.INT16, 0.1, 1),
    RegisterDefinition("battery_power", 35182, RegisterDataType.INT32),
    RegisterDefinition("battery_mode", 35184, RegisterDataType.UINT16),
    RegisterDefinition("battery_strings", 35212, RegisterDataType.UINT16),

    RegisterDefinition("warning_message_32bit", 35328, RegisterDataType.UINT32),
    RegisterDefinition("error_message_extended_32bit", 35333, RegisterDataType.UINT32),
    RegisterDefinition("warning_message_extended_32bit", 35335, RegisterDataType.UINT32),

    # Smart meter. GoodWe exposes the cumulative energy registers as IEEE-754
    # big-endian float32 values scaled by 1000 to kWh.
    RegisterDefinition("meter_test_status", 36003, RegisterDataType.UINT16),
    RegisterDefinition("meter_communication", 36004, RegisterDataType.UINT16),
    RegisterDefinition("meter_l1_power_fast", 36005, RegisterDataType.INT16),
    RegisterDefinition("meter_l2_power_fast", 36006, RegisterDataType.INT16),
    RegisterDefinition("meter_l3_power_fast", 36007, RegisterDataType.INT16),
    RegisterDefinition("meter_total_power_fast", 36008, RegisterDataType.INT16),
    RegisterDefinition("meter_frequency", 36014, RegisterDataType.UINT16, 0.01, 2),
    RegisterDefinition("meter_total_energy_export", 36015, RegisterDataType.FLOAT32, 0.001, 3),
    RegisterDefinition("meter_total_energy_import", 36017, RegisterDataType.FLOAT32, 0.001, 3),
    RegisterDefinition("meter_l1_active_power", 36019, RegisterDataType.INT32),
    RegisterDefinition("meter_l2_active_power", 36021, RegisterDataType.INT32),
    RegisterDefinition("meter_l3_active_power", 36023, RegisterDataType.INT32),
    RegisterDefinition("meter_total_active_power", 36025, RegisterDataType.INT32),
    RegisterDefinition("meter_l1_voltage", 36052, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("meter_l2_voltage", 36053, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("meter_l3_voltage", 36054, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("meter_l1_current", 36055, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("meter_l2_current", 36056, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("meter_l3_current", 36057, RegisterDataType.UINT16, 0.1, 1),

    RegisterDefinition("bms_status", 37002, RegisterDataType.UINT16),
    RegisterDefinition("bms_package_temperature", 37003, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("bms_max_charge_current", 37004, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("bms_max_discharge_current", 37005, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("bms_error_low", 37006, RegisterDataType.UINT16),
    RegisterDefinition("battery_soc", 37007, RegisterDataType.UINT16),
    RegisterDefinition("battery_soh", 37008, RegisterDataType.UINT16),
    RegisterDefinition("bms_warning_low", 37010, RegisterDataType.UINT16),
    RegisterDefinition("bms_protocol", 37011, RegisterDataType.UINT16),
    RegisterDefinition("bms_error_high", 37012, RegisterDataType.UINT16),
    RegisterDefinition("bms_warning_high", 37013, RegisterDataType.UINT16),
    RegisterDefinition("bms_software_version", 37014, RegisterDataType.UINT16),
    RegisterDefinition("bms_hardware_version", 37015, RegisterDataType.UINT16),
    RegisterDefinition("battery_max_cell_temperature", 37020, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("battery_min_cell_temperature", 37021, RegisterDataType.UINT16, 0.1, 1),
    RegisterDefinition("battery_max_cell_voltage", 37022, RegisterDataType.UINT16, 0.001, 3),
    RegisterDefinition("battery_min_cell_voltage", 37023, RegisterDataType.UINT16, 0.001, 3),

    RegisterDefinition("app_work_mode", 47000, RegisterDataType.UINT16),
    RegisterDefinition("feed_power_enable", 47509, RegisterDataType.UINT16),
    RegisterDefinition("feed_power_parameter", 47510, RegisterDataType.UINT16),
    RegisterDefinition("ems_mode", 47511, RegisterDataType.UINT16),
    RegisterDefinition("ems_setpoint", 47512, RegisterDataType.UINT16),
)


def register_word_count(definition: RegisterDefinition) -> int:
    """Return the number of 16-bit Modbus words needed by one definition."""
    if definition.data_type in {
        RegisterDataType.UINT32,
        RegisterDataType.INT32,
        RegisterDataType.FLOAT32,
    }:
        return 2
    return 1


def find_uncovered_registers(
    blocks: tuple[tuple[int, int], ...] | None = None,
) -> tuple[str, ...]:
    """Return definition keys not fully covered by the supplied read blocks."""
    if blocks is None:
        blocks = TELEMETRY_BLOCKS + OPTIONAL_TELEMETRY_BLOCKS

    uncovered: list[str] = []
    for definition in REGISTER_DEFINITIONS:
        first = definition.address
        last = first + register_word_count(definition) - 1
        if not any(
            start <= first and last <= start + count - 1
            for start, count in blocks
        ):
            uncovered.append(definition.key)
    return tuple(uncovered)
