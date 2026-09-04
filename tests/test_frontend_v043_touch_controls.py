from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class FrontendV043TouchControlsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "gw-energy-pilot-v043.js").read_text(
            encoding="utf-8"
        )

    def test_v049_active_entrypoint_retains_v043_touch_fix(self) -> None:
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        v048 = (FRONTEND / "gw-energy-pilot-v048.js").read_text(encoding="utf-8")
        v047 = (FRONTEND / "gw-energy-pilot-v047.js").read_text(encoding="utf-8")
        v046 = (FRONTEND / "gw-energy-pilot-v046.js").read_text(encoding="utf-8")
        v045 = (FRONTEND / "gw-energy-pilot-v045.js").read_text(encoding="utf-8")
        v044 = (FRONTEND / "gw-energy-pilot-v044.js").read_text(encoding="utf-8")

        self.assertIn("gw-energy-pilot-v130.js?v=1.3.0-beta.1", init_source)
        self.assertIn('import "./gw-energy-pilot-v047.js?v=1.3.0-beta.1"', v048)
        self.assertIn('import "./gw-energy-pilot-v046.js?v=1.3.0-beta.1"', v047)
        self.assertIn('import "./gw-energy-pilot-v045.js?v=1.3.0-beta.1"', v046)
        self.assertIn('import "./gw-energy-pilot-v044.js?v=1.3.0-beta.1"', v045)
        self.assertIn(
            'import "./gw-energy-pilot-v043.js?v=1.3.0-beta.1"',
            v044,
        )
        self.assertIn('import "./gw-energy-pilot-v042.js?v=1.3.0-beta.1"', self.source)
        self.assertIn('const VERSION = "0.43"', self.source)

    def test_touch_hover_cannot_impersonate_selected_state(self) -> None:
        self.assertIn("@media (hover: none), (pointer: coarse)", self.source)
        for selector in (
            ".ep-layout-button:hover",
            ".ep-optimize-now:hover:not(:disabled)",
            ".ep-battery-action:hover:not(:disabled):not(.active)",
            ".ep-v016-costfun-button:hover:not(:disabled):not(.active)",
            '.ep-v038-profile:hover:not(:disabled):not([aria-pressed="true"])',
            ".ep-v038-profile.ep-v038-hover-stable",
        ):
            with self.subTest(selector=selector):
                self.assertIn(selector, self.source)

        self.assertIn("ensureTouchHoverStyle(root)", self.source)
        self.assertIn('const TOUCH_HOVER_STYLE_ID = "ep-v043-touch-hover"', self.source)

    def test_touch_fix_does_not_intercept_native_interaction(self) -> None:
        for forbidden in (
            "addEventListener",
            "preventDefault",
            "stopPropagation",
            "setPointerCapture",
            "touchstart",
            "touchend",
            "_queueRender",
            "callService",
            "callWS",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.source)


if __name__ == "__main__":
    unittest.main()
