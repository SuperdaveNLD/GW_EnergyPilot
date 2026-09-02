from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"
CACHE_KEY = "1.2.0-beta.4-touch-methods1"


class FrontendV110ReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.release = (FRONTEND / "gw-energy-pilot-v110.js").read_text(
            encoding="utf-8"
        )

    def test_manifest_panel_and_presentation_are_v120_beta(self) -> None:
        manifest = json.loads(
            (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
        )
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        self.assertEqual(manifest["version"], "1.2.0-beta.4")
        self.assertIn(f"gw-energy-pilot-v110.js?v={CACHE_KEY}", init_source)
        self.assertIn(
            f'import "./gw-energy-pilot-v101.js?v={CACHE_KEY}"', self.release
        )
        self.assertIn('const VERSION = "1.2.0-beta.4"', self.release)
        self.assertIn("v${VERSION} BETA", self.release)
        self.assertIn("PanelClass.prototype.__epV110Installed = true", self.release)

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

    def test_beta_release_notes_exist(self) -> None:
        notes = ROOT / "docs" / "releases" / "v1.2.0-beta.4.md"
        self.assertTrue(notes.is_file())


if __name__ == "__main__":
    unittest.main()
