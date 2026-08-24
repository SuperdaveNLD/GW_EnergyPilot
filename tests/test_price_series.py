"""Unit tests for the dashboard price-series model."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "custom_components" / "gw_energypilot" / "price_series.py"

spec = importlib.util.spec_from_file_location("gw_energypilot_price_series", MODEL_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load price-series model")
model = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)


class DashboardPriceSeriesTests(unittest.TestCase):
    def test_builds_sorted_market_buy_and_sell_points(self):
        points = model.build_dashboard_price_points(
            {
                "2026-08-24T01:00:00+02:00": 0.31,
                "2026-08-24T00:00:00+02:00": 0.21,
            },
            {
                "2026-08-24T01:00:00+02:00": 0.255,
                "2026-08-24T00:00:00+02:00": 0.155,
            },
            buy_adder=0.03,
            sell_deduction=0.025,
        )

        self.assertEqual(
            [point["start"] for point in points],
            [
                "2026-08-24T00:00:00+02:00",
                "2026-08-24T01:00:00+02:00",
            ],
        )
        self.assertEqual(points[0]["market_price"], 0.18)
        self.assertEqual(points[0]["buy_price"], 0.21)
        self.assertEqual(points[0]["sell_price"], 0.155)

    def test_preserves_negative_market_prices(self):
        points = model.build_dashboard_price_points(
            {"2026-08-24T02:00:00+02:00": -0.02},
            {"2026-08-24T02:00:00+02:00": -0.055},
            buy_adder=0.01,
            sell_deduction=0.025,
        )

        self.assertEqual(points[0]["market_price"], -0.03)

    def test_uses_one_effective_series_when_the_other_is_missing(self):
        points = model.build_dashboard_price_points(
            {"2026-08-24T00:00:00+02:00": 0.25},
            {"2026-08-24T01:00:00+02:00": 0.19},
            buy_adder=0.05,
            sell_deduction=0.01,
        )

        self.assertEqual(points[0]["market_price"], 0.20)
        self.assertIsNone(points[0]["sell_price"])
        self.assertEqual(points[1]["market_price"], 0.20)
        self.assertIsNone(points[1]["buy_price"])

    def test_ignores_invalid_or_naive_timestamps_and_non_finite_prices(self):
        points = model.build_dashboard_price_points(
            {
                "not-a-date": 0.2,
                "2026-08-24T00:00:00": 0.2,
                "2026-08-24T00:15:00+02:00": float("nan"),
                "2026-08-24T00:30:00+02:00": 0.3,
            },
            {},
            buy_adder=0.0,
            sell_deduction=0.0,
        )

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]["start"], "2026-08-24T00:30:00+02:00")


if __name__ == "__main__":
    unittest.main()
