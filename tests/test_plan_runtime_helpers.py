"""Tests for persistent EMHASS plan normalization and time selection."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "custom_components" / "gw_energypilot" / "battery_plan.py"

spec = importlib.util.spec_from_file_location("gw_energypilot_battery_plan_v033", MODULE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load battery-plan helpers")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class PersistentPlanHelperTests(unittest.TestCase):
    def test_normalizes_official_emhass_plan(self):
        payload = {
            "status": "ok",
            "generated_at": "2026-08-25T04:00:00Z",
            "emhass_schema_version": "1.0",
            "plan": [
                {
                    "timestamp": "2026-08-25T04:00:00Z",
                    "P_batt": -4200,
                    "P_grid": 1800,
                },
                {
                    "timestamp": "2026-08-25T04:15:00Z",
                    "P_batt": 2500,
                    "P_grid": -1200,
                },
            ],
        }

        result = module.normalize_emhass_api_plan(payload)
        self.assertEqual(result["p_batt"][0]["value_w"], -4200.0)
        self.assertEqual(result["p_grid"][1]["value_w"], -1200.0)
        self.assertEqual(result["p_batt"][0]["start"], "2026-08-25T04:00:00+00:00")

    def test_api_plan_does_not_guess_missing_battery_column(self):
        result = module.normalize_emhass_api_plan(
            {
                "status": "ok",
                "plan": [
                    {"timestamp": "2026-08-25T04:00:00Z", "P_grid": 5000},
                ],
            }
        )
        self.assertEqual(result["p_batt"], [])
        self.assertEqual(result["p_grid"][0]["value_w"], 5000.0)

    def test_infers_fifteen_minute_step(self):
        points = [
            {"start": "2026-08-25T04:00:00Z", "value_w": -1000},
            {"start": "2026-08-25T04:15:00Z", "value_w": 0},
            {"start": "2026-08-25T04:30:00Z", "value_w": 1000},
        ]
        self.assertEqual(module.infer_plan_step_seconds(points), 900)

    def test_selects_current_step_without_extrapolating_after_plan_end(self):
        points = [
            {"start": "2026-08-25T04:00:00Z", "value_w": -1000},
            {"start": "2026-08-25T04:15:00Z", "value_w": 2000},
        ]
        step = module.infer_plan_step_seconds(points)

        self.assertEqual(
            module.plan_value_at(
                points,
                datetime(2026, 8, 25, 4, 20, tzinfo=timezone.utc),
                step,
            ),
            2000.0,
        )
        self.assertIsNone(
            module.plan_value_at(
                points,
                datetime(2026, 8, 25, 4, 31, tzinfo=timezone.utc),
                step,
            )
        )

    def test_plan_valid_until_is_last_step_boundary(self):
        points = [
            {"start": "2026-08-25T04:00:00Z", "value_w": -1000},
            {"start": "2026-08-25T04:15:00Z", "value_w": 2000},
        ]
        valid_until = module.plan_valid_until(points, 900)
        self.assertEqual(
            valid_until,
            datetime(2026, 8, 25, 4, 30, tzinfo=timezone.utc),
        )


if __name__ == "__main__":
    unittest.main()
