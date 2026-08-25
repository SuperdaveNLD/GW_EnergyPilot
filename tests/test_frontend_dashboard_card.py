from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "custom_components" / "gw_energypilot" / "frontend"
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"


class FrontendDashboardCardTests(unittest.TestCase):
    def test_battery_plan_installer_is_idempotent_and_refreshable(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v027-battery-plan-core.js").read_text(
            encoding="utf-8"
        )
        start = source.index("function installEnhancedCard")
        end = source.index("await customElements.whenDefined", start)
        installer = source[start:end]

        duplicate_guard = 'querySelectorAll(".ep-v027-battery-plan-card")'
        card_creation = 'document.createElement("article")'
        self.assertIn(duplicate_guard, installer)
        self.assertIn("existingCards.slice(1)", installer)
        self.assertIn("duplicate.remove()", installer)
        self.assertIn("dataset.epRenderKey", installer)
        self.assertIn("existingCard.replaceWith(card)", installer)
        self.assertLess(installer.index(duplicate_guard), installer.index(card_creation))

    def test_battery_plan_change_bypasses_chart_cache(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v027-battery-plan-core.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("function currentOptimizationPlanRevision", source)
        self.assertIn('_entityId?.("optimize_now")', source)
        self.assertIn("attributes?.plan_revision", source)
        self.assertIn("data?.payload?.plan_revision", source)
        self.assertIn("state.last_updated !== plan.last_updated", source)
        self.assertIn("activePlanChanged(panel, data)", source)
        self.assertIn("loadChartData(panel, true)", source)

    def test_v034_flow_direction_is_semantic_and_geometry_specific(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v034.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("function synchronizeFlowDirections", source)
        self.assertIn('grid > 0\n        ? "from"\n        : "to"', source)
        self.assertIn('battery > 0\n        ? "to"\n        : "from"', source)
        self.assertIn(
            ".ep-link-pv.ep-v034-to-hub .ep-v011-particles span,",
            source,
        )
        self.assertIn(
            ".ep-link-grid.ep-v034-from-hub .ep-v011-particles span",
            source,
        )
        self.assertIn(
            ".ep-link-house.ep-v034-from-hub .ep-v011-particles span,",
            source,
        )
        self.assertIn(
            ".ep-link-battery.ep-v034-to-hub .ep-v011-particles span",
            source,
        )
        self.assertIn("animation-direction: normal !important", source)
        self.assertIn("@keyframes epV034FlowHForward", source)
        self.assertIn("@keyframes epV034FlowHReverse", source)
        self.assertIn("@keyframes epV034FlowVForward", source)
        self.assertIn("@keyframes epV034FlowVReverse", source)

    def test_v034_flow_layout_tracks_narrow_card_resize(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v034.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("const FLOW_COMPACT_BREAKPOINT_PX = 430", source)
        self.assertIn("const FLOW_TIGHT_BREAKPOINT_PX = 340", source)
        self.assertIn("function updateResponsiveFlowLayout", source)
        self.assertIn("typeof globalThis.ResizeObserver", source)
        self.assertIn('flow.classList.toggle("ep-v034-flow-compact", compact)', source)
        self.assertIn("--ep-v034-node-width", source)
        self.assertIn("--ep-v034-stage-height", source)
        self.assertIn("height: auto !important", source)
        self.assertIn("updateParticleGeometry(flow)", source)

    def test_v035_wraps_v034_cache_busted_frontend_modules(self) -> None:
        release_v034 = (FRONTEND / "gw-energy-pilot-v034.js").read_text(
            encoding="utf-8"
        )
        release_v035 = (FRONTEND / "gw-energy-pilot-v035.js").read_text(
            encoding="utf-8"
        )
        integration = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")

        # v0.34 owns the retained behavioral layers and the bounded live-flow
        # compatibility fix. v0.35 remains a version-only release wrapper.
        self.assertIn(
            'gw-energy-pilot-v031-battery-saver.js?v=0.34-batterysaver1',
            release_v034,
        )
        self.assertIn(
            'gw-energy-pilot-v027-battery-plan-core.js?v=0.34-planrefresh1',
            release_v034,
        )
        self.assertIn('const VERSION = "0.34"', release_v034)
        self.assertIn("synchronizeFlowDirections", release_v034)

        self.assertIn(
            'gw-energy-pilot-v034.js?v=0.35-release2',
            release_v035,
        )
        self.assertIn('const VERSION = "0.35"', release_v035)
        self.assertNotIn("synchronizeFlowDirections", release_v035)
        self.assertIn(
            'gw-energy-pilot-v035.js?v=0.35-release2',
            integration,
        )

    def test_release_layer_reconciles_existing_duplicate_cards(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v030.js").read_text(encoding="utf-8")

        self.assertIn("function reconcileBatteryPlanCards", source)
        self.assertIn(".ep-v031-card-windowbar, .ep-v028-window-controls", source)
        self.assertIn("if (card !== canonical) card.remove()", source)
        self.assertIn("reconcileBatteryPlanCards(root)", source)
        self.assertIn("__epV030RenderInstalled", source)


if __name__ == "__main__":
    unittest.main()
