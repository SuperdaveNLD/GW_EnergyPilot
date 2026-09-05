from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"
BROWSER = ROOT / "tests" / "browser"


class FrontendV041StableDomTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "gw-energy-pilot-v041.js").read_text(
            encoding="utf-8"
        )
        self.runtime = (FRONTEND / "gw-energy-pilot-v038-runtime.js").read_text(
            encoding="utf-8"
        )
        self.plan_data = (
            FRONTEND / "gw-energy-pilot-v027-battery-plan-data.js"
        ).read_text(encoding="utf-8")
        self.plan_core = (
            FRONTEND / "gw-energy-pilot-v027-battery-plan-core.js"
        ).read_text(encoding="utf-8")
        self.quick_actions = (FRONTEND / "gw-energy-pilot-v010.js").read_text(
            encoding="utf-8"
        )
        self.touch_hover = (FRONTEND / "gw-energy-pilot-v043.js").read_text(
            encoding="utf-8"
        )
        self.costfun = (FRONTEND / "gw-energy-pilot-v016.js").read_text(
            encoding="utf-8"
        )
        self.manual = (FRONTEND / "gw-energy-pilot-v021.js").read_text(
            encoding="utf-8"
        )
        self.controller = (INTEGRATION / "controller.py").read_text(
            encoding="utf-8"
        )
        self.sensor = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")

    def test_v041_bypasses_the_v040_render_settle_layer(self) -> None:
        self.assertIn(
            'import "./gw-energy-pilot-v039.js?v=1.3.0-beta.3"', self.source
        )
        self.assertNotIn('import "./gw-energy-pilot-v040.js', self.source)
        self.assertIn('const VERSION = "0.41"', self.source)

    def test_ordinary_hass_updates_patch_existing_dom(self) -> None:
        self.assertIn("function patchLiveDom(panel)", self.source)
        self.assertIn("function scheduleLivePatch(panel)", self.source)
        self.assertIn("this._hass = value", self.source)
        self.assertIn("scheduleLivePatch(this)", self.source)
        self.assertIn("context !== this.__epV041ContextSignature", self.source)
        self.assertIn("structure !== this.__epV041StructureSignature", self.source)
        self.assertIn("this._queueRender();", self.source)
        self.assertIn('main.dataset.epV041StableDom = "1"', self.source)
        self.assertNotIn("shadowRoot.innerHTML", self.source)
        self.assertNotIn("scrollTop =", self.source)
        self.assertNotIn("scrollLeft =", self.source)

    def test_host_properties_ignore_semantically_identical_assignments(self) -> None:
        self.assertIn("function plainJsonEqual(left, right)", self.source)
        self.assertIn("equal = Object.is", self.source)
        self.assertIn("function installReactiveNarrowProperty(PanelClass)", self.source)
        self.assertIn("installReactiveNarrowProperty(PanelClass)", self.source)
        self.assertIn("patchNarrowControlSurface(this, next)", self.source)
        self.assertIn(
            'installStableHostProperty(PanelClass, "panel", (value) => value, plainJsonEqual)',
            self.source,
        )
        self.assertIn("issue84StructuralProbe", (
            BROWSER / "test_frontend_stability.py"
        ).read_text(encoding="utf-8"))

    def test_battery_quick_actions_use_stable_live_state(self) -> None:
        self.assertIn("function patchBatteryQuickActions", self.source)
        self.assertIn("patchBatteryQuickActions(panel, root, automaticOn)", self.source)
        self.assertIn("this.__epV041RefreshLiveDom", self.source)
        self.assertIn("requestStableLiveRefresh(panel)", self.quick_actions)
        self.assertIn('button.setAttribute("aria-pressed"', self.quick_actions)
        self.assertNotIn(
            '.ep-battery-action[data-action="resume_auto"]:hover', self.touch_hover
        )

    def test_ems_setpoint_update_is_patched_in_place(self) -> None:
        base = (FRONTEND / "gw-energy-pilot.js").read_text(encoding="utf-8")
        browser = (BROWSER / "test_frontend_stability.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("last_ems_setpoint_updated_at", base)
        self.assertIn("lastEmsSetpointUpdate", self.source)
        self.assertIn("formatTimestamp(panel", self.source)
        self.assertIn("def exercise_setpoint_update", browser)
        self.assertIn("stableMetric", browser)

    def test_ev_protection_banner_is_stable_status_only_ui(self) -> None:
        self.assertIn("function installEvProtectionBanner(root)", self.source)
        self.assertIn("function patchEvProtectionBanner(panel, root)", self.source)
        self.assertIn("patchEvProtectionBanner(panel, root)", self.source)
        self.assertIn('banner.setAttribute("role", "status")', self.source)
        self.assertIn('banner.setAttribute("aria-live", "polite")', self.source)
        self.assertIn("ev_protection_state", self.source)
        self.assertIn("EV CHARGING · ANTI-DISCHARGE ACTIVE", self.source)
        self.assertIn("EV LAADT · ONTLAADBEVEILIGING ACTIEF", self.source)
        self.assertNotIn("ev-override", self.source)
        self.assertIn("def ev_protection_state(self)", self.controller)
        self.assertIn('"ev_protection_state": controller.ev_protection_state', self.sensor)
        self.assertIn("async_dispatcher_connect(", self.sensor)
        browser_test = (BROWSER / "test_frontend_stability.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("exercise_ev_protection_banner", browser_test)

    def test_configured_ev_charger_is_a_display_only_house_flow_branch(self) -> None:
        self.assertIn("function installEvFlowNode(root)", self.source)
        self.assertIn("function patchEvFlowNode(panel, root, snapshot)", self.source)
        self.assertIn("attrs.ev_charger_configured === true", self.source)
        self.assertIn("finiteValue(attrs.ev_power_w)", self.source)
        self.assertIn('className = "ep-flow-node ep-flow-ev"', self.source)
        self.assertIn('className = "ep-flow-link ep-link-ev idle"', self.source)
        self.assertIn("houseToEv", self.source)
        self.assertIn("evPartOfLoad", self.source)
        self.assertIn("installEvFlowNode(this.shadowRoot)", self.source)
        self.assertIn("_async_ev_power_updated", self.sensor)
        self.assertIn("power_value_w", self.sensor)

    def test_other_persistent_selectors_use_stable_live_state(self) -> None:
        self.assertIn("function patchCostFunctionSelector", self.source)
        self.assertIn("patchCostFunctionSelector(panel, root)", self.source)
        self.assertIn("requestStableLiveRefresh(panel)", self.costfun)
        self.assertIn("const activeRaw = activeRawValue(panel)", self.costfun)
        self.assertIn("panel.__epV016CostfunBusy", self.costfun)
        self.assertIn("const busyRaw = panel.__epV016CostfunBusy", self.source)
        self.assertIn("requestStableLiveRefresh(panel)", self.manual)
        self.assertIn("const liveAutomaticOn", self.manual)

    def test_connectivity_status_is_structural_once_and_patched_live(self) -> None:
        browser_test = (BROWSER / "test_frontend_stability.py").read_text(
            encoding="utf-8"
        )
        harness = (BROWSER / "frontend_harness.html").read_text(encoding="utf-8")
        self.assertIn("function ensureConnectivityStatus(panel, root)", self.source)
        self.assertIn("ensureConnectivityStatus(this, root)", self.source)
        self.assertIn("function patchConnectivityStatus(panel, root)", self.source)
        self.assertIn("patchConnectivityStatus(panel, root)", self.source)
        self.assertIn("actions.insertBefore(wrap, version || null)", self.source)
        self.assertIn("@media (hover: hover) and (pointer: fine)", self.source)
        self.assertNotIn("setPointerCapture", self.source)
        self.assertIn("exercise_connectivity_status", browser_test)
        self.assertIn('"connectivity_status"', harness)

    def test_soc_limit_display_falls_back_to_canonical_live_sources(self) -> None:
        self.assertIn("function socLimitValue(panel, kind)", self.source)
        self.assertIn(
            "optimizeAttributes(panel).battery_discharge_depth_on_grid_45356",
            self.source,
        )
        self.assertIn(
            "diagnosticConfigAttributes(panel).emhass_maximum_soc_pct",
            self.source,
        )
        self.assertIn("const value = socLimitValue(panel, kind)", self.source)

    def test_emhass_mapping_uses_backend_controller_decision(self) -> None:
        self.assertIn("attrs.controller_expected_mode", self.source)
        self.assertIn("attrs.controller_target_power", self.source)
        self.assertIn("attrs.controller_command", self.source)
        self.assertIn("localizedEmsMode(language(panel), expectedMode)", self.source)
        self.assertIn('command.startsWith("waiting_")', self.source)

    def test_v038_legacy_guards_are_disabled_only_for_v041(self) -> None:
        self.assertIn("function stableRuntimeActive(panel)", self.runtime)
        self.assertIn("!stableRuntime && interactionActive(this)", self.runtime)
        self.assertIn("!stableRuntime && shouldPreserveScroll(this)", self.runtime)
        self.assertIn("if (!stableRuntime) installInteractionGuard", self.runtime)
        self.assertIn("if (!stableRuntime) stabilizeScrollAfterRender", self.runtime)
        self.assertIn("this.__epV041StableRuntime = true", self.source)
        self.assertNotIn("setPointerCapture", self.source)
        self.assertNotIn("preventDefault", self.source)

    def test_plan_refresh_is_scoped_to_the_graph_card(self) -> None:
        self.assertIn("function requestPanelRefresh(panel)", self.plan_data)
        self.assertIn("panel.__epV041RefreshBatteryPlan()", self.plan_data)
        self.assertIn(
            "export function refreshBatteryPlanCard(panel)", self.plan_core
        )
        self.assertIn("refreshBatteryPlanCard(this)", self.plan_core)
        self.assertIn(
            "function schedulePlanRefresh(panel, backendForce = true)", self.source
        )
        self.assertIn("void loadChartData(panel, true, forceBackend)", self.source)
        self.assertIn("function executionHistorySignature", self.source)
        self.assertIn("schedulePlanRefresh(this, false)", self.source)
        self.assertIn("refreshBatteryPlanCard(this)", self.source)
        self.assertIn("function preserveInteractiveShell", self.plan_core)
        self.assertIn("child !== windowBar && child !== existingHead", self.plan_core)
        self.assertIn('existingHead?.querySelectorAll("[data-chart-range]")', self.plan_core)
        self.assertNotIn('addEventListener("pointerdown"', self.plan_core)
        self.assertNotIn("setPointerCapture", self.plan_core)
        self.assertNotIn("preventDefault", self.plan_core)

    def test_only_opt_in_flow_particles_may_animate(self) -> None:
        self.assertIn("animation: none !important", self.source)
        self.assertIn("transition: none !important", self.source)
        self.assertIn("scroll-behavior: auto !important", self.source)
        self.assertIn("touch-action: manipulation", self.source)
        self.assertIn("backdrop-filter: none !important", self.source)
        self.assertIn(".ep-v011-particles span", self.source)
        self.assertIn(".ep-v027-backdrop", self.source)
        self.assertIn("display: none !important", self.source)
        self.assertIn(".ep-dashboard-layout:not(.ep-animations-off)", self.source)
        self.assertIn('data-ep-v041-flow-status="active"', self.source)
        self.assertIn("animation-name: epV038HRight !important", self.source)
        self.assertIn("animation-name: epV038VUp !important", self.source)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.source)
        self.assertIn('input.disabled = false', self.source)
        self.assertIn('input.removeAttribute("aria-disabled")', self.source)
        self.assertIn("function isV041FlowParticle", self.plan_core)
        self.assertIn("releaseV041FlowParticle(element)", self.plan_core)
        self.assertNotIn(
            '".ep-flow-arrows, .ep-flow-live span, .ep-v011-particles, .ep-v011-particles span"',
            self.plan_core,
        )

    def test_browser_matrix_uses_one_deterministic_harness(self) -> None:
        browser_test = (BROWSER / "test_frontend_stability.py").read_text(
            encoding="utf-8"
        )
        wrapper = (BROWSER / "test_frontend_stability_v131.py").read_text(
            encoding="utf-8"
        )
        harness = (BROWSER / "frontend_harness.html").read_text(
            encoding="utf-8"
        )
        workflow = (
            ROOT / ".github" / "workflows" / "frontend-browser.yml"
        ).read_text(encoding="utf-8")
        self.assertIn('Profile("desktop-chromium"', browser_test)
        self.assertIn('Profile("ipad-webkit"', browser_test)
        self.assertIn('Profile("iphone-webkit"', browser_test)
        self.assertIn("telemetry_identity", browser_test)
        self.assertIn("exercise_plan_refresh", browser_test)
        self.assertIn('animation["flowParticleAnimations"] <= 0', browser_test)
        self.assertIn('animation["otherAnimations"] != 0', browser_test)
        self.assertIn('page.emulate_media(reduced_motion="reduce")', browser_test)
        self.assertIn("frontend_harness.html?entry=v131", wrapper)
        self.assertIn('stability.EXPECTED_ENTRYPOINT = "v131"', wrapper)
        self.assertIn(
            '"v050", "v051", "v100", "v101", "v110", "v130", "v131"].includes(requestedEntry)',
            harness,
        )
        self.assertIn("exercise_touch_controls", browser_test)
        self.assertIn("exercise_beta_tests", browser_test)
        self.assertIn("exercise_optimize_stability", browser_test)
        self.assertIn("exercise_host_property_press", browser_test)
        self.assertIn("exercise_live_copy_press", browser_test)
        self.assertIn("exercise_chart_size_press", browser_test)
        self.assertIn("exercise_chart_range_press", browser_test)
        self.assertIn("exercise_soc_slider_draft", browser_test)
        self.assertIn("exercise_emhass_overview_controls", browser_test)
        self.assertIn("exercise_emhass_mapping", browser_test)
        self.assertIn("window.__epBeforeNarrowMain", browser_test)
        self.assertIn(
            "window.__epPanel.shadowRoot.querySelector('main') !==",
            browser_test,
        )
        self.assertIn("test_frontend_stability_v131.py", workflow)
        self.assertIn("window.__epReady = new Promise", harness)
        self.assertNotIn("document.write", harness)
        self.assertFalse((BROWSER / "frontend_harness_v041.html").exists())
        self.assertIn("playwright install --with-deps chromium webkit", workflow)


if __name__ == "__main__":
    unittest.main()
