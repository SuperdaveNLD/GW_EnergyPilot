from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class FrontendV045SocChartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "gw-energy-pilot-v045.js").read_text(
            encoding="utf-8"
        )

    def test_v045_release_wrapper_remains_below_v049(self) -> None:
        manifest = json.loads(
            (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
        )
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")

        v048 = (FRONTEND / "gw-energy-pilot-v048.js").read_text(encoding="utf-8")
        active = (FRONTEND / "gw-energy-pilot-v047.js").read_text(encoding="utf-8")
        v046 = (FRONTEND / "gw-energy-pilot-v046.js").read_text(encoding="utf-8")
        self.assertEqual(manifest["version"], "1.2.0-beta.5")
        self.assertIn("gw-energy-pilot-v110.js?v=1.2.0-beta.5-touch-fallback1", init_source)
        self.assertIn('import "./gw-energy-pilot-v047.js?v=1.2.0-beta.5-touch-fallback1"', v048)
        self.assertIn(
            'import "./gw-energy-pilot-v046.js?v=1.2.0-beta.5-touch-fallback1"',
            active,
        )
        self.assertIn(
            'import "./gw-energy-pilot-v045.js?v=1.2.0-beta.5-touch-fallback1"',
            v046,
        )
        self.assertIn(
            'import "./gw-energy-pilot-v044.js?v=1.2.0-beta.5-touch-fallback1"',
            self.source,
        )
        self.assertIn('const VERSION = "0.45"', self.source)
        self.assertIn("PanelClass.prototype.__epV045Installed = true", self.source)

    def test_v045_wrapper_owns_release_presentation_only(self) -> None:
        self.assertIn("function patchReleaseVersion(panel)", self.source)
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

    def test_v045_release_documents_exist(self) -> None:
        self.assertTrue((ROOT / "docs" / "RELEASE_NOTES_V045.md").is_file())
        self.assertTrue((ROOT / "docs" / "CHANGELOG_V045.md").is_file())


if __name__ == "__main__":
    unittest.main()
