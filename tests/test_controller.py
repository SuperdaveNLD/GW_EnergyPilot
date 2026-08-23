"""Safety-focused unit tests for the GW EnergyPilot controller.

These tests intentionally use only the Python standard library. Home Assistant,
the Modbus client, and the coordinator are replaced with small fakes so the
controller decision logic can be tested without hardware or network access.
"""

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
    """Import controller.py with minimal Home Assistant/client stubs."""
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

    def async_dispatcher_send(hass, signal, *args):
        hass.dispatched.append((signal, args))

    dispatcher = _module(
        "homeassistant.helpers.dispatcher",
        async_dispatcher_send=async_dispatcher_send,
    )
    helpers.dispatcher = dispatcher

    def async_track_state_change_event(hass, entity_ids, callback_func):
        hass.tracked_state_changes.append((tuple(entity_ids), callback_func))
        return lambda: None

    event = _module(
        "homeassistant.helpers.event",
        async_track_state_change_event=async_track_state_change_event,
    )
    helpers.event = event

    class GWModbusClient:
        pass

    _module(f"{PACKAGE_NAME}.client", GWModbusClient=GWModbusClient)

    class GWEnergyPilotCoordinator:
        pass

    _module(
        f"{PACKAGE_NAME}.coordinator",
        GWEnergyPilotCoordinator=GWEnergyPilotCoordinator,
    )

    const = importlib.import_module(f"{PACKAGE_NAME}.const")
    controller = importlib.import_module(f"{PACKAGE_NAME}.controller")
    return controller, const, Event


controller_module, const, Event = _load_controller()


class FakeState:
    def __init__(self, state):
        self.state = state


class FakeStates:
    def __init__(self, values=None):
        self._values = {
            entity_id: FakeState(value) for entity_id, value in (values or {}).items()
        }

    def get(self, entity_id):
        return self._values.get(entity_id)

    def set(self, entity_id, value):
        self._values[entity_id] = FakeState(value)


class FakeHass:
    def __init__(self, states=None):
        self.states = FakeStates(states)
        self.dispatched = []
        self.tracked_state_changes = []
        self.tasks = []

    def async_create_task(self, coroutine, name=None):
        task = asyncio.create_task(coroutine, name=name)
        self.tasks.append(task)
        return task


class FakeEntry:
    def __init__(self, options=None):
        self.entry_id = "test-entry"
        self.options = dict(options or {})


class FakeClient:
    def __init__(self):
        self.calls = []

    async def async_set_mode(self, mode, power):
        self.calls.append((mode, power))


class FakeCoordinator:
    def __init__(self):
        self.refresh_count = 0

    async def async_request_refresh(self):
        self.refresh_count += 1


class ControllerSafetyTests(unittest.IsolatedAsyncioTestCase):
    """Protect the controller's EMS ownership and power mapping contract."""

    def make_controller(self, *, p_batt="1000", options=None, states=None):
        merged_options = {
            const.CONF_P_BATT_ENTITY: "sensor.p_batt",
            **(options or {}),
        }
        merged_states = {"sensor.p_batt": p_batt, **(states or {})}
        hass = FakeHass(merged_states)
        entry = FakeEntry(merged_options)
        client = FakeClient()
        coordinator = FakeCoordinator()
        controller = controller_module.GWEnergyPilotController(
            hass,
            entry,
            client,
            coordinator,
        )
        return controller, hass, client, coordinator

    async def test_enable_maps_positive_p_batt_to_discharge(self):
        controller, _, client, coordinator = self.make_controller(p_batt="1200")

        await controller.async_enable()

        self.assertTrue(controller.enabled)
        self.assertEqual(
            client.calls,
            [(const.MODE_DISCHARGE_BATTERY, 1200)],
        )
        self.assertEqual(controller.target_power, 1200)
        self.assertEqual(controller.last_command, "battery_discharge")
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_negative_p_batt_maps_to_charge(self):
        controller, _, client, coordinator = self.make_controller(p_batt="-900")
        controller.enabled = True

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_CHARGE_BATTERY, 900)])
        self.assertEqual(controller.last_command, "battery_charge")
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_deadband_boundaries_hold_battery(self):
        for p_batt in ("-300", "0", "300"):
            with self.subTest(p_batt=p_batt):
                controller, _, client, coordinator = self.make_controller(
                    p_batt=p_batt,
                    options={const.CONF_DEADBAND: 300},
                )
                controller.enabled = True

                await controller.async_evaluate()

                self.assertEqual(client.calls, [(const.MODE_BATTERY_HOLD, 0)])
                self.assertEqual(controller.target_power, 0)
                self.assertEqual(controller.last_command, "battery_hold")
                self.assertEqual(coordinator.refresh_count, 1)

    async def test_power_is_clamped_to_configured_maximum(self):
        controller, _, client, _ = self.make_controller(
            p_batt="18000",
            options={const.CONF_MAX_POWER: 5000},
        )
        controller.enabled = True

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_DISCHARGE_BATTERY, 5000)])
        self.assertEqual(controller.target_power, 5000)

    async def test_invalid_p_batt_never_writes_modbus(self):
        for value in ("unknown", "unavailable", "none", "", "not-a-number", "nan", "inf", "-inf"):
            with self.subTest(value=value):
                controller, _, client, coordinator = self.make_controller(p_batt=value)
                controller.enabled = True

                await controller.async_evaluate()

                self.assertEqual(client.calls, [])
                self.assertEqual(controller.last_command, "waiting_for_p_batt")
                self.assertEqual(coordinator.refresh_count, 0)

    async def test_optimizer_must_be_ready_before_modbus_write(self):
        controller, _, client, coordinator = self.make_controller(
            p_batt="1500",
            options={
                const.CONF_OPTIM_STATUS_ENTITY: "sensor.optim_status",
                const.CONF_OPTIM_REQUIRED_STATE: "Optimal",
            },
            states={"sensor.optim_status": "Running"},
        )
        controller.enabled = True

        await controller.async_evaluate()

        self.assertEqual(client.calls, [])
        self.assertEqual(controller.last_command, "waiting_for_optimization")
        self.assertEqual(coordinator.refresh_count, 0)

    async def test_ev_charging_forces_battery_hold(self):
        controller, _, client, coordinator = self.make_controller(
            p_batt="2500",
            options={
                const.CONF_ENABLE_EV_COORDINATION: True,
                const.CONF_EV_POWER_ENTITY: "sensor.ev_power",
                const.CONF_EV_DEADBAND: 500,
            },
            states={"sensor.ev_power": "1200"},
        )
        controller.enabled = True

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_BATTERY_HOLD, 0)])
        self.assertEqual(controller.last_command, "ev_hold")
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_disable_returns_to_goodwe_auto(self):
        controller, _, client, coordinator = self.make_controller()
        controller.enabled = True
        controller.target_power = 4200
        controller.expected_mode = const.MODE_DISCHARGE_BATTERY
        controller.last_command = "battery_discharge"

        await controller.async_disable()

        self.assertFalse(controller.enabled)
        self.assertEqual(controller.target_power, 0)
        self.assertEqual(controller.expected_mode, const.MODE_AUTO)
        self.assertEqual(controller.last_command, "goodwe_auto")
        self.assertEqual(client.calls, [(const.MODE_AUTO, 0)])
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_manual_command_takes_ownership_and_blocks_auto_evaluation(self):
        controller, _, client, coordinator = self.make_controller(p_batt="3000")
        controller.enabled = True

        await controller.async_manual_command(
            const.MODE_CHARGE_BATTERY,
            4000,
            "manual_charge",
        )
        await controller.async_evaluate()

        self.assertFalse(controller.enabled)
        self.assertEqual(client.calls, [(const.MODE_CHARGE_BATTERY, 4000)])
        self.assertEqual(controller.target_power, 4000)
        self.assertEqual(controller.last_command, "manual_charge")
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_ev_stop_waits_for_fresh_native_optimization(self):
        controller, hass, client, coordinator = self.make_controller(
            p_batt="3500",
            options={
                const.CONF_ENABLE_EV_COORDINATION: True,
                const.CONF_EV_POWER_ENTITY: "sensor.ev_power",
                const.CONF_ENABLE_EMHASS_ORCHESTRATOR: True,
            },
            states={"sensor.ev_power": "0"},
        )
        controller.enabled = True
        controller._ev_was_active = True

        controller._async_source_changed(Event({"entity_id": "sensor.ev_power"}))

        self.assertEqual(client.calls, [])
        self.assertEqual(coordinator.refresh_count, 0)
        self.assertEqual(controller.target_power, 0)
        self.assertEqual(controller.expected_mode, const.MODE_BATTERY_HOLD)
        self.assertEqual(
            controller.last_command,
            "waiting_for_ev_stop_optimization",
        )
        self.assertEqual(hass.tasks, [])


if __name__ == "__main__":
    unittest.main()
