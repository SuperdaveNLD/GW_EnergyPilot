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

        # v0.34 still owns behavioral cache-busting for its modified nested
        # modules. v0.35 adds the outer render-storm and interaction guard.
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
            'gw-energy-pilot-v035.js?v=0.35-renderstorm1',
            integration,
        )

    def test_v035_filters_unrelated_hass_updates_before_rendering(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v035.js").read_text(encoding="utf-8")

        self.assertIn("function installHassRenderGuard", source)
        self.assertIn("function relevantHassStateChanged", source)
        self.assertIn("function relevantEntityIds", source)
        self.assertIn("Object.values(panel._entityMap || {})", source)
        self.assertIn('"p_batt_entity", "p_grid_entity", "optim_status_entity"', source)
        self.assertIn("previousState !== nextState", source)
        self.assertIn("this._hass = value", source)
        self.assertIn("scheduleHassRender(this)", source)
        self.assertIn("const HASS_RENDER_BATCH_MS = 80", source)

        setter_start = source.index("function installHassRenderGuard")
        render_start = source.index("if (!PanelClass.prototype.__epV035RenderInstalled)")
        setter = source[setter_start:render_start]
        self.assertNotIn("descriptor.set.call(this, value);\n      }", setter)
        self.assertLess(
            setter.index("this._hass = value"),
            setter.index("relevantHassStateChanged(this, previousHass, value)"),
        )

    def test_v035_defers_destructive_render_only_during_active_press(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v035.js").read_text(encoding="utf-8")

        self.assertIn("function installInteractionGuard", source)
        self.assertIn('root.addEventListener(\n    "pointerdown"', source)
        self.assertIn('root.addEventListener(\n    "pointerup"', source)
        self.assertIn("window.setTimeout(() => finishPointerInteraction(panel), 0)", source)
        self.assertNotIn('"pointerover"', source)
        self.assertNotIn("__epV035HoverActive", source)
        self.assertIn("function interactionActive", source)
        self.assertIn("this.__epV035RenderDeferred = true", source)
        self.assertIn("flushDeferredRender(panel)", source)
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
