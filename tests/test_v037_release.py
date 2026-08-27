from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class V039ReleaseTests(unittest.TestCase):
    def test_v039_behavior_layer_remains_wired_consistently(self) -> None:
        manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        release = (FRONTEND / "gw-energy-pilot-v039.js").read_text(encoding="utf-8")
        v038 = (FRONTEND / "gw-energy-pilot-v038.js").read_text(encoding="utf-8")
        runtime = (FRONTEND / "gw-energy-pilot-v038-runtime.js").read_text(
            encoding="utf-8"
        )
        i18n = (FRONTEND / "gw-energy-pilot-v038-i18n.js").read_text(
            encoding="utf-8"
        )

        # v0.39 remains a tested behavior layer even when a later release
        # wrapper owns the active panel/version presentation. Later releases
        # may refresh nested cache keys without changing the v0.39 contract.
        version = manifest["version"]
        if version == "0.39":
            self.assertIn("gw-energy-pilot-v039.js?v=0.39-release1", init_source)
            self.assertIn('import "./gw-energy-pilot-v038.js?v=0.39-v0381"', release)
            self.assertIn('gw-energy-pilot-v038-runtime.js?v=0.38-release1', v038)
        elif version == "0.40":
            self.assertIn("gw-energy-pilot-v040.js?v=0.40-mobile-scroll1", init_source)
            v040 = (FRONTEND / "gw-energy-pilot-v040.js").read_text(
                encoding="utf-8"
            )
            self.assertIn(
                'import "./gw-energy-pilot-v039.js?v=0.40-mobile-scroll1"',
                v040,
            )
            self.assertIn(
                'import "./gw-energy-pilot-v038.js?v=0.40-mobile-scroll1"',
                release,
            )
            self.assertIn(
                'gw-energy-pilot-v038-runtime.js?v=0.40-mobile-scroll1',
                v038,
            )
        elif version == "0.41":
            self.assertIn("gw-energy-pilot-v041.js?v=0.41-stable1", init_source)
            v041 = (FRONTEND / "gw-energy-pilot-v041.js").read_text(
                encoding="utf-8"
            )
            self.assertIn(
                'import "./gw-energy-pilot-v039.js?v=0.41-stable1"',
                v041,
            )
            self.assertNotIn('import "./gw-energy-pilot-v040.js', v041)
            self.assertIn(
                'import "./gw-energy-pilot-v038.js?v=0.41-stable1"',
                release,
            )
            self.assertIn(
                'gw-energy-pilot-v038-runtime.js?v=0.41-stable1',
                v038,
            )
        else:
            self.fail(f"Unsupported release version in regression: {version}")

        self.assertIn('const VERSION = "0.39"', release)
        self.assertIn("__epV039Installed", release)
        self.assertIn("energyPilotV039Render", release)
        self.assertIn('gw-energy-pilot-v038-i18n.js?v=0.38-i18n1', v038)
        self.assertIn("localizeV038Controller(this, root)", v038)
        self.assertIn('const VERSION = "0.38"', runtime)
        self.assertIn("__epV038Installed", runtime)
        self.assertIn('windowLabel: "Regelaar"', i18n)
        self.assertIn('manualKicker: "HANDMATIGE EMS-TEST"', i18n)
        self.assertIn('12: ["Batterijontlaadvermogen"', i18n)

    def test_release_has_executable_frontend_regression_tests(self) -> None:
        model_test = ROOT / "tests" / "test_frontend_v038.mjs"
        controls_test = ROOT / "tests" / "test_frontend_v038_controls.mjs"
        i18n_test = ROOT / "tests" / "test_frontend_v038_i18n.mjs"
        self.assertTrue(model_test.is_file())
        self.assertTrue(controls_test.is_file())
        self.assertTrue(i18n_test.is_file())
        source = (
            model_test.read_text(encoding="utf-8")
            + controls_test.read_text(encoding="utf-8")
            + i18n_test.read_text(encoding="utf-8")
        )
        self.assertIn("flowMotionMap", source)
        self.assertIn("resolveHousePower", source)
        self.assertIn("canonicalProfiles", source)
        self.assertIn("Batterijbesparing", source)
        self.assertIn("Battery Saver", source)
        self.assertIn("gw_energypilot/battery_saver/set", source)
        self.assertIn("buttons.every((button) => button.disabled === false)", source)
        self.assertIn("Batterijontlaadvermogen", source)
        self.assertIn("English backend Balanced description", source)

    def test_architecture_note_records_rebuilt_control_contract(self) -> None:
        notes = (ROOT / "docs" / "FRONTEND_CONTROL_REBUILD.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("v0.38 Beta release", notes)
        self.assertIn("visible text is never a control identity", notes)
        self.assertIn("Mobile touch/render contract", notes)
        self.assertIn("350 ms settle interval", notes)
        self.assertIn("PV production: left to right", notes)
        self.assertIn("No GoodWe register", notes)

    def test_dedicated_release_notes_exist(self) -> None:
        notes = ROOT / "docs" / "RELEASE_NOTES_V039.md"
        self.assertTrue(notes.is_file())
        source = notes.read_text(encoding="utf-8")
        self.assertIn("GW EnergyPilot v0.39 Beta", source)
        self.assertIn("hover", source.lower())
        self.assertIn("Dutch", source)
        self.assertTrue((ROOT / "docs" / "RELEASE_NOTES_V038.md").is_file())


if __name__ == "__main__":
    unittest.main()
