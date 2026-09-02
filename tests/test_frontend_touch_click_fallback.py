"""Static safety contract for the iOS Companion click fallback."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "custom_components" / "gw_energypilot" / "frontend"


class FrontendTouchClickFallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter = (FRONTEND / "ep-touch-click-fallback.js").read_text(
            encoding="utf-8"
        )
        cls.stable = (FRONTEND / "gw-energy-pilot-v041.js").read_text(
            encoding="utf-8"
        )
        cls.beta_tests = (FRONTEND / "ep-beta-tests.js").read_text(
            encoding="utf-8"
        )

    def test_one_root_scoped_adapter_owns_the_iphone_fallback(self) -> None:
        self.assertIn("installEnergyPilotTouchClickFallback", self.adapter)
        self.assertIn("installEnergyPilotTouchClickFallback", self.stable)
        self.assertIn("const installations = new WeakMap()", self.adapter)
        self.assertIn("installations.get(root)", self.adapter)

    def test_fallback_uses_the_existing_native_action_path(self) -> None:
        self.assertIn("element.click();", self.adapter)
        self.assertNotIn("callService", self.adapter)
        self.assertNotIn("callWS", self.adapter)
        self.assertNotIn("dispatchEvent", self.adapter)
        self.assertIn("internalActivation", self.adapter)
        self.assertIn("late_clicks_suppressed", self.adapter)
        self.assertIn("guardDisconnectedLateClick", self.adapter)

    def test_native_scroll_and_disabled_controls_remain_safe(self) -> None:
        self.assertIn('const CLICK_FALLBACK_MS = 120;', self.adapter)
        self.assertIn('const MOVE_THRESHOLD_PX = 12;', self.adapter)
        self.assertIn('pointer.moved', self.adapter)
        self.assertIn('event.type === "pointercancel"', self.adapter)
        self.assertIn('event.pointerType !== TOUCH_POINTER_TYPE', self.adapter)
        self.assertIn('event.isPrimary === false', self.adapter)
        self.assertIn('passive: true', self.adapter)
        self.assertNotIn("setPointerCapture", self.adapter)
        self.assertNotIn("releasePointerCapture", self.adapter)
        self.assertNotIn("touch-action", self.adapter)
        self.assertNotIn("scrollTop", self.adapter)
        self.assertNotIn("scrollLeft", self.adapter)

    def test_buttons_menu_switches_and_diagnostic_boundary_are_explicit(self) -> None:
        for token in (
            "HTMLButtonElement",
            "HTMLInputElement",
            '"checkbox"',
            '"radio"',
            'node.tagName === "SUMMARY"',
            'node.getAttribute("role") === "button"',
        ):
            self.assertIn(token, self.adapter)
        self.assertIn('node.hasAttribute("data-beta-control")', self.adapter)
        self.assertIn("production_touch_fallback", self.beta_tests)


if __name__ == "__main__":
    unittest.main()
