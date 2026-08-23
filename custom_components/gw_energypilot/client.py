"""Modbus client for GW EnergyPilot."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
from struct import pack, unpack

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import MODES_ZERO_POWER, REGISTER_EMS_MODE, REGISTER_EMS_POWER
from .registers import (
    OPTIONAL_TELEMETRY_BLOCKS,
    REGISTER_DEFINITIONS,
    TELEMETRY_BLOCKS,
    RegisterDataType,
    RegisterDefinition,
)

_LOGGER = logging.getLogger(__name__)


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
    """Async Modbus TCP client for a GoodWe ETA G20 inverter."""

    def __init__(self, host: str, port: int, slave: int) -> None:
        self.host = host
        self.port = port
        self.slave = slave
        # G20 is a local LAN device. Long retry chains make an inverter that is
        # asleep/offline look like a Home Assistant startup problem. A short
        # timeout lets the coordinator mark telemetry unavailable and retry on
        # the normal polling schedule instead.
        self._client = AsyncModbusTcpClient(host, port=port, timeout=3, retries=1)
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
        """Decode one GoodWe holding-register value."""
        address = definition.address
        if definition.data_type in (RegisterDataType.UINT16, RegisterDataType.INT16):
            raw: int | float = register_map[address]
            if definition.data_type == RegisterDataType.INT16:
                raw = cls._unsigned_to_signed(int(raw), 16)
        elif definition.data_type == RegisterDataType.FLOAT32:
            raw_bytes = pack(">HH", register_map[address], register_map[address + 1])
            raw = float(unpack(">f", raw_bytes)[0])
        elif definition.data_type == RegisterDataType.UINT64:
            raw = 0
            for offset in range(4):
                raw = (int(raw) << 16) | register_map[address + offset]
        else:
            raw = (register_map[address] << 16) | register_map[address + 1]
            if definition.data_type == RegisterDataType.INT32:
                raw = cls._unsigned_to_signed(int(raw), 32)

        value = float(raw) * definition.scale
        if definition.precision is not None:
            return round(value, definition.precision)
        if definition.scale == 1 and definition.data_type != RegisterDataType.FLOAT32:
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
            self._client.close()
            raise GWModbusError(str(err)) from err

        try:
            self._validate_response(
                response, f"reading registers {start}-{start + count - 1}"
            )
        except GWModbusError:
            self._client.close()
            raise

        registers = getattr(response, "registers", None)
        if registers is None or len(registers) != count:
            self._client.close()
            raise GWModbusError(
                f"Register block {start}-{start + count - 1} returned an unexpected length"
            )
        return [int(register) for register in registers]

    async def async_read_data(self) -> GWETAData:
        """Read GoodWe ETA G20 runtime telemetry used by EnergyPilot."""
        async with self._lock:
            await self._async_ensure_connected()

            register_map: dict[int, int] = {}
            for start, count in TELEMETRY_BLOCKS:
                registers = await self._async_read_block(start, count)
                register_map.update(
                    {start + offset: value for offset, value in enumerate(registers)}
                )

            for start, count in OPTIONAL_TELEMETRY_BLOCKS:
                try:
                    # A rejected optional register read closes the Modbus socket.
                    # Reconnect before every optional block so one unsupported
                    # diagnostic range cannot suppress the remaining ranges.
                    await self._async_ensure_connected()
                    registers = await self._async_read_block(start, count)
                except GWModbusError as err:
                    _LOGGER.debug(
                        "Optional GoodWe register block %s-%s unavailable: %s",
                        start,
                        start + count - 1,
                        err,
                    )
                    continue
                register_map.update(
                    {start + offset: value for offset, value in enumerate(registers)}
                )

            values: dict[str, int | float] = {}
            for definition in REGISTER_DEFINITIONS:
                try:
                    values[definition.key] = self._decode_value(
                        register_map,
                        definition,
                    )
                except KeyError:
                    continue

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
                self._client.close()
                raise GWModbusError(str(err)) from err
