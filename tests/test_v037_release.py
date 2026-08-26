from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class V038FrontendCandidateTests(unittest.TestCase):
    def test_candidate_is_wired_without_republishing_v037(self) -> None:
        manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        candidate = (FRONTEND / "gw-energy-pilot-v038.js").read_text(encoding="utf-8")
        runtime = (FRONTEND / "gw-energy-pilot-v038-runtime.js").read_text(
            encoding="utf-8"
        )

        self.assertEqual("0.37", manifest["version"])
        self.assertIn(
            'gw-energy-pilot-v038.js?v=0.38-control-flow-rebuild3',
            init_source,
        )
        self.assertIn(
            'gw-energy-pilot-v038-runtime.js?v=0.38-runtime3',
            candidate,
        )
        self.assertIn('const VERSION = "0.37"', candidate)
        self.assertIn('const VERSION = "0.37"', runtime)
        self.assertIn("__epV038Installed", runtime)

    def test_candidate_has_executable_model_regression_tests(self) -> None:
        model_test = ROOT / "tests" / "test_frontend_v038.mjs"
        controls_test = ROOT / "tests" / "test_frontend_v038_controls.mjs"
        self.assertTrue(model_test.is_file())
        self.assertTrue(controls_test.is_file())
        source = model_test.read_text(encoding="utf-8") + controls_test.read_text(
            encoding="utf-8"
        )
        self.assertIn("flowMotionMap", source)
        self.assertIn("resolveHousePower", source)
        self.assertIn("canonicalProfiles", source)
        self.assertIn("Batterijbesparing", source)
        self.assertIn("Battery Saver", source)
        self.assertIn("gw_energypilot/battery_saver/set", source)

    def test_architecture_note_records_field_test_boundary(self) -> None:
        notes = (ROOT / "docs" / "FRONTEND_CONTROL_REBUILD.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("v0.38 frontend field-test candidate", notes)
        self.assertIn("visible text is never a control identity", notes)
        self.assertIn("PV production: left to right", notes)
        self.assertIn("No GoodWe register", notes)


if __name__ == "__main__":
    unittest.main()
