"""Connectivity and EV reachability regressions for issue #95."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
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


class FakeState:
    def __init__(self, entity_id: str, state: str) -> None:
        self.entity_id = entity_id
        self.state = state


def _load_modules():
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

    class Event:
        pass

    class HomeAssistant:
        pass

    core = _module(
        "homeassistant.core",
        Event=Event,
        HomeAssistant=HomeAssistant,
        callback=lambda func: func,
    )
    homeassistant.core = core

    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    homeassistant.helpers = helpers

    def async_dispatcher_send(hass, signal, *args):
        hass.dispatched.append((signal, args))

    helpers.dispatcher = _module(
        "homeassistant.helpers.dispatcher",
        async_dispatcher_send=async_dispatcher_send,
    )

    def async_call_later(hass, delay, callback_func):
        record = {"delay": delay, "callback": callback_func, "cancelled": False}
        hass.timers.append(record)

        def cancel():
            record["cancelled"] = True

        return cancel

    def async_track_state_change_event(hass, entity_ids, callback_func):
        hass.tracked.append((tuple(entity_ids), callback_func))
        return lambda: None

    helpers.event = _module(
        "homeassistant.helpers.event",
        async_call_later=async_call_later,
        async_track_state_change_event=async_track_state_change_event,
    )

    model = importlib.import_module(f"{PACKAGE_NAME}.connectivity_model")
    runtime = importlib.import_module(f"{PACKAGE_NAME}.connectivity")
    const = importlib.import_module(f"{PACKAGE_NAME}.const")
    return model, runtime, const


model, runtime_module, const = _load_modules()


class FakeStates:
    def __init__(self, values=None) -> None:
        self.values = dict(values or {})

    def get(self, entity_id):
        value = self.values.get(entity_id)
        return None if value is None else FakeState(entity_id, value)


class FakeHass:
    def __init__(self, states=None) -> None:
        self.states = FakeStates(states)
        self.dispatched = []
        self.timers = []
        self.tracked = []


class FakeEntry:
    entry_id = "test-entry"

    def __init__(self, options) -> None:
        self.options = dict(options)


class FakeCoordinator:
    def __init__(self) -> None:
        self.data = object()
        self.last_update_success = True
        self.last_exception = None
        self.listeners = []

    def async_add_listener(self, callback_func):
        self.listeners.append(callback_func)
        return lambda: None


class FakeDebugLog:
    def __init__(self) -> None:
        self.events = []
        self.log = self

    def record(self, category, event, data):
        self.events.append((category, event, data))


class EVSourceInterpretationTests(unittest.TestCase):
    def test_missing_states_are_unreachable(self) -> None:
        for state in (None, "", "unknown", "unavailable", "none"):
            with self.subTest(state=state):
                value = None if state is None else FakeState("sensor.ev", state)
                self.assertFalse(model.ev_source_online(value))

    def test_binary_sensor_is_an_explicit_online_signal(self) -> None:
        self.assertTrue(model.ev_source_online(FakeState("binary_sensor.ev", "on")))
        self.assertFalse(model.ev_source_online(FakeState("binary_sensor.ev", "off")))

    def test_other_available_entities_report_a_live_integration(self) -> None:
        self.assertTrue(model.ev_source_online(FakeState("switch.ev", "off")))
        self.assertTrue(model.ev_source_online(FakeState("sensor.ev_power", "0")))


class EVConnectivityGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.start = datetime(2026, 8, 30, 10, 0, tzinfo=timezone.utc)
        self.guard = model.EVConnectivityGuard(300)

    def update(self, seconds, *, online, enabled=True, configured=True):
        return self.guard.update(
            now=self.start + timedelta(seconds=seconds),
            user_enabled=enabled,
            source_configured=configured,
            online=online,
        )

    def test_offline_and_online_each_require_five_stable_minutes(self) -> None:
        self.assertEqual(
            [event.event for event in self.update(0, online=False)],
            ["ev_connectivity_lost"],
        )
        self.assertTrue(self.guard.effective(True))
        self.assertEqual(self.guard.transition, "suspend_pending")
        self.update(299, online=False)
        self.assertTrue(self.guard.effective(True))
        self.assertEqual(
            [event.event for event in self.update(300, online=False)],
            ["ev_coordination_suspended"],
        )
        self.assertFalse(self.guard.effective(True))

        self.assertEqual(
            [event.event for event in self.update(301, online=True)],
            ["ev_connectivity_restored"],
        )
        self.assertEqual(self.guard.transition, "resume_pending")
        self.update(600, online=True)
        self.assertFalse(self.guard.effective(True))
        self.assertEqual(
            [event.event for event in self.update(601, online=True)],
            ["ev_coordination_resumed"],
        )
        self.assertTrue(self.guard.effective(True))

    def test_flapping_resets_both_stable_windows(self) -> None:
        self.update(0, online=False)
        self.update(240, online=True)
        self.update(300, online=False)
        self.update(599, online=False)
        self.assertTrue(self.guard.effective(True))
        self.update(600, online=False)
        self.assertFalse(self.guard.effective(True))
        self.update(660, online=True)
        self.update(900, online=False)
        self.update(960, online=True)
        self.update(1259, online=True)
        self.assertFalse(self.guard.effective(True))
        self.update(1260, online=True)
        self.assertTrue(self.guard.effective(True))

    def test_user_disable_cancels_automatic_resume(self) -> None:
        self.update(0, online=False)
        self.update(300, online=False)
        self.update(301, online=True)
        events = self.update(400, online=True, enabled=False)
        self.assertEqual(
            [event.event for event in events],
            ["ev_resume_cancelled_by_user"],
        )
        self.assertFalse(self.guard.effective(False))
        self.update(900, online=True, enabled=False)
        self.assertFalse(self.guard.effective(False))

    def test_unconfigured_source_never_suspends(self) -> None:
        self.update(0, online=False, configured=False)
        self.update(900, online=False, configured=False)
        self.assertTrue(self.guard.effective(True))
        self.assertIsNone(self.guard.transition)


class ConnectivityRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_runtime_follows_poll_interval_and_logs_guard_transitions(self) -> None:
        clock = [datetime(2026, 8, 30, 10, 0, tzinfo=timezone.utc)]
        hass = FakeHass({"binary_sensor.charger_online": "off"})
        entry = FakeEntry(
            {
                const.CONF_ENABLE_EV_COORDINATION: True,
                const.CONF_EV_ONLINE_ENTITY: "binary_sensor.charger_online",
                const.CONF_SCAN_INTERVAL: 15,
            }
        )
        coordinator = FakeCoordinator()
        debug_log = FakeDebugLog()
        runtime = runtime_module.GWEnergyPilotConnectivity(
            hass,
            entry,
            coordinator,
            debug_log,
            now_fn=lambda: clock[0],
        )

        await runtime.async_start()

        self.assertEqual(runtime.state, "issue")
        self.assertTrue(runtime.ev_coordination_effective)
        self.assertEqual(runtime.attributes["refresh_seconds"], 15)
        self.assertIsNotNone(runtime.attributes["modbus_last_success"])
        self.assertEqual(runtime.attributes["ev_transition"], "suspend_pending")
        self.assertEqual(hass.timers[-1]["delay"], 300)

        clock[0] += timedelta(seconds=300)
        runtime._evaluate()
        self.assertFalse(runtime.ev_coordination_effective)
        self.assertIn(
            "ev_coordination_suspended",
            [event for _, event, _ in debug_log.events],
        )

        hass.states.values["binary_sensor.charger_online"] = "on"
        clock[0] += timedelta(seconds=1)
        runtime._evaluate()
        self.assertFalse(runtime.ev_coordination_effective)
        self.assertEqual(runtime.attributes["ev_transition"], "resume_pending")

        clock[0] += timedelta(seconds=300)
        runtime._evaluate()
        self.assertTrue(runtime.ev_coordination_effective)
        self.assertEqual(runtime.state, "all_ok")
        self.assertIn(
            "ev_coordination_resumed",
            [event for _, event, _ in debug_log.events],
        )

    async def test_failed_coordinator_update_is_reported_without_new_polling(self) -> None:
        clock = [datetime(2026, 8, 30, 10, 0, tzinfo=timezone.utc)]
        hass = FakeHass()
        entry = FakeEntry({const.CONF_SCAN_INTERVAL: 23})
        coordinator = FakeCoordinator()
        runtime = runtime_module.GWEnergyPilotConnectivity(
            hass,
            entry,
            coordinator,
            FakeDebugLog(),
            now_fn=lambda: clock[0],
        )
        await runtime.async_start()
        self.assertEqual(len(coordinator.listeners), 1)
        self.assertEqual(hass.timers, [])

        coordinator.last_update_success = False
        coordinator.last_exception = RuntimeError("timeout")
        coordinator.listeners[0]()

        self.assertEqual(runtime.state, "issue")
        self.assertEqual(runtime.attributes["modbus_status"], "unreachable")
        self.assertEqual(runtime.attributes["modbus_last_error"], "timeout")
        self.assertEqual(runtime.attributes["refresh_seconds"], 23)
        self.assertIsNotNone(runtime.attributes["modbus_last_failure"])


if __name__ == "__main__":
    unittest.main()
