from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class FrontendV044OptimizeStabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "gw-energy-pilot-v044.js").read_text(
            encoding="utf-8"
        )

    def test_v049_retains_v044_over_the_complete_frontend(self) -> None:
        manifest = json.loads(
            (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
        )
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")

        v048 = (FRONTEND / "gw-energy-pilot-v048.js").read_text(encoding="utf-8")
        v047 = (FRONTEND / "gw-energy-pilot-v047.js").read_text(encoding="utf-8")
        v046 = (FRONTEND / "gw-energy-pilot-v046.js").read_text(encoding="utf-8")
        v045 = (FRONTEND / "gw-energy-pilot-v045.js").read_text(encoding="utf-8")
        self.assertEqual(manifest["version"], "1.0.1-beta.3")
        self.assertIn(
            "gw-energy-pilot-v101.js?v=1.0.1-beta3",
            init_source,
        )
        self.assertIn('import "./gw-energy-pilot-v047.js?v=1.0.1-beta3"', v048)
        self.assertIn('import "./gw-energy-pilot-v046.js?v=1.0.1-beta3"', v047)
        self.assertIn('import "./gw-energy-pilot-v045.js?v=1.0.1-beta3"', v046)
        self.assertIn('import "./gw-energy-pilot-v044.js?v=1.0.1-beta3"', v045)
        self.assertIn(
            'import "./gw-energy-pilot-v043.js?v=1.0.1-beta3"',
            self.source,
        )
        self.assertIn('const VERSION = "0.44"', self.source)

    def test_optimize_action_replaces_the_legacy_full_render_listener(self) -> None:
        self.assertIn("button.cloneNode(true)", self.source)
        self.assertIn("button.replaceWith(replacement)", self.source)
        self.assertIn('replacement.dataset[OPTIMIZE_MARKER] = "1"', self.source)
        self.assertIn('button.addEventListener("click", async (event) =>', self.source)
        self.assertIn(
            'await panel._hass.callService("button", "press", { entity_id: entityId })',
            self.source,
        )
        self.assertIn("panel.__epV044OptimizePending = true", self.source)
        self.assertIn("panel.__epV044OptimizePending = false", self.source)
        self.assertIn(
            'button.setAttribute("aria-busy", busy ? "true" : "false")',
            self.source,
        )
        self.assertNotIn("panel._queueRender();", self.source)

    def test_optimize_action_is_one_safe_area_aware_floating_control(self) -> None:
        self.assertIn(
            'const FLOATING_STYLE_ID = "ep-v044-floating-optimize"',
            self.source,
        )
        self.assertIn("function ensureFloatingOptimizeStyle(root)", self.source)
        self.assertIn("position: fixed !important", self.source)
        self.assertIn(
            "right: calc(16px + env(safe-area-inset-right))",
            self.source,
        )
        self.assertIn(
            "bottom: calc(16px + env(safe-area-inset-bottom))",
            self.source,
        )
        self.assertIn("min-width: 44px", self.source)
        self.assertIn("min-height: 44px", self.source)
        self.assertIn(
            "padding-bottom: calc(96px + env(safe-area-inset-bottom))",
            self.source,
        )
        self.assertIn('const main = root.querySelector("main")', self.source)
        self.assertIn("if (main) main.appendChild(button)", self.source)
        self.assertNotIn("position: sticky", self.source)
        for forbidden in (
            "animation:",
            "transition:",
            "scrollTop",
            "scrollLeft",
            "setPointerCapture",
            "touchstart",
            "touchmove",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.source)

    def test_optimize_runtime_status_is_patched_in_place(self) -> None:
        self.assertIn("function patchOptimizeUi(panel)", self.source)
        self.assertIn("function patchOrchestrator(panel, root, attributes)", self.source)
        self.assertIn(
            'const descriptor = Object.getOwnPropertyDescriptor(PanelClass.prototype, "hass")',
            self.source,
        )
        self.assertIn("descriptor.set.call(this, value)", self.source)
        self.assertIn("patchOptimizeUi(this)", self.source)
        self.assertIn("previousRender.apply(this, args)", self.source)
        self.assertIn("PanelClass.prototype.__epV044Installed = true", self.source)


if __name__ == "__main__":
    unittest.main()
