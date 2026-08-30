from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"
CACHE_KEY = "0.48-hybrid-control1"


class FrontendV048ReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "gw-energy-pilot-v048.js").read_text(
            encoding="utf-8"
        )

    def test_manifest_panel_and_presentation_are_v048(self) -> None:
        manifest = json.loads(
            (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
        )
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")

        self.assertEqual(manifest["version"], "0.48")
        self.assertIn(f"gw-energy-pilot-v048.js?v={CACHE_KEY}", init_source)
        self.assertIn(
            f'import "./gw-energy-pilot-v047.js?v={CACHE_KEY}"',
            self.source,
        )
        self.assertIn('const VERSION = "0.48"', self.source)
        self.assertIn("PanelClass.prototype.__epV048Installed = true", self.source)

    def test_release_wrapper_is_presentation_only(self) -> None:
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
                self.assertNotIn(forbidden, self.source)

    def test_release_documentation_exists(self) -> None:
        self.assertTrue((ROOT / "docs" / "RELEASE_NOTES_V048.md").is_file())
        self.assertTrue((ROOT / "docs" / "CHANGELOG_V048.md").is_file())


if __name__ == "__main__":
    unittest.main()
