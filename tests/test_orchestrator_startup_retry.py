"""Regression tests for restart-time EMHASS optimization retries."""

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
    exceptions = _module("homeassistant.exceptions")

    class HomeAssistantError(Exception):
        pass

    exceptions.HomeAssistantError = HomeAssistantError
    homeassistant.exceptions = exceptions

    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    homeassistant.helpers = helpers
    scheduled = []

    def async_call_later(_hass, delay, callback):
        scheduled.append((delay, callback))
        return lambda: None

    event = _module("homeassistant.helpers.event", async_call_later=async_call_later)
    helpers.event = event

    class FakeBaseOrchestrator:
        def __init__(self, hass, entry, coordinator) -> None:
            self.hass = hass
            self.entry = entry
            self.coordinator = coordinator
            self.last_success = None
            self._unsubs = []
            self.optimize_calls = []
            self.failures_remaining = 0

        @property
        def enabled(self):
            return True

        async def async_setup(self):
            return None

        async def async_optimize(self, reason="manual"):
            self.optimize_calls.append(reason)
            if self.failures_remaining:
                self.failures_remaining -= 1
                raise HomeAssistantError("startup dependency unavailable")
            self.last_success = datetime.now(timezone.utc)

    _module(
        f"{PACKAGE_NAME}.orchestrator_v033",
        GWEnergyPilotOrchestrator=FakeBaseOrchestrator,
    )
    module = importlib.import_module(f"{PACKAGE_NAME}.orchestrator_v043")
    return module, scheduled


class StartupOptimizeRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_startup_optimize_schedules_bounded_retry(self):
        module, scheduled = _load_module()
        orchestrator = module.GWEnergyPilotOrchestrator(object(), object(), object())
        orchestrator.failures_remaining = 1
        await orchestrator.async_setup()

        await orchestrator._async_initial_optimize(datetime.now(timezone.utc))

        self.assertEqual(orchestrator.optimize_calls, ["startup"])
        self.assertEqual([delay for delay, _callback in scheduled], [15])
        self.assertEqual(len(orchestrator._unsubs), 1)

    async def test_successful_startup_optimize_does_not_schedule_retry(self):
        module, scheduled = _load_module()
        orchestrator = module.GWEnergyPilotOrchestrator(object(), object(), object())
        await orchestrator.async_setup()

        await orchestrator._async_initial_optimize(datetime.now(timezone.utc))

        self.assertEqual(orchestrator.optimize_calls, ["startup"])
        self.assertEqual(scheduled, [])

    async def test_external_success_before_startup_callback_skips_duplicate_optimize(self):
        module, scheduled = _load_module()
        orchestrator = module.GWEnergyPilotOrchestrator(object(), object(), object())
        restored = datetime(2026, 8, 28, 8, 0, tzinfo=timezone.utc)
        orchestrator.last_success = restored
        await orchestrator.async_setup()
        orchestrator.last_success = datetime(2026, 8, 28, 8, 1, tzinfo=timezone.utc)

        await orchestrator._async_initial_optimize(datetime.now(timezone.utc))

        self.assertEqual(orchestrator.optimize_calls, [])
        self.assertEqual(scheduled, [])

    async def test_retry_backoff_is_bounded(self):
        module, scheduled = _load_module()
        orchestrator = module.GWEnergyPilotOrchestrator(object(), object(), object())
        orchestrator.failures_remaining = 4
        await orchestrator.async_setup()

        for _index in range(4):
            await orchestrator._async_initial_optimize(datetime.now(timezone.utc))

        self.assertEqual(orchestrator.optimize_calls, ["startup"] * 4)
        self.assertEqual([delay for delay, _callback in scheduled], [15, 30, 60])


if __name__ == "__main__":
    unittest.main()
