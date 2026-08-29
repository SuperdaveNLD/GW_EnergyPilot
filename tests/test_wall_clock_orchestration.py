"""Regression tests for wall-clock EMHASS plan ownership."""

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


def _load_orchestrator():
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

    class ClientError(Exception):
        pass

    _module("aiohttp", ClientError=ClientError)

    homeassistant = _module("homeassistant")
    homeassistant.__path__ = []

    class CoreState:
        running = "running"

    class Event:
        pass

    core = _module(
        "homeassistant.core",
        CoreState=CoreState,
        Event=Event,
        callback=lambda function: function,
    )
    homeassistant.core = core

    class HomeAssistantError(Exception):
        pass

    exceptions = _module(
        "homeassistant.exceptions", HomeAssistantError=HomeAssistantError
    )
    homeassistant.exceptions = exceptions

    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    homeassistant.helpers = helpers
    aiohttp_client = _module(
        "homeassistant.helpers.aiohttp_client",
        async_get_clientsession=lambda _hass: None,
    )
    helpers.aiohttp_client = aiohttp_client
    dispatcher = _module(
        "homeassistant.helpers.dispatcher",
        async_dispatcher_send=lambda hass, signal, *args: hass.dispatched.append(
            (signal, args)
        ),
    )
    helpers.dispatcher = dispatcher

    tracked = []

    def async_track_time_change(hass, callback, **pattern):
        record = {"callback": callback, "pattern": pattern, "cancelled": False}
        tracked.append(record)

        def cancel():
            record["cancelled"] = True

        return cancel

    event = _module(
        "homeassistant.helpers.event",
        async_call_later=lambda _hass, _delay, _callback: lambda: None,
        async_track_time_change=async_track_time_change,
    )
    helpers.event = event

    now = datetime(2026, 8, 30, 0, 0, 15, tzinfo=timezone.utc)
    util = _module("homeassistant.util")
    util.__path__ = []
    dt_module = _module(
        "homeassistant.util.dt",
        as_local=lambda value: value,
        now=lambda: now,
        utcnow=lambda: now,
    )
    util.dt = dt_module
    homeassistant.util = util

    class FakeBaseOrchestrator:
        def __init__(self, hass, entry, coordinator) -> None:
            self.hass = hass
            self.entry = entry
            self.coordinator = coordinator
            self.status = "idle"
            self.last_error = None
            self.last_success = None
            self.last_reason = None
            self.last_p_batt = None
            self.publish_http_status = None
            self._lock = asyncio.Lock()
            self._unsubs = []

        @property
        def enabled(self):
            return True

        @property
        def price_automation_enabled(self):
            return False

        @property
        def signal(self):
            return "orchestrator-signal"

        @property
        def attributes(self):
            return {}

        def _legacy_yaml_present(self):
            return False

        def _set_status(self, status, error=None):
            self.status = status
            self.last_error = error

        async def async_unload(self):
            while self._unsubs:
                self._unsubs.pop()()

    _module(
        f"{PACKAGE_NAME}.orchestrator",
        GWEnergyPilotOrchestrator=FakeBaseOrchestrator,
        OUTPUT_TIMEOUT=30,
    )
    module = importlib.import_module(f"{PACKAGE_NAME}.orchestrator_v012")
    return module, HomeAssistantError, tracked


class FakeStates:
    def get(self, _entity_id):
        return None

    def async_all(self):
        return []


class FakeConfigEntries:
    def async_entries(self, _domain):
        return []


class FakeHass:
    def __init__(self):
        self.states = FakeStates()
        self.config_entries = FakeConfigEntries()
        self.dispatched = []
        self.loop = asyncio.get_running_loop()


class FakePlanRuntime:
    def __init__(self, step_seconds):
        self.step_seconds = step_seconds

    def current_step_seconds(self):
        return self.step_seconds


class FakeController:
    def __init__(self, calls):
        self.calls = calls
        self.control_strategy = "battery"
        self.suspensions = 0

    def suspend_plan_updates(self):
        self.suspensions += 1

    def resume_plan_updates(self):
        self.suspensions -= 1

    async def async_evaluate(self):
        self.calls.append("steer")

    async def async_hold_for_plan_step(self, reason):
        self.calls.append(f"hold:{reason}")


class FakeEntry:
    def __init__(self, interval=15, step_seconds=900, calls=None):
        self.entry_id = "entry-1"
        self.options = {"emhass_optimization_interval": interval}
        calls = calls if calls is not None else []
        self.runtime_data = types.SimpleNamespace(
            plan_runtime=FakePlanRuntime(step_seconds),
            controller=FakeController(calls),
        )


class WallClockOrchestrationTests(unittest.IsolatedAsyncioTestCase):
    def make_orchestrator(self, *, interval=15, step_seconds=900):
        module, error_type, tracked = _load_orchestrator()
        calls = []
        entry = FakeEntry(interval, step_seconds, calls)
        orchestrator = module.GWEnergyPilotOrchestrator(FakeHass(), entry, object())
        return orchestrator, error_type, tracked, calls

    async def test_setup_registers_offset_wall_clock_timer_and_unload_cancels_it(self):
        orchestrator, _, tracked, _ = self.make_orchestrator()

        await orchestrator.async_setup()

        self.assertEqual(len(tracked), 1)
        self.assertEqual(tracked[0]["pattern"], {"minute": "/5", "second": 15})
        self.assertEqual(orchestrator.status, "scheduled")

        await orchestrator.async_unload()

        self.assertTrue(tracked[0]["cancelled"])
        self.assertEqual(orchestrator._unsubs, [])

    async def test_optimization_wins_when_optimize_and_plan_step_are_both_due(self):
        orchestrator, _, _, calls = self.make_orchestrator(interval=30)

        async def optimize(*, reason):
            calls.append(f"optimize:{reason}")

        async def publish():
            calls.append("publish")

        orchestrator.async_optimize = optimize
        orchestrator._async_publish_plan_step = publish

        await orchestrator._async_wall_clock_tick(
            datetime(2026, 8, 30, 0, 30, 15, tzinfo=timezone.utc)
        )

        self.assertEqual(calls, ["optimize:scheduled"])

    async def test_plan_step_publishes_without_full_optimize_on_intermediate_boundary(self):
        orchestrator, _, _, calls = self.make_orchestrator(interval=60)

        async def optimize(*, reason):
            calls.append(f"optimize:{reason}")

        async def publish():
            calls.append("publish")

        orchestrator.async_optimize = optimize
        orchestrator._async_publish_plan_step = publish

        await orchestrator._async_wall_clock_tick(
            datetime(2026, 8, 30, 0, 15, 15, tzinfo=timezone.utc)
        )

        self.assertEqual(calls, ["publish"])

    async def test_failed_optimization_falls_back_to_due_plan_step(self):
        orchestrator, error_type, _, calls = self.make_orchestrator(interval=30)

        async def optimize(*, reason):
            calls.append(f"optimize:{reason}")
            raise error_type("solve failed")

        async def publish():
            calls.append("publish")

        orchestrator.async_optimize = optimize
        orchestrator._async_publish_plan_step = publish

        await orchestrator._async_wall_clock_tick(
            datetime(2026, 8, 30, 0, 30, 15, tzinfo=timezone.utc)
        )

        self.assertEqual(calls, ["optimize:scheduled", "publish"])

    async def test_failed_publish_or_missing_plan_applies_battery_hold(self):
        orchestrator, error_type, _, calls = self.make_orchestrator(interval=60)

        async def publish():
            calls.append("publish")
            raise error_type("publish failed")

        orchestrator._async_publish_plan_step = publish
        await orchestrator._async_wall_clock_tick(
            datetime(2026, 8, 30, 0, 15, 15, tzinfo=timezone.utc)
        )
        self.assertEqual(calls, ["publish", "hold:plan_step_publish_failed"])

        missing, _, _, missing_calls = self.make_orchestrator(
            interval=60, step_seconds=None
        )
        await missing._async_wall_clock_tick(
            datetime(2026, 8, 30, 0, 15, 15, tzinfo=timezone.utc)
        )
        self.assertEqual(missing_calls, ["hold:plan_step_unavailable"])

    async def test_successful_step_is_verified_before_explicit_steering(self):
        orchestrator, _, _, calls = self.make_orchestrator(interval=60)

        async def post(endpoint, payload, timeout):
            calls.append(("post", endpoint, payload, timeout))
            return 200, "ok"

        async def wait(before):
            calls.append(("fresh", before))
            return -2400.0

        orchestrator._async_post_emhass = post
        orchestrator._async_wait_for_fresh_output = wait

        await orchestrator._async_publish_plan_step()

        self.assertEqual(calls[0][0:2], ("post", "/action/publish-data"))
        self.assertEqual(calls[1], ("fresh", None))
        self.assertEqual(calls[2], "steer")
        self.assertEqual(orchestrator.last_p_batt, -2400.0)
        self.assertEqual(orchestrator.status, "ready")
        self.assertEqual(
            orchestrator.entry.runtime_data.controller.suspensions,
            0,
        )

    async def test_grid_strategy_requires_fresh_grid_before_steering(self):
        orchestrator, _, _, calls = self.make_orchestrator(interval=60)
        orchestrator.entry.runtime_data.controller.control_strategy = "grid"

        async def post(_endpoint, _payload, _timeout):
            calls.append("post")
            return 200, "ok"

        async def wait_batt(_before):
            calls.append("fresh_batt")
            return -2400.0

        async def wait_grid(entity_id, _before):
            calls.append(f"fresh_grid:{entity_id}")
            return 1100.0

        orchestrator._async_post_emhass = post
        orchestrator._async_wait_for_fresh_output = wait_batt
        orchestrator._async_wait_for_fresh_entity = wait_grid

        await orchestrator._async_publish_plan_step()

        self.assertEqual(
            calls,
            ["post", "fresh_batt", "fresh_grid:sensor.p_grid_forecast", "steer"],
        )

    async def test_controller_failure_after_publish_is_converted_to_hold(self):
        orchestrator, _, _, calls = self.make_orchestrator(interval=60)

        class FailingController(FakeController):
            async def async_evaluate(self):
                self.calls.append("steer")
                raise RuntimeError("Modbus unavailable")

        orchestrator.entry.runtime_data.controller = FailingController(calls)

        async def post(_endpoint, _payload, _timeout):
            return 200, "ok"

        async def wait(_before):
            return -2400.0

        orchestrator._async_post_emhass = post
        orchestrator._async_wait_for_fresh_output = wait

        await orchestrator._async_wall_clock_tick(
            datetime(2026, 8, 30, 0, 15, 15, tzinfo=timezone.utc)
        )

        self.assertEqual(calls, ["steer", "hold:plan_step_control_failed"])
        self.assertEqual(orchestrator.status, "error_plan_step_control")
        self.assertIn("Modbus unavailable", orchestrator.last_plan_step_error)

    async def test_overlapping_wall_clock_callbacks_do_not_duplicate_work(self):
        orchestrator, _, _, calls = self.make_orchestrator(interval=15)
        entered = asyncio.Event()
        release = asyncio.Event()

        async def optimize(*, reason):
            calls.append(f"optimize:{reason}")
            entered.set()
            await release.wait()

        orchestrator.async_optimize = optimize
        now = datetime(2026, 8, 30, 0, 15, 15, tzinfo=timezone.utc)
        first = asyncio.create_task(orchestrator._async_wall_clock_tick(now))
        await entered.wait()

        await orchestrator._async_wall_clock_tick(now)
        release.set()
        await first

        self.assertEqual(calls, ["optimize:scheduled"])

    async def test_publish_rejects_an_overlapping_owned_cycle(self):
        orchestrator, error_type, _, _ = self.make_orchestrator(interval=60)
        await orchestrator._cycle_lock.acquire()
        try:
            with self.assertRaisesRegex(error_type, "already running"):
                await orchestrator._async_publish_plan_step()
        finally:
            orchestrator._cycle_lock.release()


class WallClockHelperTests(unittest.TestCase):
    def test_wall_clock_boundaries_are_anchored_to_local_midnight(self):
        _load_orchestrator()
        module = importlib.import_module(f"{PACKAGE_NAME}.wall_clock")
        self.assertTrue(
            module.cadence_is_due(
                datetime(2026, 8, 30, 12, 30, 15, tzinfo=timezone.utc), 30
            )
        )
        self.assertFalse(
            module.cadence_is_due(
                datetime(2026, 8, 30, 12, 15, 15, tzinfo=timezone.utc), 30
            )
        )
        self.assertEqual(module.plan_step_minutes(900), 15)
        self.assertEqual(module.plan_step_minutes(3600), 60)
        self.assertIsNone(module.plan_step_minutes(901))


if __name__ == "__main__":
    unittest.main()
