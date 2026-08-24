"""Tests for persistent GW EnergyPilot orchestrator runtime state."""

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
    fixed_now = datetime(2026, 8, 23, 18, 31, tzinfo=timezone.utc)
    dt_module = _module(
        "homeassistant.util.dt",
        as_local=lambda value: value,
        now=lambda: fixed_now,
        utcnow=lambda: fixed_now,
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
            self.last_soc_init = None
            self.last_price_area = None
            self.last_price_points = 0
            self.last_load_points = 0
            self.last_p_batt = None
            self.optimize_http_status = None
            self.publish_http_status = None
            self.last_price_source = "not_checked"

        @property
        def attributes(self):
            return {"calculated_home_power": None}

        def _coordinator_number(self, key):
            return 1234.0 if key == "total_load_power" else None

        async def async_setup(self) -> None:
            self.base_setup_calls += 1

        async def async_optimize(self, reason: str = "manual") -> None:
            self.base_optimize_calls += 1
            self.last_soc_init = 0.48
            self.last_price_area = "NL"
            self.last_price_points = 48
            self.last_load_points = 25
            self.optimize_http_status = 200
            if self.fail_optimize:
                self.publish_http_status = None
                raise RuntimeError("optimization failed")
            self.publish_http_status = 200
            self.last_p_batt = -4200.0
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

    class FakeOptimizationLog:
        records: list[dict] = []

        def __init__(self, _hass, _entry_id) -> None:
            pass

        async def async_append(self, record):
            type(self).records.append(dict(record))

    _module(
        f"{PACKAGE_NAME}.optimization_log",
        GWEnergyPilotOptimizationLog=FakeOptimizationLog,
    )

    orchestrator = importlib.import_module(f"{PACKAGE_NAME}.orchestrator_v013")
    return orchestrator, FakeRuntimeStore, FakeOptimizationLog


class FakeHass:
    def __init__(self) -> None:
        self.dispatched = []


class FakeEntry:
    def __init__(self, options=None) -> None:
        self.entry_id = "entry-1"
        self.options = dict(options or {})


class OrchestratorPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_setup_restores_last_success_before_base_setup(self):
        orchestrator_module, fake_store, fake_log = _load_v013_orchestrator()
        restored = datetime(2026, 8, 23, 17, 0, tzinfo=timezone.utc)
        fake_store.persisted = restored
        fake_store.save_calls = []
        fake_log.records = []
        orchestrator = orchestrator_module.GWEnergyPilotOrchestrator(
            FakeHass(),
            FakeEntry(),
            object(),
        )

        await orchestrator.async_setup()

        self.assertEqual(orchestrator.last_success, restored)
        self.assertEqual(orchestrator.base_setup_calls, 1)

    async def test_successful_optimization_replaces_persisted_timestamp_and_logs(self):
        orchestrator_module, fake_store, fake_log = _load_v013_orchestrator()
        fake_store.persisted = datetime(2026, 8, 23, 17, 0, tzinfo=timezone.utc)
        fake_store.save_calls = []
        fake_log.records = []
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
        self.assertEqual(len(fake_log.records), 1)
        record = fake_log.records[0]
        self.assertTrue(record["success"])
        self.assertEqual(record["reason"], "manual_button")
        self.assertEqual(record["soc_init"], 0.48)
        self.assertEqual(record["current_load"], 1234.0)
        self.assertEqual(record["price_points"], 48)
        self.assertEqual(record["load_forecast_points"], 25)
        self.assertEqual(record["p_batt"], -4200.0)
        self.assertIsNone(record["error"])

    async def test_failed_optimization_keeps_success_and_logs_failure(self):
        orchestrator_module, fake_store, fake_log = _load_v013_orchestrator()
        previous = datetime(2026, 8, 23, 17, 0, tzinfo=timezone.utc)
        fake_store.persisted = previous
        fake_store.save_calls = []
        fake_log.records = []
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
        self.assertEqual(len(fake_log.records), 1)
        record = fake_log.records[0]
        self.assertFalse(record["success"])
        self.assertEqual(record["reason"], "scheduled")
        self.assertEqual(record["error"], "optimization failed")
        self.assertIsNone(record["p_batt"])


if __name__ == "__main__":
    unittest.main()
