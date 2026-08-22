"""Modbus client for GW EnergyPilot."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import MODES_ZERO_POWER, REGISTER_EMS_MODE, REGISTER_EMS_POWER


class GWModbusError(Exception):
    """Raised when Modbus communication fails."""


@dataclass(slots=True)
class GWEMSStatus:
    """Current EMS status."""

    mode: int
    power: int


class GWModbusClient:
    """Async Modbus TCP client for the GoodWe ETA EMS registers."""

    def __init__(self, host: str, port: int, slave: int) -> None:
        self.host = host
        self.port = port
        self.slave = slave
        self._client = AsyncModbusTcpClient(host, port=port, timeout=5, retries=3)
        self._lock = asyncio.Lock()

    async def async_connect(self) -> None:
        if self._client.connected:
            return
        try:
            connected = await self._client.connect()
        except (ModbusException, OSError) as err:
            raise GWModbusError(str(err)) from err
        if not connected or not self._client.connected:
            raise GWModbusError(f"Unable to connect to {self.host}:{self.port}")

    async def async_close(self) -> None:
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

    async def async_read_status(self) -> GWEMSStatus:
        async with self._lock:
            await self._async_ensure_connected()
            try:
                response = await self._client.read_holding_registers(
                    REGISTER_EMS_MODE,
                    count=2,
                    device_id=self.slave,
                )
            except (ModbusException, OSError) as err:
                raise GWModbusError(str(err)) from err

            self._validate_response(response, "reading EMS status")
            registers = getattr(response, "registers", None)
            if not registers or len(registers) < 2:
                raise GWModbusError("EMS response did not contain two registers")
            return GWEMSStatus(mode=int(registers[0]), power=int(registers[1]))

    async def async_set_mode(self, mode: int, power: int) -> None:
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
