from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"
CACHE_KEY = "1.2.0-beta.2-soc-end-sems2-beta-tests1"


class FrontendV048ReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "gw-energy-pilot-v048.js").read_text(
            encoding="utf-8"
        )

    def test_v048_remains_below_the_active_v051_wrapper(self) -> None:
        manifest = json.loads(
            (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
        )
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")

        active = (FRONTEND / "gw-energy-pilot-v051.js").read_text(encoding="utf-8")
        v050 = (FRONTEND / "gw-energy-pilot-v050.js").read_text(encoding="utf-8")
        v049 = (FRONTEND / "gw-energy-pilot-v049.js").read_text(encoding="utf-8")

        self.assertEqual(manifest["version"], "1.2.0-beta.2")
        self.assertIn("gw-energy-pilot-v110.js?v=1.2.0-beta.2-soc-end-sems2-beta-tests1", init_source)
        self.assertIn(
            f'import "./gw-energy-pilot-v050.js?v={CACHE_KEY}"',
            active,
        )
        self.assertIn(
            f'import "./gw-energy-pilot-v049.js?v={CACHE_KEY}"',
            v050,
        )
        self.assertIn(
            f'import "./gw-energy-pilot-v048.js?v={CACHE_KEY}"',
            v049,
        )
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

    def test_hybrid_note_only_rebuilds_for_context_changes(self) -> None:
        self.assertIn("const presentationKey = `${language(panel)}:${strategy}`", self.source)
        self.assertIn('note.dataset.epReleasePresentationOwner = "v048-hybrid"', self.source)
        self.assertIn("note.dataset.epV048PresentationKey !== presentationKey", self.source)
        self.assertIn("note.dataset.epV048PresentationKey = presentationKey", self.source)
        for predecessor in ("v024", "v026", "v028", "v038-i18n"):
            source = (FRONTEND / f"gw-energy-pilot-{predecessor}.js").read_text(encoding="utf-8")
            with self.subTest(predecessor=predecessor):
                self.assertIn("epReleasePresentationOwner", source)

    def test_release_documentation_exists(self) -> None:
        self.assertTrue((ROOT / "docs" / "RELEASE_NOTES_V048.md").is_file())
        self.assertTrue((ROOT / "docs" / "CHANGELOG_V048.md").is_file())


if __name__ == "__main__":
    unittest.main()
