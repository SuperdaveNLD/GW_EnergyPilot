from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class FrontendHoverStabilityTests(unittest.TestCase):
    def test_v038_preserves_only_visual_mouse_hover_across_full_render(self) -> None:
        entry = (FRONTEND / "gw-energy-pilot-v038.js").read_text(encoding="utf-8")
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")

        self.assertIn('const HOVER_CLASS = "ep-v038-hover-stable"', entry)
        self.assertIn("function setStableHover", entry)
        self.assertIn("function installHoverTracking", entry)
        self.assertIn('root.addEventListener(\n    "pointermove"', entry)
        self.assertIn('panel.addEventListener(\n    "pointerleave"', entry)
        self.assertIn("setStableHover(rootBefore, hoveredBefore)", entry)
        self.assertIn(".ep-v038-profile.${HOVER_CLASS}:not(:disabled)", entry)
        self.assertLess(entry.index("setStableHover(rootBefore, hoveredBefore)"), entry.index("previousRender.call(this)"))
        self.assertNotIn("__epV038RenderDeferred", entry)
        self.assertNotIn("_queueRender(", entry)
        self.assertNotIn("setPointerCapture", entry)
        self.assertNotIn("interactionActive", entry)

        if "gw-energy-pilot-v042.js?v=" in init_source:
            release = (FRONTEND / "gw-energy-pilot-v042.js").read_text(encoding="utf-8")
            settings = (FRONTEND / "gw-energy-pilot-v041-emhass-settings.js").read_text(encoding="utf-8")
            v041 = (FRONTEND / "gw-energy-pilot-v041.js").read_text(encoding="utf-8")
            v039 = (FRONTEND / "gw-energy-pilot-v039.js").read_text(encoding="utf-8")
            self.assertIn('import "./gw-energy-pilot-v041-emhass-settings.js?v=', release)
            self.assertIn('import "./gw-energy-pilot-v041.js?v=', settings)
            self.assertIn('import "./gw-energy-pilot-v039.js?v=', v041)
            self.assertIn('import "./gw-energy-pilot-v038.js?v=', v039)
        elif "gw-energy-pilot-v041-emhass-settings.js?v=" in init_source:
            settings = (FRONTEND / "gw-energy-pilot-v041-emhass-settings.js").read_text(encoding="utf-8")
            self.assertIn('import "./gw-energy-pilot-v041.js?v=', settings)
        else:
            self.assertTrue(any(name in init_source for name in ("gw-energy-pilot-v041.js?v=", "gw-energy-pilot-v040.js?v=", "gw-energy-pilot-v039.js?v=", "gw-energy-pilot-v038.js?v=")))


if __name__ == "__main__":
    unittest.main()
