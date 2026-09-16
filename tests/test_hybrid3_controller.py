"""Hybrid 3.0 runtime guards and read-back regressions; no hardware I/O."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import test_controller as base_tests
import test_controller_v034_ev as ev_tests

module = ev_tests.controller_v033_module
const = ev_tests.const


class Hybrid3ControllerTests(unittest.IsolatedAsyncioTestCase):
    def make_controller(self, battery="0", grid="0", ev=True):
        helper = ev_tests.EVAntiDischargeStrategyTests()
        controller, client = helper.make_controller(
            p_batt=battery, p_grid=grid, strategy="hybrid_3")
        controller.hass.states.set("sensor.ev_power", "11000" if ev else "0")
        controller.execution_history = base_tests.FakeExecutionHistory()
        client.readbacks = []
        client.read_count = 0

        async def read_control():
            client.read_count += 1
            result = client.readbacks.pop(0) if client.readbacks else client.calls[-1]
            if isinstance(result, Exception):
                raise result
            return SimpleNamespace(mode=result[0], power=result[1], values={})

        def publish(control):
            if controller.coordinator.data is not None:
                controller.coordinator.data.mode = control.mode
                controller.coordinator.data.power = control.power

        client.async_read_control_status = read_control
        controller.coordinator.async_publish_local_readback = publish
        return controller, client

    async def test_live_six_scenarios(self):
        for battery, grid, ev, expected in (
            ("0", "700", False, (1, 0)), ("0", "700", True, (5, 600)),
            ("4200", "-5000", False, (3, 4200)), ("4200", "-5000", True, (5, 600)),
            ("-700", "5000", False, (2, 700)), ("-700", "5000", True, (2, 700)),
        ):
            with self.subTest(battery=battery, ev=ev):
                c, client = self.make_controller(battery, grid, ev)
                await c.async_evaluate()
                self.assertEqual(client.calls, [expected])
                self.assertEqual(c.hybrid3_diagnostics["command_readback"], "verified")
                self.assertEqual(client.read_count, 1)

    async def test_charge_does_not_require_house_reference(self):
        c, client = self.make_controller("-15000", "9574")
        c.coordinator.data.source = "sems"
        c.hass.states.get("sensor.ev_power").last_reported -= timedelta(minutes=1)
        await c.async_evaluate()
        self.assertEqual(client.calls, [(2, 15000)])
        self.assertEqual(c.last_command, "ev_battery_charge")

    async def test_exact_measurement_faults_hold(self):
        for fault in ("ev_units_invalid", "ev_stale", "ev_timestamp_future",
                      "ev_timestamp_invalid", "load_stale", "load_timestamp_future",
                      "load_timestamp_invalid", "load_not_local", "load_read_failed",
                      "load_invalid", "measurement_time_skew"):
            with self.subTest(fault=fault):
                c, client = self.make_controller()
                state = c.hass.states.get("sensor.ev_power")
                data = c.coordinator.data
                if fault == "ev_units_invalid": state.attributes["unit_of_measurement"] = "A"
                if fault == "ev_stale": state.last_reported -= timedelta(seconds=31)
                if fault == "ev_timestamp_future": state.last_reported += timedelta(seconds=5)
                if fault == "ev_timestamp_invalid": state.last_reported = datetime.now()
                if fault == "load_stale": data.source_updated_at -= timedelta(seconds=31)
                if fault == "load_timestamp_future": data.source_updated_at += timedelta(seconds=5)
                if fault == "load_timestamp_invalid": data.source_updated_at = datetime.now()
                if fault == "load_not_local": data.source = "sems"
                if fault == "load_read_failed": c.coordinator.last_update_success = False
                if fault == "load_invalid": data.values["total_load_power"] = float("nan")
                if fault == "measurement_time_skew": data.source_updated_at -= timedelta(seconds=20)
                await c.async_evaluate()
                self.assertEqual(client.calls, [(8, 0)])
                self.assertEqual(c.hybrid3_diagnostics["hold_reason"], fault)
                self.assertTrue(c.hybrid3_diagnostics["recovering"])
                event = c.execution_history.events[-1]
                self.assertEqual(event["actual"]["hybrid3"]["hold_reason"], fault)

    async def test_recovery_requires_distinct_pairs_and_one_interval(self):
        c, client = self.make_controller()
        c.coordinator.data.source_updated_at -= timedelta(seconds=31)
        await c.async_evaluate()
        c.coordinator.data.source_updated_at = datetime.now(timezone.utc)
        c.hass.states.set("sensor.ev_power", "11000")
        with patch.object(module, "monotonic", return_value=100):
            await c.async_evaluate()
        self.assertEqual(c.expected_mode, 8)
        with patch.object(module, "monotonic", return_value=116):
            await c.async_evaluate()
        self.assertEqual(c.expected_mode, 8)  # same pair cannot release Hold
        c.coordinator.data.source_updated_at = datetime.now(timezone.utc)
        c.hass.states.set("sensor.ev_power", "11000")
        with patch.object(module, "monotonic", return_value=116):
            await c.async_evaluate()
        self.assertEqual(c.expected_mode, 5)
        self.assertEqual(client.calls[-1], (5, 600))
        self.assertFalse(c.hybrid3_diagnostics["recovering"])

    async def test_reference_throttle_and_safety_bypass(self):
        c, client = self.make_controller()
        with patch.object(module, "monotonic", return_value=100):
            await c.async_evaluate()
        c.coordinator.data.values["total_load_power"] = 12000
        with patch.object(module, "monotonic", return_value=114):
            await c.async_evaluate()
        self.assertEqual(client.calls, [(5, 600)])
        with patch.object(module, "monotonic", return_value=115):
            await c.async_evaluate()
        self.assertEqual(client.calls[-1], (5, 1000))
        c.coordinator.data.source_updated_at -= timedelta(seconds=31)
        with patch.object(module, "monotonic", return_value=116):
            await c.async_evaluate()
        self.assertEqual(client.calls[-1], (8, 0))

    async def test_direct_readback_bypasses_full_refresh_and_preserves_load_age(self):
        c, client = self.make_controller()
        before = c.coordinator.data.source_updated_at
        c.coordinator.last_update_success = True
        await c.async_evaluate()
        self.assertEqual(c.coordinator.refresh_count, 0)
        self.assertEqual(c.coordinator.data.source_updated_at, before)
        await c._async_apply_command(5, 600, "ev_house_self_consumption", skip_if_readback_matches=True)
        self.assertEqual(client.calls, [(5, 600)])

    async def test_delayed_readback_is_retried_without_rewriting(self):
        c, client = self.make_controller()
        client.readbacks = [(8, 0), (8, 0), (5, 600)]
        with patch.object(module.asyncio, "sleep", new=AsyncMock()):
            await c.async_evaluate()
        self.assertEqual(client.calls, [(5, 600)])
        self.assertEqual(client.read_count, 3)
        self.assertEqual(c.hybrid3_diagnostics["command_readback"], "verified")

    async def test_unconfirmed_hold_invalidates_old_mode5_ack(self):
        c, client = self.make_controller()
        await c.async_evaluate()
        client.readbacks = [(5, 600)] * 3
        with patch.object(module.asyncio, "sleep", new=AsyncMock()):
            with self.assertRaisesRegex(RuntimeError, "not confirmed"):
                await c._async_apply_command(8, 0, "ev_self_consumption_hold", skip_if_readback_matches=True)
        self.assertEqual(c.hybrid3_diagnostics["command_readback"], "mismatch")
        self.assertFalse(c._actual_command_matches(5, 600))
        await c._async_apply_command(5, 600, "ev_house_self_consumption", skip_if_readback_matches=True)
        self.assertEqual(client.calls, [(5, 600), (8, 0), (5, 600)])

    async def test_failed_readback_cannot_verify_cached_matching_mode(self):
        c, client = self.make_controller()
        c.coordinator.data.mode, c.coordinator.data.power = 5, 600
        client.readbacks = [RuntimeError("read failed")]
        with self.assertRaisesRegex(RuntimeError, "read failed"):
            await c.async_evaluate()
        self.assertEqual(c.hybrid3_diagnostics["command_readback"], "unavailable")
        self.assertFalse(c._actual_command_matches(5, 600))
        self.assertEqual(c.execution_history.events[-1]["outcome"]["verification_status"], "unavailable")

    async def test_failed_write_is_diagnosed_and_never_acknowledged(self):
        c, client = self.make_controller()
        client.async_set_mode = AsyncMock(side_effect=RuntimeError("write failed"))
        with self.assertRaisesRegex(RuntimeError, "write failed"):
            await c.async_evaluate()
        self.assertEqual(c.hybrid3_diagnostics["command_readback"], "write_failed")
        self.assertEqual(client.read_count, 0)
        self.assertIsNone(c._h3_ack)

    async def test_invalid_plan_holds_with_and_without_ev(self):
        for ev in (False, True):
            for entity in ("sensor.p_batt", "sensor.p_grid"):
                c, client = self.make_controller(ev=ev)
                c.hass.states.set(entity, "unavailable")
                await c.async_evaluate()
                self.assertEqual(client.calls, [(8, 0)])
                self.assertEqual(c.hybrid3_diagnostics["hold_reason"], entity.removeprefix("sensor.") + "_unavailable")

    async def test_ev_stop_requires_new_success_and_both_live_reports(self):
        c, client = self.make_controller("4000", "-5000", ev=False)
        stop = datetime.now(timezone.utc) - timedelta(seconds=5)
        c._h3_ev_stop_at = stop
        c.entry.runtime_data = SimpleNamespace(orchestrator=SimpleNamespace(last_success=stop - timedelta(seconds=1)))
        for _ in range(2):
            await c.async_evaluate()
            self.assertEqual(c.expected_mode, 8)
        c.entry.runtime_data.orchestrator.last_success = datetime.now(timezone.utc)
        c.hass.states.get("sensor.p_grid").last_reported = stop
        await c.async_evaluate()
        self.assertEqual(c.expected_mode, 8)
        c.hass.states.get("sensor.p_grid").last_reported = datetime.now()
        await c.async_evaluate()  # reject naive report, do not crash
        self.assertEqual(c.expected_mode, 8)
        c.hass.states.set("sensor.p_grid", "-5000")
        await c.async_evaluate()
        self.assertEqual(client.calls[-1], (3, 4000))
        self.assertIsNone(c._h3_ev_stop_at)

    async def test_manual_modes_and_disable_are_not_remapped(self):
        c, client = self.make_controller()
        for mode in range(1, 13):
            await c.async_manual_command(mode, 700, f"manual_mode_{mode}")
            self.assertEqual(client.calls[-1][0], mode)
            self.assertFalse(c.enabled)
        c.enabled = True
        await c.async_disable()
        self.assertEqual(client.calls[-1], (1, 0))
        self.assertFalse(c.enabled)

    async def test_ev_stop_callback_latches_hold_across_repeated_idle_events(self):
        c, client = self.make_controller("4000", "-5000")
        c.entry.options[const.CONF_ENABLE_EMHASS_ORCHESTRATOR] = True
        await c.async_evaluate()
        c.hass.states.set("sensor.ev_power", "0")
        event = SimpleNamespace(data={"entity_id": "sensor.ev_power"})
        c._async_source_changed(event)
        stop = c._h3_ev_stop_at
        self.assertIsNotNone(stop)
        await asyncio.gather(*c.hass.tasks)
        self.assertEqual(client.calls[-1], (8, 0))
        c._async_source_changed(event)
        await asyncio.gather(*c.hass.tasks)
        self.assertEqual(c._h3_ev_stop_at, stop)
        self.assertEqual(c.last_command, "waiting_for_ev_stop_optimization")
        self.assertNotIn((3, 4000), client.calls)

    async def test_known_ev_stays_guarded_after_invalid_plan_then_missing_ev(self):
        c, client = self.make_controller()
        c.hass.states.set("sensor.p_batt", "unavailable")
        await c.async_evaluate()
        self.assertTrue(c._ev_was_active)
        c.hass.states.set("sensor.ev_power", "unavailable")
        c.hass.states.set("sensor.p_batt", "0")
        await c.async_evaluate()
        self.assertTrue(c.ev_is_active())
        self.assertEqual(client.calls[-1], (8, 0))

    async def test_optional_ev_source_absent_does_not_break_non_ev_control(self):
        c, client = self.make_controller(ev=False)
        c.entry.options.pop(const.CONF_EV_POWER_ENTITY)
        original_get = c.hass.states.get
        def get(entity_id):
            self.assertIsInstance(entity_id, str)
            return original_get(entity_id)
        c.hass.states.get = get
        await c.async_evaluate()
        self.assertEqual(client.calls, [(1, 0)])
        self.assertEqual(c.hybrid3_diagnostics["reason"], "ev_missing")

    async def test_valid_mirror_can_bridge_missing_but_not_explicit_nonready_plan(self):
        c, client = self.make_controller("unavailable", "unavailable")
        c.entry.options[const.CONF_OPTIM_STATUS_ENTITY] = "sensor.optim_status"
        plan = SimpleNamespace(current_p_batt=lambda: -700, current_p_grid=lambda: 5000,
                               has_current_plan=lambda: True, diagnostics={})
        c.entry.runtime_data = SimpleNamespace(plan_runtime=plan)
        await c.async_evaluate()
        self.assertEqual(client.calls[-1], (2, 700))
        c.hass.states.set("sensor.optim_status", "running")
        await c.async_evaluate()
        self.assertEqual(client.calls[-1], (8, 0))
        self.assertEqual(c.hybrid3_diagnostics["hold_reason"], "optimizer_not_ready")

    async def test_reference_recovery_requires_both_sources_to_advance(self):
        c, client = self.make_controller()
        c._h3_reference.invalidate("load_stale")
        with patch.object(module, "monotonic", return_value=100):
            await c.async_evaluate()
        c.hass.states.set("sensor.ev_power", "11000")
        with patch.object(module, "monotonic", return_value=116):
            await c.async_evaluate()
        self.assertEqual(c.expected_mode, 8)
        c.coordinator.data.source_updated_at = datetime.now(timezone.utc)
        with patch.object(module, "monotonic", return_value=116):
            await c.async_evaluate()
        self.assertEqual(client.calls[-1], (5, 600))

    async def test_preview_is_read_only_and_exposes_guard(self):
        c, client = self.make_controller("4000", "-5000")
        before = dict(vars(c._h3_reference))
        for _ in range(3):
            model = c.mapping_preview()
        self.assertEqual(model["model"], "hybrid_3_ev_excluded_v1")
        self.assertEqual(model["mode"], 5)
        self.assertIn("runtime_guard", model)
        self.assertEqual(vars(c._h3_reference), before)
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
