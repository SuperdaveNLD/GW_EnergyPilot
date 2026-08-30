"""Tests for persistent EMS setpoint-write evidence."""

from __future__ import annotations

from datetime import datetime, timezone
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


class FakeStore:
    data_by_key: dict[str, dict] = {}

    def __class_getitem__(cls, _item):
        return cls

    def __init__(self, _hass, _version, key):
        self.key = key

    async def async_load(self):
        data = self.data_by_key.get(self.key)
        return dict(data) if data is not None else None

    async def async_save(self, data):
        self.data_by_key[self.key] = dict(data)


def _load_control_history():
    for name in list(sys.modules):
        if name == "custom_components" or name.startswith(PACKAGE_NAME):
            del sys.modules[name]
        elif name == "homeassistant" or name.startswith("homeassistant."):
            del sys.modules[name]

    custom_components = _module("custom_components")
    custom_components.__path__ = [str(CUSTOM_COMPONENTS)]
    package = _module(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_DIR)]
    package.__package__ = PACKAGE_NAME

    homeassistant = _module("homeassistant")
    homeassistant.__path__ = []
    core = _module("homeassistant.core", HomeAssistant=object)
    homeassistant.core = core
    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    homeassistant.helpers = helpers
    storage = _module("homeassistant.helpers.storage", Store=FakeStore)
    helpers.storage = storage

    importlib.import_module(f"{PACKAGE_NAME}.const")
    return importlib.import_module(f"{PACKAGE_NAME}.control_history")


class ControlHistoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        FakeStore.data_by_key = {}

    async def test_successful_setpoint_write_evidence_survives_restart(self):
        module = _load_control_history()
        timestamp = datetime(2026, 8, 30, 8, 15, 2, tzinfo=timezone.utc)
        first = module.GWEnergyPilotControlHistory(object(), "entry-1")
        first.record(
            timestamp,
            setpoint=3750,
            mode=9,
            command="grid_import_target",
        )
        await first.async_save()

        restored = module.GWEnergyPilotControlHistory(object(), "entry-1")
        await restored.async_restore()

        self.assertEqual(restored.last_ems_setpoint_updated_at, timestamp)
        self.assertEqual(restored.last_ems_setpoint, 3750)
        self.assertEqual(restored.last_ems_mode, 9)
        self.assertEqual(restored.last_command, "grid_import_target")

    async def test_invalid_history_is_ignored(self):
        module = _load_control_history()
        key = f"{module.CONTROL_HISTORY_STORE_KEY}.entry-1"
        FakeStore.data_by_key[key] = {
            "last_ems_setpoint_updated_at": "not-a-timestamp",
            "last_ems_setpoint": 3750,
            "last_ems_mode": 9,
        }
        history = module.GWEnergyPilotControlHistory(object(), "entry-1")

        await history.async_restore()

        self.assertIsNone(history.last_ems_setpoint_updated_at)

    async def test_naive_timestamp_is_rejected(self):
        module = _load_control_history()
        history = module.GWEnergyPilotControlHistory(object(), "entry-1")
        with self.assertRaises(ValueError):
            history.record(
                datetime(2026, 8, 30, 8, 15, 2),
                setpoint=3750,
                mode=9,
                command="grid_import_target",
            )


if __name__ == "__main__":
    unittest.main()
