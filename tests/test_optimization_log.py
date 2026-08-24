"""Tests for the bounded GW EnergyPilot optimization history log."""

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


def _reset_modules() -> None:
    for name in list(sys.modules):
        if name == "custom_components" or name.startswith(PACKAGE_NAME):
            del sys.modules[name]
        elif name == "homeassistant" or name.startswith("homeassistant."):
            del sys.modules[name]


class FakeStore:
    """Small in-memory stand-in for Home Assistant Store."""

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


def _load_optimization_log():
    _reset_modules()

    custom_components = _module("custom_components")
    custom_components.__path__ = [str(CUSTOM_COMPONENTS)]
    package = _module(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_DIR)]
    package.__package__ = PACKAGE_NAME

    homeassistant = _module("homeassistant")
    homeassistant.__path__ = []

    class HomeAssistant:
        pass

    core = _module("homeassistant.core", HomeAssistant=HomeAssistant)
    homeassistant.core = core

    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    homeassistant.helpers = helpers
    storage = _module("homeassistant.helpers.storage", Store=FakeStore)
    helpers.storage = storage

    importlib.import_module(f"{PACKAGE_NAME}.const")
    return importlib.import_module(f"{PACKAGE_NAME}.optimization_log")


class OptimizationLogTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        FakeStore.data_by_key = {}

    async def test_history_survives_new_instance(self):
        module = _load_optimization_log()
        first = module.GWEnergyPilotOptimizationLog(object(), "entry-1")
        await first.async_append({"reason": "manual_button", "success": True})

        second = module.GWEnergyPilotOptimizationLog(object(), "entry-1")
        history = await second.async_history()

        self.assertEqual(
            history,
            [{"reason": "manual_button", "success": True}],
        )

    async def test_history_keeps_only_newest_fifty_records(self):
        module = _load_optimization_log()
        log = module.GWEnergyPilotOptimizationLog(object(), "entry-1")

        for index in range(55):
            await log.async_append({"index": index})

        history = await log.async_history()
        self.assertEqual(len(history), module.OPTIMIZATION_LOG_LIMIT)
        self.assertEqual(history[0]["index"], 5)
        self.assertEqual(history[-1]["index"], 54)

    async def test_invalid_stored_history_fails_safe(self):
        module = _load_optimization_log()
        key = f"{module.OPTIMIZATION_LOG_KEY}.entry-1"
        FakeStore.data_by_key[key] = {"history": "not-a-list"}

        log = module.GWEnergyPilotOptimizationLog(object(), "entry-1")
        self.assertEqual(await log.async_history(), [])


if __name__ == "__main__":
    unittest.main()
