"""Hybrid 2.0 house self-consumption, periodic reference and failure behavior."""

import asyncio
from datetime import datetime, timedelta, timezone
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_controller_v034_ev as fixtures

runtime = fixtures.controller_v033_module
const = fixtures.const


class Hybrid2EVReferenceTests(unittest.IsolatedAsyncioTestCase):
    def make_controller(self):
        helper = fixtures.EVAntiDischargeStrategyTests()
        controller, client = helper.make_controller(p_batt="700", p_grid="0", strategy="hybrid_2")
        controller.hass.states.set("sensor.ev_power", "11000")
        return controller, client

    def event(self):
        return SimpleNamespace(data={"entity_id": "sensor.ev_power"})

    async def test_positive_battery_plan_neutral_grid_allows_house_self_use(self):
        controller, client = self.make_controller()
        controller.coordinator.data.values.update(total_load_power=11600, pv_total_power=400)
        await controller.async_evaluate()
        self.assertEqual(client.calls, [(5, 600)])
        self.assertEqual(controller.ev_protection_state, "house_self_consumption")
        self.assertEqual(controller._actual_snapshot()["ev_reference_power_w"], 11000)

    async def test_15_second_reference_follows_load_minus_ev_without_meter_feedback(self):
        controller, client = self.make_controller()
        with patch.object(runtime, "monotonic", return_value=100):
            await controller.async_evaluate()
        controller.hass.states.set("sensor.ev_power", "9000")
        controller.coordinator.data.values.update(total_load_power=18000, meter_total_power_fast=-15000)
        with patch.object(runtime, "monotonic", return_value=114):
            controller._async_source_changed(self.event())
            await asyncio.gather(*controller.hass.tasks)
        self.assertEqual(client.calls, [(5, 600)])
        with patch.object(runtime, "monotonic", return_value=115):
            controller._async_ev_reference_tick(None)
            await asyncio.gather(*controller.hass.tasks)
        self.assertEqual(client.calls, [(5, 600), (5, 9000)])

    async def test_missing_ev_measurement_holds_without_claiming_ev_stopped(self):
        controller, client = self.make_controller()
        controller.entry.options[const.CONF_ENABLE_EMHASS_ORCHESTRATOR] = True
        await controller.async_evaluate()
        controller.hass.states.set("sensor.ev_power", "unavailable")
        controller._async_source_changed(self.event())
        await asyncio.gather(*controller.hass.tasks)
        self.assertTrue(controller.ev_is_active())
        self.assertEqual(client.calls[-1], (8, 0))
        self.assertEqual(controller.ev_protection_state, "self_consumption_hold")
        controller.hass.states.set("sensor.ev_power", "11000")
        controller._async_source_changed(self.event())
        await asyncio.gather(*controller.hass.tasks)
        self.assertEqual(client.calls[-1], (5, 600))

    async def test_stale_future_invalid_or_unsupported_power_holds(self):
        cases = ("unknown", "nan", "inf", "-5", "stale", "future", "naive", "no_time", "unit_A", "unit_missing")
        for case in cases:
            with self.subTest(case=case):
                controller, client = self.make_controller()
                await controller.async_evaluate()
                state = controller.hass.states.get("sensor.ev_power")
                if case == "stale":
                    state.last_reported -= timedelta(seconds=31)
                elif case == "future":
                    state.last_reported += timedelta(seconds=5)
                elif case == "naive":
                    state.last_reported = datetime.now()
                elif case == "no_time":
                    state.last_reported = state.last_updated = None
                elif case.startswith("unit_"):
                    state.attributes["unit_of_measurement"] = "A" if case == "unit_A" else None
                else:
                    state.state = case
                controller._async_ev_reference_tick(None)
                await asyncio.gather(*controller.hass.tasks)
                self.assertEqual(client.calls[-1], (8, 0))

    async def test_report_timestamp_and_units_define_reference(self):
        for unit, raw in (("W", "11000"), ("kW", "11"), ("MW", "0.011"), ("mW", "11000000")):
            controller, client = self.make_controller()
            state = controller.hass.states.get("sensor.ev_power")
            state.state = raw
            state.attributes["unit_of_measurement"] = unit
            state.last_updated = datetime.now(timezone.utc) - timedelta(minutes=10)
            await controller.async_evaluate()
            self.assertEqual(client.calls, [(5, 600)])
        controller, client = self.make_controller()
        state = controller.hass.states.get("sensor.ev_power")
        state.last_reported = None
        await controller.async_evaluate()
        self.assertEqual(client.calls, [(5, 600)])

    async def test_house_allowance_is_capped_without_capping_ev_power(self):
        controller, client = self.make_controller()
        controller.entry.options[const.CONF_MAX_POWER] = 10000
        controller.coordinator.data.values["total_load_power"] = 27000
        await controller.async_evaluate()
        self.assertEqual(client.calls, [(5, 10000)])

    async def test_plan_pause_or_sell_interrupts_reference_throttle(self):
        for battery, grid in (("0", "4000"), ("700", "-4000"), ("700", "4000")):
            controller, client = self.make_controller()
            with patch.object(runtime, "monotonic", return_value=100):
                await controller.async_evaluate()
                controller.hass.states.set("sensor.p_batt", battery)
                controller.hass.states.set("sensor.p_grid", grid)
                await controller.async_evaluate()
            self.assertEqual(client.calls, [(5, 600), (8, 0)])

    async def test_neutral_battery_at_zero_grid_keeps_house_supply(self):
        controller, client = self.make_controller()
        controller.hass.states.set("sensor.p_batt", "0")
        await controller.async_evaluate()
        self.assertEqual(client.calls, [(5, 600)])
        await controller.async_manual_command(8, 0, "manual_pause")
        controller._async_ev_reference_tick(None)
        self.assertEqual(client.calls, [(5, 600), (8, 0)])
        self.assertEqual(controller.mapping_preview()["reason"], "explicit_pause")

    async def test_stale_failed_missing_or_cloud_load_cannot_feed_house_reference(self):
        for case in ("stale", "future", "naive", "missing_time", "cloud", "failed", "missing_load", "invalid_load"):
            with self.subTest(case=case):
                controller, client = self.make_controller()
                await controller.async_evaluate()
                data = controller.coordinator.data
                if case == "stale":
                    data.source_updated_at -= timedelta(seconds=31)
                elif case == "future":
                    data.source_updated_at += timedelta(seconds=5)
                elif case == "naive":
                    data.source_updated_at = datetime.now()
                elif case == "missing_time":
                    data.source_updated_at = None
                elif case == "cloud":
                    data.source = "sems"
                elif case == "failed":
                    controller.coordinator.last_update_success = False
                elif case == "missing_load":
                    data.values.pop("total_load_power")
                else:
                    data.values["total_load_power"] = float("nan")
                controller._async_ev_reference_tick(None)
                await asyncio.gather(*controller.hass.tasks)
                self.assertEqual(client.calls[-1], (8, 0))
                self.assertIsNone(controller.mapping_preview()["inputs"]["load_35172_w"])

    async def test_preview_and_live_share_model_but_preview_has_no_side_effects(self):
        controller, client = self.make_controller()
        preview = controller.mapping_preview()
        self.assertEqual((preview["mode"], preview["power_w"]), (5, 600))
        self.assertTrue(preview["preview_only"])
        self.assertTrue(preview["validation_required"])
        self.assertEqual(client.calls, [])
        self.assertEqual(controller.hass.tasks, [])
        await controller.async_evaluate()
        self.assertEqual(client.calls, [(preview["mode"], preview["power_w"])])

    async def test_charge_and_discharge_transitions_keep_grid_first_watts(self):
        controller, client = self.make_controller()
        controller.hass.states.set("sensor.ev_power", "0")
        for battery, grid, expected in (("0", "700", (1, 0)), ("5000", "-4000", (3, 5000)),
                                       ("-8400", "2900", (2, 8400)), ("0", "-4000", (10, 4000))):
            controller.hass.states.set("sensor.p_batt", battery)
            controller.hass.states.set("sensor.p_grid", grid)
            await controller.async_evaluate()
            self.assertEqual(client.calls[-1], expected)

    async def test_missing_or_suspended_plan_holds_even_with_a_fresh_ev_reference(self):
        for source in ("sensor.p_batt", "sensor.p_grid", "suspended"):
            controller, client = self.make_controller()
            await controller.async_evaluate()
            if source == "suspended":
                controller._plan_update_suspensions = 1
            else:
                controller.hass.states.set(source, "unavailable")
            controller._async_ev_reference_tick(None)
            await asyncio.gather(*controller.hass.tasks)
            self.assertEqual(client.calls[-1], (8, 0))

    async def test_status_detection_still_requires_measured_power_for_self_use(self):
        controller, client = self.make_controller()
        controller.entry.options[const.CONF_EV_DETECTION_METHOD] = const.EV_DETECTION_METHOD_STATE
        controller.entry.options[const.CONF_EV_MODE_ENTITY] = "binary_sensor.ev"
        controller.hass.states.set("binary_sensor.ev", "on")
        controller.hass.states.set("sensor.ev_power", "unavailable")
        await controller.async_evaluate()
        self.assertEqual(client.calls, [(8, 0)])
        self.assertIn("sensor.ev_power", controller.ev_source_ids)

    async def test_periodic_subscription_has_one_task_and_stops_for_manual_or_unload(self):
        controller, client = self.make_controller()
        schedules, unsubscribed = [], []

        def subscribe(hass, callback, interval):
            schedules.append((callback, interval))
            return lambda: unsubscribed.append(True)

        events = SimpleNamespace(async_track_time_interval=subscribe, async_track_state_change_event=lambda *_: None)
        with patch.dict(sys.modules, {"homeassistant.helpers.event": events}):
            await controller.async_setup()
        self.assertEqual(schedules[0][1].total_seconds(), 15)
        tick = schedules[0][0]
        tick(None)
        tick(None)
        self.assertEqual(len(controller.hass.tasks), 1)
        await asyncio.gather(*controller.hass.tasks)
        self.assertEqual(client.calls, [(5, 600)])
        await controller.async_manual_command(11, 4000, "manual_test")
        tick(None)
        self.assertEqual(len(controller.hass.tasks), 1)
        await controller.async_unload()
        self.assertEqual(unsubscribed, [True])
        controller.enabled = True
        tick(None)
        self.assertEqual(len(controller.hass.tasks), 1)

    async def test_live_strategy_switch_observes_reference_with_status_detection(self):
        controller, client = self.make_controller()
        controller.entry.data[const.CONF_CONTROL_STRATEGY] = "grid"
        controller.entry.options[const.CONF_EV_DETECTION_METHOD] = const.EV_DETECTION_METHOD_STATE
        controller.entry.options[const.CONF_EV_MODE_ENTITY] = "binary_sensor.ev"
        controller.hass.states.set("binary_sensor.ev", "on")
        listeners = []

        def listen(hass, sources, callback):
            listeners.append((sources, callback))
            return lambda: None

        events = SimpleNamespace(
            async_track_time_interval=lambda *_: (lambda: None),
            async_track_state_change_event=listen,
        )
        with patch.dict(sys.modules, {"homeassistant.helpers.event": events}):
            await controller.async_setup()
        self.assertEqual(listeners[0][0], ["sensor.ev_power"])
        listeners[0][1](self.event())
        self.assertEqual(controller.hass.tasks, [])
        controller.entry.data[const.CONF_CONTROL_STRATEGY] = "hybrid_2"
        listeners[0][1](self.event())
        await asyncio.gather(*controller.hass.tasks)
        self.assertEqual(client.calls, [(5, 600)])
        await controller.async_unload()
