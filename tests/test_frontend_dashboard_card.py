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

    def test_v035_wraps_v034_cache_busted_frontend_modules(self) -> None:
        release_v034 = (FRONTEND / "gw-energy-pilot-v034.js").read_text(
            encoding="utf-8"
        )
        release_v035 = (FRONTEND / "gw-energy-pilot-v035.js").read_text(
            encoding="utf-8"
        )
        integration = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")

        # v0.34 still owns the behavioral cache-busting for the two modified
        # nested modules. v0.35 adds the interaction-safe outer render layer.
        self.assertIn(
            'gw-energy-pilot-v031-battery-saver.js?v=0.34-batterysaver1',
            release_v034,
        )
        self.assertIn(
            'gw-energy-pilot-v027-battery-plan-core.js?v=0.34-planrefresh1',
            release_v034,
        )
        self.assertIn('const VERSION = "0.34"', release_v034)

        self.assertIn(
            'gw-energy-pilot-v034.js?v=0.35-release1',
            release_v035,
        )
        self.assertIn('const VERSION = "0.35"', release_v035)
        self.assertIn(
            'gw-energy-pilot-v035.js?v=0.35-interaction1',
            integration,
        )

    def test_v035_defers_destructive_render_during_control_interaction(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v035.js").read_text(encoding="utf-8")

        self.assertIn("function installInteractionGuard", source)
        self.assertIn('root.addEventListener(\n    "pointerover"', source)
        self.assertIn('root.addEventListener(\n    "pointerdown"', source)
        self.assertIn('root.addEventListener("pointerup", finishPointer, true)', source)
        self.assertIn("function interactionActive", source)
        self.assertIn("this.__epV035RenderDeferred = true", source)
        self.assertIn("flushDeferredRender(panel)", source)
        self.assertIn("panel._queueRender()", source)
        self.assertLess(
            source.index("if (interactionActive(this))"),
            source.index("previousRender.call(this)"),
        )
        self.assertLess(
            source.index("previousRender.call(this)"),
            source.index("installInteractionGuard(this, root)"),
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
