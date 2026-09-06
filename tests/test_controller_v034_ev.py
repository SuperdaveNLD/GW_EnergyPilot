"""v0.34 EV anti-discharge strategy regression tests."""

from __future__ import annotations

import asyncio
import importlib
from types import SimpleNamespace
import unittest

from test_controller import ControllerSafetyTests, PACKAGE_NAME, const

controller_v033_module = importlib.import_module(f"{PACKAGE_NAME}.controller_v033")


class EVAntiDischargeStrategyTests(unittest.IsolatedAsyncioTestCase):
    """Verify EV protection blocks discharge but preserves planned charging."""

    def make_controller(self, *, p_batt: str, p_grid: str, strategy: str):
        helper = ControllerSafetyTests(
            methodName="test_positive_p_grid_maps_to_mode9_import_target"
        )
        base_controller, hass, client, coordinator = helper.make_controller(
            p_batt=p_batt,
            p_grid=p_grid,
            options={
                const.CONF_ENABLE_EV_COORDINATION: True,
                const.CONF_EV_POWER_ENTITY: "sensor.ev_power",
                const.CONF_EV_DEADBAND: 500,
                const.CONF_DEADBAND: 300,
            },
            states={"sensor.ev_power": "1200"},
        )
        base_controller.entry.data = {const.CONF_CONTROL_STRATEGY: strategy}
        controller = controller_v033_module.GWEnergyPilotController(
            hass,
            base_controller.entry,
            client,
            coordinator,
        )
        controller.enabled = True
        controller.hass.states.get("sensor.ev_power").attributes["unit_of_measurement"] = "W"
        return controller, client

    async def test_ev_discharge_plan_is_held_even_in_grid_strategy(self):
        controller, client = self.make_controller(
            p_batt="2500",
            p_grid="4000",
            strategy=const.CONTROL_STRATEGY_GRID,
        )

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_BATTERY_HOLD, 0)])
        self.assertEqual(controller.last_command, "ev_anti_discharge_hold")
        self.assertEqual(controller.ev_protection_state, "blocking_discharge")

    async def test_ev_neutral_plan_is_held(self):
        controller, client = self.make_controller(
            p_batt="100",
            p_grid="6000",
            strategy=const.CONTROL_STRATEGY_GRID,
        )

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_BATTERY_HOLD, 0)])
        self.assertEqual(controller.last_command, "ev_anti_discharge_hold")

    async def test_ev_battery_strategy_charge_uses_mode11(self):
        controller, client = self.make_controller(
            p_batt="-2500",
            p_grid="4000",
            strategy=const.CONTROL_STRATEGY_BATTERY,
        )

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_CHARGE_BATTERY, 2500)])
        self.assertEqual(controller.last_command, "ev_battery_charge")
        self.assertEqual(controller.ev_protection_state, "allowing_charge")

    async def test_ev_grid_strategy_charge_uses_mode9(self):
        controller, client = self.make_controller(
            p_batt="-2500",
            p_grid="4000",
            strategy=const.CONTROL_STRATEGY_GRID,
        )

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_GRID_IMPORT_TARGET, 4000)])
        self.assertEqual(controller.last_command, "ev_grid_import_charge")
        self.assertEqual(controller.ev_protection_state, "allowing_charge")

    async def test_ev_hybrid_charge_without_import_preserves_auto(self):
        controller, client = self.make_controller(
            p_batt="-2500",
            p_grid="0",
            strategy=const.CONTROL_STRATEGY_HYBRID,
        )

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_AUTO, 0)])
        self.assertEqual(controller.last_command, "ev_charge_allowed")
        self.assertEqual(controller.ev_protection_state, "allowing_charge")

    async def test_ev_charge_missing_grid_waits_without_write(self):
        for strategy in ("grid", "hybrid"):
            for grid in ("unknown", "unavailable", "nan", "inf"):
                with self.subTest(strategy=strategy, grid=grid):
                    controller, client = self.make_controller(
                        p_batt="-2500", p_grid=grid, strategy=strategy)
                    await controller.async_evaluate()
                    self.assertEqual(client.calls, [])
                    self.assertEqual(controller.last_command, "waiting_for_p_grid")

    async def test_ev_charge_with_pv_export_preserves_grid_target(self):
        for strategy in (const.CONTROL_STRATEGY_GRID, const.CONTROL_STRATEGY_HYBRID):
            controller, client = self.make_controller(
                p_batt="-2500", p_grid="-4000", strategy=strategy)
            await controller.async_evaluate()
            self.assertEqual(client.calls, [(const.MODE_GRID_EXPORT_TARGET, 4000)])
            self.assertEqual(controller.ev_protection_state, "allowing_charge")

    async def test_hybrid2_ev_self_use_for_pv_charge_with_planned_export(self):
        controller, client = self.make_controller(
            p_batt="-2500", p_grid="-4000", strategy="hybrid_2")
        await controller.async_evaluate()
        self.assertEqual(client.calls, [(9, 1200)])
        self.assertEqual(controller.ev_protection_state, "house_self_consumption")

    async def test_ev_start_event_preserves_existing_charge_command(self):
        for strategy in ("battery", "grid", "hybrid", "hybrid_2"):
            for grid in ("-4000", "0", "9574"):
                with self.subTest(strategy=strategy, grid=grid):
                    controller, client = self.make_controller(
                        p_batt="-15000", p_grid=grid, strategy=strategy)
                    controller.hass.states.set("sensor.ev_power", "0")
                    await controller.async_evaluate()
                    normal = (controller.expected_mode, controller.target_power)
                    controller.hass.states.set("sensor.ev_power", "11000")
                    controller._async_source_changed(SimpleNamespace(
                        data={"entity_id": "sensor.ev_power"}))
                    await asyncio.gather(*controller.hass.tasks)
                    if strategy == "hybrid_2" and grid in ("-4000", "0"):
                        self.assertEqual(client.calls, [normal, (9, 11000)])
                        self.assertEqual(controller.ev_protection_state, "house_self_consumption")
                    else:
                        self.assertEqual((controller.expected_mode, controller.target_power), normal)
                        self.assertTrue(all(call == normal for call in client.calls))
                        self.assertEqual(controller.ev_protection_state, "allowing_charge")

    async def test_ev_charge_uses_valid_persistent_grid_plan(self):
        controller, client = self.make_controller(
            p_batt="-2500", p_grid="unavailable", strategy="hybrid")
        controller.entry.runtime_data = SimpleNamespace(
            plan_runtime=SimpleNamespace(current_p_grid=lambda: 4000, diagnostics={}))
        await controller.async_evaluate()
        self.assertEqual(client.calls, [(const.MODE_GRID_IMPORT_TARGET, 4000)])


    async def test_hybrid2_charge_uses_planned_watts_with_and_without_ev(self):
        for ev in ("0", "11000"):
            for grid in ("2900", "9574"):
                with self.subTest(ev=ev, grid=grid):
                    controller, client = self.make_controller(
                        p_batt="-1330", p_grid=grid, strategy="hybrid_2")
                    controller.entry.options[const.CONF_MAX_POWER] = 12000
                    controller.hass.states.set("sensor.ev_power", ev)
                    await controller.async_evaluate()
                    self.assertEqual(client.calls, [(11, 1330)])
                    self.assertEqual(controller.control_strategy, "hybrid_2")

    async def test_hybrid2_ev_start_excludes_ev_and_follows_charge_window(self):
        controller, client = self.make_controller(
            p_batt="-1330", p_grid="-29", strategy="hybrid_2")
        controller.hass.states.set("sensor.ev_power", "0")
        await controller.async_evaluate()
        self.assertEqual(client.calls, [(1, 0)])

        controller.hass.states.set("sensor.ev_power", "11000")
        controller._async_source_changed(SimpleNamespace(data={"entity_id": "sensor.ev_power"}))
        await asyncio.gather(*controller.hass.tasks)
        self.assertEqual(client.calls, [(1, 0), (9, 11000)])
        self.assertEqual(controller.last_command, "ev_house_self_consumption")
        self.assertEqual(controller.ev_protection_state, "house_self_consumption")

        # The next EMHASS window explicitly buys grid energy for the battery.
        controller.hass.states.set("sensor.p_batt", "-4300")
        controller.hass.states.set("sensor.p_grid", "3600")
        await controller.async_evaluate()
        self.assertEqual(client.calls[-1], (11, 4300))
        self.assertEqual(controller.ev_protection_state, "allowing_charge")

        # A following PV-only window must end grid-assisted charging again.
        controller.hass.states.set("sensor.p_batt", "-700")
        controller.hass.states.set("sensor.p_grid", "0")
        await controller.async_evaluate()
        self.assertEqual(client.calls[-1], (9, 11000))

    async def test_hybrid2_missing_grid_without_ev_waits_for_every_battery_direction(self):
        for battery in ("-1330", "0", "15000"):
            for grid in ("unknown", "unavailable", "nan", "inf"):
                with self.subTest(battery=battery, grid=grid):
                    controller, client = self.make_controller(
                        p_batt=battery, p_grid=grid, strategy="hybrid_2")
                    controller.hass.states.set("sensor.ev_power", "0")
                    await controller.async_evaluate()
                    self.assertEqual(client.calls, [])
                    self.assertEqual(controller.last_command, "waiting_for_p_grid")

    async def test_hybrid2_ev_blocks_neutral_and_discharge_plans(self):
        for battery in ("-300", "0", "300", "15000"):
            controller, client = self.make_controller(
                p_batt=battery, p_grid="9574", strategy="hybrid_2")
            await controller.async_evaluate()
            self.assertEqual(client.calls, [(8, 0)])
            self.assertEqual(controller.ev_protection_state, "blocking_discharge")

    async def test_hybrid2_live_unready_status_overrides_persistent_plan(self):
        controller, client = self.make_controller(
            p_batt="-15000", p_grid="9574", strategy="hybrid_2")
        controller.entry.options[const.CONF_OPTIM_STATUS_ENTITY] = "sensor.status"
        controller.hass.states.set("sensor.status", "Running")
        controller.entry.runtime_data = SimpleNamespace(plan_runtime=SimpleNamespace(
            current_p_batt=lambda: -15000, current_p_grid=lambda: 9574,
            diagnostics={}, has_valid_current_plan=True))
        await controller.async_evaluate()
        self.assertEqual(client.calls, [(8, 0)])
        self.assertEqual(controller.last_command, "ev_self_consumption_hold")

    async def test_hybrid2_uses_valid_persistent_grid_plan(self):
        controller, client = self.make_controller(
            p_batt="-8400", p_grid="unavailable", strategy="hybrid_2")
        controller.entry.runtime_data = SimpleNamespace(plan_runtime=SimpleNamespace(
            current_p_grid=lambda: 2900, diagnostics={}))
        await controller.async_evaluate()
        self.assertEqual(client.calls, [(11, 8400)])

    async def test_hybrid2_ev_stop_still_requires_fresh_native_plan(self):
        controller, client = self.make_controller(
            p_batt="2500", p_grid="-4000", strategy="hybrid_2")
        controller.entry.options[const.CONF_ENABLE_EMHASS_ORCHESTRATOR] = True
        controller.hass.states.set("sensor.ev_power", "0")
        controller._ev_was_active = True
        controller._async_source_changed(SimpleNamespace(data={"entity_id": "sensor.ev_power"}))
        self.assertEqual(client.calls, [])
        self.assertEqual(controller.expected_mode, 8)
        self.assertEqual(controller.last_command, "waiting_for_ev_stop_optimization")
        await asyncio.gather(*controller.hass.tasks)
        self.assertEqual(client.calls, [(8, 0)])

    async def test_hybrid2_does_not_remap_manual_commands(self):
        for mode in (2, 4, 9, 11):
            controller, client = self.make_controller(
                p_batt="-15000", p_grid="9574", strategy="hybrid_2")
            await controller.async_manual_command(mode, 4000, "manual_test")
            await controller.async_evaluate()
            self.assertEqual(client.calls, [(mode, 4000)])
            self.assertFalse(controller.enabled)


if __name__ == "__main__":
    unittest.main()
