from pathlib import Path
import json
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"
CACHE_KEY = "1.3.0-beta.4"


class FrontendV049ReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "gw-energy-pilot-v049.js").read_text(
            encoding="utf-8"
        )

    def test_v049_remains_below_the_active_v051_wrapper(self) -> None:
        manifest = json.loads(
            (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
        )
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        active = (FRONTEND / "gw-energy-pilot-v051.js").read_text(encoding="utf-8")
        v050 = (FRONTEND / "gw-energy-pilot-v050.js").read_text(encoding="utf-8")

        self.assertEqual(manifest["version"], "1.3.0-beta.4")
        self.assertIn("gw-energy-pilot-v131.js?v=1.3.0-beta.4", init_source)
        self.assertIn(
            f'import "./gw-energy-pilot-v050.js?v={CACHE_KEY}"',
            active,
        )
        self.assertIn(
            f'import "./gw-energy-pilot-v049.js?v={CACHE_KEY}"',
            v050,
        )
        self.assertIn(
            f'import "./gw-energy-pilot-v048.js?v={CACHE_KEY}"',
            self.source,
        )
        self.assertIn('const VERSION = "0.49"', self.source)
        self.assertIn("PanelClass.prototype.__epV049Installed = true", self.source)

    def test_complete_active_module_graph_has_one_fresh_cache_key(self) -> None:
        statement_pattern = re.compile(r"^import\s+[\s\S]*?;", re.MULTILINE)
        dependency_pattern = re.compile(r'["\'](\./[^"\']+)["\']')
        pending = ["gw-energy-pilot-v049.js"]
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

        self.assertIn("gw-energy-pilot-v048.js", visited)
        self.assertIn("gw-energy-pilot-v041.js", visited)
        self.assertIn("gw-energy-pilot-v038-i18n.js", visited)
        self.assertIn("gw-energy-pilot-v027-battery-plan-core.js", visited)
        self.assertIn("gw-energy-pilot.js", visited)

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

    def test_release_documentation_exists(self) -> None:
        self.assertTrue((ROOT / "docs" / "RELEASE_NOTES_V049.md").is_file())
        self.assertTrue((ROOT / "docs" / "CHANGELOG_V049.md").is_file())


if __name__ == "__main__":
    unittest.main()
