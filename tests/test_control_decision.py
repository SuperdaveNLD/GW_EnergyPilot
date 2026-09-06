"""Golden tests for pure EMHASS-to-GoodWe decision mapping."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
CUSTOM_COMPONENTS = ROOT / "custom_components"
PACKAGE_DIR = CUSTOM_COMPONENTS / "gw_energypilot"
PACKAGE_NAME = "custom_components.gw_energypilot"


def _load_module():
    for name in list(sys.modules):
        if name == "custom_components" or name.startswith(PACKAGE_NAME):
            del sys.modules[name]
    custom_components = types.ModuleType("custom_components")
    custom_components.__path__ = [str(CUSTOM_COMPONENTS)]
    sys.modules["custom_components"] = custom_components
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_DIR)]
    package.__package__ = PACKAGE_NAME
    sys.modules[PACKAGE_NAME] = package
    return importlib.import_module(f"{PACKAGE_NAME}.control_decision")


class ControlDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load_module()
        self.const = importlib.import_module(f"{PACKAGE_NAME}.const")

    def resolve(
        self,
        strategy,
        p_batt,
        p_grid=None,
        ev_active=False,
        battery_deadband=100,
        grid_deadband=1000,
        max_power=10000,
        ev_power_w=6000,
        load_power_w=7000,
    ):
        return self.module.resolve_control_decision(
            strategy=strategy,
            p_batt=p_batt,
            p_grid=p_grid,
            battery_deadband=battery_deadband,
            grid_deadband=grid_deadband,
            max_power=max_power,
            ev_active=ev_active,
            ev_power_w=ev_power_w,
            load_power_w=load_power_w,
        )

    def test_battery_boundaries_and_clamp(self):
        c = self.const
        for value in (-100, 0, 100):
            with self.subTest(value=value):
                decision = self.resolve(c.CONTROL_STRATEGY_BATTERY, value)
                self.assertEqual((decision.mode, decision.power), (c.MODE_BATTERY_HOLD, 0))
        charge = self.resolve(c.CONTROL_STRATEGY_BATTERY, -15000)
        discharge = self.resolve(c.CONTROL_STRATEGY_BATTERY, 4200)
        self.assertEqual((charge.mode, charge.power, charge.command), (c.MODE_CHARGE_BATTERY, 10000, "battery_charge"))
        self.assertEqual((discharge.mode, discharge.power), (c.MODE_DISCHARGE_BATTERY, 4200))

    def test_grid_and_hybrid_mapping(self):
        c = self.const
        imported = self.resolve(c.CONTROL_STRATEGY_GRID, -2000, 3500)
        exported = self.resolve(c.CONTROL_STRATEGY_GRID, 2000, -3500)
        self.assertEqual((imported.mode, imported.power), (c.MODE_GRID_IMPORT_TARGET, 3500))
        self.assertEqual((exported.mode, exported.power), (c.MODE_GRID_EXPORT_TARGET, 3500))
        hold = self.resolve(c.CONTROL_STRATEGY_HYBRID, 100, 8000)
        auto = self.resolve(c.CONTROL_STRATEGY_HYBRID, -2000, -1000)
        self.assertEqual((hold.mode, hold.power), (c.MODE_BATTERY_HOLD, 0))
        self.assertEqual((auto.mode, auto.power), (c.MODE_AUTO, 0))

    def test_missing_inputs_are_explicit_waiting_states(self):
        c = self.const
        self.assertEqual(
            self.resolve(c.CONTROL_STRATEGY_BATTERY, None).command,
            "waiting_for_p_batt",
        )
        self.assertEqual(
            self.resolve(c.CONTROL_STRATEGY_GRID, -1000, None).command,
            "waiting_for_p_grid",
        )

    def test_ev_override_only_allows_charge_direction(self):
        c = self.const
        hold = self.resolve(c.CONTROL_STRATEGY_HYBRID, 2000, -2000, True)
        import_charge = self.resolve(c.CONTROL_STRATEGY_HYBRID, -2000, 3500, True)
        fallback = self.resolve(c.CONTROL_STRATEGY_GRID, -2000, -1000, True)
        self.assertEqual((hold.mode, hold.command), (c.MODE_BATTERY_HOLD, "ev_anti_discharge_hold"))
        self.assertEqual((import_charge.mode, import_charge.power), (c.MODE_GRID_IMPORT_TARGET, 3500))
        self.assertEqual((fallback.mode, fallback.command), (c.MODE_AUTO, "ev_charge_allowed"))

    def test_ev_charge_preserves_normal_mode_and_setpoint(self):
        for strategy in ("battery", "grid", "hybrid"):
            for grid in (-20000, -1001, -1000, 0, 1000, 1001, 9574, 20000,
                         None, float("nan"), float("inf")):
                with self.subTest(strategy=strategy, grid=grid):
                    normal = self.resolve(strategy, -15000, grid)
                    active = self.resolve(strategy, -15000, grid, True)
                    self.assertEqual((active.mode, active.power),
                                     (normal.mode, normal.power))
                    if not normal.ready:
                        self.assertEqual(active.command, normal.command)

    def test_ev_hold_boundaries_ignore_grid_availability(self):
        for strategy in ("battery", "grid", "hybrid"):
            for battery in (-100, 0, 100, 15000):
                for grid in (None, -15000, 0, 15000):
                    with self.subTest(strategy=strategy, battery=battery, grid=grid):
                        decision = self.resolve(strategy, battery, grid, True)
                        self.assertEqual((decision.mode, decision.power), (8, 0))

    def test_hybrid_field_example_uses_mode1_between_deadbands(self):
        c = self.const
        decision = self.resolve(c.CONTROL_STRATEGY_HYBRID, -231, 0)
        self.assertEqual(
            (decision.mode, decision.power, decision.command),
            (c.MODE_AUTO, 0, "hybrid_grid_zero_auto"),
        )

    def test_hybrid2_charge_plan_follows_battery_watts_with_maximum_as_cap(self):
        for battery, grid in (
            (-15000, 9574),
            (-8400, 2900),
            (-1330, 1001),
            (-101, 15000),
        ):
            for maximum in (0, 8000, 15000, 20000):
                with self.subTest(battery=battery, grid=grid, maximum=maximum):
                    decision = self.resolve("hybrid_2", battery, grid, max_power=maximum)
                    if maximum == 0:
                        self.assertEqual((decision.mode, decision.power), (8, 0))
                        continue
                    self.assertEqual((decision.mode, decision.power, decision.command),
                                     (11, min(abs(battery), maximum, 15000), "hybrid2_planned_battery_charge"))

    def test_hybrid2_uses_grid_deadband_before_battery_direction(self):
        for battery in (-15000, -101, -100, 0, 100, 101, 15000):
            for grid in (-15000, -1001, -1000, 0, 1000, 1001, 15000):
                with self.subTest(battery=battery, grid=grid):
                    expected = (1, 0) if abs(grid) <= 1000 else (
                        (11, min(abs(battery), 10000)) if battery < -100 else
                        (3, min(battery, 10000)) if battery > 100 else
                        (9 if grid > 0 else 10, min(abs(grid), 10000))
                    )
                    result = self.resolve("hybrid_2", battery, grid)
                    self.assertEqual((result.mode, result.power), expected)

    def test_hybrid2_requires_finite_plan_inputs(self):
        for missing in (None, float("nan"), float("inf"), float("-inf")):
            with self.subTest(missing=missing):
                self.assertFalse(self.resolve("hybrid_2", missing, 9574).ready)
                for battery in (-15000, 0, 15000):
                    decision = self.resolve("hybrid_2", battery, missing)
                    self.assertFalse(decision.ready)
                    self.assertEqual(decision.command, "waiting_for_p_grid")
                self.assertEqual(self.resolve("hybrid_2", -15000, missing, True).mode, 8)

    def test_hybrid2_ev_classifies_self_use_before_battery_direction(self):
        for battery in (-15000, -1330, -101, -100, 0, 100, 15000):
            for grid in (-15000, -1001, -1000, -29, 0, 1000, 1001, 15000):
                with self.subTest(battery=battery, grid=grid):
                    decision = self.resolve("hybrid_2", battery, grid, True)
                    if abs(grid) <= 1000:
                        expected = (5, 1000, "ev_house_self_consumption")
                    elif battery < -100:
                        expected = (11, min(abs(battery), 10000), "ev_battery_charge")
                    elif battery > 100:
                        expected = (8, 0, "ev_anti_discharge_hold")
                    else:
                        expected = (8, 0, "ev_self_consumption_hold")
                    self.assertEqual((decision.mode, decision.power, decision.command), expected)

    def test_hybrid2_pv_charge_field_case_auto_without_ev_excludes_ev_with_ev(self):
        normal = self.resolve("hybrid_2", -1330, -29)
        active = self.resolve("hybrid_2", -1330, -29, True)
        self.assertEqual((normal.mode, normal.power), (1, 0))
        self.assertEqual((active.mode, active.power), (5, 1000))

    def test_hybrid2_ev_missing_or_invalid_measurement_holds(self):
        for power in (None, float("nan"), float("inf"), -1, 0):
            with self.subTest(power=power):
                decision = self.resolve("hybrid_2", 700, 0, True, ev_power_w=power)
                self.assertEqual((decision.mode, decision.power, decision.command),
                                 (8, 0, "ev_self_consumption_hold"))


if __name__ == "__main__":
    unittest.main()
