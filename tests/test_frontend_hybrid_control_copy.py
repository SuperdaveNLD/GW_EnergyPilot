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

        self.assertIn("gw-energy-pilot-v131.js?v=1.3.0-beta.11", init_source)
        self.assertIn(
            'import "./gw-energy-pilot-v048.js?v=1.3.0-beta.11";',
            active,
        )
        self.assertIn(
            'import "./gw-energy-pilot-v047.js?v=1.3.0-beta.11";',
            self.source,
        )
        self.assertIn('panel._stateByKey?.("control_strategy")?.state', self.source)
        self.assertIn("PanelClass.prototype.__epV048Installed = true", self.source)

    def test_copy_describes_two_deadbands_and_full_setpoint(self) -> None:
        for expected in (
            "Battery Hold deadband on P_batt",
            "separate GoodWe Auto deadband",
            "full grid target as setpoint",
            "Battery Hold-deadband op P_batt",
            "aparte GoodWe Auto-deadband",
            "volledige netdoel als setpoint",
        ):
            self.assertIn(expected, self.source)

    def test_hybrid2_mode2_target_is_presented_as_grid_assistance(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v041.js").read_text(encoding="utf-8")
        self.assertIn('gridAssistanceTarget: "Grid assistance allowance"', source)
        self.assertIn('gridAssistanceTarget: "Netassistentie-limiet"', source)
        self.assertIn('command === "ev_battery_charge" && ["hybrid_2", "hybrid_3"].includes(strategy)', source)
        self.assertIn('command === "hybrid3_planned_battery_charge"', source)
        self.assertIn('const targetText = controllerTargetLabel(panel, t)', source)

    def test_hybrid3_scenario_copy_and_error_evidence(self) -> None:
        surface = (FRONTEND / "ep-control-surface.js").read_text(encoding="utf-8")
        self.assertIn("Hybrid 3.0 excl. EV", surface)
        self.assertIn("Tibber Grid Rewards", surface)
        self.assertIn("zes scenario’s", surface)
        self.assertIn("two fresh pairs", surface)
        self.assertIn('class="ep-hybrid3-scenarios"', surface)
        history = (FRONTEND / "gw-energy-pilot-v051-history.js").read_text(encoding="utf-8")
        start = history.index("function statusModel")
        end = history.index("function sourceModel", start)
        status = history[start:end]
        self.assertLess(status.index('verification_status === "mismatch"'),
                        status.index('command.startsWith("ev_")'))
        self.assertIn("guard.hold_reason", history)

    def test_hybrid2_mode2_copy_explains_pv_addition_without_changing_other_modes(self) -> None:
        for name in ("ep-control-surface.js", "gw-energy-pilot-v026.js", "gw-energy-pilot-v024.js"):
            with self.subTest(module=name):
                source = (FRONTEND / name).read_text(encoding="utf-8")
                self.assertIn("modus 2", source)
                self.assertIn("netassistentie met PV-voorrang", source)
                self.assertIn("PV kan extra bijdragen aan acculaden", source)
                self.assertNotIn("modus 11 de geplande laadwatts", source)
                self.assertNotIn("mode 11 follows planned charging watts", source)
                if name != "gw-energy-pilot-v024.js":
                    self.assertIn("mode 2", source)
                    self.assertIn("grid assistance with PV priority", source)
                    self.assertIn("PV can add to battery charging", source)


if __name__ == "__main__":
    unittest.main()
