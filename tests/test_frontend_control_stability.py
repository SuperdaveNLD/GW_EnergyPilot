from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class FrontendControlStabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.entry = (FRONTEND / "gw-energy-pilot-v038.js").read_text(
            encoding="utf-8"
        )
        self.runtime = (FRONTEND / "gw-energy-pilot-v038-runtime.js").read_text(
            encoding="utf-8"
        )
        self.strategy = (FRONTEND / "gw-energy-pilot-v038-strategy.js").read_text(
            encoding="utf-8"
        )
        self.styles = (FRONTEND / "gw-energy-pilot-v038-styles.js").read_text(
            encoding="utf-8"
        )
        self.model = (FRONTEND / "gw-energy-pilot-v038-model.js").read_text(
            encoding="utf-8"
        )

    def test_v038_bypasses_failed_pointer_and_button_reuse_layers(self) -> None:
        self.assertIn("gw-energy-pilot-v038-runtime.js?v=0.38-release1", self.entry)
        self.assertIn('gw-energy-pilot-v034.js?v=0.38-clean-base1', self.runtime)
        combined = self.entry + self.runtime + self.strategy
        self.assertNotIn("gw-energy-pilot-v035.js", combined)
        self.assertNotIn("gw-energy-pilot-v0363-control-stability.js", combined)
        self.assertNotIn("captureStableButtons", combined)
        self.assertNotIn("buttonIdentity", combined)
        self.assertNotIn("normalizedText", combined)
        self.assertNotIn("renderedButton.replaceWith(stableButton)", combined)
        self.assertNotIn("setPointerCapture", combined)

    def test_v038_strategy_uses_stable_keys_and_delegated_events(self) -> None:
        self.assertIn("function installV038DelegatedControls", self.strategy)
        self.assertIn('button[data-ep-v038-profile]', self.strategy)
        self.assertIn("button.dataset.epV038Profile", self.strategy)
        self.assertIn(
            'aria-pressed="${activeMode === mode.key ? "true" : "false"}"',
            self.strategy,
        )
        self.assertIn('.ep-v038-profile[aria-pressed="true"]', self.styles)
        self.assertIn('wrap.setAttribute("translate", "no")', self.strategy)
        self.assertIn("PROFILE_KEYS", self.strategy)
        self.assertIn("canonicalProfiles", self.strategy)
        self.assertIn("reusableStrategy", self.strategy)
        self.assertIn("strategySignature", self.strategy)
        self.assertIn("wrap.dataset.epV038Signature", self.strategy)
        self.assertIn("cache.busy || cache.loading || !cache.data", self.strategy)
        self.assertIn("updateStrategyVisualState(panel, true)", self.strategy)
        self.assertIn("updateStrategyVisualState(panel);", self.strategy)

    def test_v038_profile_identity_is_language_independent(self) -> None:
        self.assertIn('label: "Battery Saver"', self.model)
        self.assertIn('label: "Batterijbesparing"', self.model)
        self.assertIn('label: "Custom"', self.model)
        self.assertIn('label: "Aangepast"', self.model)
        self.assertIn("export const PROFILE_KEYS", self.model)
        self.assertIn("export function localizedProfile", self.model)
        self.assertIn("export function canonicalProfiles", self.model)
        self.assertIn(
            'const key = typeof mode === "string" ? mode : mode?.key',
            self.model,
        )

    def test_v038_interaction_guard_cannot_remain_stuck(self) -> None:
        self.assertIn("function installInteractionGuard", self.runtime)
        self.assertIn('globalThis.addEventListener?.(\n    "pointerup"', self.runtime)
        self.assertIn('globalThis.addEventListener?.(\n    "pointercancel"', self.runtime)
        self.assertIn('globalThis.addEventListener?.("blur"', self.runtime)
        self.assertIn("function completePointerInteraction", self.runtime)
        self.assertIn("function completeKeyboardInteraction", self.runtime)
        self.assertIn("function completeAllInteractions", self.runtime)
        self.assertIn("const INTERACTION_SAFETY_TIMEOUT_MS = 3000", self.runtime)
        self.assertIn("const TOUCH_SCROLL_THRESHOLD_PX = 8", self.runtime)
        self.assertIn("pointerSafetyTimer", self.runtime)
        self.assertIn("keyboardSafetyTimer", self.runtime)
        self.assertIn("this.__epV038RenderDeferred = true", self.runtime)
        self.assertLess(
            self.runtime.index("if (interactionActive(this))"),
            self.runtime.index("previousRender.call(this)"),
        )

    def test_v038_flow_uses_one_physical_direction_contract(self) -> None:
        self.assertIn("export function resolveHousePower", self.model)
        self.assertIn("export function flowMotionMap", self.model)
        self.assertIn(
            "const house = resolveHousePower(values?.house, pv, grid, battery)",
            self.model,
        )
        self.assertIn('grid > 0\n          ? "right"\n          : "left"', self.model)
        self.assertIn('battery > 0\n          ? "up"\n          : "down"', self.model)
        self.assertIn('data-ep-v038-motion="right"', self.styles)
        self.assertIn('data-ep-v038-motion="left"', self.styles)
        self.assertIn('data-ep-v038-motion="up"', self.styles)
        self.assertIn('data-ep-v038-motion="down"', self.styles)
        self.assertIn("@keyframes epV038HRight", self.styles)
        self.assertIn("@keyframes epV038HLeft", self.styles)
        self.assertIn("@keyframes epV038VUp", self.styles)
        self.assertIn("@keyframes epV038VDown", self.styles)
        self.assertIn("animation-direction:normal !important", self.styles)
        self.assertIn("synchronizeFlowDirections(this, root)", self.runtime)


if __name__ == "__main__":
    unittest.main()
