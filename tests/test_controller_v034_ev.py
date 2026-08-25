"""v0.34 EV anti-discharge strategy regression tests."""

from __future__ import annotations

import importlib
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

    async def test_ev_grid_strategy_charge_uses_mode9(self):
        controller, client = self.make_controller(
            p_batt="-2500",
            p_grid="4000",
            strategy=const.CONTROL_STRATEGY_GRID,
        )

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_GRID_IMPORT_TARGET, 4000)])
        self.assertEqual(controller.last_command, "ev_grid_import_charge")

    async def test_ev_hybrid_charge_without_import_falls_back_to_mode11(self):
        controller, client = self.make_controller(
            p_batt="-2500",
            p_grid="0",
            strategy=const.CONTROL_STRATEGY_HYBRID,
        )

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_CHARGE_BATTERY, 2500)])
        self.assertEqual(controller.last_command, "ev_charge_fallback")


if __name__ == "__main__":
    unittest.main()
