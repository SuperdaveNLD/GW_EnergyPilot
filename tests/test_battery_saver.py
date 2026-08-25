"""Unit tests for EnergyPilot Battery Saver policy helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "custom_components" / "gw_energypilot" / "battery_saver.py"
SPEC = importlib.util.spec_from_file_location("gw_energypilot_battery_saver", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
battery_saver = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = battery_saver
SPEC.loader.exec_module(battery_saver)


class BatterySaverTests(unittest.TestCase):
    def test_public_mode_order_and_mad_steve_name(self):
        payloads = battery_saver.battery_saver_mode_payloads()
        self.assertEqual(
            [item["key"] for item in payloads],
            ["mad_steve", "gold_rush", "balanced", "battery_saver"],
        )
        self.assertEqual(payloads[0]["label"], "Mad-Steve")
        self.assertTrue(payloads[2]["recommended"])

    def test_profiles_scale_virtual_costs_with_price_reference(self):
        mad = battery_saver.build_battery_saver_profile("mad_steve", 0.20)
        gold = battery_saver.build_battery_saver_profile("gold_rush", 0.20)
        balanced = battery_saver.build_battery_saver_profile("balanced", 0.20)
        saver = battery_saver.build_battery_saver_profile("battery_saver", 0.20)

        self.assertEqual(mad["battery_soc_deficit_cost"], 0.0)
        self.assertEqual(mad["battery_soc_surplus_cost"], 0.0)
        self.assertEqual(mad["battery_stress_cost"], 0.0)

        self.assertEqual(gold["battery_soc_deficit_threshold"], 0.05)
        self.assertEqual(gold["battery_soc_surplus_threshold"], 0.96)
        self.assertEqual(gold["battery_soc_surplus_cost"], 0.01)
        self.assertEqual(gold["battery_stress_cost"], 0.006)

        self.assertEqual(balanced["battery_soc_deficit_threshold"], 0.10)
        self.assertEqual(balanced["battery_soc_deficit_cost"], 0.01)
        self.assertEqual(balanced["battery_soc_surplus_threshold"], 0.95)
        self.assertEqual(balanced["battery_soc_surplus_cost"], 0.02)
        self.assertEqual(balanced["battery_stress_cost"], 0.016)

        self.assertEqual(saver["battery_soc_deficit_threshold"], 0.15)
        self.assertEqual(saver["battery_soc_deficit_cost"], 0.02)
        self.assertEqual(saver["battery_soc_surplus_threshold"], 0.90)
        self.assertEqual(saver["battery_soc_surplus_cost"], 0.05)
        self.assertEqual(saver["battery_stress_cost"], 0.04)
        self.assertEqual(saver["battery_stress_segments"], 10)

    def test_price_reference_prefers_positive_runtime_import_prices(self):
        reference = battery_saver.battery_saver_price_reference(
            {
                "a": -0.10,
                "b": 0.10,
                "c": 0.20,
                "d": 0.30,
            },
            {},
        )
        self.assertEqual(reference, 0.20)

    def test_price_reference_falls_back_to_emhass_config(self):
        reference = battery_saver.battery_saver_price_reference(
            {},
            {
                "load_peak_hours_cost": 0.32,
                "load_offpeak_hours_cost": 0.12,
            },
        )
        self.assertEqual(reference, 0.22)

    def test_apply_profile_preserves_unrelated_emhass_config(self):
        original = {
            "custom_setting": {"keep": True},
            "battery_soc_deficit_cost": 99,
        }
        updated, profile = battery_saver.apply_battery_saver_profile(
            original,
            "balanced",
            0.20,
        )
        self.assertEqual(updated["custom_setting"], original["custom_setting"])
        self.assertEqual(updated["battery_soc_deficit_cost"], 0.01)
        self.assertEqual(profile["mode"], "balanced")
        self.assertEqual(original["battery_soc_deficit_cost"], 99)

    def test_terminal_soc_is_clamped_to_hard_limits(self):
        self.assertEqual(battery_saver.clamp_soc_final(0.10, 0.23, 1.0), 0.23)
        self.assertEqual(battery_saver.clamp_soc_final(0.80, 0.23, 0.90), 0.80)
        self.assertEqual(battery_saver.clamp_soc_final(0.98, 0.23, 0.90), 0.90)
        with self.assertRaises(ValueError):
            battery_saver.clamp_soc_final(0.5, 0.8, 0.7)

    def test_stress_profiles_require_emhass_0181_when_version_is_known(self):
        self.assertFalse(battery_saver.emhass_supports_battery_stress("0.18.0"))
        self.assertTrue(battery_saver.emhass_supports_battery_stress("0.18.1"))
        self.assertTrue(battery_saver.emhass_supports_battery_stress("0.19.0-beta"))
        self.assertTrue(battery_saver.emhass_supports_battery_stress(None))

    def test_zero_cost_detection_is_behavioral(self):
        self.assertTrue(
            battery_saver.battery_saver_costs_are_zero(
                {
                    "battery_soc_deficit_cost": 0,
                    "battery_soc_surplus_cost": 0.0,
                    "battery_stress_cost": 0,
                }
            )
        )
        self.assertFalse(
            battery_saver.battery_saver_costs_are_zero(
                {
                    "battery_soc_deficit_cost": 0,
                    "battery_soc_surplus_cost": 0.01,
                    "battery_stress_cost": 0,
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
