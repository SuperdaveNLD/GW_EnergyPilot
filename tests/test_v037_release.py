from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class V039ReleaseTests(unittest.TestCase):
    def test_v039_behavior_layer_remains_wired_consistently(self) -> None:
        manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        release = (FRONTEND / "gw-energy-pilot-v039.js").read_text(encoding="utf-8")
        v038 = (FRONTEND / "gw-energy-pilot-v038.js").read_text(encoding="utf-8")
        runtime = (FRONTEND / "gw-energy-pilot-v038-runtime.js").read_text(encoding="utf-8")
        i18n = (FRONTEND / "gw-energy-pilot-v038-i18n.js").read_text(encoding="utf-8")
        version = manifest["version"]

        if version == "0.39":
            self.assertIn("gw-energy-pilot-v039.js?v=0.39-release1", init_source)
            self.assertIn('import "./gw-energy-pilot-v038.js?v=0.39-v0381"', release)
        elif version == "0.40":
            self.assertIn("gw-energy-pilot-v040.js?v=0.40-mobile-scroll1", init_source)
        elif version in {"0.41", "0.42", "0.43", "0.44", "0.45", "0.46", "0.47", "0.48", "0.49", "0.50"}:
            settings = (FRONTEND / "gw-energy-pilot-v041-emhass-settings.js").read_text(encoding="utf-8")
            v041 = (FRONTEND / "gw-energy-pilot-v041.js").read_text(encoding="utf-8")
            if version in {"0.42", "0.43", "0.44", "0.45", "0.46", "0.47", "0.48", "0.49", "0.50"}:
                v042 = (FRONTEND / "gw-energy-pilot-v042.js").read_text(encoding="utf-8")
                if version in {"0.43", "0.44", "0.45", "0.46", "0.47", "0.48", "0.49", "0.50"}:
                    v043 = (FRONTEND / "gw-energy-pilot-v043.js").read_text(encoding="utf-8")
                    if version in {"0.46", "0.47", "0.48", "0.49", "0.50"}:
                        if version in {"0.47", "0.48", "0.49", "0.50"}:
                            if version in {"0.48", "0.49", "0.50"}:
                                if version == "0.50":
                                    v050 = (FRONTEND / "gw-energy-pilot-v050.js").read_text(encoding="utf-8")
                                    self.assertIn(
                                        "gw-energy-pilot-v050.js?v=0.50-ev1",
                                        init_source,
                                    )
                                    self.assertIn(
                                        'import "./gw-energy-pilot-v049.js?v=0.50-ev1"',
                                        v050,
                                    )
                                if version in {"0.49", "0.50"}:
                                    v049 = (FRONTEND / "gw-energy-pilot-v049.js").read_text(encoding="utf-8")
                                    if version == "0.49":
                                        self.assertIn(
                                            "gw-energy-pilot-v049.js?v=0.50-ev1",
                                            init_source,
                                        )
                                    self.assertIn(
                                        'import "./gw-energy-pilot-v048.js?v=0.50-ev1"',
                                        v049,
                                    )
                                v048 = (FRONTEND / "gw-energy-pilot-v048.js").read_text(encoding="utf-8")
                                if version == "0.48":
                                    self.assertIn(
                                        "gw-energy-pilot-v048.js?v=0.50-ev1",
                                        init_source,
                                    )
                                self.assertIn(
                                    'import "./gw-energy-pilot-v047.js?v=0.50-ev1"',
                                    v048,
                                )
                            v047 = (FRONTEND / "gw-energy-pilot-v047.js").read_text(encoding="utf-8")
                            if version == "0.47":
                                self.assertIn(
                                    "gw-energy-pilot-v047.js?v=0.50-ev1",
                                    init_source,
                                )
                            self.assertIn(
                                'import "./gw-energy-pilot-v046.js?v=0.50-ev1"',
                                v047,
                            )
                        v046 = (FRONTEND / "gw-energy-pilot-v046.js").read_text(encoding="utf-8")
                        v045 = (FRONTEND / "gw-energy-pilot-v045.js").read_text(encoding="utf-8")
                        v044 = (FRONTEND / "gw-energy-pilot-v044.js").read_text(encoding="utf-8")
                        if version == "0.46":
                            self.assertIn(
                                "gw-energy-pilot-v046.js?v=0.50-ev1",
                                init_source,
                            )
                        self.assertIn(
                            'import "./gw-energy-pilot-v045.js?v=0.50-ev1"',
                            v046,
                        )
                        self.assertIn(
                            'import "./gw-energy-pilot-v044.js?v=0.50-ev1"',
                            v045,
                        )
                        self.assertIn(
                            'import "./gw-energy-pilot-v043.js?v=0.50-ev1"',
                            v044,
                        )
                        self.assertIn(
                            'import "./gw-energy-pilot-v042.js?v=0.50-ev1"',
                            v043,
                        )
                    elif version == "0.45":
                        self.assertIn("gw-energy-pilot-v045.js?v=0.45-integrated1", init_source)
                    elif version == "0.44":
                        v044 = (FRONTEND / "gw-energy-pilot-v044.js").read_text(encoding="utf-8")
                        self.assertIn(
                            "gw-energy-pilot-v044.js?v=0.44-optimize-stable1",
                            init_source,
                        )
                        self.assertIn(
                            'import "./gw-energy-pilot-v043.js?v=0.44-optimize-stable1"',
                            v044,
                        )
                    else:
                        self.assertIn("gw-energy-pilot-v043.js?v=0.43-touch1", init_source)
                else:
                    self.assertIn("gw-energy-pilot-v042.js?v=0.42-release1", init_source)
                expected_key = "0.50-ev1" if version in {"0.46", "0.47", "0.48", "0.49", "0.50"} else "0.42-emhass1"
                self.assertIn(
                    f'import "./gw-energy-pilot-v041-emhass-settings.js?v={expected_key}"',
                    v042,
                )
            else:
                self.assertIn("gw-energy-pilot-v041-emhass-settings.js?v=0.41-emhass1", init_source)
            stable_key = "0.50-ev1" if version in {"0.46", "0.47", "0.48", "0.49", "0.50"} else "0.41-stable1"
            self.assertIn(f'import "./gw-energy-pilot-v041.js?v={stable_key}"', settings)
            self.assertIn(f'import "./gw-energy-pilot-v039.js?v={stable_key}"', v041)
            self.assertNotIn('import "./gw-energy-pilot-v040.js', v041)
            self.assertIn(f'import "./gw-energy-pilot-v038.js?v={stable_key}"', release)
            self.assertIn(f'gw-energy-pilot-v038-runtime.js?v={stable_key}', v038)
        else:
            self.fail(f"Unsupported release version in regression: {version}")

        self.assertIn('const VERSION = "0.39"', release)
        self.assertIn("__epV039Installed", release)
        self.assertIn("energyPilotV039Render", release)
        i18n_key = "0.50-ev1" if version in {"0.46", "0.47", "0.48", "0.49", "0.50"} else "0.38-i18n1"
        self.assertIn(f'gw-energy-pilot-v038-i18n.js?v={i18n_key}', v038)
        self.assertIn("localizeV038Controller(this, root)", v038)
        self.assertIn('const VERSION = "0.38"', runtime)
        self.assertIn("__epV038Installed", runtime)
        self.assertIn('windowLabel: "Regelaar"', i18n)
        self.assertIn('manualKicker: "HANDMATIGE EMS-TEST"', i18n)
        self.assertIn('12: ["Batterijontlaadvermogen"', i18n)

    def test_release_has_executable_frontend_regression_tests(self) -> None:
        source = "".join((ROOT / "tests" / name).read_text(encoding="utf-8") for name in ("test_frontend_v038.mjs", "test_frontend_v038_controls.mjs", "test_frontend_v038_i18n.mjs"))
        self.assertIn("flowMotionMap", source)
        self.assertIn("resolveHousePower", source)
        self.assertIn("canonicalProfiles", source)
        self.assertIn("Batterijbesparing", source)
        self.assertIn("Battery Saver", source)
        self.assertIn("gw_energypilot/battery_saver/set", source)
        self.assertIn("buttons.every((button) => button.disabled === false)", source)
        self.assertIn("Batterijontlaadvermogen", source)

    def test_architecture_note_records_rebuilt_control_contract(self) -> None:
        notes = (ROOT / "docs" / "FRONTEND_CONTROL_REBUILD.md").read_text(encoding="utf-8")
        self.assertIn("v0.38 Beta release", notes)
        self.assertIn("visible text is never a control identity", notes)
        self.assertIn("Mobile touch/render contract", notes)
        self.assertIn("350 ms settle interval", notes)
        self.assertIn("PV production: left to right", notes)
        self.assertIn("No GoodWe register", notes)

    def test_dedicated_release_notes_exist(self) -> None:
        notes = ROOT / "docs" / "RELEASE_NOTES_V039.md"
        self.assertTrue(notes.is_file())
        source = notes.read_text(encoding="utf-8")
        self.assertIn("GW EnergyPilot v0.39 Beta", source)
        self.assertIn("hover", source.lower())
        self.assertIn("Dutch", source)
        self.assertTrue((ROOT / "docs" / "RELEASE_NOTES_V038.md").is_file())


if __name__ == "__main__":
    unittest.main()
