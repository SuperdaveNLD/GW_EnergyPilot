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
        for strategy in (const.CONTROL_STRATEGY_GRID, const.CONTROL_STRATEGY_HYBRID):
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

    async def test_hybrid2_charge_plan_uses_mode2_despite_planned_export(self):
        controller, client = self.make_controller(
            p_batt="-2500", p_grid="-4000", strategy="hybrid_2")
        await controller.async_evaluate()
        self.assertEqual(client.calls, [(const.MODE_CHARGE_PV, 15000)])
        self.assertEqual(controller.ev_protection_state, "allowing_charge")

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


    async def test_hybrid2_mode2_uses_configured_maximum_with_and_without_ev(self):
        for ev in ("0", "11000"):
            for grid in ("2900", "-29", "-4000", "unavailable"):
                with self.subTest(ev=ev, grid=grid):
                    controller, client = self.make_controller(
                        p_batt="-1330", p_grid=grid, strategy="hybrid_2")
                    controller.entry.options[const.CONF_MAX_POWER] = 12000
                    controller.hass.states.set("sensor.ev_power", ev)
                    await controller.async_evaluate()
                    self.assertEqual(client.calls, [(2, 12000)])
                    self.assertEqual(controller.control_strategy, "hybrid_2")

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
        self.assertEqual(client.calls, [])
        self.assertEqual(controller.last_command, "waiting_for_optimization")

    async def test_hybrid2_uses_valid_persistent_grid_plan(self):
        controller, client = self.make_controller(
            p_batt="-8400", p_grid="unavailable", strategy="hybrid_2")
        controller.entry.runtime_data = SimpleNamespace(plan_runtime=SimpleNamespace(
            current_p_grid=lambda: 2900, diagnostics={}))
        await controller.async_evaluate()
        self.assertEqual(client.calls, [(2, const.DEFAULT_MAX_POWER)])

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
