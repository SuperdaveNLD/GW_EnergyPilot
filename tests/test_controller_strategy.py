"""Strategy-switch regression tests for GW EnergyPilot automatic control."""

from __future__ import annotations

import unittest

from test_controller import ControllerSafetyTests, const


class ControllerStrategyTests(unittest.IsolatedAsyncioTestCase):
    """Verify the GoodWe smart-meter switch changes only the actuator mapping."""

    def make_controller(self, **kwargs):
        helper = ControllerSafetyTests(methodName="test_positive_p_grid_maps_to_mode9_import_target")
        return helper.make_controller(**kwargs)

    async def test_missing_setting_defaults_to_direct_mode11_charge(self):
        controller, _, client, _ = self.make_controller(
            p_batt="-4200",
            p_grid="3500",
        )
        controller.entry.data = {}
        controller.enabled = True

        await controller.async_evaluate()

        self.assertFalse(controller.use_goodwe_smart_meter)
        self.assertEqual(client.calls, [(const.MODE_CHARGE_BATTERY, 4200)])
        self.assertEqual(controller.last_command, "battery_charge")

    async def test_missing_setting_defaults_to_direct_mode12_discharge(self):
        controller, _, client, _ = self.make_controller(
            p_batt="962",
            p_grid="0",
        )
        controller.entry.data = {}
        controller.enabled = True

        await controller.async_evaluate()

        self.assertFalse(controller.use_goodwe_smart_meter)
        self.assertEqual(client.calls, [(const.MODE_DISCHARGE_BATTERY, 962)])
        self.assertEqual(controller.last_command, "battery_discharge")

    async def test_smart_meter_explicitly_enabled_uses_mode9(self):
        controller, _, client, _ = self.make_controller(
            p_batt="-4200",
            p_grid="3500",
        )
        controller.entry.data = {const.CONF_USE_GOODWE_SMART_METER: True}
        controller.enabled = True

        await controller.async_evaluate()

        self.assertTrue(controller.use_goodwe_smart_meter)
        self.assertEqual(client.calls, [(const.MODE_GRID_IMPORT_TARGET, 3500)])

    async def test_smart_meter_disabled_uses_mode11_for_charge(self):
        controller, _, client, _ = self.make_controller(
            p_batt="-4200",
            p_grid="3500",
        )
        controller.entry.data = {const.CONF_USE_GOODWE_SMART_METER: False}
        controller.enabled = True

        await controller.async_evaluate()

        self.assertFalse(controller.use_goodwe_smart_meter)
        self.assertEqual(client.calls, [(const.MODE_CHARGE_BATTERY, 4200)])
        self.assertEqual(controller.last_command, "battery_charge")

    async def test_smart_meter_disabled_uses_mode12_for_discharge(self):
        controller, _, client, _ = self.make_controller(
            p_batt="5100",
            p_grid="-4500",
        )
        controller.entry.data = {const.CONF_USE_GOODWE_SMART_METER: False}
        controller.enabled = True

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_DISCHARGE_BATTERY, 5100)])
        self.assertEqual(controller.last_command, "battery_discharge")

    async def test_smart_meter_disabled_uses_mode8_in_battery_deadband(self):
        controller, _, client, _ = self.make_controller(
            p_batt="200",
            p_grid="5000",
            options={const.CONF_DEADBAND: 300},
        )
        controller.entry.data = {const.CONF_USE_GOODWE_SMART_METER: False}
        controller.enabled = True

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_BATTERY_HOLD, 0)])
        self.assertEqual(controller.last_command, "battery_hold")

    async def test_direct_battery_strategy_does_not_require_p_grid(self):
        controller, _, client, _ = self.make_controller(
            p_batt="-1800",
            p_grid="unavailable",
        )
        controller.entry.data = {const.CONF_USE_GOODWE_SMART_METER: False}
        controller.enabled = True

        await controller.async_evaluate()

        self.assertEqual(client.calls, [(const.MODE_CHARGE_BATTERY, 1800)])
        self.assertEqual(controller.last_command, "battery_charge")


if __name__ == "__main__":
    unittest.main()
