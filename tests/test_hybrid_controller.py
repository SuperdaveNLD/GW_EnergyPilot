"""Regression tests for GW EnergyPilot automatic control strategy selection."""

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
    def __init__(self, values):
        self._values = {
            entity_id: FakeState(value) for entity_id, value in values.items()
        }

    def get(self, entity_id):
        return self._values.get(entity_id)


class FakeHass:
    def __init__(self, values):
        self.states = FakeStates(values)

    def async_create_task(self, coroutine, name=None):
        return asyncio.create_task(coroutine, name=name)


class FakeEntry:
    def __init__(self, data):
        self.entry_id = "strategy-test"
        self.data = dict(data)
        self.options = {
            const.CONF_P_BATT_ENTITY: "sensor.p_batt",
            const.CONF_P_GRID_ENTITY: "sensor.p_grid",
            const.CONF_DEADBAND: 300,
            const.CONF_MAX_POWER: 15000,
        }


class FakeClient:
    def __init__(self):
        self.calls = []

    async def async_set_mode(self, mode, power):
        self.calls.append((mode, power))


class FakeCoordinatorData:
    def __init__(self):
        self.values = {"meter_total_power_fast": 0}
        self.mode = None
        self.power = None


class FakeCoordinator:
    def __init__(self):
        self.data = FakeCoordinatorData()
        self.refresh_count = 0

    async def async_request_refresh(self):
        self.refresh_count += 1


def make_controller(*, strategy_data, p_batt, p_grid):
    hass = FakeHass(
        {
            "sensor.p_batt": str(p_batt),
            "sensor.p_grid": str(p_grid),
        }
    )
    entry = FakeEntry(strategy_data)
    client = FakeClient()
    coordinator = FakeCoordinator()
    controller = controller_module.GWEnergyPilotController(
        hass,
        entry,
        client,
        coordinator,
    )
    controller.enabled = True
    return controller, client


class HybridControllerTests(unittest.IsolatedAsyncioTestCase):
    async def test_hybrid_charge_uses_direct_mode11(self):
        controller, client = make_controller(
            strategy_data={
                const.CONF_CONTROL_STRATEGY: const.CONTROL_STRATEGY_HYBRID,
            },
            p_batt=-4200,
            p_grid=6500,
        )

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_CHARGE_BATTERY, 4200)])
        self.assertEqual(controller.last_command, "hybrid_battery_charge")

    async def test_hybrid_export_uses_mode10_when_not_charging(self):
        controller, client = make_controller(
            strategy_data={
                const.CONF_CONTROL_STRATEGY: const.CONTROL_STRATEGY_HYBRID,
            },
            p_batt=1800,
            p_grid=-3600,
        )

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_GRID_EXPORT_TARGET, 3600)])
        self.assertEqual(controller.last_command, "hybrid_grid_export")

    async def test_hybrid_uses_auto_for_normal_self_use(self):
        controller, client = make_controller(
            strategy_data={
                const.CONF_CONTROL_STRATEGY: const.CONTROL_STRATEGY_HYBRID,
            },
            p_batt=2500,
            p_grid=1200,
        )

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_AUTO, 0)])
        self.assertEqual(controller.last_command, "hybrid_auto")

    async def test_missing_strategy_keeps_legacy_battery_default(self):
        controller, client = make_controller(
            strategy_data={},
            p_batt=962,
            p_grid=0,
        )

        await controller.async_evaluate()

        self.assertEqual(controller.control_strategy, const.CONTROL_STRATEGY_BATTERY)
        self.assertEqual(client.calls, [(const.MODE_DISCHARGE_BATTERY, 962)])
        self.assertEqual(controller.last_command, "battery_discharge")

    async def test_legacy_true_boolean_still_selects_grid_control(self):
        controller, client = make_controller(
            strategy_data={const.CONF_USE_GOODWE_SMART_METER: True},
            p_batt=-2500,
            p_grid=3100,
        )

        await controller.async_evaluate()

        self.assertEqual(controller.control_strategy, const.CONTROL_STRATEGY_GRID)
        self.assertEqual(client.calls, [(const.MODE_GRID_IMPORT_TARGET, 3100)])
        self.assertEqual(controller.last_command, "grid_import_target")


if __name__ == "__main__":
    unittest.main()
