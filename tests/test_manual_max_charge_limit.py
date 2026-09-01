"""Regression tests for the SOC-guarded Max charge quick action."""

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


def _load_controller():
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
        def __init__(self, data=None):
            self.data = data or {}

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

    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    homeassistant.helpers = helpers

    dispatcher = _module(
        "homeassistant.helpers.dispatcher",
        async_dispatcher_connect=lambda *_args, **_kwargs: (lambda: None),
        async_dispatcher_send=lambda *_args, **_kwargs: None,
    )
    helpers.dispatcher = dispatcher

    event = _module(
        "homeassistant.helpers.event",
        async_track_state_change_event=lambda *_args, **_kwargs: (lambda: None),
    )
    helpers.event = event

    class GWModbusClient:
        pass

    class GWEnergyPilotCoordinator:
        pass

    _module(f"{PACKAGE_NAME}.client", GWModbusClient=GWModbusClient)
    _module(
        f"{PACKAGE_NAME}.coordinator",
        GWEnergyPilotCoordinator=GWEnergyPilotCoordinator,
    )

    const = importlib.import_module(f"{PACKAGE_NAME}.const")
    controller = importlib.import_module(f"{PACKAGE_NAME}.controller")
    return controller, const


controller_module, const = _load_controller()


class FakeState:
    def __init__(self, state):
        self.state = state


class FakeStates:
    def __init__(self):
        self._values = {
            "sensor.p_batt": FakeState("0"),
            "sensor.p_grid": FakeState("0"),
        }

    def get(self, entity_id):
        return self._values.get(entity_id)


class FakeHass:
    def __init__(self):
        self.states = FakeStates()
        self.tasks = []

    def async_create_task(self, coroutine, name=None):
        task = asyncio.create_task(coroutine, name=name)
        self.tasks.append(task)
        return task


class FakeEntry:
    def __init__(self):
        self.entry_id = "max-charge-test"
        self.data = {}
        self.options = {
            const.CONF_P_BATT_ENTITY: "sensor.p_batt",
            const.CONF_P_GRID_ENTITY: "sensor.p_grid",
            const.CONF_MAX_POWER: 15000,
        }


class FakeClient:
    def __init__(self):
        self.calls = []

    async def async_set_mode(self, mode, power):
        self.calls.append((mode, power))


class FakeCoordinatorData:
    def __init__(self, battery_soc):
        self.values = {
            "meter_total_power_fast": 0,
            "battery_soc": battery_soc,
        }
        self.mode = None
        self.power = None


class FakeCoordinator:
    def __init__(self, battery_soc):
        self.data = FakeCoordinatorData(battery_soc)
        self.refresh_count = 0
        self.listeners = []

    async def async_request_refresh(self):
        self.refresh_count += 1

    def async_add_listener(self, listener):
        self.listeners.append(listener)

        def _remove():
            if listener in self.listeners:
                self.listeners.remove(listener)

        return _remove

    def set_battery_soc(self, value):
        self.data.values["battery_soc"] = value
        for listener in tuple(self.listeners):
            listener()


def make_controller(battery_soc):
    hass = FakeHass()
    entry = FakeEntry()
    client = FakeClient()
    coordinator = FakeCoordinator(battery_soc)
    controller = controller_module.GWEnergyPilotController(
        hass,
        entry,
        client,
        coordinator,
    )
    return controller, hass, client, coordinator


class ManualMaxChargeLimitTests(unittest.IsolatedAsyncioTestCase):
    async def test_max_charge_starts_below_limit(self):
        controller, _, client, coordinator = make_controller(94)

        await controller.async_manual_max_charge(15000, 95)

        self.assertFalse(controller.enabled)
        self.assertEqual(controller.manual_charge_limit_soc, 95)
        self.assertEqual(controller.last_command, "manual_max_charge")
        self.assertEqual(client.calls, [(const.MODE_CHARGE_BATTERY, 15000)])
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_max_charge_holds_immediately_at_or_above_limit(self):
        for battery_soc in (95, 99):
            with self.subTest(battery_soc=battery_soc):
                controller, _, client, _ = make_controller(battery_soc)

                await controller.async_manual_max_charge(15000, 95)

                self.assertEqual(controller.last_command, "manual_max_charge_soc_limit")
                self.assertEqual(controller.target_power, 0)
                self.assertEqual(client.calls, [(const.MODE_BATTERY_HOLD, 0)])

    async def test_max_charge_stops_on_next_telemetry_at_limit(self):
        controller, hass, client, coordinator = make_controller(94)
        await controller.async_setup()
        await controller.async_manual_max_charge(15000, 95)

        coordinator.set_battery_soc(95)
        await asyncio.gather(*hass.tasks)

        self.assertEqual(
            client.calls,
            [
                (const.MODE_CHARGE_BATTERY, 15000),
                (const.MODE_BATTERY_HOLD, 0),
            ],
        )
        self.assertEqual(controller.last_command, "manual_max_charge_soc_limit")
        self.assertEqual(controller.target_power, 0)

    async def test_max_charge_fails_safe_when_soc_is_unavailable(self):
        controller, _, client, coordinator = make_controller(None)

        with self.assertRaisesRegex(ValueError, "battery SOC is unavailable"):
            await controller.async_manual_max_charge(15000, 95)

        self.assertEqual(client.calls, [])
        self.assertEqual(coordinator.refresh_count, 0)
        self.assertIsNone(controller.manual_charge_limit_soc)

    async def test_max_charge_rejects_soc_after_failed_telemetry_refresh(self):
        controller, _, client, coordinator = make_controller(80)
        coordinator.last_update_success = False

        with self.assertRaisesRegex(ValueError, "battery SOC is unavailable"):
            await controller.async_manual_max_charge(15000, 95)

        self.assertEqual(client.calls, [])
        self.assertEqual(coordinator.refresh_count, 0)

    async def test_direct_manual_mode11_remains_direct_operator_command(self):
        controller, _, client, coordinator = make_controller(99)

        await controller.async_manual_command(
            const.MODE_CHARGE_BATTERY,
            4000,
            "manual_mode_11",
        )

        self.assertEqual(client.calls, [(const.MODE_CHARGE_BATTERY, 4000)])
        self.assertEqual(controller.last_command, "manual_mode_11")
        self.assertIsNone(controller.manual_charge_limit_soc)
        self.assertEqual(coordinator.refresh_count, 1)


if __name__ == "__main__":
    unittest.main()
