from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class V037ReleaseTests(unittest.TestCase):
    def test_v037_frontend_wraps_stable_control_stack(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v037.js").read_text(encoding="utf-8")

        self.assertIn(
            'gw-energy-pilot-v0363-control-stability.js?v=0.37-stable-controls1',
            source,
        )
        self.assertIn('const VERSION = "0.37"', source)
        self.assertIn("__epV037ReleaseInstalled", source)
        self.assertIn("previousRender.call(this)", source)
        self.assertIn("updateVersion(this.shadowRoot)", source)

    def test_v037_manifest_and_panel_wiring_match(self) -> None:
        manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")

        self.assertEqual("0.37", manifest["version"])
        self.assertIn(
            'gw-energy-pilot-v037.js?v=0.37-release1',
            init_source,
        )

    def test_v037_release_notes_exist(self) -> None:
        notes = (ROOT / "docs" / "RELEASE_NOTES_V037.md").read_text(encoding="utf-8")

        self.assertIn("# GW EnergyPilot v0.37 Beta", notes)
        self.assertIn("button DOM nodes", notes)
        self.assertIn("No GoodWe register definitions", notes)


if __name__ == "__main__":
    unittest.main()
