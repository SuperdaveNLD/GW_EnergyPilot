from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "custom_components" / "gw_energypilot" / "frontend"
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"


class FrontendControlStabilityTests(unittest.TestCase):
    def test_v0363_reuses_existing_button_nodes_on_equivalent_render(self) -> None:
        source = (
            FRONTEND / "gw-energy-pilot-v0363-control-stability.js"
        ).read_text(encoding="utf-8")

        self.assertIn("function captureStableButtons", source)
        self.assertIn("function buttonIdentity", source)
        self.assertIn("function sameButtonStructure", source)
        self.assertIn("function restoreStableButtons", source)
        self.assertIn("renderedButton.replaceWith(stableButton)", source)
        self.assertIn("syncAttributes(stableButton, renderedButton)", source)
        self.assertIn("focused.focus({ preventScroll: true })", source)

        capture = source.index("const buttonSnapshot = captureStableButtons(this)")
        render = source.index("previousRender.call(this)")
        restore = source.index("restoreStableButtons(this, buttonSnapshot)")
        self.assertLess(capture, render)
        self.assertLess(render, restore)

    def test_v0363_falls_back_to_new_render_when_controls_change(self) -> None:
        source = (
            FRONTEND / "gw-energy-pilot-v0363-control-stability.js"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "if (!sameButtonStructure(snapshot, renderedButtons)) return;",
            source,
        )
        self.assertIn("snapshot.buttons.length !== buttons.length", source)
        self.assertIn("buttonIdentity(button) === snapshot.identities[index]", source)

    def test_v0363_keeps_v0362_scroll_stability_and_release_wiring(self) -> None:
        source = (
            FRONTEND / "gw-energy-pilot-v0363-control-stability.js"
        ).read_text(encoding="utf-8")
        integration = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        manifest = (INTEGRATION / "manifest.json").read_text(encoding="utf-8")

        self.assertIn(
            'gw-energy-pilot-v0362-scroll-stability.js?v=0.36.3-control-stability1',
            source,
        )
        self.assertIn('const VERSION = "0.36.3"', source)
        self.assertIn('"version": "0.36.3"', manifest)
        self.assertIn(
            'gw-energy-pilot-v0363-control-stability.js?v=0.36.3-release1',
            integration,
        )


if __name__ == "__main__":
    unittest.main()
