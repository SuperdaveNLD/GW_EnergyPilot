from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"
SOURCE = FRONTEND / "gw-energy-pilot-v038.js"


class FrontendV038Tests(unittest.TestCase):
    def source(self) -> str:
        return SOURCE.read_text(encoding="utf-8")

    def test_v038_is_clean_active_layer_over_v034(self) -> None:
        source = self.source()
        first_import = source.splitlines()[0]

        self.assertEqual(
            first_import,
            'import "./gw-energy-pilot-v034.js?v=0.38-base1";',
        )
        for legacy_active_module in (
            "gw-energy-pilot-v035.js",
            "gw-energy-pilot-v036-customer-controller.js",
            "gw-energy-pilot-v0362-scroll-stability.js",
            "gw-energy-pilot-v0363-control-stability.js",
            "gw-energy-pilot-v037.js",
        ):
            self.assertNotIn(f'import "./{legacy_active_module}', source)
        self.assertIn('const VERSION = "0.38"', source)

    def test_profile_identity_and_highlight_are_language_independent(self) -> None:
        source = self.source()

        self.assertIn('data-ep-v038-profile="${panel._escape(mode.key)}"', source)
        self.assertIn('aria-pressed="${selected ? "true" : "false"}"', source)
        self.assertIn('.ep-v038-profile[aria-pressed="true"]', source)
        self.assertIn("button.dataset.epV038Profile", source)
        self.assertIn('root.addEventListener("click", (event) => {', source)
        self.assertIn("function profilePresentation", source)
        self.assertIn("mad_steve:", source)
        self.assertIn("gold_rush:", source)
        self.assertIn("Batterijstrategie", source)
        self.assertIn("Battery strategy", source)

        # v0.37 used visible translated text as part of button identity and then
        # reinserted old button nodes. v0.38 must not repeat either mechanism.
        self.assertNotIn("normalizedText", source)
        self.assertNotIn("buttonIdentity", source)
        self.assertNotIn("captureStableButtons", source)
        self.assertNotIn("replaceWith(stableButton)", source)

    def test_press_protection_never_captures_or_blocks_the_pointer(self) -> None:
        source = self.source()

        self.assertIn("const PRESS_RENDER_QUIET_MS = 300", source)
        self.assertIn("function installPressQuietWindow", source)
        self.assertIn("panel.__epV038RenderQuietUntil", source)
        self.assertIn("function neutralizeLegacyInteractionState", source)
        self.assertNotIn("setPointerCapture", source)
        self.assertNotIn("preventDefault()", source)
        self.assertNotIn("stopPropagation()", source)
        self.assertNotIn("__epV038PointerActive", source)
        self.assertNotIn("if (interactionActive(this))", source)

    def test_already_open_v037_realm_cannot_restore_stale_buttons(self) -> None:
        source = self.source()

        self.assertIn("function armLegacyStableButtonBypass", source)
        self.assertIn("__epV0363ControlStabilityInstalled", source)
        self.assertIn("data-ep-v038-render-sentinel", source)
        self.assertIn("sentinel.dataset.epV038RenderSentinel", source)
        self.assertLess(
            source.index("armLegacyStableButtonBypass(this, PanelClass)"),
            source.index("previousRender.call(this)"),
        )

    def test_flow_direction_uses_one_canonical_semantic_mapping(self) -> None:
        source = self.source()

        self.assertIn("function enforceCanonicalFlowDirections", source)
        self.assertIn("link.dataset.epV038Flow = direction", source)
        self.assertIn('pv > 50 ? "to-hub" : null', source)
        self.assertIn('grid > 0\n        ? "from-hub"\n        : "to-hub"', source)
        self.assertIn('houseLink?.classList.contains("idle") ? null : "from-hub"', source)
        self.assertIn('battery > 0\n        ? "to-hub"\n        : "from-hub"', source)

        # Geometry table: PV -> hub, grid import -> hub, hub -> grid export,
        # hub -> house, battery discharge -> hub, hub -> battery charge.
        self.assertIn('.ep-link-pv[data-ep-v038-flow="to-hub"]', source)
        self.assertIn('.ep-link-grid[data-ep-v038-flow="to-hub"]', source)
        self.assertIn('.ep-link-grid[data-ep-v038-flow="from-hub"]', source)
        self.assertIn('.ep-link-house[data-ep-v038-flow="from-hub"]', source)
        self.assertIn('.ep-link-battery[data-ep-v038-flow="to-hub"]', source)
        self.assertIn('.ep-link-battery[data-ep-v038-flow="from-hub"]', source)
        self.assertIn("animation-direction:normal !important", source)
        self.assertNotIn("animation-direction:reverse", source)
        for keyframe in (
            "epV038HForward",
            "epV038HReverse",
            "epV038VForward",
            "epV038VReverse",
        ):
            self.assertIn(f"@keyframes {keyframe}", source)

    def test_relevant_hass_filter_and_mobile_scroll_survive_rebuild(self) -> None:
        source = self.source()

        self.assertIn("const HASS_RENDER_BATCH_MS = 80", source)
        self.assertIn("function installHassRenderGuard", source)
        self.assertIn("function relevantHassStateChanged", source)
        self.assertIn("previousHass.states[entityId] !== nextHass.states[entityId]", source)
        self.assertIn("this._hass = value", source)
        self.assertIn("const MOBILE_SCROLL_BREAKPOINT_PX = 720", source)
        self.assertIn("function captureScrollPositions", source)
        self.assertIn("function stabilizeScrollAfterRender", source)
        self.assertGreaterEqual(source.count("globalThis.requestAnimationFrame?."), 2)

    def test_release_wiring_is_consistent(self) -> None:
        integration = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["version"], "0.38")
        self.assertIn(
            'gw-energy-pilot-v038.js?v=0.38-controls-flow1',
            integration,
        )


if __name__ == "__main__":
    unittest.main()
