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

        self.assertIn("gw-energy-pilot-v049.js?v=0.49-consolidated1", init_source)
        self.assertIn(
            'import "./gw-energy-pilot-v048.js?v=0.49-consolidated1";',
            active,
        )
        self.assertIn(
            'import "./gw-energy-pilot-v047.js?v=0.49-consolidated1";',
            self.source,
        )
        self.assertIn('panel._stateByKey?.("control_strategy")?.state', self.source)
        self.assertIn("PanelClass.prototype.__epV048Installed = true", self.source)

    def test_copy_describes_neutral_hold_variable_deadband_and_full_setpoint(self) -> None:
        for expected in (
            "neutral P_batt plan in mode 8",
            "configured deadband",
            "full grid target as setpoint",
            "neutraal P_batt-plan vast in modus 8",
            "ingestelde deadband",
            "volledige netdoel als setpoint",
        ):
            self.assertIn(expected, self.source)


if __name__ == "__main__":
    unittest.main()
