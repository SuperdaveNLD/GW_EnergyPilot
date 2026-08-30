from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"
CACHE_KEY = "1.0.1-beta2"


class FrontendV101ReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.release = (FRONTEND / "gw-energy-pilot-v101.js").read_text(
            encoding="utf-8"
        )

    def test_manifest_panel_and_presentation_are_beta_v101(self) -> None:
        manifest = json.loads(
            (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
        )
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        self.assertEqual(manifest["version"], "1.0.1-beta.2")
        self.assertIn(f"gw-energy-pilot-v101.js?v={CACHE_KEY}", init_source)
        self.assertIn(
            f'import "./gw-energy-pilot-v051.js?v={CACHE_KEY}"', self.release
        )
        self.assertIn('const VERSION = "1.0.1-beta.2"', self.release)
        self.assertIn("v${VERSION} BETA", self.release)
        self.assertIn("PanelClass.prototype.__epV101Installed = true", self.release)

    def test_beta_wrapper_remains_presentation_only(self) -> None:
        for forbidden in (
            "addEventListener",
            "callService",
            "callWS",
            "_queueRender",
            "scrollTop",
            "scrollLeft",
            "setPointerCapture",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.release)

    def test_beta_tag_notes_exist(self) -> None:
        notes = ROOT / "docs" / "releases" / "v1.0.1-beta.2.md"
        self.assertTrue(notes.is_file())
        content = notes.read_text(encoding="utf-8")
        self.assertIn("# GW EnergyPilot v1.0.1-beta.2", content)
        self.assertIn("**Channel:** Beta prerelease", content)

    def test_live_copy_updates_are_idempotent(self) -> None:
        v041 = (FRONTEND / "gw-energy-pilot-v041.js").read_text(encoding="utf-8")
        v044 = (FRONTEND / "gw-energy-pilot-v044.js").read_text(encoding="utf-8")
        self.assertIn(
            "if (button.textContent !== nextText) button.textContent = nextText;",
            v041,
        )
        self.assertIn(
            "if (button.textContent !== nextText) button.textContent = nextText;",
            v044,
        )

    def test_two_deadband_control_and_settings_visual_are_wired(self) -> None:
        constants = (INTEGRATION / "const.py").read_text(encoding="utf-8")
        decision = (INTEGRATION / "control_decision.py").read_text(
            encoding="utf-8"
        )
        settings = (FRONTEND / "gw-energy-pilot-settings-v016.js").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'CONF_GOODWE_AUTO_DEADBAND = "goodwe_auto_deadband"', constants
        )
        self.assertIn("DEFAULT_DEADBAND = 100", constants)
        self.assertIn("DEFAULT_GOODWE_AUTO_DEADBAND = 1000", constants)
        self.assertIn("abs(battery) <= battery_boundary", decision)
        self.assertIn("abs(grid) <= grid_boundary", decision)
        self.assertIn('class="ep-v016-deadband-window"', settings)
        self.assertIn('class="ep-v016-deadband-zero">0 W', settings)
        self.assertIn("negatief P_batt", settings)
        self.assertIn("positief P_batt", settings)


if __name__ == "__main__":
    unittest.main()
