"""Tests for persistent GW EnergyPilot orchestrator runtime state."""

from __future__ import annotations

import asyncio
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


def _reset_modules() -> None:
    for name in list(sys.modules):
        if name == "custom_components" or name.startswith(PACKAGE_NAME):
            del sys.modules[name]
        elif name == "homeassistant" or name.startswith("homeassistant."):
            del sys.modules[name]


def _setup_package() -> None:
    custom_components = _module("custom_components")
    custom_components.__path__ = [str(CUSTOM_COMPONENTS)]

    package = _module(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_DIR)]
    package.__package__ = PACKAGE_NAME


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


def _load_runtime_store():
    _reset_modules()
    _setup_package()

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
    return importlib.import_module(f"{PACKAGE_NAME}.runtime_store")


class RuntimeStoreTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        FakeStore.data_by_key = {}

    async def test_last_success_survives_new_store_instance(self):
        runtime_store = _load_runtime_store()
        timestamp = datetime(2026, 8, 23, 18, 15, 32, tzinfo=timezone.utc)

        first = runtime_store.GWEnergyPilotRuntimeStore(object(), "entry-1")
        await first.async_save_last_success(timestamp)

        second = runtime_store.GWEnergyPilotRuntimeStore(object(), "entry-1")
        restored = await second.async_load_last_success()

        self.assertEqual(restored, timestamp)

    async def test_invalid_stored_timestamp_is_ignored(self):
        runtime_store = _load_runtime_store()
        key = f"{runtime_store.RUNTIME_STORE_KEY}.entry-1"
        FakeStore.data_by_key[key] = {"last_success": "not-a-timestamp"}

        store = runtime_store.GWEnergyPilotRuntimeStore(object(), "entry-1")

        self.assertIsNone(await store.async_load_last_success())

    async def test_naive_timestamp_is_not_persisted(self):
        runtime_store = _load_runtime_store()
        store = runtime_store.GWEnergyPilotRuntimeStore(object(), "entry-1")

        with self.assertRaises(ValueError):
            await store.async_save_last_success(datetime(2026, 8, 23, 18, 15, 32))


def _load_v013_orchestrator():
    _reset_modules()
    _setup_package()

    homeassistant = _module("homeassistant")
    homeassistant.__path__ = []

    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    homeassistant.helpers = helpers

    def async_dispatcher_send(hass, signal, *args):
        hass.dispatched.append((signal, args))

    dispatcher = _module(
        "homeassistant.helpers.dispatcher",
        async_dispatcher_send=async_dispatcher_send,
    )
    helpers.dispatcher = dispatcher

    util = _module("homeassistant.util")
    util.__path__ = []
    dt_module = _module(
        "homeassistant.util.dt",
        as_local=lambda value: value,
        now=lambda: datetime.now(timezone.utc),
    )
    util.dt = dt_module
    homeassistant.util = util

    importlib.import_module(f"{PACKAGE_NAME}.const")

    class FakeBaseOrchestrator:
        def __init__(self, hass, entry, coordinator) -> None:
            self.hass = hass
            self.entry = entry
            self.coordinator = coordinator
            self.last_success = None
            self.signal = "test-orchestrator-signal"
            self.base_setup_calls = 0
            self.base_optimize_calls = 0
            self.fail_optimize = False

        @property
        def attributes(self):
            return {"calculated_home_power": None}

        async def async_setup(self) -> None:
            self.base_setup_calls += 1

        async def async_optimize(self, reason: str = "manual") -> None:
            self.base_optimize_calls += 1
            if self.fail_optimize:
                raise RuntimeError("optimization failed")
            self.last_success = datetime(
                2026,
                8,
                23,
                18,
                30,
                0,
                tzinfo=timezone.utc,
            )

    _module(
        f"{PACKAGE_NAME}.orchestrator_v012",
        GWEnergyPilotOrchestrator=FakeBaseOrchestrator,
    )

    class FakeRuntimeStore:
        persisted: datetime | None = None
        save_calls: list[datetime] = []

        def __init__(self, _hass, _entry_id) -> None:
            pass

        async def async_load_last_success(self):
            return type(self).persisted

        async def async_save_last_success(self, timestamp):
            type(self).persisted = timestamp
            type(self).save_calls.append(timestamp)

    _module(
        f"{PACKAGE_NAME}.runtime_store",
        GWEnergyPilotRuntimeStore=FakeRuntimeStore,
    )

    orchestrator = importlib.import_module(f"{PACKAGE_NAME}.orchestrator_v013")
    return orchestrator, FakeRuntimeStore


class FakeHass:
    def __init__(self) -> None:
        self.dispatched = []


class FakeEntry:
    def __init__(self, options=None) -> None:
        self.entry_id = "entry-1"
        self.options = dict(options or {})


class OrchestratorPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_setup_restores_last_success_before_base_setup(self):
        orchestrator_module, fake_store = _load_v013_orchestrator()
        restored = datetime(2026, 8, 23, 17, 0, tzinfo=timezone.utc)
        fake_store.persisted = restored
        fake_store.save_calls = []
        orchestrator = orchestrator_module.GWEnergyPilotOrchestrator(
            FakeHass(),
            FakeEntry(),
            object(),
        )

        await orchestrator.async_setup()

        self.assertEqual(orchestrator.last_success, restored)
        self.assertEqual(orchestrator.base_setup_calls, 1)

    async def test_successful_optimization_replaces_persisted_timestamp(self):
        orchestrator_module, fake_store = _load_v013_orchestrator()
        fake_store.persisted = datetime(2026, 8, 23, 17, 0, tzinfo=timezone.utc)
        fake_store.save_calls = []
        orchestrator = orchestrator_module.GWEnergyPilotOrchestrator(
            FakeHass(),
            FakeEntry(),
            object(),
        )
        await orchestrator.async_setup()

        await orchestrator.async_optimize(reason="manual_button")

        expected = datetime(2026, 8, 23, 18, 30, tzinfo=timezone.utc)
        self.assertEqual(orchestrator.last_success, expected)
        self.assertEqual(fake_store.persisted, expected)
        self.assertEqual(fake_store.save_calls, [expected])
        self.assertEqual(orchestrator.base_optimize_calls, 1)

    async def test_failed_optimization_keeps_previous_persisted_success(self):
        orchestrator_module, fake_store = _load_v013_orchestrator()
        previous = datetime(2026, 8, 23, 17, 0, tzinfo=timezone.utc)
        fake_store.persisted = previous
        fake_store.save_calls = []
        orchestrator = orchestrator_module.GWEnergyPilotOrchestrator(
            FakeHass(),
            FakeEntry(),
            object(),
        )
        await orchestrator.async_setup()
        orchestrator.fail_optimize = True

        with self.assertRaisesRegex(RuntimeError, "optimization failed"):
            await orchestrator.async_optimize(reason="scheduled")

        self.assertEqual(orchestrator.last_success, previous)
        self.assertEqual(fake_store.persisted, previous)
        self.assertEqual(fake_store.save_calls, [])


if __name__ == "__main__":
    unittest.main()
