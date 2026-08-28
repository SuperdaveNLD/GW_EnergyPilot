"""Regression tests for v0.44 restart-time EMHASS optimization recovery."""

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


def _load_module(*, enabled: bool = True, setup_status: str = "scheduled"):
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
            self.restored_success = None
            self.status = "idle"
            self._unsubs = []
            self.optimize_calls = []
            self.failures_remaining = 0
            self.enabled_value = enabled

        @property
        def enabled(self):
            return self.enabled_value

        async def async_setup(self):
            self.last_success = self.restored_success
            self.status = setup_status

        async def async_optimize(self, reason="manual"):
            self.optimize_calls.append(reason)
            if self.failures_remaining:
                self.failures_remaining -= 1
                raise HomeAssistantError("startup dependency unavailable")
            baseline = self.last_success or datetime(2026, 8, 28, tzinfo=timezone.utc)
            self.last_success = baseline + timedelta(seconds=1)

    _module(
        f"{PACKAGE_NAME}.orchestrator_v033",
        GWEnergyPilotOrchestrator=FakeBaseOrchestrator,
    )
    module = importlib.import_module(f"{PACKAGE_NAME}.orchestrator_v044")
    return module, scheduled


class StartupOptimizeRetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_setup_schedules_initial_attempt_after_restored_state(self):
        module, scheduled = _load_module()
        orchestrator = module.GWEnergyPilotOrchestrator(object(), object(), object())
        restored = datetime(2026, 8, 28, 8, 0, tzinfo=timezone.utc)
        orchestrator.restored_success = restored

        await orchestrator.async_setup()

        self.assertEqual(orchestrator._startup_success_baseline, restored)
        self.assertEqual([delay for delay, _callback in scheduled], [60])
        self.assertEqual(len(orchestrator._unsubs), 1)

    async def test_disabled_or_non_scheduled_setup_has_no_startup_attempt(self):
        for enabled, status in ((False, "manual_only"), (True, "legacy_yaml_detected")):
            with self.subTest(enabled=enabled, status=status):
                module, scheduled = _load_module(
                    enabled=enabled,
                    setup_status=status,
                )
                orchestrator = module.GWEnergyPilotOrchestrator(
                    object(), object(), object()
                )

                await orchestrator.async_setup()

                self.assertEqual(scheduled, [])

    async def test_failed_startup_optimize_schedules_bounded_backoff(self):
        module, scheduled = _load_module()
        orchestrator = module.GWEnergyPilotOrchestrator(object(), object(), object())
        orchestrator.failures_remaining = 4
        await orchestrator.async_setup()

        for _index in range(4):
            await orchestrator._async_initial_optimize(datetime.now(timezone.utc))

        self.assertEqual(orchestrator.optimize_calls, ["startup"] * 4)
        self.assertEqual(
            [delay for delay, _callback in scheduled],
            [60, 15, 30, 60],
        )

    async def test_successful_startup_optimize_does_not_schedule_retry(self):
        module, scheduled = _load_module()
        orchestrator = module.GWEnergyPilotOrchestrator(object(), object(), object())
        await orchestrator.async_setup()

        await orchestrator._async_initial_optimize(datetime.now(timezone.utc))

        self.assertEqual(orchestrator.optimize_calls, ["startup"])
        self.assertEqual([delay for delay, _callback in scheduled], [60])

    async def test_external_success_before_callback_skips_duplicate_optimize(self):
        module, scheduled = _load_module()
        orchestrator = module.GWEnergyPilotOrchestrator(object(), object(), object())
        restored = datetime(2026, 8, 28, 8, 0, tzinfo=timezone.utc)
        orchestrator.restored_success = restored
        await orchestrator.async_setup()
        orchestrator.last_success = restored + timedelta(minutes=1)

        await orchestrator._async_initial_optimize(datetime.now(timezone.utc))

        self.assertEqual(orchestrator.optimize_calls, [])
        self.assertEqual([delay for delay, _callback in scheduled], [60])

    async def test_disabled_before_callback_skips_startup_optimize(self):
        module, scheduled = _load_module()
        orchestrator = module.GWEnergyPilotOrchestrator(object(), object(), object())
        await orchestrator.async_setup()
        orchestrator.enabled_value = False

        await orchestrator._async_initial_optimize(datetime.now(timezone.utc))

        self.assertEqual(orchestrator.optimize_calls, [])
        self.assertEqual([delay for delay, _callback in scheduled], [60])


if __name__ == "__main__":
    unittest.main()
