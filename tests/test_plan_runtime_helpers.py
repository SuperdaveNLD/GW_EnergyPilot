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
                    "P_PV": 3600,
                    "P_Load": 1200,
                    "SOC_opt": 0.563,
                },
                {
                    "timestamp": "2026-08-25T04:15:00Z",
                    "P_batt": 2500,
                    "P_grid": -1200,
                    "P_PV": 900,
                    "P_Load": 2100,
                    "SOC_opt": 0.5,
                },
            ],
        }

        result = module.normalize_emhass_api_plan(payload)
        self.assertEqual(result["p_batt"][0]["value_w"], -4200.0)
        self.assertEqual(result["p_grid"][1]["value_w"], -1200.0)
        self.assertEqual(result["p_pv"][0]["value_w"], 3600.0)
        self.assertEqual(result["p_load"][1]["value_w"], 2100.0)
        self.assertEqual(result["soc_opt"][0]["value_pct"], 56.3)
        self.assertEqual(result["soc_opt"][1]["value_pct"], 50.0)
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

    def test_soc_opt_accepts_only_documented_fraction_range(self):
        rows = [
            {"timestamp": "2026-08-25T04:00:00Z", "P_batt": 0, "SOC_opt": 0},
            {"timestamp": "2026-08-25T04:15:00Z", "P_batt": 0, "SOC_opt": 1},
            {"timestamp": "2026-08-25T04:30:00Z", "P_batt": 0, "SOC_opt": -0.01},
            {"timestamp": "2026-08-25T04:45:00Z", "P_batt": 0, "SOC_opt": 1.01},
            {"timestamp": "2026-08-25T05:00:00Z", "P_batt": 0, "SOC_opt": 56},
            {"timestamp": "2026-08-25T05:15:00Z", "P_batt": 0, "SOC_opt": "nan"},
        ]

        result = module.normalize_emhass_api_plan({"status": "ok", "plan": rows})

        self.assertEqual(
            result["soc_opt"],
            [
                {"start": "2026-08-25T04:00:00+00:00", "value_pct": 0.0},
                {"start": "2026-08-25T04:15:00+00:00", "value_pct": 100.0},
            ],
        )

    def test_soc_opt_does_not_guess_custom_or_multi_battery_columns(self):
        result = module.normalize_emhass_api_plan(
            {
                "status": "ok",
                "plan": [
                    {
                        "timestamp": "2026-08-25T04:00:00Z",
                        "P_batt": 0,
                        "SOC_opt_0": 0.5,
                        "soc_batt_forecast": 50,
                    }
                ],
            }
        )

        self.assertEqual(result["soc_opt"], [])

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

    def test_selects_desired_soc_without_extrapolating(self):
        points = [
            {"start": "2026-08-25T04:00:00Z", "value_pct": 42},
            {"start": "2026-08-25T04:15:00Z", "value_pct": 55},
        ]
        self.assertEqual(
            module.plan_percentage_at(
                points,
                datetime(2026, 8, 25, 4, 20, tzinfo=timezone.utc),
                900,
            ),
            55.0,
        )
        self.assertIsNone(
            module.plan_percentage_at(
                points,
                datetime(2026, 8, 25, 4, 31, tzinfo=timezone.utc),
                900,
            )
        )

    def test_soc_targets_use_the_inferred_interval_end(self):
        point = {"start": "2026-08-25T04:00:00Z", "value_pct": 42}

        for step_seconds, expected in (
            (900, "2026-08-25T04:15:00+00:00"),
            (1800, "2026-08-25T04:30:00+00:00"),
            (3600, "2026-08-25T05:00:00+00:00"),
        ):
            with self.subTest(step_seconds=step_seconds):
                self.assertEqual(
                    module.soc_interval_end_points([point], step_seconds),
                    [
                        {
                            "start": "2026-08-25T04:00:00+00:00",
                            "target_at": expected,
                            "value_pct": 42.0,
                        }
                    ],
                )

        self.assertEqual(module.soc_interval_end_points([point], None), [])

    def test_active_soc_target_returns_end_of_its_own_slot(self):
        points = [
            {"start": "2026-08-25T04:00:00Z", "value_pct": 42},
            {"start": "2026-08-25T04:15:00Z", "value_pct": 55},
        ]

        value, target_at = module.plan_percentage_target_at(
            points,
            datetime(2026, 8, 25, 4, 7, tzinfo=timezone.utc),
            900,
        )
        self.assertEqual(value, 42.0)
        self.assertEqual(
            target_at,
            datetime(2026, 8, 25, 4, 15, tzinfo=timezone.utc),
        )
        self.assertIsNone(
            module.plan_percentage_target_at(
                points,
                datetime(2026, 8, 25, 4, 7, tzinfo=timezone.utc),
                None,
            )
        )

    def test_soc_interval_end_is_an_absolute_dst_safe_instant(self):
        points = [
            {"start": "2026-10-25T02:45:00+02:00", "value_pct": 60},
        ]

        self.assertEqual(
            module.soc_interval_end_points(points, 900)[0]["target_at"],
            "2026-10-25T01:00:00+00:00",
        )


if __name__ == "__main__":
    unittest.main()
