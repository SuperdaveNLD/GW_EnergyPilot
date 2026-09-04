from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "custom_components" / "gw_energypilot" / "frontend"


class FrontendBetaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "ep-beta-tests.js").read_text(encoding="utf-8")
        self.v041 = (FRONTEND / "gw-energy-pilot-v041.js").read_text(
            encoding="utf-8"
        )

    def test_page_is_mounted_from_the_stable_functional_layer(self) -> None:
        self.assertIn(
            'from "./ep-beta-tests.js?v=1.3.0-beta.1"',
            self.v041,
        )
        self.assertIn("mountEnergyPilotControlSurface(this, this.shadowRoot);", self.v041)
        self.assertIn("mountEnergyPilotBetaTests(this, this.shadowRoot);", self.v041)
        self.assertLess(
            self.v041.index("mountEnergyPilotControlSurface(this, this.shadowRoot);"),
            self.v041.index("mountEnergyPilotBetaTests(this, this.shadowRoot);"),
        )

    def test_menu_entry_and_all_native_control_variants_exist(self) -> None:
        self.assertIn('title.textContent = "Beta tests"', self.source)
        self.assertIn('className = "ep-beta-tests-menu"', self.source)
        for control in (
            "lit-button",
            "listener-button",
            "icon-button",
            "shadow-button",
            "checkbox-switch",
            "label-switch",
            "native-select",
            "native-range",
        ):
            self.assertIn(f'key: "{control}"', self.source)
            self.assertIn(f'"{control}"', self.source)

    def test_clean_comparison_methods_are_exposed(self) -> None:
        for method in (
            "method-native-click",
            "method-pointerup-direct",
            "method-pointerup-delegated",
            "method-click-fallback",
            "method-pointerup-dedupe",
        ):
            self.assertIn(f'key: "{method}"', self.source)
            self.assertIn(f'data-beta-control="{method}"', self.source)
        self.assertIn("CLICK_FALLBACK_MS = 120", self.source)
        self.assertIn("CLICK_DEDUPE_MS = 700", self.source)
        self.assertIn("MOVE_THRESHOLD_PX = 12", self.source)
        self.assertIn("fallback_actions", self.source)
        self.assertIn("pointer_actions", self.source)
        self.assertIn("deduped", self.source)

    def test_event_measurement_does_not_rerender_during_click_synthesis(self) -> None:
        record_body = self.source.split("  _record(event) {", 1)[1].split(
            "\n  _action(", 1
        )[0]
        self.assertIn("this._metricsBuffer", record_body)
        self.assertIn("this._recentBuffer", record_body)
        self.assertIn("this._scheduleDisplayFlush()", record_body)
        self.assertNotIn("this.metrics =", record_body)
        self.assertNotIn("this.recent =", record_body)
        self.assertNotIn("queueMicrotask", record_body)
        self.assertIn("setTimeout(() => this._finishPointer", record_body)
        self.assertIn("DISPLAY_SETTLE_MS = 650", self.source)
        self.assertIn("methods: collect(METHOD_DEFINITIONS)", self.source)

    def test_diagnostics_track_native_events_and_action_completion(self) -> None:
        for metric in (
            "pointerdown",
            "pointermove",
            "pointerup",
            "pointercancel",
            "click",
            "change",
            "input",
            "actions",
        ):
            self.assertIn(f'"{metric}"', self.source)
        self.assertIn("event.isTrusted", self.source)
        self.assertIn("this.isConnected", self.source)
        self.assertIn("globalThis.__epBetaTests", self.source)

    def test_page_is_local_only_and_does_not_add_touch_adapters(self) -> None:
        for forbidden in (
            ".callService(",
            ".callWS(",
            "preventDefault(",
            "setPointerCapture(",
            "releasePointerCapture(",
            ".click()",
            'addEventListener("touchstart"',
            'addEventListener("touchend"',
        ):
            self.assertNotIn(forbidden, self.source)
        self.assertIn("no_home_assistant_calls: true", self.source)
        self.assertIn("touch-action:manipulation", self.source)
        self.assertIn("min-height:48px", self.source)

    def test_same_test_node_is_reused_across_structural_renders(self) -> None:
        self.assertIn("panel.__epPermanentBetaTests", self.source)
        self.assertIn("if (!tests.isConnected)", self.source)
        self.assertIn("tests.hidden = !open", self.source)
        self.assertIn("ep-beta-tests[hidden]", self.source)
        self.assertNotIn("main.innerHTML", self.source)
        self.assertNotIn("root.innerHTML", self.source)


if __name__ == "__main__":
    unittest.main()
