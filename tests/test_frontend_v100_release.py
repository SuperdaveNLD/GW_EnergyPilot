from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"
CACHE_KEY = "1.0.0-stable1"


class FrontendV100ReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.release = (FRONTEND / "gw-energy-pilot-v100.js").read_text(
            encoding="utf-8"
        )

    def test_historical_presentation_remains_stable_v100(self) -> None:
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        self.assertNotIn(f"gw-energy-pilot-v100.js?v={CACHE_KEY}", init_source)
        self.assertIn(
            f'import "./gw-energy-pilot-v051.js?v={CACHE_KEY}"', self.release
        )
        self.assertIn('const VERSION = "1.0.0"', self.release)
        self.assertIn("v${VERSION} STABLE", self.release)
        self.assertIn("PanelClass.prototype.__epV100Installed = true", self.release)

    def test_stable_wrapper_remains_presentation_only(self) -> None:
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

    def test_stable_tag_notes_exist(self) -> None:
        notes = ROOT / "docs" / "releases" / "v1.0.0.md"
        self.assertTrue(notes.is_file())
        content = notes.read_text(encoding="utf-8")
        self.assertIn("# GW EnergyPilot v1.0.0", content)
        self.assertIn("**Channel:** Stable", content)


if __name__ == "__main__":
    unittest.main()
