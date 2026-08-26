from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "custom_components" / "gw_energypilot" / "frontend"
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
WORKFLOWS = ROOT / ".github" / "workflows"


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

    def test_v035_loads_rewritten_controls_and_authoritative_flow_layer(self) -> None:
        release_v034 = (FRONTEND / "gw-energy-pilot-v034.js").read_text(
            encoding="utf-8"
        )
        release_v035 = (FRONTEND / "gw-energy-pilot-v035.js").read_text(
            encoding="utf-8"
        )
        integration = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")

        self.assertIn(
            'gw-energy-pilot-v031-battery-saver.js?v=0.34-batterysaver1',
            release_v034,
        )
        self.assertIn(
            'gw-energy-pilot-v027-battery-plan-core.js?v=0.34-planrefresh1',
            release_v034,
        )
        self.assertIn(
            'gw-energy-pilot-v031-window-controls.js?v=0.35-controls-rewrite1',
            release_v035,
        )
        self.assertIn(
            'gw-energy-pilot-v036-flow-direction.js?v=0.35-flow-direction1',
            release_v035,
        )
        self.assertIn('const VERSION = "0.35"', release_v035)
        self.assertIn(
            'gw-energy-pilot-v035.js?v=0.35-controls-flow2',
            integration,
        )

    def test_v035_filters_hass_updates_without_pointer_locking(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v035.js").read_text(encoding="utf-8")

        self.assertIn("function installRelevantHassGuard", source)
        self.assertIn("function relevantStateObjectsChanged", source)
        self.assertIn("function uiContextSignature", source)
        self.assertIn("function relevantEntityIds", source)
        self.assertIn("Object.values(panel._entityMap || {})", source)
        self.assertIn('"p_batt_entity", "p_grid_entity", "optim_status_entity"', source)
        self.assertIn("previousStates[entityId] !== nextStates[entityId]", source)
        self.assertIn("this._hass = value", source)
        self.assertIn("scheduleHassRender(this)", source)
        self.assertIn("const HASS_RENDER_BATCH_MS = 100", source)

        self.assertNotIn("setPointerCapture", source)
        self.assertNotIn('"pointerdown"', source)
        self.assertNotIn('"pointerup"', source)
        self.assertNotIn("interactionActive", source)
        self.assertNotIn("__epV035PointerActive", source)
        self.assertNotIn("__epV035KeyboardActive", source)

    def test_window_controls_are_css_only_and_click_delegated(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v031-window-controls.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("function installDelegatedActions", source)
        self.assertIn('root.addEventListener("click"', source)
        self.assertIn('data-ep-window-action="close"', source)
        self.assertIn('data-ep-window-action="minimize"', source)
        self.assertIn('data-ep-window-action="maximize"', source)
        self.assertIn(".ep-v036-window-button:hover", source)
        self.assertIn(".ep-v036-window-button:focus-visible", source)
        self.assertIn("touch-action:manipulation", source)
        self.assertIn("applyWindowState(card, state)", source)

        self.assertNotIn("setPointerCapture", source)
        self.assertNotIn('"pointerdown"', source)
        self.assertNotIn('"pointerup"', source)
        self.assertNotIn("_queueRender()", source)
        self.assertNotIn("__epV035PointerActive", source)

    def test_flow_direction_has_one_final_animation_authority(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v036-flow-direction.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("function flowAnimationDirections", source)
        self.assertIn('grid: direction(grid, "normal", "reverse")', source)
        self.assertIn('house: direction(house, "reverse", "normal")', source)
        self.assertIn('battery: direction(battery, "reverse", "normal")', source)
        self.assertIn("ep-v036-flow-normal", source)
        self.assertIn("ep-v036-flow-reverse", source)
        self.assertIn("animation-direction:normal!important", source)
        self.assertIn("animation-direction:reverse!important", source)
        self.assertIn("__epV036FlowDirectionRenderInstalled", source)

    def test_frontend_runtime_contract_is_executed_by_node_ci(self) -> None:
        runtime = (FRONTEND / "gw-energy-pilot-v036-runtime.js").read_text(
            encoding="utf-8"
        )
        node_test = (ROOT / "tests" / "frontend_v036_runtime.mjs").read_text(
            encoding="utf-8"
        )
        workflow = (WORKFLOWS / "quality.yml").read_text(encoding="utf-8")

        self.assertIn("export function flowAnimationDirections", runtime)
        self.assertIn("export function relevantStateObjectsChanged", runtime)
        self.assertIn("export function uiContextSignature", runtime)
        self.assertIn("flow directions match the rendered dashboard geometry", node_test)
        self.assertIn("unrelated Home Assistant state objects do not request a render", node_test)
        self.assertIn("actions/setup-node@v4", workflow)
        self.assertIn("node --test tests/frontend_v036_runtime.mjs", workflow)

    def test_release_layer_reconciles_existing_duplicate_cards(self) -> None:
        source = (FRONTEND / "gw-energy-pilot-v030.js").read_text(encoding="utf-8")

        self.assertIn("function reconcileBatteryPlanCards", source)
        self.assertIn(".ep-v031-card-windowbar, .ep-v028-window-controls", source)
        self.assertIn("if (card !== canonical) card.remove()", source)
        self.assertIn("reconcileBatteryPlanCards(root)", source)
        self.assertIn("__epV030RenderInstalled", source)


if __name__ == "__main__":
    unittest.main()
