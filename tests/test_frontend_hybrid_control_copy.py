"""Protect the active Hybrid Automatic Control operator copy and cache path."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class HybridControlFrontendCopyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "gw-energy-pilot-v048.js").read_text(
            encoding="utf-8"
        )

    def test_active_frontend_loads_fresh_hybrid_control_module(self) -> None:
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        active = (FRONTEND / "gw-energy-pilot-v049.js").read_text(encoding="utf-8")

        self.assertIn("gw-energy-pilot-v101.js?v=1.0.1-beta4", init_source)
        self.assertIn(
            'import "./gw-energy-pilot-v048.js?v=1.0.1-beta4";',
            active,
        )
        self.assertIn(
            'import "./gw-energy-pilot-v047.js?v=1.0.1-beta4";',
            self.source,
        )
        self.assertIn('panel._stateByKey?.("control_strategy")?.state', self.source)
        self.assertIn("PanelClass.prototype.__epV048Installed = true", self.source)

    def test_copy_describes_separate_deadbands_and_full_setpoint(self) -> None:
        for expected in (
            "Battery Hold deadband on P_batt",
            "separate GoodWe Auto deadband",
            "full grid target as setpoint",
            "Battery Hold-deadband op P_batt",
            "aparte GoodWe Auto-deadband",
            "volledige netdoel als setpoint",
        ):
            self.assertIn(expected, self.source)


if __name__ == "__main__":
    unittest.main()
