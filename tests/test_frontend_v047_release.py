from pathlib import Path
import json
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"
CACHE_KEY = "1.0.1-beta3"


class FrontendV047ReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "gw-energy-pilot-v047.js").read_text(
            encoding="utf-8"
        )

    def test_v047_remains_below_the_active_v049_wrapper(self) -> None:
        manifest = json.loads(
            (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
        )
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")

        v049 = (FRONTEND / "gw-energy-pilot-v049.js").read_text(encoding="utf-8")
        active = (FRONTEND / "gw-energy-pilot-v048.js").read_text(encoding="utf-8")

        self.assertEqual(manifest["version"], "1.0.1-beta.3")
        self.assertIn("gw-energy-pilot-v101.js?v=1.0.1-beta3", init_source)
        self.assertIn('import "./gw-energy-pilot-v048.js?v=1.0.1-beta3"', v049)
        self.assertIn(
            'import "./gw-energy-pilot-v047.js?v=1.0.1-beta3"',
            active,
        )
        self.assertIn(
            'import "./gw-energy-pilot-v046.js?v=1.0.1-beta3"',
            self.source,
        )
        self.assertIn('const VERSION = "0.47"', self.source)
        self.assertIn("PanelClass.prototype.__epV047Installed = true", self.source)

    def test_complete_active_module_graph_has_fresh_v047_cache_key(self) -> None:
        statement_pattern = re.compile(r"^import\s+[\s\S]*?;", re.MULTILINE)
        dependency_pattern = re.compile(r'["\'](\./[^"\']+)["\']')
        pending = ["gw-energy-pilot-v047.js"]
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

        self.assertIn("gw-energy-pilot-v046.js", visited)
        self.assertIn("gw-energy-pilot-v031-battery-saver.js", visited)
        self.assertIn("gw-energy-pilot-v038-strategy.js", visited)
        self.assertIn("gw-energy-pilot.js", visited)

    def test_custom_battery_release_scope_is_wired_and_documented(self) -> None:
        battery_saver = (INTEGRATION / "battery_saver.py").read_text(encoding="utf-8")
        api = (INTEGRATION / "battery_saver_api.py").read_text(encoding="utf-8")
        settings = (FRONTEND / "gw-energy-pilot-v031-battery-saver.js").read_text(
            encoding="utf-8"
        )
        strategy = (FRONTEND / "gw-energy-pilot-v038-strategy.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("CUSTOM_BATTERY_COST_KEYS", battery_saver)
        self.assertIn('"gw_energypilot/battery_saver/custom_set"', api)
        self.assertIn("data-bs-custom-form", settings)
        self.assertIn("data-ep-v038-custom-form", strategy)
        self.assertTrue((ROOT / "docs" / "RELEASE_NOTES_V047.md").is_file())
        self.assertTrue((ROOT / "docs" / "CHANGELOG_V047.md").is_file())

    def test_release_wrapper_is_presentation_only(self) -> None:
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
                self.assertNotIn(forbidden, self.source)


if __name__ == "__main__":
    unittest.main()
