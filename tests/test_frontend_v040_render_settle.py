from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class FrontendV040RenderSettleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "gw-energy-pilot-v040.js").read_text(encoding="utf-8")

    def test_v040_remains_a_valid_historical_entrypoint_under_v048(self) -> None:
        manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
        init = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        v048 = (FRONTEND / "gw-energy-pilot-v048.js").read_text(encoding="utf-8")
        v047 = (FRONTEND / "gw-energy-pilot-v047.js").read_text(encoding="utf-8")
        v046 = (FRONTEND / "gw-energy-pilot-v046.js").read_text(encoding="utf-8")
        v045 = (FRONTEND / "gw-energy-pilot-v045.js").read_text(encoding="utf-8")
        release = (FRONTEND / "gw-energy-pilot-v044.js").read_text(encoding="utf-8")
        v043 = (FRONTEND / "gw-energy-pilot-v043.js").read_text(encoding="utf-8")
        v042 = (FRONTEND / "gw-energy-pilot-v042.js").read_text(encoding="utf-8")
        settings = (FRONTEND / "gw-energy-pilot-v041-emhass-settings.js").read_text(encoding="utf-8")
        v041 = (FRONTEND / "gw-energy-pilot-v041.js").read_text(encoding="utf-8")
        self.assertEqual(manifest["version"], "0.48")
        self.assertIn("gw-energy-pilot-v048.js?v=0.48-hybrid-control1", init)
        self.assertIn('import "./gw-energy-pilot-v047.js?v=0.48-hybrid-control1"', v048)
        self.assertIn('import "./gw-energy-pilot-v046.js?v=0.47-custom-battery1"', v047)
        self.assertIn('import "./gw-energy-pilot-v045.js?v=0.47-custom-battery1"', v046)
        self.assertIn('import "./gw-energy-pilot-v044.js?v=0.47-custom-battery1"', v045)
        self.assertIn(
            'import "./gw-energy-pilot-v043.js?v=0.47-custom-battery1"',
            release,
        )
        self.assertIn('import "./gw-energy-pilot-v042.js?v=0.47-custom-battery1"', v043)
        self.assertIn('import "./gw-energy-pilot-v041-emhass-settings.js?v=0.47-custom-battery1"', v042)
        self.assertIn('import "./gw-energy-pilot-v041.js?v=0.47-custom-battery1"', settings)
        self.assertIn('import "./gw-energy-pilot-v039.js?v=0.47-custom-battery1"', v041)
        self.assertNotIn('import "./gw-energy-pilot-v040.js', v041)
        self.assertIn('import "./gw-energy-pilot-v039.js?v=0.40-mobile-scroll1"', self.source)
        self.assertIn('const VERSION = "0.40"', self.source)

    def test_v040_suppresses_only_transition_restart_during_render_settle(self) -> None:
        self.assertIn("const INTERACTIVE_SELECTOR", self.source)
        self.assertIn("button, input, select, textarea", self.source)
        self.assertIn('[role="button"], [tabindex]', self.source)
        self.assertIn("transition: none !important", self.source)
        self.assertIn(":is(${INTERACTIVE_SELECTOR}) *", self.source)
        self.assertIn(":is(${INTERACTIVE_SELECTOR})::before", self.source)
        self.assertIn(":is(${INTERACTIVE_SELECTOR})::after", self.source)
        self.assertNotIn("animation: none", self.source)
        self.assertNotIn("animation-duration", self.source)

    def test_v040_settle_style_survives_shadowroot_innerhtml_rebuild(self) -> None:
        self.assertIn('"adoptedStyleSheets" in root', self.source)
        self.assertIn("new globalThis.CSSStyleSheet()", self.source)
        self.assertIn("sheet.replaceSync(SETTLE_CSS)", self.source)
        self.assertIn("ensureFallbackSettleStyle", self.source)
        self.assertIn('const SETTLE_STYLE_ID = "ep-v040-render-settle-style"', self.source)

    def test_v040_keeps_settle_until_one_paint_and_guards_rapid_renders(self) -> None:
        self.assertIn("__epV040RenderGeneration", self.source)
        self.assertIn("panel.__epV040RenderGeneration !== generation", self.source)
        self.assertGreaterEqual(self.source.count("globalThis.requestAnimationFrame"), 3)
        self.assertIn("globalThis.setTimeout?.(finish, 34)", self.source)
        self.assertLess(self.source.index("this.classList.add(SETTLE_CLASS)"), self.source.index("previousRender.apply(this, args)"))
        self.assertGreater(self.source.index("scheduleSettleEnd(this, generation)"), self.source.index("previousRender.apply(this, args)"))

    def test_v040_does_not_restore_removed_hover_locks_or_stale_node_reuse(self) -> None:
        for forbidden in ("setPointerCapture", "__epV035HoverActive", "captureStableButtons", "renderedButton.replaceWith"):
            self.assertNotIn(forbidden, self.source)

    def test_v040_scope_covers_known_recreated_menu_and_window_controls(self) -> None:
        menu = (FRONTEND / "gw-energy-pilot-v008.js").read_text(encoding="utf-8")
        windows = (FRONTEND / "gw-energy-pilot-v031-window-controls.js").read_text(encoding="utf-8")
        base = (FRONTEND / "gw-energy-pilot.js").read_text(encoding="utf-8")
        self.assertIn(".ep-layout-button", menu)
        self.assertIn(".ep-menu-row input", menu)
        self.assertIn("transition: border-color .18s ease", menu)
        self.assertIn(".ep-v031-window-dot", windows)
        self.assertIn("transition:transform .12s ease", windows)
        self.assertIn(".switch-knob", base)
        self.assertIn("transition: transform .18s ease", base)


if __name__ == "__main__":
    unittest.main()
