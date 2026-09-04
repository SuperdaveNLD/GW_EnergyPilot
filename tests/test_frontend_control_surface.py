"""Static architecture contract for the permanent issue #84 control surface."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "custom_components" / "gw_energypilot" / "frontend"


class FrontendControlSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.component = (FRONTEND / "ep-control-surface.js").read_text(
            encoding="utf-8"
        )
        cls.base = (FRONTEND / "gw-energy-pilot.js").read_text(encoding="utf-8")
        cls.layout = (FRONTEND / "gw-energy-pilot-v008.js").read_text(
            encoding="utf-8"
        )
        cls.stable = (FRONTEND / "gw-energy-pilot-v041.js").read_text(
            encoding="utf-8"
        )
        cls.optimize = (FRONTEND / "gw-energy-pilot-v044.js").read_text(
            encoding="utf-8"
        )

    def test_lit_surface_has_fixed_operational_children(self) -> None:
        self.assertIn("extends LitElement", self.component)
        self.assertIn('["ep-control-surface",', self.component)
        for tag in (
            "ep-battery-actions",
            "ep-automatic-control",
            "ep-emhass-strategy",
            "ep-battery-strategy",
            "ep-optimize-action",
            "ep-manual-ems-controls",
        ):
            self.assertEqual(self.component.count(f"<{tag}"), 1, tag)
            self.assertIn(f'["{tag}",', self.component)

    def test_controls_use_native_declarative_click_only(self) -> None:
        self.assertIn('<button type="button"', self.component)
        self.assertIn("@click=", self.component)
        self.assertNotIn('role="button"', self.component)
        for forbidden in (
            "touchend",
            "ontouch",
            "setPointerCapture",
            "releasePointerCapture",
        ):
            self.assertNotIn(forbidden, self.component)
        self.assertNotRegex(
            self.component,
            re.compile(r"@pointerdown\s*=|addEventListener\(\s*[\"']pointerdown"),
        )

    def test_touch_targets_and_native_scroll_contract_are_explicit(self) -> None:
        self.assertRegex(self.component, re.compile(r"min-width:\s*44px"))
        self.assertRegex(self.component, re.compile(r"min-height:\s*44px"))
        self.assertRegex(self.component, re.compile(r"touch-action:\s*manipulation"))
        self.assertRegex(self.component, re.compile(r"touch-action:\s*pan-y"))
        self.assertIn(":focus-visible", self.component)
        self.assertIn("pointer-events: none", self.component)
        self.assertNotIn("transition:", self.component)
        self.assertNotIn("animation:", self.component)
        self.assertNotIn("backdrop-filter", self.component)

    def test_header_automatic_status_is_compact_and_not_a_touch_target(self) -> None:
        self.assertIn('class="status ep-automatic-status ${statusClass}"', self.base)
        self.assertRegex(
            self.base,
            re.compile(
                r"\.status\.ep-automatic-status\s*\{[^}]*"
                r"padding:\s*4px 7px;[^}]*font-size:\s*9px;"
            ),
        )
        self.assertRegex(
            self.base,
            re.compile(
                r"\.status\.ep-automatic-status \.dot\s*\{[^}]*"
                r"width:\s*5px;[^}]*height:\s*5px;"
            ),
        )

    def test_surface_overlays_card_window_controls_when_expanded(self) -> None:
        window_controls = (
            FRONTEND / "gw-energy-pilot-v031-window-controls.js"
        ).read_text(encoding="utf-8")
        self.assertIn("position:relative; z-index:70", window_controls)
        self.assertRegex(
            self.component,
            re.compile(
                r"ep-control-surface\s*\{[^}]*position:\s*relative;[^}]*"
                r"z-index:\s*80;"
            ),
        )

    def test_every_operational_group_uses_the_same_state_machine(self) -> None:
        for state in ("idle", "pending", "acknowledged", "error"):
            self.assertIn(f'"{state}"', self.component)
        self.assertIn("class EpAcknowledgedControl", self.component)
        self.assertIn("_beginRequest", self.component)
        self.assertIn("_checkAcknowledgement", self.component)
        self.assertIn("aria-busy", self.component)
        self.assertIn("aria-pressed", self.component)

    def test_backend_model_not_full_hass_is_passed_to_children(self) -> None:
        self.assertIn("buildControlSurfaceModel", self.component)
        self.assertIn("Object.freeze", self.component)
        self.assertNotRegex(
            self.component,
            re.compile(r"\.hass\s*=|(?:^|\s)hass:\s*\{", re.MULTILINE),
        )

    def test_structural_render_preserves_the_connected_surface(self) -> None:
        self.assertIn("_commitStructuralRender", self.base)
        self.assertIn("data-ep-control-anchor", self.base)
        self.assertIn("ep-control-surface", self.base)
        self.assertIn("existingSurfaceContainer", self.base)
        self.assertIn('classList.contains("ep-dashboard-layout")', self.base)
        self.assertNotIn("this.shadowRoot.innerHTML =", self.base)
        self.assertIn("existingSurface.isConnected", self.base)

    def test_surface_is_one_compact_fixed_dashboard_card(self) -> None:
        self.assertLess(
            self.layout.index('{ id: "grid"'),
            self.layout.index('id: "controls"'),
        )
        self.assertLess(
            self.layout.index('id: "controls"'),
            self.layout.index('{ id: "battery"'),
        )
        self.assertIn('selector: "ep-control-surface"', self.layout)
        self.assertIn("fixed: true, toggleable: false", self.layout)
        self.assertIn("mergeStoredOrder", self.layout)
        self.assertIn("__epV008PlaceControlSurface", self.layout)
        self.assertIn('dataset.epFixedCard === "true"', self.layout)
        window_controls = (
            FRONTEND / "gw-energy-pilot-v031-window-controls.js"
        ).read_text(encoding="utf-8")
        self.assertIn('card.dataset.epFixedCard === "true"', window_controls)
        self.assertIn('grid-template-columns:repeat(2,minmax(0,1fr))', self.component)
        self.assertIn('class="ep-control-selectors"', self.component)
        self.assertIn('class="ep-compact-selector"', self.component)
        self.assertIn(
            '.ep-compact-selector:not([open]) > .ep-compact-selector-menu',
            self.component,
        )
        self.assertIn('data-control-id="emhass-selector"', self.component)
        self.assertIn('data-control-id="battery-selector"', self.component)
        self.assertIn('class="ep-manual-disclosure"', self.component)

    def test_stable_layer_mounts_and_updates_one_surface(self) -> None:
        self.assertIn('import {', self.stable)
        self.assertIn('from "./ep-control-surface.js?v=1.3.0-beta.2"', self.stable)
        self.assertIn("mountEnergyPilotControlSurface", self.stable)
        self.assertIn("refreshEnergyPilotControlSurface", self.stable)
        self.assertIn("__epControlSurfaceArchitecture", self.stable)
        self.assertIn("patchNarrowControlSurface", self.stable)

    def test_legacy_operational_creators_are_disabled_not_duplicated(self) -> None:
        for name in (
            "gw-energy-pilot-v010.js",
            "gw-energy-pilot-v016.js",
            "gw-energy-pilot-v021.js",
            "gw-energy-pilot-v038.js",
            "gw-energy-pilot-v038-strategy.js",
        ):
            source = (FRONTEND / name).read_text(encoding="utf-8")
            self.assertIn("__epControlSurfaceArchitecture", source, name)
        self.assertIn("__epControlSurfaceArchitecture", self.base)
        self.assertIn("__epControlSurfaceArchitecture", self.optimize)
        localization = (FRONTEND / "gw-energy-pilot-v026.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('closest("ep-control-surface")', localization)
        self.assertIn('!note.closest("ep-control-surface")', localization)
        hybrid_note = (FRONTEND / "gw-energy-pilot-v048.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('closest("ep-control-surface")', hybrid_note)
        for name in ("gw-energy-pilot-v024.js", "gw-energy-pilot-v028.js"):
            historical_note = (FRONTEND / name).read_text(encoding="utf-8")
            self.assertIn('closest("ep-control-surface")', historical_note, name)

        legacy_soc = (FRONTEND / "gw-energy-pilot-v011.js").read_text(
            encoding="utf-8"
        )
        start = legacy_soc.index("function installSocSliders")
        guard = legacy_soc.index(
            "if (panel.__epControlSurfaceArchitecture) return;", start
        )
        self.assertLess(guard - start, 420)

    def test_emhass_overview_cost_function_reflects_confirmed_state(self) -> None:
        legacy = (FRONTEND / "gw-energy-pilot-v015.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("button.dataset.emhassOverviewCostfun = value", legacy)
        self.assertIn('button.setAttribute("aria-pressed", "false")', legacy)
        self.assertIn('.ep-v015-costfun-button[aria-pressed="true"]', legacy)
        self.assertIn(
            '".panel-card.emhass .ep-v016-costfun, .panel-card.emhass .ep-v015-costfun"',
            self.stable,
        )
        self.assertIn("patchCostFunctionSelector(panel, root);", self.stable)

    def test_lit_profile_presentation_has_single_dom_owner(self) -> None:
        self.assertIn('class="ep-v038-managed"', self.component)
        for metadata in (
            "minimum_soc_pct",
            "maximum_soc_pct",
            "deficit_threshold_pct",
            "surplus_threshold_pct",
            "deficit_cost_factor_pct",
            "surplus_cost_factor_pct",
            "stress_cost_factor_pct",
            "anti_churn_cost_factor_pct",
        ):
            self.assertIn(metadata, self.component)

        for name, function in (
            ("gw-energy-pilot-v038-i18n.js", "localizeStrategyProfiles"),
            ("gw-energy-pilot-v038-strategy.js", "updateStrategyVisualState"),
            ("gw-energy-pilot-v041.js", "patchStrategy"),
        ):
            source = (FRONTEND / name).read_text(encoding="utf-8")
            start = source.index(f"function {function}")
            guard = source.index(
                "if (panel.__epControlSurfaceArchitecture) return;", start
            )
            self.assertLess(guard - start, 160, name)

    def test_trace_covers_physical_device_acceptance_events(self) -> None:
        combined = self.component + self.base
        for event in (
            "pointerdown",
            "pointermove",
            "pointerup",
            "pointercancel",
            "click",
            "servicecall-start",
            "servicecall-end",
            "hass-state-publication",
            "structural-render",
        ):
            self.assertIn(f'"{event}"', combined)
        self.assertIn("isConnected", self.component)
        self.assertIn("nodeIdentity", self.component)


if __name__ == "__main__":
    unittest.main()
