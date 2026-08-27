from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class FrontendV041StableDomTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "gw-energy-pilot-v041.js").read_text(
            encoding="utf-8"
        )

    def test_v041_bypasses_the_v040_render_settle_layer(self) -> None:
        self.assertIn('import "./gw-energy-pilot-v039.js?v=0.41-stable-dom1"', self.source)
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
        self.assertNotIn("shadowRoot.innerHTML", self.source)
        self.assertNotIn("scrollTop =", self.source)
        self.assertNotIn("scrollLeft =", self.source)

    def test_pointer_guard_is_not_installed_for_stable_v041_sessions(self) -> None:
        self.assertIn("this.__epV041StableRuntime = true", self.source)
        self.assertIn("this.__epV038InteractionGuardInstalled = true", self.source)
        self.assertNotIn("setPointerCapture", self.source)
        self.assertNotIn("preventDefault", self.source)

    def test_all_dashboard_motion_is_disabled(self) -> None:
        self.assertIn("animation: none !important", self.source)
        self.assertIn("transition: none !important", self.source)
        self.assertIn("scroll-behavior: auto !important", self.source)
        self.assertIn("touch-action: manipulation", self.source)
        self.assertIn("backdrop-filter: none !important", self.source)
        self.assertIn(".ep-v011-particles span", self.source)
        self.assertIn("display: none !important", self.source)

    def test_browser_matrix_covers_desktop_ipad_and_iphone(self) -> None:
        browser_test = (
            ROOT / "tests" / "browser" / "test_frontend_stability.py"
        ).read_text(encoding="utf-8")
        wrapper = (
            ROOT / "tests" / "browser" / "test_frontend_stability_v041.py"
        ).read_text(encoding="utf-8")
        workflow = (
            ROOT / ".github" / "workflows" / "frontend-browser.yml"
        ).read_text(encoding="utf-8")
        self.assertIn('Profile("desktop-chromium"', browser_test)
        self.assertIn('Profile("ipad-webkit"', browser_test)
        self.assertIn('Profile("iphone-webkit"', browser_test)
        self.assertIn("frontend_harness_v041.html", wrapper)
        self.assertIn("playwright install --with-deps chromium webkit", workflow)


if __name__ == "__main__":
    unittest.main()
