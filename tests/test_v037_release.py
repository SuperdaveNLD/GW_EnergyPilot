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
            'gw-energy-pilot-v038.js?v=0.38-control-flow-rebuild1',
            init_source,
        )
        self.assertIn('const VERSION = "0.37"', candidate)
        self.assertIn('const VERSION = "0.37"', runtime)
        self.assertIn("__epV038Installed", runtime)

    def test_candidate_has_executable_model_regression_test(self) -> None:
        test_path = ROOT / "tests" / "test_frontend_v038.mjs"
        self.assertTrue(test_path.is_file())
        source = test_path.read_text(encoding="utf-8")
        self.assertIn("flowMotionMap", source)
        self.assertIn("Batterijbesparing", source)
        self.assertIn("Battery Saver", source)

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
