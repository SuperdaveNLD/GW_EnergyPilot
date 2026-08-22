"""Modbus client for GW EnergyPilot."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import MODES_ZERO_POWER, REGISTER_EMS_MODE, REGISTER_EMS_POWER
from .registers import (
    REGISTER_DEFINITIONS,
    TELEMETRY_BLOCKS,
    RegisterDataType,
    RegisterDefinition,
)


class GWModbusError(Exception):
    """Raised when Modbus communication fails."""


@dataclass(slots=True)
class GWETAData:
    """Current GoodWe ETA telemetry snapshot."""

    values: dict[str, int | float]

    @property
    def mode(self) -> int | None:
        value = self.values.get("ems_mode")
        return int(value) if value is not None else None

    @property
    def power(self) -> int | None:
        value = self.values.get("ems_setpoint")
        return int(value) if value is not None else None


class GWModbusClient:
    """Async Modbus TCP client for a GoodWe ETA inverter."""

    def __init__(self, host: str, port: int, slave: int) -> None:
        self.host = host
        self.port = port
        self.slave = slave
        self._client = AsyncModbusTcpClient(host, port=port, timeout=5, retries=3)
        self._lock = asyncio.Lock()

    async def async_connect(self) -> None:
        """Connect to the inverter."""
        if self._client.connected:
            return
        try:
            connected = await self._client.connect()
        except (ModbusException, OSError) as err:
            raise GWModbusError(str(err)) from err
        if not connected or not self._client.connected:
            raise GWModbusError(f"Unable to connect to {self.host}:{self.port}")

    async def async_close(self) -> None:
        """Close the Modbus connection."""
        self._client.close()

    async def _async_ensure_connected(self) -> None:
        if not self._client.connected:
            await self.async_connect()

    @staticmethod
    def _validate_response(response: object, context: str) -> None:
        if response is None:
            raise GWModbusError(f"No response while {context}")
        is_error = getattr(response, "isError", None)
        if callable(is_error) and is_error():
            raise GWModbusError(f"Modbus error while {context}: {response}")

    @staticmethod
    def _unsigned_to_signed(value: int, bits: int) -> int:
        sign_bit = 1 << (bits - 1)
        return value - (1 << bits) if value & sign_bit else value

    @classmethod
    def _decode_value(
        cls,
        register_map: dict[int, int],
        definition: RegisterDefinition,
    ) -> int | float:
        """Decode one value using Home Assistant Modbus-style big-endian words."""
        address = definition.address
        if definition.data_type in (RegisterDataType.UINT16, RegisterDataType.INT16):
            raw = register_map[address]
            if definition.data_type == RegisterDataType.INT16:
                raw = cls._unsigned_to_signed(raw, 16)
        else:
            raw = (register_map[address] << 16) | register_map[address + 1]
            if definition.data_type == RegisterDataType.INT32:
                raw = cls._unsigned_to_signed(raw, 32)

        value = raw * definition.scale
        if definition.precision is not None:
            return round(value, definition.precision)
        if definition.scale == 1:
            return int(value)
        return value

    async def _async_read_block(self, start: int, count: int) -> list[int]:
        """Read one contiguous holding-register block."""
        try:
            response = await self._client.read_holding_registers(
                start,
                count=count,
                device_id=self.slave,
            )
        except (ModbusException, OSError) as err:
            raise GWModbusError(str(err)) from err

        self._validate_response(response, f"reading registers {start}-{start + count - 1}")
        registers = getattr(response, "registers", None)
        if registers is None or len(registers) != count:
            raise GWModbusError(
                f"Register block {start}-{start + count - 1} returned an unexpected length"
            )
        return [int(register) for register in registers]

    async def async_read_data(self) -> GWETAData:
        """Read the GoodWe ETA runtime telemetry used by EnergyPilot."""
        async with self._lock:
            await self._async_ensure_connected()

            register_map: dict[int, int] = {}
            for start, count in TELEMETRY_BLOCKS:
                registers = await self._async_read_block(start, count)
                register_map.update(
                    {start + offset: value for offset, value in enumerate(registers)}
                )

            values = {
                definition.key: self._decode_value(register_map, definition)
                for definition in REGISTER_DEFINITIONS
            }
            return GWETAData(values=values)

    async def async_read_status(self) -> GWETAData:
        """Read data for setup validation and backward compatibility."""
        return await self.async_read_data()

    async def async_set_mode(self, mode: int, power: int) -> None:
        """Set GoodWe EMS power first, then EMS mode."""
        if mode < 1 or mode > 12:
            raise ValueError("EMS mode must be between 1 and 12")

        power = max(0, min(int(power), 15000))
        if mode in MODES_ZERO_POWER:
            power = 0

        async with self._lock:
            await self._async_ensure_connected()
            try:
                response = await self._client.write_register(
                    REGISTER_EMS_POWER,
                    power,
                    device_id=self.slave,
                )
                self._validate_response(response, "writing EMS power")

                await asyncio.sleep(2)

                response = await self._client.write_register(
                    REGISTER_EMS_MODE,
                    mode,
                    device_id=self.slave,
                )
                self._validate_response(response, "writing EMS mode")
            except (ModbusException, OSError) as err:
                raise GWModbusError(str(err)) from err
