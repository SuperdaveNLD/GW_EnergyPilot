from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "custom_components" / "gw_energypilot" / "frontend"


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
        self.assertIn("preserveInteractiveShell(existingCard, card)", installer)
        self.assertIn("installedCard = existingCard", installer)
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

    def test_soc_chart_uses_explicit_percent_contracts(self) -> None:
        data = (FRONTEND / "gw-energy-pilot-v027-battery-plan-data.js").read_text(
            encoding="utf-8"
        )
        view = (FRONTEND / "gw-energy-pilot-v027-battery-plan-view.js").read_text(
            encoding="utf-8"
        )

        self.assertIn('_entityId?.("battery_soc")', data)
        self.assertIn("normalizeSocStatisticRows", data)
        self.assertIn("normalizeSocPlanPoints", data)
        self.assertIn("p.value_pct", data)
        self.assertNotIn("p.pct <= 1)", data)
        self.assertIn('data-series="actual-soc"', view)
        self.assertIn('data-series="forecast-soc"', view)
        self.assertIn('t(panel, "socAxis")', view)

    def test_ev_protection_overlay_reuses_verified_execution_history(self) -> None:
        data = (FRONTEND / "gw-energy-pilot-v027-battery-plan-data.js").read_text(
            encoding="utf-8"
        )
        view = (FRONTEND / "gw-energy-pilot-v027-battery-plan-view.js").read_text(
            encoding="utf-8"
        )
        core = (FRONTEND / "gw-energy-pilot-v027-battery-plan-core.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("normalizeExecutionEvIntervals", data)
        self.assertIn('outcome.verification_status !== "verified"', data)
        self.assertIn("runtime_session_id", data)
        self.assertNotIn("payload?.ev_protection?.intervals", data)
        self.assertIn('data-series="ev-protection"', view)
        self.assertIn('data-ev-kind="${interval.kind}"', view)
        self.assertIn("epV027EvChargeStripes", view)
        self.assertIn("ev-charge-allowed", view)
        self.assertIn("ev-discharge-blocked", view)
        self.assertIn("activeExecutionHistoryChanged(panel, data)", core)
        self.assertIn("loadChartData(panel, true, false)", core)

    def test_chart_ranges_are_local_views_over_one_cached_dataset(self) -> None:
        data = (FRONTEND / "gw-energy-pilot-v027-battery-plan-data.js").read_text(
            encoding="utf-8"
        )
        view = (FRONTEND / "gw-energy-pilot-v027-battery-plan-view.js").read_text(
            encoding="utf-8"
        )
        core = (FRONTEND / "gw-energy-pilot-v027-battery-plan-core.js").read_text(
            encoding="utf-8"
        )

        self.assertIn('new Set(["12h", "24h", "36h"])', data)
        self.assertIn('const DEFAULT_RANGE = "24h"', data)
        self.assertIn("export function chartWindowData", data)
        self.assertIn("chartTime.historyStartMs", data)
        self.assertIn("chartTime.maxEndMs", data)
        self.assertIn("dayActualRows", data)
        self.assertIn("data-chart-range", view)
        self.assertIn("rangeControlHtml(panel, range)", core)
        self.assertIn("saveChartRange(button.dataset.chartRange)", core)
        self.assertNotIn("loadChartData(panel", core[core.index('card.querySelectorAll("[data-chart-range]")'):core.index('card.querySelectorAll("[data-chart-size]")')])

    def test_range_controls_remain_in_the_connected_header(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v027-battery-plan-core.js").read_text(
            encoding="utf-8"
        )

        self.assertIn('existingHead?.querySelectorAll("[data-chart-range]")', source)
        self.assertIn('nextHead?.querySelectorAll("[data-chart-range]")', source)
        self.assertIn("nextByRange", source)
        self.assertIn("child !== windowBar && child !== existingHead", source)

    def test_v034_flow_direction_neutralizes_legacy_reversal_specificity(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v034.js").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            ".ep-flow-link.ep-v022-to-hub .ep-v011-particles span,",
            source,
        )
        self.assertIn(
            ".ep-flow-link.ep-v022-from-hub .ep-v011-particles span",
            source,
        )
        self.assertIn("animation-direction: normal !important", source)
        self.assertIn("geometry-specific v0.13", source)
        self.assertNotIn("function synchronizeFlowDirections", source)
        self.assertNotIn("@keyframes epV034Flow", source)

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
        self.assertIn("window.setTimeout(() => finishPointerInteraction(panel, true), 0)", source)
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

    def test_v035_mobile_touch_scroll_is_not_pointer_captured(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v035.js").read_text(encoding="utf-8")
        customer = (
            FRONTEND / "gw-energy-pilot-v036-customer-controller.js"
        ).read_text(encoding="utf-8")

        self.assertIn("const TOUCH_SCROLL_THRESHOLD_PX = 8", source)
        self.assertIn("const TOUCH_SCROLL_SETTLE_MS = 350", source)
        self.assertIn("const POINTER_SAFETY_TIMEOUT_MS = 5000", source)
        self.assertIn('root.addEventListener(\n    "pointermove"', source)
        self.assertIn('if (event.pointerType === "mouse")', source)
        self.assertIn("panel.__epV035TouchMoved = true", source)
        self.assertIn("finishPointerInteraction(panel, true)", source)
        self.assertIn("completePointerInteraction(panel)", source)
        self.assertIn("touch-action:pan-y", customer)

    def test_v0362_preserves_mobile_scroll_across_refresh_render(self) -> None:
        source = (
            FRONTEND / "gw-energy-pilot-v0362-scroll-stability.js"
        ).read_text(encoding="utf-8")

        self.assertIn("const MOBILE_SCROLL_BREAKPOINT_PX = 720", source)
        self.assertIn("function composedParent", source)
        self.assertIn("function captureScrollPositions", source)
        self.assertIn("globalThis.document?.scrollingElement", source)
        self.assertIn('this.style.setProperty("overflow-anchor", "none")', source)
        self.assertIn("function stabilizeScrollAfterRender", source)
        self.assertGreaterEqual(source.count("globalThis.requestAnimationFrame?."), 2)
        render_call = source.index("previousRender.call(this)")
        restore_call = source.rindex("stabilizeScrollAfterRender(snapshots)")
        self.assertLess(
            source.index("const snapshots = preserveScroll ? captureScrollPositions(this) : []"),
            render_call,
        )
        self.assertLess(render_call, restore_call)

    def test_v0362_loads_customer_controller_chain(self) -> None:
        release_v034 = (FRONTEND / "gw-energy-pilot-v034.js").read_text(
            encoding="utf-8"
        )
        release_v035 = (FRONTEND / "gw-energy-pilot-v035.js").read_text(
            encoding="utf-8"
        )
        release_v036 = (
            FRONTEND / "gw-energy-pilot-v036-customer-controller.js"
        ).read_text(encoding="utf-8")
        release_v0362 = (
            FRONTEND / "gw-energy-pilot-v0362-scroll-stability.js"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'gw-energy-pilot-v031-battery-saver.js?v=1.1.0-beta.2-settings1',
            release_v034,
        )
        self.assertIn(
            'gw-energy-pilot-v027-battery-plan-core.js?v=1.1.0-beta.2-settings1',
            release_v034,
        )
        self.assertIn('gw-energy-pilot-v034.js?v=0.36-flowmobile1', release_v035)
        self.assertIn('gw-energy-pilot-v035.js?v=0.36.1-mobile-scroll1', release_v036)
        self.assertIn('const VERSION = "0.36.1"', release_v036)
        self.assertIn(
            'gw-energy-pilot-v036-customer-controller.js?v=0.36.2-scroll-stability1',
            release_v0362,
        )
        self.assertIn('const VERSION = "0.36.2"', release_v0362)

    def test_customer_controller_reuses_existing_policy_and_soc_paths(self) -> None:
        source = (
            FRONTEND / "gw-energy-pilot-v036-customer-controller.js"
        ).read_text(encoding="utf-8")

        self.assertIn('type: "gw_energypilot/battery_saver/get"', source)
        self.assertIn('type: "gw_energypilot/battery_saver/set"', source)
        self.assertIn('const CUSTOM_MODE = "custom"', source)
        self.assertIn('numberModel(panel, "emhass_minimum_soc"', source)
        self.assertIn('numberModel(panel, "emhass_maximum_soc"', source)
        self.assertIn('callService("number", "set_value"', source)
        self.assertIn('if (label === "command" || label === "commando")', source)
        self.assertIn("current_emhass_values", source)

    def test_customer_strategy_exposes_profiles_and_diagnostic_boundary(self) -> None:
        source = (
            FRONTEND / "gw-energy-pilot-v036-customer-controller.js"
        ).read_text(encoding="utf-8")

        self.assertIn("const CUSTOM_MODE = \"custom\"", source)
        self.assertIn("data?.modes || []", source)
        self.assertIn("data-v036-mode", source)
        self.assertIn("current_emhass_values", source)
        self.assertIn("battery_soc_deficit_cost", source)
        self.assertIn("battery_soc_surplus_cost", source)
        self.assertIn("battery_stress_cost", source)
        self.assertIn("weight_battery_charge", source)
        self.assertIn("weight_battery_discharge", source)
        self.assertIn("Low-level controller command is available in Diagnostics.", source)
        self.assertIn("Het technische controllercommando staat in Diagnostiek.", source)

    def test_release_layer_reconciles_existing_duplicate_cards(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v030.js").read_text(encoding="utf-8")

        self.assertIn("function reconcileBatteryPlanCards", source)
        self.assertIn(".ep-v031-card-windowbar, .ep-v028-window-controls", source)
        self.assertIn("if (card !== canonical) card.remove()", source)
        self.assertIn("reconcileBatteryPlanCards(root)", source)
        self.assertIn("__epV030RenderInstalled", source)


if __name__ == "__main__":
    unittest.main()
