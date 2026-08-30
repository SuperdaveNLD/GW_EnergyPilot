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
    ):
        return self.module.resolve_control_decision(
            strategy=strategy,
            p_batt=p_batt,
            p_grid=p_grid,
            battery_deadband=battery_deadband,
            grid_deadband=grid_deadband,
            max_power=10000,
            ev_active=ev_active,
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
        self.assertEqual((fallback.mode, fallback.command), (c.MODE_CHARGE_BATTERY, "ev_charge_fallback"))

    def test_hybrid_field_example_uses_mode1_between_deadbands(self):
        c = self.const
        decision = self.resolve(c.CONTROL_STRATEGY_HYBRID, -231, 0)
        self.assertEqual(
            (decision.mode, decision.power, decision.command),
            (c.MODE_AUTO, 0, "hybrid_grid_zero_auto"),
        )


if __name__ == "__main__":
    unittest.main()
