from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class FrontendV0411OptimizeScrollTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "gw-energy-pilot-v0411.js").read_text(
            encoding="utf-8"
        )

    def test_v0411_is_active_and_version_synchronized(self) -> None:
        manifest = json.loads(
            (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
        )
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")

        self.assertEqual(manifest["version"], "0.41.1")
        self.assertIn(
            "gw-energy-pilot-v0411.js?v=0.41.1-optimize-scroll1",
            init_source,
        )
        self.assertIn(
            'import "./gw-energy-pilot-v041.js?v=0.41.1-optimize-scroll1"',
            self.source,
        )
        self.assertIn('const VERSION = "0.41.1"', self.source)

    def test_optimize_action_replaces_the_legacy_full_render_listener(self) -> None:
        self.assertIn("button.cloneNode(true)", self.source)
        self.assertIn("button.replaceWith(replacement)", self.source)
        self.assertIn('replacement.dataset[OPTIMIZE_MARKER] = "1"', self.source)
        self.assertIn('button.addEventListener("click", async (event) =>', self.source)
        self.assertIn(
            'await panel._hass.callService("button", "press", { entity_id: entityId })',
            self.source,
        )
        self.assertIn("panel.__epV0411OptimizePending = true", self.source)
        self.assertIn("panel.__epV0411OptimizePending = false", self.source)
        self.assertIn('button.setAttribute("aria-busy", busy ? "true" : "false")', self.source)
        self.assertNotIn("panel._queueRender();", self.source)

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
        self.assertIn("PanelClass.prototype.__epV0411Installed = true", self.source)


if __name__ == "__main__":
    unittest.main()
