from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"
CACHE_KEY = "1.3.0-beta.1"


class FrontendV051ReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.release = (FRONTEND / "gw-energy-pilot-v051.js").read_text(
            encoding="utf-8"
        )
        self.history = (FRONTEND / "gw-energy-pilot-v051-history.js").read_text(
            encoding="utf-8"
        )

    def test_v051_feature_layer_and_presentation_remain_intact(self) -> None:
        self.assertIn(
            f'import "./gw-energy-pilot-v050.js?v={CACHE_KEY}"', self.release
        )
        self.assertIn(
            f'from "./gw-energy-pilot-v051-history.js?v={CACHE_KEY}"',
            self.release,
        )
        self.assertIn('const VERSION = "0.51"', self.release)
        self.assertIn("PanelClass.prototype.__epV051Installed = true", self.release)

    def test_complete_active_module_graph_has_one_cache_key(self) -> None:
        statement_pattern = re.compile(r"^import\s+[\s\S]*?;", re.MULTILINE)
        dependency_pattern = re.compile(r'["\'](\./[^"\']+)["\']')
        pending = ["gw-energy-pilot-v051.js"]
        visited: set[str] = set()
        while pending:
            name = pending.pop()
            if name in visited:
                continue
            visited.add(name)
            source = (FRONTEND / name).read_text(encoding="utf-8")
            for statement in statement_pattern.findall(source):
                match = dependency_pattern.search(statement)
                if match is None:
                    continue
                raw = match.group(1)
                dependency, separator, query = raw[2:].partition("?")
                self.assertEqual(
                    (separator, query),
                    ("?", f"v={CACHE_KEY}"),
                    f"stale active import in {name}: {raw}",
                )
                pending.append(dependency)
        for expected in (
            "gw-energy-pilot-v050.js",
            "gw-energy-pilot-v051-history.js",
            "gw-energy-pilot-v041.js",
            "gw-energy-pilot-v027-battery-plan-data.js",
            "gw-energy-pilot-v027-battery-plan-view.js",
            "gw-energy-pilot.js",
        ):
            self.assertIn(expected, visited)

    def test_release_wrapper_remains_presentation_only(self) -> None:
        for forbidden in (
            "addEventListener",
            "callService",
            "callWS",
            "_queueRender",
            "scrollTop",
            "scrollLeft",
            "setPointerCapture",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.release)

    def test_history_card_respects_stable_dom_and_native_scroll(self) -> None:
        self.assertIn("refreshHistoryCard(panel)", self.history)
        self.assertIn("existing?.dataset.epRenderKey", self.history)
        self.assertIn('querySelectorAll(".ep-v051-history-card")', self.history)
        self.assertIn("overflow:auto", self.history)
        self.assertIn("backdrop-filter:none!important", self.history)
        for forbidden in (
            "scrollTop =",
            "scrollLeft =",
            "setPointerCapture",
            "preventDefault",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.history)

    def test_chart_has_attribution_and_historical_wanted_soc(self) -> None:
        data = (FRONTEND / "gw-energy-pilot-v027-battery-plan-data.js").read_text(
            encoding="utf-8"
        )
        view = (FRONTEND / "gw-energy-pilot-v027-battery-plan-view.js").read_text(
            encoding="utf-8"
        )
        for key in (
            'panel._entityId?.("pv_generation_power")',
            'panel._entityId?.("total_load_power")',
            'panel._entityId?.("meter_total_power_fast")',
            "attributeActualRows",
            "historicalSocWantedRows",
        ):
            self.assertIn(key, data)
        for key in (
            'data-source-series="${key}"',
            "epV051UnknownHatch",
            "desiredSocPoints(data)",
            'data-history-points="${data.historicalSocWantedRows?.length || 0}"',
            'stroke-dasharray="7 5"',
        ):
            self.assertIn(key, view)

    def test_release_documentation_exists(self) -> None:
        self.assertTrue((ROOT / "docs" / "RELEASE_NOTES_V051.md").is_file())
        self.assertTrue((ROOT / "docs" / "CHANGELOG_V051.md").is_file())


if __name__ == "__main__":
    unittest.main()
