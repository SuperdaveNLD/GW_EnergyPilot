"""Unit tests for the persistent grid-accounting model."""

from __future__ import annotations

from datetime import date
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = (
    ROOT
    / "custom_components"
    / "gw_energypilot"
    / "accounting_model.py"
)

spec = importlib.util.spec_from_file_location("gw_energypilot_accounting_model", MODEL_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load accounting model")
model = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)


class GridAccountingModelTests(unittest.TestCase):
    def test_first_sample_establishes_baseline_without_fake_energy(self):
        state = model.GridAccountingState(day="2026-08-23")

        model.apply_meter_totals(
            state,
            date(2026, 8, 23),
            import_total_kwh=100.0,
            export_total_kwh=50.0,
        )

        self.assertEqual(state.today_import_kwh, 0.0)
        self.assertEqual(state.today_export_kwh, 0.0)
        self.assertEqual(state.last_import_total_kwh, 100.0)
        self.assertEqual(state.last_export_total_kwh, 50.0)

    def test_same_day_lifetime_deltas_accumulate(self):
        state = model.GridAccountingState(day="2026-08-23")
        model.apply_meter_totals(
            state,
            date(2026, 8, 23),
            import_total_kwh=100.0,
            export_total_kwh=50.0,
        )
        model.apply_meter_totals(
            state,
            date(2026, 8, 23),
            import_total_kwh=100.125,
            export_total_kwh=50.075,
        )

        self.assertEqual(state.today_import_kwh, 0.125)
        self.assertEqual(state.today_export_kwh, 0.075)

    def test_counter_decrease_rebaselines_without_negative_energy(self):
        state = model.GridAccountingState(day="2026-08-23")
        model.apply_meter_totals(
            state,
            date(2026, 8, 23),
            import_total_kwh=100.0,
            export_total_kwh=50.0,
        )
        model.apply_meter_totals(
            state,
            date(2026, 8, 23),
            import_total_kwh=5.0,
            export_total_kwh=2.0,
        )
        model.apply_meter_totals(
            state,
            date(2026, 8, 23),
            import_total_kwh=5.2,
            export_total_kwh=2.1,
        )

        self.assertEqual(state.today_import_kwh, 0.2)
        self.assertEqual(state.today_export_kwh, 0.1)

    def test_normal_midnight_rollover_preserves_yesterday(self):
        state = model.GridAccountingState(
            day="2026-08-23",
            today_import_kwh=12.3,
            today_export_kwh=4.5,
            last_import_total_kwh=100.0,
            last_export_total_kwh=50.0,
            bootstrap_complete=True,
        )

        model.apply_meter_totals(
            state,
            date(2026, 8, 24),
            import_total_kwh=100.1,
            export_total_kwh=50.05,
        )

        self.assertEqual(state.yesterday_import_kwh, 12.3)
        self.assertEqual(state.yesterday_export_kwh, 4.5)
        self.assertEqual(state.today_import_kwh, 0.1)
        self.assertEqual(state.today_export_kwh, 0.05)
        self.assertTrue(state.bootstrap_complete)

    def test_startup_day_roll_discards_unknown_offline_delta(self):
        state = model.GridAccountingState(
            day="2026-08-23",
            today_import_kwh=8.0,
            today_export_kwh=2.0,
            last_import_total_kwh=100.0,
            last_export_total_kwh=50.0,
            bootstrap_complete=True,
        )

        changed = model.roll_to_day(state, date(2026, 8, 24))

        self.assertTrue(changed)
        self.assertEqual(state.yesterday_import_kwh, 8.0)
        self.assertEqual(state.yesterday_export_kwh, 2.0)
        self.assertEqual(state.today_import_kwh, 0.0)
        self.assertEqual(state.today_export_kwh, 0.0)
        self.assertIsNone(state.last_import_total_kwh)
        self.assertIsNone(state.last_export_total_kwh)
        self.assertFalse(state.bootstrap_complete)

    def test_recorder_bootstrap_seeds_existing_installation(self):
        state = model.GridAccountingState()

        seeded = model.seed_daily_totals(
            state,
            date(2026, 8, 23),
            today_import_kwh=14.66,
            today_export_kwh=1.25,
            yesterday_import_kwh=22.4,
            yesterday_export_kwh=3.1,
        )

        self.assertTrue(seeded)
        self.assertEqual(state.day, "2026-08-23")
        self.assertEqual(state.today_import_kwh, 14.66)
        self.assertEqual(state.today_export_kwh, 1.25)
        self.assertEqual(state.yesterday_import_kwh, 22.4)
        self.assertEqual(state.yesterday_export_kwh, 3.1)
        self.assertTrue(state.bootstrap_complete)

    def test_persistence_round_trip(self):
        state = model.GridAccountingState(
            day="2026-08-23",
            today_import_kwh=12.345678,
            today_export_kwh=4.5,
            yesterday_import_kwh=9.1,
            yesterday_export_kwh=2.3,
            last_import_total_kwh=1234.567,
            last_export_total_kwh=345.678,
            bootstrap_complete=True,
        )

        restored = model.GridAccountingState.from_dict(state.as_dict())

        self.assertEqual(restored, state)


if __name__ == "__main__":
    unittest.main()
