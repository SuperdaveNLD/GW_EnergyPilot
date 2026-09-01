"""Unit tests for hardware-independent Modbus decoding helpers."""

from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
CUSTOM_COMPONENTS = ROOT / "custom_components"
PACKAGE_DIR = CUSTOM_COMPONENTS / "gw_energypilot"
PACKAGE_NAME = "custom_components.gw_energypilot"


def _module(name: str, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_modules():
    for name in list(sys.modules):
        if name == "custom_components" or name.startswith(PACKAGE_NAME):
            del sys.modules[name]
        elif name == "pymodbus" or name.startswith("pymodbus."):
            del sys.modules[name]

    custom_components = _module("custom_components")
    custom_components.__path__ = [str(CUSTOM_COMPONENTS)]

    package = _module(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_DIR)]
    package.__package__ = PACKAGE_NAME

    pymodbus = _module("pymodbus")
    pymodbus.__path__ = []

    class AsyncModbusTcpClient:
        pass

    class ModbusException(Exception):
        pass

    client_stub = _module("pymodbus.client", AsyncModbusTcpClient=AsyncModbusTcpClient)
    exceptions_stub = _module("pymodbus.exceptions", ModbusException=ModbusException)
    pymodbus.client = client_stub
    pymodbus.exceptions = exceptions_stub

    registers = importlib.import_module(f"{PACKAGE_NAME}.registers")
    client = importlib.import_module(f"{PACKAGE_NAME}.client")
    return registers, client


registers, client = _load_modules()


class FakeResponse:
    def __init__(self, registers=None, error: bool = False) -> None:
        self.registers = registers
        self._error = error

    def isError(self) -> bool:
        return self._error


class FakeModbusClient:
    def __init__(self) -> None:
        self.connected = True
        self.values = {45356: 10, 45357: 0, 45358: 12, 47511: 8, 47512: 0}
        self.fail_reads: set[int] = set()
        self.writes: list[tuple[int, int, int]] = []

    async def write_register(self, address: int, value: int, device_id: int):
        self.writes.append((address, value, device_id))
        self.values[address] = value
        return FakeResponse()

    async def read_holding_registers(self, start: int, count: int, device_id: int):
        if start in self.fail_reads:
            return FakeResponse(error=True)
        return FakeResponse([self.values[start + offset] for offset in range(count)])

    def close(self) -> None:
        self.connected = False


def _beta_test_client():
    instance = object.__new__(client.GWModbusClient)
    instance.host = "127.0.0.1"
    instance.port = 502
    instance.slave = 247
    instance._client = FakeModbusClient()
    instance._lock = asyncio.Lock()
    return instance


class ModbusDecodingTests(unittest.TestCase):
    def test_uint64_extended_meter_counter_big_endian_and_scaled(self):
        definition = registers.RegisterDefinition(
            "candidate",
            36104,
            registers.RegisterDataType.UINT64,
            0.01,
            3,
        )
        register_map = {
            36104: 0x0000,
            36105: 0x0001,
            36106: 0x0002,
            36107: 0x0003,
        }

        raw = (0x0000 << 48) | (0x0001 << 32) | (0x0002 << 16) | 0x0003
        expected = round(raw * 0.01, 3)

        self.assertEqual(
            client.GWModbusClient._decode_value(register_map, definition),
            expected,
        )

    def test_uint64_definition_requires_four_words(self):
        definition = registers.RegisterDefinition(
            "candidate",
            36120,
            registers.RegisterDataType.UINT64,
        )
        self.assertEqual(registers.register_word_count(definition), 4)

    def test_all_beta_registers_are_covered_by_optional_blocks(self):
        self.assertEqual(registers.find_uncovered_registers(), ())
        self.assertIn((36092, 32), registers.OPTIONAL_TELEMETRY_BLOCKS)
        self.assertIn((45356, 1), registers.OPTIONAL_TELEMETRY_BLOCKS)
        self.assertIn((45358, 1), registers.OPTIONAL_TELEMETRY_BLOCKS)
        self.assertIn((47500, 1), registers.OPTIONAL_TELEMETRY_BLOCKS)

    def test_beta_soc_write_keys_resolve_to_canonical_registers(self):
        definitions = {definition.key: definition.address for definition in registers.REGISTER_DEFINITIONS}
        self.assertEqual(definitions["battery_discharge_depth_on_grid"], 45356)
        self.assertEqual(definitions["battery_discharge_depth_off_grid"], 45358)
        self.assertEqual(
            set(client.BETA_SOC_FLOOR_KEYS),
            {"battery_discharge_depth_on_grid", "battery_discharge_depth_off_grid"},
        )


class BetaSocWriteTests(unittest.IsolatedAsyncioTestCase):
    async def test_cloud_control_readback_keeps_local_soc_floor_values(self):
        instance = _beta_test_client()

        snapshot = await instance.async_read_control_status()

        self.assertEqual(snapshot.values["ems_mode"], 8)
        self.assertEqual(snapshot.values["ems_setpoint"], 0)
        self.assertEqual(snapshot.values["battery_discharge_depth_on_grid"], 10)
        self.assertEqual(snapshot.values["battery_discharge_depth_off_grid"], 12)

    async def test_optional_soc_floor_failure_does_not_hide_ems_readback(self):
        instance = _beta_test_client()
        instance._client.fail_reads.add(45356)

        snapshot = await instance.async_read_control_status()

        self.assertEqual(
            snapshot.values,
            {
                "ems_mode": 8,
                "ems_setpoint": 0,
                "battery_discharge_depth_off_grid": 12,
            },
        )

    async def test_on_grid_soc_floor_write_is_verified(self):
        instance = _beta_test_client()

        readback = await instance.async_set_beta_soc_floor(
            "battery_discharge_depth_on_grid", 5
        )

        self.assertEqual(readback, 5)
        self.assertEqual(instance._client.writes, [(45356, 5, 247)])
        self.assertEqual(instance._client.values[45356], 5)

    async def test_off_grid_soc_floor_write_is_verified(self):
        instance = _beta_test_client()

        readback = await instance.async_set_beta_soc_floor(
            "battery_discharge_depth_off_grid", 7
        )

        self.assertEqual(readback, 7)
        self.assertEqual(instance._client.writes, [(45358, 7, 247)])

    async def test_beta_soc_floor_rejects_unknown_register_key(self):
        instance = _beta_test_client()
        with self.assertRaises(ValueError):
            await instance.async_set_beta_soc_floor("battery_soc_protection", 5)
        self.assertEqual(instance._client.writes, [])

    async def test_beta_soc_floor_rejects_out_of_range_value(self):
        instance = _beta_test_client()
        with self.assertRaises(ValueError):
            await instance.async_set_beta_soc_floor(
                "battery_discharge_depth_on_grid", 101
            )
        self.assertEqual(instance._client.writes, [])


if __name__ == "__main__":
    unittest.main()
