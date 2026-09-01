"""Safety-focused unit tests for the GW EnergyPilot controller.

These tests intentionally use only the Python standard library. Home Assistant,
the Modbus client, and the coordinator are replaced with small fakes so the
controller decision logic can be tested without hardware or network access.
"""

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

    def async_dispatcher_connect(hass, signal, callback_func):
        hass.dispatcher_listeners.append((signal, callback_func))
        return lambda: None

    dispatcher = _module(
        "homeassistant.helpers.dispatcher",
        async_dispatcher_connect=async_dispatcher_connect,
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
    def __init__(self, state, **attributes):
        self.state = state
        self.attributes = attributes


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
        self.dispatcher_listeners = []
        self.tracked_state_changes = []
        self.tasks = []

    def async_create_task(self, coroutine, name=None):
        task = asyncio.create_task(coroutine, name=name)
        self.tasks.append(task)
        return task


class FakeEntry:
    def __init__(self, options=None, data=None):
        self.entry_id = "test-entry"
        self.options = dict(options or {})
        # The controller safety suite exercises the explicit PCC strategy unless
        # a strategy-specific test deliberately replaces/clears entry.data.
        if data is None:
            data = {const.CONF_USE_GOODWE_SMART_METER: True}
        self.data = dict(data)


class FakeClient:
    def __init__(self):
        self.calls = []

    async def async_set_mode(self, mode, power):
        self.calls.append((mode, power))


class FakeCoordinatorData:
    def __init__(self, *, mode=None, power=None):
        self.values = {"meter_total_power_fast": 0}
        self.mode = mode
        self.power = power


class FakeCoordinator:
    def __init__(self, *, mode=None, power=None):
        self.refresh_count = 0
        self.data = FakeCoordinatorData(mode=mode, power=power)

    async def async_request_refresh(self):
        self.refresh_count += 1


class FakeExecutionHistory:
    def __init__(self):
        self.events = []

    async def async_append(self, event):
        self.events.append(event)
        return event


class ControllerSafetyTests(unittest.IsolatedAsyncioTestCase):
    """Protect PCC target mapping and automatic/manual ownership."""

    def make_controller(
        self,
        *,
        p_batt="0",
        p_grid="0",
        coordinator_mode=None,
        coordinator_power=None,
        options=None,
        states=None,
        execution_history=None,
    ):
        merged_options = {
            const.CONF_P_BATT_ENTITY: "sensor.p_batt",
            const.CONF_P_GRID_ENTITY: "sensor.p_grid",
            **(options or {}),
        }
        merged_states = {
            "sensor.p_batt": p_batt,
            "sensor.p_grid": p_grid,
            **(states or {}),
        }
        hass = FakeHass(merged_states)
        entry = FakeEntry(merged_options)
        client = FakeClient()
        coordinator = FakeCoordinator(
            mode=coordinator_mode,
            power=coordinator_power,
        )
        controller = controller_module.GWEnergyPilotController(
            hass,
            entry,
            client,
            coordinator,
            execution_history=execution_history,
        )
        return controller, hass, client, coordinator

    async def test_setup_tracks_both_emhass_outputs_without_feedback_timer(self):
        controller, hass, _, _ = self.make_controller()

        await controller.async_setup()

        self.assertEqual(len(hass.tracked_state_changes), 1)
        tracked_entities = set(hass.tracked_state_changes[0][0])
        self.assertIn("sensor.p_batt", tracked_entities)
        self.assertIn("sensor.p_grid", tracked_entities)
        self.assertFalse(hasattr(hass, "tracked_intervals"))

    async def test_missing_scheduled_plan_step_holds_enabled_battery(self):
        controller, _, client, coordinator = self.make_controller(
            p_batt="4200",
            p_grid="-4200",
        )
        controller.enabled = True

        await controller.async_hold_for_plan_step("plan_step_unavailable")

        self.assertEqual(client.calls, [(const.MODE_BATTERY_HOLD, 0)])
        self.assertEqual(controller.last_command, "plan_step_unavailable")
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_plan_step_fail_safe_does_not_take_manual_ownership(self):
        controller, _, client, coordinator = self.make_controller(
            coordinator_mode=const.MODE_BATTERY_HOLD,
            coordinator_power=0,
        )

        await controller.async_hold_for_plan_step("plan_step_publish_failed")

        self.assertEqual(client.calls, [])
        self.assertEqual(coordinator.refresh_count, 0)
        self.assertEqual(controller.last_command, "goodwe_auto")

    async def test_plan_source_events_wait_until_orchestrator_resumes_controller(self):
        controller, hass, client, _ = self.make_controller(
            p_batt="2500",
            p_grid="-2500",
        )
        controller.enabled = True
        controller.suspend_plan_updates()

        controller._async_source_changed(
            Event({"entity_id": "sensor.p_batt"})
        )
        await controller.async_evaluate()

        self.assertEqual(hass.tasks, [])
        self.assertEqual(client.calls, [])

        controller.resume_plan_updates()
        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_GRID_EXPORT_TARGET, 2500)])

    async def test_positive_p_grid_maps_to_mode9_import_target(self):
        controller, _, client, coordinator = self.make_controller(
            p_batt="-4200",
            p_grid="3750",
        )

        await controller.async_enable()

        self.assertTrue(controller.enabled)
        self.assertEqual(client.calls, [(const.MODE_GRID_IMPORT_TARGET, 3750)])
        self.assertEqual(controller.target_power, 3750)
        self.assertEqual(controller.expected_mode, const.MODE_GRID_IMPORT_TARGET)
        self.assertEqual(controller.last_command, "grid_import_target")
        self.assertIsNotNone(controller.last_ems_setpoint_updated_at)
        self.assertIsNotNone(controller.last_ems_setpoint_updated_at.tzinfo)
        self.assertEqual(controller.last_ems_setpoint, 3750)
        self.assertEqual(controller.last_ems_mode, const.MODE_GRID_IMPORT_TARGET)
        self.assertEqual(
            controller.last_ems_setpoint_command,
            "grid_import_target",
        )
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_negative_p_grid_maps_to_mode10_export_target(self):
        controller, _, client, coordinator = self.make_controller(
            p_batt="5200",
            p_grid="-4100",
        )
        controller.enabled = True

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_GRID_EXPORT_TARGET, 4100)])
        self.assertEqual(controller.target_power, 4100)
        self.assertEqual(controller.last_command, "grid_export_target")
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_p_grid_direction_is_authoritative_over_p_batt_direction(self):
        """Mode 9/10 may charge or discharge internally to meet the PCC target."""
        controller, _, client, _ = self.make_controller(
            p_batt="2500",  # discharge reference
            p_grid="6000",  # but site still plans net import
        )
        controller.enabled = True

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_GRID_IMPORT_TARGET, 6000)])
        self.assertEqual(controller.last_command, "grid_import_target")

    async def test_zero_grid_deadband_uses_goodwe_auto(self):
        for p_grid in ("-1000", "0", "1000"):
            with self.subTest(p_grid=p_grid):
                controller, _, client, coordinator = self.make_controller(
                    p_batt="-1800",
                    p_grid=p_grid,
                    options={
                        const.CONF_DEADBAND: 100,
                        const.CONF_GOODWE_AUTO_DEADBAND: 1000,
                    },
                )
                controller.enabled = True

                await controller.async_evaluate()

                self.assertEqual(client.calls, [(const.MODE_AUTO, 0)])
                self.assertEqual(controller.target_power, 0)
                self.assertEqual(controller.expected_mode, const.MODE_AUTO)
                self.assertEqual(controller.last_command, "grid_zero_auto")
                self.assertEqual(coordinator.refresh_count, 1)

    async def test_zero_power_mode_records_the_actual_written_setpoint(self):
        controller, _, client, _ = self.make_controller()

        await controller.async_manual_command(const.MODE_AUTO, 4200, "manual_auto")

        self.assertEqual(client.calls, [(const.MODE_AUTO, 0)])
        self.assertEqual(controller.last_ems_setpoint, 0)

    async def test_grid_target_is_clamped_to_configured_maximum(self):
        for p_grid, mode in (
            ("18000", const.MODE_GRID_IMPORT_TARGET),
            ("-18000", const.MODE_GRID_EXPORT_TARGET),
        ):
            with self.subTest(p_grid=p_grid):
                controller, _, client, _ = self.make_controller(
                    p_batt="0",
                    p_grid=p_grid,
                    options={const.CONF_MAX_POWER: 5000},
                )
                controller.enabled = True

                await controller.async_evaluate()

                self.assertEqual(client.calls, [(mode, 5000)])
                self.assertEqual(controller.target_power, 5000)

    async def test_invalid_p_batt_never_writes_modbus(self):
        for value in (
            "unknown",
            "unavailable",
            "none",
            "",
            "not-a-number",
            "nan",
            "inf",
            "-inf",
        ):
            with self.subTest(value=value):
                controller, _, client, coordinator = self.make_controller(
                    p_batt=value,
                    p_grid="3000",
                )
                controller.enabled = True

                await controller.async_evaluate()

                self.assertEqual(client.calls, [])
                self.assertEqual(controller.last_command, "waiting_for_p_batt")
                self.assertEqual(coordinator.refresh_count, 0)

    async def test_invalid_p_grid_never_writes_modbus(self):
        for value in (
            "unknown",
            "unavailable",
            "none",
            "",
            "not-a-number",
            "nan",
            "inf",
            "-inf",
        ):
            with self.subTest(value=value):
                controller, _, client, coordinator = self.make_controller(
                    p_batt="-2500",
                    p_grid=value,
                )
                controller.enabled = True

                await controller.async_evaluate()

                self.assertEqual(client.calls, [])
                self.assertEqual(controller.last_command, "waiting_for_p_grid")
                self.assertEqual(coordinator.refresh_count, 0)

    async def test_optimizer_must_be_ready_before_modbus_write(self):
        controller, _, client, coordinator = self.make_controller(
            p_batt="-1500",
            p_grid="1200",
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

    async def test_ev_charging_blocks_battery_discharge(self):
        controller, _, client, coordinator = self.make_controller(
            p_batt="2500",
            p_grid="4000",
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
        self.assertEqual(controller.last_command, "ev_anti_discharge_hold")
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_status_detection_uses_attached_tesla_charging_boolean(self):
        charging_id = "binary_sensor.tesla_wall_connector_opladen"
        controller, hass, _, _ = self.make_controller(
            options={
                const.CONF_ENABLE_EV_COORDINATION: True,
                const.CONF_EV_DETECTION_METHOD: const.EV_DETECTION_METHOD_STATE,
                const.CONF_EV_MODE_ENTITY: charging_id,
                const.CONF_EV_POWER_ENTITY: "sensor.ev_power",
            },
            states={
                charging_id: "on",
                "sensor.ev_power": "1200",
            },
        )

        await controller.async_setup()

        self.assertEqual(controller.ev_source_ids, {charging_id})
        self.assertTrue(controller.ev_is_active())
        hass.states.set(charging_id, "off")
        self.assertFalse(controller.ev_is_active())

    async def test_power_detection_ignores_active_status_source(self):
        controller, _, _, _ = self.make_controller(
            options={
                const.CONF_ENABLE_EV_COORDINATION: True,
                const.CONF_EV_DETECTION_METHOD: const.EV_DETECTION_METHOD_POWER,
                const.CONF_EV_MODE_ENTITY: "binary_sensor.charging",
                const.CONF_EV_POWER_ENTITY: "sensor.ev_power",
                const.CONF_EV_DEADBAND: 500,
            },
            states={
                "binary_sensor.charging": "on",
                "sensor.ev_power": "0",
            },
        )

        self.assertEqual(controller.ev_source_ids, {"sensor.ev_power"})
        self.assertFalse(controller.ev_is_active())

    async def test_suspended_ev_coordination_does_not_apply_ev_override(self):
        controller, _, client, coordinator = self.make_controller(
            p_batt="2500",
            p_grid="4000",
            options={
                const.CONF_ENABLE_EV_COORDINATION: True,
                const.CONF_EV_POWER_ENTITY: "sensor.ev_power",
                const.CONF_EV_DEADBAND: 500,
            },
            states={"sensor.ev_power": "1200"},
        )
        controller.entry.runtime_data = types.SimpleNamespace(
            connectivity=types.SimpleNamespace(
                ev_coordination_effective=False,
                signal="test_connectivity",
            )
        )
        controller.enabled = True

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_GRID_IMPORT_TARGET, 4000)])
        self.assertEqual(controller.last_command, "grid_import_target")
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_ev_charging_allows_explicit_battery_charge(self):
        controller, _, client, coordinator = self.make_controller(
            p_batt="-2500",
            p_grid="4000",
            options={
                const.CONF_ENABLE_EV_COORDINATION: True,
                const.CONF_EV_POWER_ENTITY: "sensor.ev_power",
                const.CONF_EV_DEADBAND: 500,
            },
            states={"sensor.ev_power": "1200"},
        )
        controller.enabled = True

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_CHARGE_BATTERY, 2500)])
        self.assertEqual(controller.last_command, "ev_charge_allowed")
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_ev_charging_neutral_plan_holds_battery(self):
        controller, _, client, coordinator = self.make_controller(
            p_batt="100",
            p_grid="6000",
            options={
                const.CONF_ENABLE_EV_COORDINATION: True,
                const.CONF_EV_POWER_ENTITY: "sensor.ev_power",
                const.CONF_EV_DEADBAND: 500,
                const.CONF_DEADBAND: 300,
            },
            states={"sensor.ev_power": "1200"},
        )
        controller.enabled = True

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_BATTERY_HOLD, 0)])
        self.assertEqual(controller.last_command, "ev_anti_discharge_hold")
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_ev_protection_presentation_has_no_independent_control_state(self):
        controller, _, _, _ = self.make_controller(
            options={
                const.CONF_ENABLE_EV_COORDINATION: True,
                const.CONF_EV_POWER_ENTITY: "sensor.ev_power",
                const.CONF_EV_DEADBAND: 500,
            },
            states={"sensor.ev_power": "1200"},
        )

        self.assertEqual(controller.ev_protection_state, "inactive")

        controller.enabled = True
        self.assertEqual(controller.ev_protection_state, "active_pending")

        controller.last_command = "ev_anti_discharge_hold"
        self.assertEqual(controller.ev_protection_state, "blocking_discharge")

        controller.last_command = "waiting_for_ev_stop_optimization"
        controller.hass.states.set("sensor.ev_power", "0")
        self.assertEqual(controller.ev_protection_state, "waiting_for_fresh_plan")

    async def test_disable_returns_to_goodwe_auto(self):
        controller, _, client, coordinator = self.make_controller(
            p_grid="5000",
        )
        controller.enabled = True
        controller.target_power = 5000
        controller.expected_mode = const.MODE_GRID_IMPORT_TARGET
        controller.last_command = "grid_import_target"

        await controller.async_disable()

        self.assertFalse(controller.enabled)
        self.assertEqual(controller.target_power, 0)
        self.assertEqual(controller.expected_mode, const.MODE_AUTO)
        self.assertEqual(controller.last_command, "goodwe_auto")
        self.assertEqual(client.calls, [(const.MODE_AUTO, 0)])
        self.assertEqual(coordinator.refresh_count, 1)

    async def test_manual_command_takes_ownership_and_blocks_auto_evaluation(self):
        controller, _, client, coordinator = self.make_controller(
            p_batt="-3000",
            p_grid="5000",
        )
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

    async def test_matching_readback_suppresses_duplicate_auto_write(self):
        controller, _, client, coordinator = self.make_controller(
            p_batt="-3000",
            p_grid="2400",
            coordinator_mode=const.MODE_GRID_IMPORT_TARGET,
            coordinator_power=2400,
        )
        controller.enabled = True

        await controller.async_evaluate()

        self.assertEqual(client.calls, [])
        self.assertEqual(controller.target_power, 2400)
        self.assertEqual(controller.last_command, "grid_import_target")
        self.assertIsNone(controller.last_ems_setpoint_updated_at)
        self.assertEqual(coordinator.refresh_count, 0)

    async def test_failed_write_does_not_advance_setpoint_update_evidence(self):
        controller, _, client, coordinator = self.make_controller(
            p_batt="-3000",
            p_grid="2400",
        )
        controller.enabled = True

        async def fail_write(_mode, _power):
            raise RuntimeError("write failed")

        client.async_set_mode = fail_write
        with self.assertRaisesRegex(RuntimeError, "write failed"):
            await controller.async_evaluate()

        self.assertIsNone(controller.last_ems_setpoint_updated_at)
        self.assertEqual(coordinator.refresh_count, 0)

    async def test_execution_history_separates_write_from_verified_readback(self):
        history = FakeExecutionHistory()
        controller, _, client, coordinator = self.make_controller(
            coordinator_mode=const.MODE_GRID_IMPORT_TARGET,
            coordinator_power=3000,
            execution_history=history,
        )

        await controller.async_manual_command(
            const.MODE_GRID_IMPORT_TARGET,
            3000,
            "manual_grid_import",
        )

        self.assertEqual(client.calls, [(const.MODE_GRID_IMPORT_TARGET, 3000)])
        self.assertEqual(coordinator.refresh_count, 1)
        self.assertEqual(len(history.events), 1)
        self.assertEqual(
            history.events[0]["runtime_session_id"],
            controller.execution_session_id,
        )
        self.assertTrue(controller.execution_session_id)
        outcome = history.events[0]["outcome"]
        self.assertEqual(outcome["write_status"], "completed")
        self.assertEqual(outcome["verification_status"], "verified")
        self.assertEqual(outcome["readback_mode"], const.MODE_GRID_IMPORT_TARGET)

    def test_execution_context_records_soc_interval_end_evidence(self):
        controller, _, _, _ = self.make_controller()
        target_at = datetime(2026, 9, 1, 19, 15, tzinfo=timezone.utc)

        class FakePlanRuntime:
            diagnostics = {
                "source": "emhass_api_v1_plan",
                "step_seconds": 900,
            }

            @staticmethod
            def current_soc_opt_target(_now):
                return 50.0, target_at

        controller.entry.runtime_data = types.SimpleNamespace(
            plan_runtime=FakePlanRuntime(),
            orchestrator=types.SimpleNamespace(plan_revision=12),
        )

        context = controller._execution_context()

        self.assertEqual(context["plan"]["soc_opt_pct"], 50.0)
        self.assertEqual(
            context["plan"]["soc_opt_target_at"],
            "2026-09-01T19:15:00+00:00",
        )
        self.assertEqual(context["plan"]["step_seconds"], 900)

    async def test_matching_readback_is_logged_as_verified_without_write(self):
        history = FakeExecutionHistory()
        controller, _, client, _ = self.make_controller(
            p_batt="-3000",
            p_grid="2400",
            coordinator_mode=const.MODE_GRID_IMPORT_TARGET,
            coordinator_power=2400,
            execution_history=history,
        )
        controller.enabled = True

        await controller.async_evaluate()

        self.assertEqual(client.calls, [])
        self.assertEqual(
            history.events[0]["outcome"]["write_status"],
            "skipped_matching_readback",
        )
        self.assertEqual(
            history.events[0]["outcome"]["verification_status"],
            "verified",
        )

    async def test_failed_write_is_logged_without_claiming_readback(self):
        history = FakeExecutionHistory()
        controller, _, client, _ = self.make_controller(
            p_batt="-3000",
            p_grid="2400",
            execution_history=history,
        )
        controller.enabled = True

        async def fail_write(_mode, _power):
            raise RuntimeError("write failed")

        client.async_set_mode = fail_write
        with self.assertRaises(RuntimeError):
            await controller.async_evaluate()

        outcome = history.events[0]["outcome"]
        self.assertEqual(outcome["write_status"], "failed")
        self.assertEqual(outcome["verification_status"], "not_attempted")
        self.assertEqual(outcome["error_type"], "RuntimeError")

    async def test_ev_stop_waits_for_fresh_native_optimization(self):
        controller, hass, client, coordinator = self.make_controller(
            p_batt="3500",
            p_grid="-3000",
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

    async def test_legacy_grid_neutral_diagnostics_remain_inactive(self):
        controller, _, _, _ = self.make_controller()

        self.assertFalse(controller.grid_neutral_active)
        self.assertEqual(controller.grid_neutral_charge_cap, 0)
        self.assertIsNone(controller.grid_neutral_last_meter_power)
        self.assertEqual(controller.grid_neutral_export_samples, 0)
        self.assertEqual(controller.grid_neutral_hold_remaining, 0)


if __name__ == "__main__":
    unittest.main()
