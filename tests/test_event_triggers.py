"""Regression tests for EV-stop optimization recovery."""

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


def _load_module():
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

    def callback(func):
        return func

    core = _module(
        "homeassistant.core",
        Event=Event,
        HomeAssistant=HomeAssistant,
        callback=callback,
    )
    homeassistant.core = core

    class HomeAssistantError(Exception):
        pass

    exceptions = _module(
        "homeassistant.exceptions",
        HomeAssistantError=HomeAssistantError,
    )
    homeassistant.exceptions = exceptions

    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    homeassistant.helpers = helpers
    scheduled = []
    listeners = []

    def async_call_later(_hass, delay, action):
        record = {"delay": delay, "action": action, "cancelled": False}
        scheduled.append(record)

        def cancel():
            record["cancelled"] = True

        return cancel

    def async_track_state_change_event(_hass, entity_ids, action):
        listeners.append((tuple(entity_ids), action))
        return lambda: None

    event = _module(
        "homeassistant.helpers.event",
        async_call_later=async_call_later,
        async_track_state_change_event=async_track_state_change_event,
    )
    helpers.event = event
    module = importlib.import_module(f"{PACKAGE_NAME}.event_triggers")
    return module, HomeAssistantError, listeners, scheduled


class FakeHass:
    def __init__(self):
        self.tasks = []

    def async_create_task(self, coroutine, name=None):
        task = asyncio.create_task(coroutine, name=name)
        self.tasks.append(task)
        return task


class EVStopTriggerTests(unittest.IsolatedAsyncioTestCase):
    async def test_retry_backoff_is_bounded(self):
        module, HomeAssistantError, listeners, scheduled = _load_module()
        hass = FakeHass()

        class Controller:
            active = True
            ev_source_ids = {"sensor.ev_power"}

            def ev_is_active(self):
                return self.active

        class Orchestrator:
            async def async_optimize(self, *, reason):
                raise HomeAssistantError(f"temporary: {reason}")

        controller = Controller()
        entry = types.SimpleNamespace(
            options={
                "enable_emhass_orchestrator": True,
                "enable_ev_coordination": True,
            },
            runtime_data=types.SimpleNamespace(
                controller=controller,
                orchestrator=Orchestrator(),
            ),
        )
        module.async_setup_event_triggers(hass, entry)
        controller.active = False
        listeners[0][1](object())
        await hass.tasks[-1]

        for index, delay in enumerate((5, 15, 30, 60)):
            self.assertEqual(scheduled[index]["delay"], delay)
            await scheduled[index]["action"](None)
            await hass.tasks[-1]

        self.assertEqual(len(scheduled), 4)

    async def test_transient_failure_retries_and_releases_on_success(self):
        module, HomeAssistantError, listeners, scheduled = _load_module()
        hass = FakeHass()

        class Controller:
            active = True
            ev_source_ids = {"binary_sensor.charging"}

            def ev_is_active(self):
                return self.active

        class Orchestrator:
            def __init__(self):
                self.reasons = []

            async def async_optimize(self, reason):
                self.reasons.append(reason)
                if len(self.reasons) == 1:
                    raise HomeAssistantError("cycle already running")

        controller = Controller()
        orchestrator = Orchestrator()
        entry = types.SimpleNamespace(
            options={
                "enable_emhass_orchestrator": True,
                "enable_ev_coordination": True,
            },
            runtime_data=types.SimpleNamespace(
                controller=controller,
                orchestrator=orchestrator,
            ),
        )
        unsubs = module.async_setup_event_triggers(hass, entry)
        self.assertEqual(listeners[0][0], ("binary_sensor.charging",))

        controller.active = False
        listeners[0][1](object())
        await hass.tasks[-1]

        self.assertEqual(orchestrator.reasons, ["ev_charging_stopped"])
        self.assertEqual(scheduled[0]["delay"], 5)
        self.assertFalse(scheduled[0]["cancelled"])

        await scheduled[0]["action"](None)
        await hass.tasks[-1]

        self.assertEqual(
            orchestrator.reasons,
            ["ev_charging_stopped", "ev_charging_stopped"],
        )
        self.assertEqual(len(scheduled), 1)
        for unsub in reversed(unsubs):
            unsub()

    async def test_ev_restart_cancels_pending_stop_retry(self):
        module, HomeAssistantError, listeners, scheduled = _load_module()
        hass = FakeHass()

        class Controller:
            active = True
            ev_source_ids = {"sensor.ev_power"}

            def ev_is_active(self):
                return self.active

        class Orchestrator:
            async def async_optimize(self, _reason=None, *, reason=None):
                raise HomeAssistantError("temporary")

        controller = Controller()
        entry = types.SimpleNamespace(
            options={
                "enable_emhass_orchestrator": True,
                "enable_ev_coordination": True,
            },
            runtime_data=types.SimpleNamespace(
                controller=controller,
                orchestrator=Orchestrator(),
            ),
        )
        module.async_setup_event_triggers(hass, entry)
        controller.active = False
        listeners[0][1](object())
        await hass.tasks[-1]
        self.assertFalse(scheduled[0]["cancelled"])

        controller.active = True
        listeners[0][1](object())
        self.assertTrue(scheduled[0]["cancelled"])


if __name__ == "__main__":
    unittest.main()
