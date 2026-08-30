from __future__ import annotations

import importlib.util
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"

SPEC = importlib.util.spec_from_file_location(
    "gw_energypilot_pv_insight",
    INTEGRATION / "pv_insight.py",
)
assert SPEC and SPEC.loader
PV_INSIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PV_INSIGHT)


class PVInsightTests(unittest.TestCase):
    def test_power_units_are_normalized_to_watts(self) -> None:
        normalize = PV_INSIGHT.normalize_generation_power_w
        self.assertEqual(normalize("725", "W"), 725.0)
        self.assertEqual(normalize(1.25, "kW"), 1250.0)
        self.assertEqual(normalize(0.002, "MW"), 2000.0)
        self.assertEqual(normalize(500, "mW"), 0.5)

    def test_unsafe_or_non_generation_values_are_rejected(self) -> None:
        normalize = PV_INSIGHT.normalize_generation_power_w
        for value, unit in (
            (-1, "W"),
            ("unavailable", "W"),
            (math.nan, "W"),
            (math.inf, "W"),
            (True, "W"),
            (500, "A"),
            (500, None),
        ):
            with self.subTest(value=value, unit=unit):
                self.assertIsNone(normalize(value, unit))

    def test_only_available_sources_contribute_to_the_total(self) -> None:
        total = PV_INSIGHT.sum_generation_power_w
        self.assertEqual(total([1250.0, None, 750.25]), 2000.25)
        self.assertIsNone(total([None, None]))

    def test_external_master_switch_preserves_v045_configurations(self) -> None:
        enabled = PV_INSIGHT.external_sources_enabled
        keys = ("external_pv_entity_1", "external_pv_entity_2")
        self.assertFalse(
            enabled({}, enable_key="enable_external_pv", entity_keys=keys)
        )
        self.assertTrue(
            enabled(
                {"external_pv_entity_1": "sensor.roof_pv"},
                enable_key="enable_external_pv",
                entity_keys=keys,
            )
        )
        self.assertFalse(
            enabled(
                {
                    "enable_external_pv": False,
                    "external_pv_entity_1": "sensor.roof_pv",
                },
                enable_key="enable_external_pv",
                entity_keys=keys,
            )
        )
        self.assertTrue(
            enabled(
                {"enable_external_pv": True},
                enable_key="enable_external_pv",
                entity_keys=keys,
            )
        )

    def test_configuration_is_bounded_and_display_only(self) -> None:
        constants = (INTEGRATION / "const.py").read_text(encoding="utf-8")
        settings = (INTEGRATION / "settings_api.py").read_text(encoding="utf-8")
        sensor = (INTEGRATION / "sensor.py").read_text(encoding="utf-8")
        settings_frontend = (
            FRONTEND / "gw-energy-pilot-settings-v016.js"
        ).read_text(encoding="utf-8")

        for index in range(1, 5):
            self.assertIn(f'external_pv_entity_{index}', constants)
        self.assertNotIn('external_pv_entity_5', constants)
        self.assertIn('CONF_ENABLE_EXTERNAL_PV = "enable_external_pv"', constants)
        self.assertIn('SECTION_PV = "pv"', settings)
        self.assertIn('"purpose": "display_only"', sensor)
        self.assertIn(
            'const SECTION_ORDER = ["energypilot", "ev", "emhass", "pv", "goodwe"]',
            settings_frontend,
        )
        self.assertIn('field.type === "entity"', settings_frontend)
        self.assertIn('data-pv-external-group', settings_frontend)
        self.assertIn('syncExternalPvFields(form)', settings_frontend)

    def test_dashboard_uses_combined_pv_for_live_flow_without_scroll_writes(self) -> None:
        dashboard = (FRONTEND / "gw-energy-pilot.js").read_text(encoding="utf-8")
        stable = (FRONTEND / "gw-energy-pilot-v041.js").read_text(encoding="utf-8")

        self.assertIn('this._stateByKey("pv_generation_power")', dashboard)
        self.assertIn('pvGenerationSnapshot(panel)', stable)
        self.assertIn(
            'const pvSnapshot = pvGenerationSnapshot(panel);\n  const pv = pvSnapshot.power;',
            stable,
        )
        self.assertIn('patchFlow(panel, root, pv, load, grid, battery, soc)', stable)
        self.assertNotIn("scrollTop =", stable)
        self.assertNotIn("scrollLeft =", stable)


if __name__ == "__main__":
    unittest.main()
