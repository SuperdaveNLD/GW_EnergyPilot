"""Tests for post-start EMHASS recovery behavior."""

from __future__ import annotations

import asyncio
from enum import Enum
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


def _load_orchestrator():
    _reset_modules()
    custom_components = _module("custom_components")
    custom_components.__path__ = [str(CUSTOM_COMPONENTS)]
    package = _module(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_DIR)]
    package.__package__ = PACKAGE_NAME

    homeassistant = _module("homeassistant")
    homeassistant.__path__ = []

    class CoreState(Enum):
        starting = "starting"
        running = "running"

    class Event:
        def __init__(self, data=None):
            self.data = data or {}

    core = _module(
        "homeassistant.core",
        CoreState=CoreState,
        Event=Event,
        callback=lambda func: func,
    )
    homeassistant.core = core
    const = _module(
        "homeassistant.const",
        EVENT_HOMEASSISTANT_STARTED="homeassistant_started",
    )
    homeassistant.const = const

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

    def async_call_later(_hass, _delay, _callback):
        return lambda: None

    event_helpers = _module(
        "homeassistant.helpers.event",
        async_call_later=async_call_later,
    )
    helpers.event = event_helpers

    importlib.import_module(f"{PACKAGE_NAME}.const")

    class FakeParent:
        def __init__(self, hass, entry, coordinator):
            self.hass = hass
            self.entry = entry
            self.coordinator = coordinator
            self.enabled = True
            self._unsubs = []
            self._lock = asyncio.Lock()
            self.optimize_reasons = []
            self.parent_price_events = 0

        async def async_setup(self):
            return None

        async def async_optimize(self, reason="manual"):
            self.optimize_reasons.append(reason)

        def _optimization_ready(self):
            state = self.hass.states.get("sensor.optim_status")
            return state is not None and state.state == "Optimal"

        def _async_tomorrow_price_changed(self, _event):
            self.parent_price_events += 1

    _module(
        f"{PACKAGE_NAME}.orchestrator_v013",
        GWEnergyPilotOrchestrator=FakeParent,
    )
    module = importlib.import_module(f"{PACKAGE_NAME}.orchestrator_v014")
    return module, CoreState, Event


class FakeState:
    def __init__(self, state):
        self.state = state


class FakeHass:
    def __init__(self, core_state):
        self.state = core_state
        self.states = {}
        self.created_tasks = []
        self.bus = types.SimpleNamespace(async_listen_once=lambda *_args: lambda: None)

    def async_create_task(self, coro, _name):
        task = asyncio.create_task(coro)
        self.created_tasks.append(task)
        return task


class FakeEntry:
    entry_id = "entry-1"

    def __init__(self):
        self.options = {
            "p_batt_entity": "sensor.p_batt_forecast",
            "optim_status_entity": "sensor.optim_status",
            "optim_required_state": "Optimal",
        }


class FakeCoordinator:
    def __init__(self, ready=True):
        self.data = object() if ready else None
        self.last_update_success = ready


class StartupRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_plan_is_recovered_after_startup(self):
        module, core_state, _event = _load_orchestrator()
        hass = FakeHass(core_state.running)
        orchestrator = module.GWEnergyPilotOrchestrator(
            hass,
            FakeEntry(),
            FakeCoordinator(),
        )

        await orchestrator._async_startup_recovery(1)

        self.assertEqual(orchestrator.optimize_reasons, ["startup_recovery"])

    async def test_valid_plan_does_not_trigger_recovery(self):
        module, core_state, _event = _load_orchestrator()
        hass = FakeHass(core_state.running)
        hass.states["sensor.p_batt_forecast"] = FakeState("725.0")
        hass.states["sensor.optim_status"] = FakeState("Optimal")
        orchestrator = module.GWEnergyPilotOrchestrator(
            hass,
            FakeEntry(),
            FakeCoordinator(),
        )

        await orchestrator._async_startup_recovery(1)

        self.assertEqual(orchestrator.optimize_reasons, [])

    async def test_price_event_is_ignored_during_home_assistant_startup(self):
        module, core_state, event = _load_orchestrator()
        hass = FakeHass(core_state.starting)
        orchestrator = module.GWEnergyPilotOrchestrator(
            hass,
            FakeEntry(),
            FakeCoordinator(),
        )

        orchestrator._async_tomorrow_price_changed(event())

        self.assertEqual(orchestrator.parent_price_events, 0)

        hass.state = core_state.running
        orchestrator._async_tomorrow_price_changed(event())
        self.assertEqual(orchestrator.parent_price_events, 1)


if __name__ == "__main__":
    unittest.main()
