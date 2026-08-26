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
        self.assertLess(
            entry.index("setStableHover(rootBefore, hoveredBefore)"),
            entry.index("previousRender.call(this)"),
        )

        # Hover continuity is presentation-only. It must never become another
        # render lock, pointer capture or telemetry deferral mechanism.
        self.assertNotIn("__epV038RenderDeferred", entry)
        self.assertNotIn("_queueRender(", entry)
        self.assertNotIn("setPointerCapture", entry)
        self.assertNotIn("interactionActive", entry)

        # Release wrappers may sit above v0.38. The hover regression only owns
        # reachability of the v0.38 behavior, not the release cache token.
        if "gw-energy-pilot-v039.js?v=" in init_source:
            release = (FRONTEND / "gw-energy-pilot-v039.js").read_text(
                encoding="utf-8"
            )
            self.assertIn('import "./gw-energy-pilot-v038.js?v=', release)
        else:
            self.assertIn("gw-energy-pilot-v038.js?v=", init_source)


if __name__ == "__main__":
    unittest.main()
