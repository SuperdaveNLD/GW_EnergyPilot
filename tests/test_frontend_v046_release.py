from pathlib import Path
import json
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"
CACHE_KEY = "1.2.0-stable1"


class FrontendV046ReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "gw-energy-pilot-v046.js").read_text(
            encoding="utf-8"
        )

    def test_v046_remains_below_the_active_v049_wrapper(self) -> None:
        manifest = json.loads(
            (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
        )
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")

        v048 = (FRONTEND / "gw-energy-pilot-v048.js").read_text(encoding="utf-8")
        active = (FRONTEND / "gw-energy-pilot-v047.js").read_text(encoding="utf-8")

        self.assertEqual(manifest["version"], "1.2.0")
        self.assertIn("gw-energy-pilot-v110.js?v=1.2.0-stable1", init_source)
        self.assertIn('import "./gw-energy-pilot-v047.js?v=1.2.0-stable1"', v048)
        self.assertIn(
            'import "./gw-energy-pilot-v046.js?v=1.2.0-stable1"',
            active,
        )
        self.assertIn(
            'import "./gw-energy-pilot-v045.js?v=1.2.0-stable1"',
            self.source,
        )
        self.assertIn('const VERSION = "0.46"', self.source)
        self.assertIn("PanelClass.prototype.__epV046Installed = true", self.source)

    def test_v046_subgraph_uses_the_active_v047_cache_key(self) -> None:
        statement_pattern = re.compile(r"^import\s+[\s\S]*?;", re.MULTILINE)
        dependency_pattern = re.compile(r'["\'](\./[^"\']+)["\']')
        pending = ["gw-energy-pilot-v046.js"]
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

        self.assertIn("gw-energy-pilot-settings-v016.js", visited)
        self.assertIn("gw-energy-pilot-v041.js", visited)
        self.assertIn("gw-energy-pilot.js", visited)

    def test_external_pv_switch_and_single_panel_are_wired(self) -> None:
        constants = (INTEGRATION / "const.py").read_text(encoding="utf-8")
        sensor = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
        settings = (FRONTEND / "gw-energy-pilot-settings-v016.js").read_text(
            encoding="utf-8"
        )

        self.assertIn('CONF_ENABLE_EXTERNAL_PV = "enable_external_pv"', constants)
        self.assertIn("external_sources_enabled(", sensor)
        self.assertIn('data-pv-external-group', settings)
        self.assertIn('class="ep-v016-external-inputs"', settings)
        self.assertIn("syncExternalPvFields(form)", settings)
        self.assertIn("input.disabled = !enabled", settings)
        self.assertTrue((ROOT / "docs" / "RELEASE_NOTES_V046.md").is_file())
        self.assertTrue((ROOT / "docs" / "CHANGELOG_V046.md").is_file())

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
