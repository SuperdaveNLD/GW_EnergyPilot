from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"
BROWSER = ROOT / "tests" / "browser"


class FrontendV041StableDomTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "gw-energy-pilot-v041.js").read_text(
            encoding="utf-8"
        )
        self.runtime = (FRONTEND / "gw-energy-pilot-v038-runtime.js").read_text(
            encoding="utf-8"
        )
        self.plan_data = (
            FRONTEND / "gw-energy-pilot-v027-battery-plan-data.js"
        ).read_text(encoding="utf-8")
        self.plan_core = (
            FRONTEND / "gw-energy-pilot-v027-battery-plan-core.js"
        ).read_text(encoding="utf-8")

    def test_v041_bypasses_the_v040_render_settle_layer(self) -> None:
        self.assertIn(
            'import "./gw-energy-pilot-v039.js?v=0.41-stable1"', self.source
        )
        self.assertNotIn('import "./gw-energy-pilot-v040.js', self.source)
        self.assertIn('const VERSION = "0.41"', self.source)

    def test_ordinary_hass_updates_patch_existing_dom(self) -> None:
        self.assertIn("function patchLiveDom(panel)", self.source)
        self.assertIn("function scheduleLivePatch(panel)", self.source)
        self.assertIn("this._hass = value", self.source)
        self.assertIn("scheduleLivePatch(this)", self.source)
        self.assertIn("context !== this.__epV041ContextSignature", self.source)
        self.assertIn("structure !== this.__epV041StructureSignature", self.source)
        self.assertIn("this._queueRender();", self.source)
        self.assertIn('main.dataset.epV041StableDom = "1"', self.source)
        self.assertNotIn("shadowRoot.innerHTML", self.source)
        self.assertNotIn("scrollTop =", self.source)
        self.assertNotIn("scrollLeft =", self.source)

    def test_v038_legacy_guards_are_disabled_only_for_v041(self) -> None:
        self.assertIn("function stableRuntimeActive(panel)", self.runtime)
        self.assertIn("!stableRuntime && interactionActive(this)", self.runtime)
        self.assertIn("!stableRuntime && shouldPreserveScroll(this)", self.runtime)
        self.assertIn("if (!stableRuntime) installInteractionGuard", self.runtime)
        self.assertIn("if (!stableRuntime) stabilizeScrollAfterRender", self.runtime)
        self.assertIn("this.__epV041StableRuntime = true", self.source)
        self.assertNotIn("setPointerCapture", self.source)
        self.assertNotIn("preventDefault", self.source)

    def test_plan_refresh_is_scoped_to_the_graph_card(self) -> None:
        self.assertIn("function requestPanelRefresh(panel)", self.plan_data)
        self.assertIn("panel.__epV041RefreshBatteryPlan()", self.plan_data)
        self.assertIn(
            "export function refreshBatteryPlanCard(panel)", self.plan_core
        )
        self.assertIn("refreshBatteryPlanCard(this)", self.plan_core)
        self.assertIn("function schedulePlanRefresh(panel)", self.source)
        self.assertIn("void loadChartData(panel, true)", self.source)
        self.assertIn("refreshBatteryPlanCard(this)", self.source)

    def test_all_dashboard_motion_is_disabled(self) -> None:
        self.assertIn("animation: none !important", self.source)
        self.assertIn("transition: none !important", self.source)
        self.assertIn("scroll-behavior: auto !important", self.source)
        self.assertIn("touch-action: manipulation", self.source)
        self.assertIn("backdrop-filter: none !important", self.source)
        self.assertIn(".ep-v011-particles span", self.source)
        self.assertIn(".ep-v027-backdrop", self.source)
        self.assertIn("display: none !important", self.source)
        self.assertIn('input.disabled = true', self.source)

    def test_browser_matrix_uses_one_deterministic_harness(self) -> None:
        browser_test = (BROWSER / "test_frontend_stability.py").read_text(
            encoding="utf-8"
        )
        wrapper = (BROWSER / "test_frontend_stability_v043.py").read_text(
            encoding="utf-8"
        )
        harness = (BROWSER / "frontend_harness.html").read_text(
            encoding="utf-8"
        )
        workflow = (
            ROOT / ".github" / "workflows" / "frontend-browser.yml"
        ).read_text(encoding="utf-8")
        self.assertIn('Profile("desktop-chromium"', browser_test)
        self.assertIn('Profile("ipad-webkit"', browser_test)
        self.assertIn('Profile("iphone-webkit"', browser_test)
        self.assertIn("telemetry_identity", browser_test)
        self.assertIn("exercise_plan_refresh", browser_test)
        self.assertIn("animation[\"animations\"] != 0", browser_test)
        self.assertIn("frontend_harness.html?entry=v043", wrapper)
        self.assertIn('stability.EXPECTED_ENTRYPOINT = "v043"', wrapper)
        self.assertIn('"v043"].includes(requestedEntry)', harness)
        self.assertIn("exercise_touch_controls", browser_test)
        self.assertIn("test_frontend_stability_v043.py", workflow)
        self.assertIn("window.__epReady = new Promise", harness)
        self.assertNotIn("document.write", harness)
        self.assertFalse((BROWSER / "frontend_harness_v041.html").exists())
        self.assertIn("playwright install --with-deps chromium webkit", workflow)


if __name__ == "__main__":
    unittest.main()
