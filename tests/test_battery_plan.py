"""Tests for battery-plan chart normalization."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "custom_components" / "gw_energypilot" / "battery_plan.py"

spec = importlib.util.spec_from_file_location("gw_energypilot_battery_plan", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load battery-plan helpers")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class BatteryPlanTests(unittest.TestCase):
    def test_parses_standard_emhass_forecasts(self):
        points = module.normalize_emhass_forecasts(
            "sensor.p_batt_forecast",
            {
                "forecasts": [
                    {"date": "2026-08-24T13:00:00+02:00", "p_batt_forecast": "-4200"},
                    {"date": "2026-08-24T14:00:00+02:00", "p_batt_forecast": "3500"},
                ]
            },
        )

        self.assertEqual(
            points,
            [
                {"start": "2026-08-24T13:00:00+02:00", "value_w": -4200.0},
                {"start": "2026-08-24T14:00:00+02:00", "value_w": 3500.0},
            ],
        )

    def test_custom_entity_id_selects_custom_value_key(self):
        points = module.normalize_emhass_forecasts(
            "sensor.my_battery_plan",
            {
                "forecasts": [
                    {"date": "2026-08-24T13:00:00Z", "my_battery_plan": 1250},
                ]
            },
        )

        self.assertEqual(points[0]["value_w"], 1250.0)
        self.assertEqual(points[0]["start"], "2026-08-24T13:00:00+00:00")

    def test_accepts_conservative_value_fallback(self):
        points = module.normalize_emhass_forecasts(
            "sensor.custom_plan",
            {
                "forecasts": [
                    {"start": "2026-08-24T13:00:00+02:00", "value": "-2500.5"},
                ]
            },
        )

        self.assertEqual(points[0]["value_w"], -2500.5)

    def test_invalid_rows_are_ignored_and_duplicate_timestamp_uses_latest(self):
        points = module.normalize_emhass_forecasts(
            "sensor.p_batt_forecast",
            {
                "forecasts": [
                    None,
                    {"date": "invalid", "p_batt_forecast": 10},
                    {"date": "2026-08-24T13:00:00+02:00", "p_batt_forecast": "nan"},
                    {"date": "2026-08-24T14:00:00+02:00", "p_batt_forecast": 1000},
                    {"date": "2026-08-24T14:00:00+02:00", "p_batt_forecast": 2000},
                ]
            },
        )

        self.assertEqual(
            points,
            [{"start": "2026-08-24T14:00:00+02:00", "value_w": 2000.0}],
        )

    def test_nonnegative_number_rejects_invalid_or_negative_values(self):
        self.assertEqual(module.nonnegative_number("4.2"), 4.2)
        self.assertIsNone(module.nonnegative_number(-1))
        self.assertIsNone(module.nonnegative_number("unknown"))


if __name__ == "__main__":
    unittest.main()
