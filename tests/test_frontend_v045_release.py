from pathlib import Path
import json
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"
CACHE_KEY = "0.45-integrated1"


class FrontendV045ReleaseTests(unittest.TestCase):
    def test_manifest_panel_and_presentation_are_v045(self) -> None:
        manifest = json.loads(
            (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
        )
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        release = (FRONTEND / "gw-energy-pilot-v045.js").read_text(encoding="utf-8")

        self.assertEqual(manifest["version"], "0.45")
        self.assertIn(
            "gw-energy-pilot-v045.js?v=0.45-integrated1", init_source
        )
        self.assertIn('const VERSION = "0.45"', release)
        self.assertIn("__epV045Installed", release)
        self.assertIn(
            'import "./gw-energy-pilot-v044.js?v=0.45-integrated1"', release
        )

    def test_complete_active_module_graph_has_fresh_v045_cache_key(self) -> None:
        statement_pattern = re.compile(r"^import\s+[\s\S]*?;", re.MULTILINE)
        dependency_pattern = re.compile(r'["\'](\./[^"\']+)["\']')
        pending = ["gw-energy-pilot-v045.js"]
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

        self.assertIn("gw-energy-pilot.js", visited)
        self.assertIn("gw-energy-pilot-settings-v016.js", visited)
        self.assertIn("gw-energy-pilot-v038-strategy.js", visited)
        self.assertIn("gw-energy-pilot-v041.js", visited)

    def test_v045_release_scope_and_docs_are_present(self) -> None:
        strategy = (FRONTEND / "gw-energy-pilot-v038-strategy.js").read_text(
            encoding="utf-8"
        )
        stable = (FRONTEND / "gw-energy-pilot-v041.js").read_text(
            encoding="utf-8"
        )
        sensor = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")

        self.assertIn("input.dataset.epSocDraft = input.value", strategy)
        self.assertIn("const displayValue", stable)
        self.assertIn("pvGenerationSnapshot", stable)
        self.assertIn("GWPVGenerationPowerSensor", sensor)
        self.assertTrue((ROOT / "docs" / "RELEASE_NOTES_V045.md").is_file())
        self.assertTrue((ROOT / "docs" / "CHANGELOG_V045.md").is_file())


if __name__ == "__main__":
    unittest.main()
