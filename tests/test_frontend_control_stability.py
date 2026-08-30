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
        self.manual = (FRONTEND / "gw-energy-pilot-v021.js").read_text(
            encoding="utf-8"
        )
        self.stable = (FRONTEND / "gw-energy-pilot-v041.js").read_text(
            encoding="utf-8"
        )
        self.settings_battery = (
            FRONTEND / "gw-energy-pilot-v031-battery-saver.js"
        ).read_text(encoding="utf-8")

    def test_v038_bypasses_failed_pointer_and_button_reuse_layers(self) -> None:
        self.assertIn("gw-energy-pilot-v038-runtime.js?v=", self.entry)
        self.assertIn('gw-energy-pilot-v034.js?v=0.51-h1', self.runtime)
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
        self.assertIn("function requestStrategyRefresh(panel)", self.strategy)
        self.assertIn("panel.__epV041RefreshStrategy", self.strategy)
        self.assertIn("requestStrategyRefresh(panel)", self.strategy)
        self.assertIn("updateStrategyVisualState(panel, true)", self.strategy)

    def test_custom_costs_are_editable_in_dashboard_and_settings(self) -> None:
        for source in (self.strategy, self.settings_battery):
            with self.subTest(source=source[:40]):
                self.assertIn("gw_energypilot/battery_saver/custom_set", source)
                self.assertIn("battery_soc_deficit_cost", source)
                self.assertIn("battery_soc_surplus_cost", source)
                self.assertIn("battery_stress_cost", source)
                self.assertIn("weight_battery_charge", source)
                self.assertIn("weight_battery_discharge", source)
                self.assertIn('type="number"', source)
                self.assertIn('min="0"', source)
                self.assertIn('step="0.000001"', source)

        self.assertIn('form[data-ep-v038-custom-form]', self.strategy)
        self.assertIn("shareBatterySaverData", self.strategy)
        self.assertIn('const CUSTOM_MODE = "custom"', self.settings_battery)
        self.assertIn("data-bs-custom-form", self.settings_battery)
        self.assertIn("shareBatterySaverData", self.settings_battery)

    def test_battery_strategy_typography_no_longer_uses_six_or_seven_px_copy(self) -> None:
        self.assertNotIn("font-size:6px", self.styles)
        self.assertNotIn("font-size:7px", self.styles)
        self.assertNotIn("font-size:6px", self.settings_battery)
        self.assertNotIn("font-size:7px", self.settings_battery)

    def test_manual_controls_compact_without_replacing_control_nodes(self) -> None:
        self.assertIn('pad.className = `ep-v021-manual-pad', self.manual)
        self.assertIn('class="ep-v021-mode-grid"${compact ? " hidden" : ""}', self.manual)
        self.assertIn('class="ep-v021-power-row"${compact ? " hidden" : ""}', self.manual)
        self.assertIn('manual.classList.toggle("compact", compact)', self.stable)
        self.assertIn("if (modeGrid) modeGrid.hidden = compact", self.stable)
        self.assertIn("if (powerRow) powerRow.hidden = compact", self.stable)
        self.assertNotIn("manual.remove()", self.stable)
        self.assertNotIn("manual.replaceWith", self.stable)

    def test_manual_controls_read_live_ownership_after_initial_lock(self) -> None:
        self.assertIn(
            'const liveAutomaticOn =\n        panel._stateByKey?.("automatic_control")?.state === "on";',
            self.manual,
        )
        self.assertIn(
            "if (slider.disabled || liveAutomaticOn || !liveControlsReady || panel.__epV021ManualBusy) return;",
            self.manual,
        )
        self.assertNotIn("if (slider && !locked)", self.manual)
        self.assertIn(
            'modeButton.setAttribute("aria-disabled", modeButton.disabled ? "true" : "false")',
            self.stable,
        )
        self.assertIn(
            'note.innerHTML = `<strong>${panel._escape(t.automaticOwner)}</strong>',
            self.stable,
        )
        self.assertIn(
            "if (automaticOn && panel.__epV021ManualMessage)",
            self.stable,
        )
        self.assertLess(
            self.stable.index("if (automaticOn) {", self.stable.index("const message = panel.__epV021ManualMessage")),
            self.stable.index("} else if (message?.text)"),
        )

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
        self.assertIn("function finishPointerInteraction", self.runtime)
        self.assertIn("function completeKeyboardInteraction", self.runtime)
        self.assertIn("function completeAllInteractions", self.runtime)
        self.assertIn("const INTERACTION_SAFETY_TIMEOUT_MS = 3000", self.runtime)
        self.assertIn("const TOUCH_SCROLL_THRESHOLD_PX = 8", self.runtime)
        self.assertIn("const TOUCH_SCROLL_SETTLE_MS = 350", self.runtime)
        self.assertIn("pointerFinishTimer", self.runtime)
        self.assertIn("pointerSafetyTimer", self.runtime)
        self.assertIn("keyboardSafetyTimer", self.runtime)
        self.assertIn("this.__epV038RenderDeferred = true", self.runtime)
        self.assertIn("function stableRuntimeActive(panel)", self.runtime)
        self.assertLess(
            self.runtime.index("if (!stableRuntime && interactionActive(this))"),
            self.runtime.index("previousRender.call(this)"),
        )

    def test_v038_touch_scroll_owns_viewport_until_gesture_settles(self) -> None:
        self.assertIn('const touchPointer = event.pointerType === "touch"', self.runtime)
        self.assertIn(
            "if (!touchPointer && !eventInteractiveElement(event)) return;",
            self.runtime,
        )
        self.assertIn("state.touchMoved = false", self.runtime)
        self.assertIn("state.touchMoved = true", self.runtime)
        self.assertIn("finishPointerInteraction(panel, true)", self.runtime)
        self.assertIn("function touchInteractionActive", self.runtime)
        self.assertIn("function stabilizeScrollAfterRender(panel, snapshots)", self.runtime)
        self.assertIn("if (touchInteractionActive(panel)) return;", self.runtime)
        self.assertIn("stabilizeScrollAfterRender(this, scrollSnapshots)", self.runtime)

        move_start = self.runtime.index('globalThis.addEventListener?.(\n    "pointermove"')
        move_end = self.runtime.index('globalThis.addEventListener?.(\n    "pointerup"', move_start)
        pointermove = self.runtime[move_start:move_end]
        self.assertIn("state.touchMoved = true", pointermove)
        self.assertNotIn("completePointerInteraction(panel)", pointermove)
        self.assertNotIn("preventDefault", pointermove)
        self.assertNotIn("setPointerCapture", self.runtime)

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
        self.assertIn("export function flowVisualMap", self.model)
        self.assertIn("const direction = flowMotionMap", self.model)
        self.assertIn('status: "unknown"', self.model)
        self.assertIn('status: "idle"', self.model)
        self.assertIn('status: "active"', self.model)


if __name__ == "__main__":
    unittest.main()
