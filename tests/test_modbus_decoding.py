"""Unit tests for hardware-independent Modbus decoding helpers."""

from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
