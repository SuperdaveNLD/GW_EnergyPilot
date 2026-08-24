"""Unit tests for the persistent grid-accounting model."""

from __future__ import annotations

from datetime import date
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "custom_components" / "gw_energypilot" / "accounting_model.py"

spec = importlib.util.spec_from_file_location("gw_energypilot_accounting_model", MODEL_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load accounting model")
model = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = model
spec.loader.exec_module(model)


class GridAccountingModelTests(unittest.TestCase):
    def test_prefers_extended_meter_pair_when_available(self):
        selected = model.select_meter_totals(
            {
                model.LEGACY_IMPORT_KEY: 100.0,
                model.LEGACY_EXPORT_KEY: 50.0,
                model.EXTENDED_IMPORT_KEY: 1513.4,
                model.EXTENDED_EXPORT_KEY: 1267.7,
            }
        )
        self.assertEqual(selected, (model.SOURCE_EXTENDED, 1513.4, 1267.7))

    def test_falls_back_to_legacy_when_extended_pair_is_unavailable(self):
        selected = model.select_meter_totals(
            {
                model.LEGACY_IMPORT_KEY: 100.0,
                model.LEGACY_EXPORT_KEY: 50.0,
            }
        )
        self.assertEqual(selected, (model.SOURCE_LEGACY, 100.0, 50.0))

    def test_active_extended_source_does_not_flap_to_legacy(self):
        selected = model.select_meter_totals(
            {
                model.LEGACY_IMPORT_KEY: 100.0,
                model.LEGACY_EXPORT_KEY: 50.0,
            },
            model.SOURCE_EXTENDED,
        )
        self.assertIsNone(selected)

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
        self.assertEqual(state.source_pair, model.SOURCE_LEGACY)

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

    def test_source_switch_rebaselines_without_cross_layout_delta(self):
        state = model.GridAccountingState(
            day="2026-08-23",
            today_import_kwh=1.2,
            today_export_kwh=0.8,
            last_import_total_kwh=100.0,
            last_export_total_kwh=50.0,
            source_pair=model.SOURCE_LEGACY,
            bootstrap_complete=True,
        )
        model.apply_meter_totals(
            state,
            date(2026, 8, 23),
            import_total_kwh=1513.4,
            export_total_kwh=1267.7,
            source_pair=model.SOURCE_EXTENDED,
        )
        self.assertEqual(state.today_import_kwh, 1.2)
        self.assertEqual(state.today_export_kwh, 0.8)
        self.assertEqual(state.last_import_total_kwh, 1513.4)
        self.assertEqual(state.last_export_total_kwh, 1267.7)
        self.assertEqual(state.source_pair, model.SOURCE_EXTENDED)

        model.apply_meter_totals(
            state,
            date(2026, 8, 23),
            import_total_kwh=1513.55,
            export_total_kwh=1267.95,
            source_pair=model.SOURCE_EXTENDED,
        )
        self.assertEqual(state.today_import_kwh, 1.35)
        self.assertEqual(state.today_export_kwh, 1.05)

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
            source_pair=model.SOURCE_LEGACY,
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

    def test_midnight_source_change_does_not_create_cross_layout_delta(self):
        state = model.GridAccountingState(
            day="2026-08-23",
            today_import_kwh=12.3,
            today_export_kwh=4.5,
            last_import_total_kwh=100.0,
            last_export_total_kwh=50.0,
            source_pair=model.SOURCE_LEGACY,
            bootstrap_complete=True,
        )
        model.apply_meter_totals(
            state,
            date(2026, 8, 24),
            import_total_kwh=1513.4,
            export_total_kwh=1267.7,
            source_pair=model.SOURCE_EXTENDED,
        )
        self.assertEqual(state.yesterday_import_kwh, 12.3)
        self.assertEqual(state.yesterday_export_kwh, 4.5)
        self.assertEqual(state.today_import_kwh, 0.0)
        self.assertEqual(state.today_export_kwh, 0.0)
        self.assertEqual(state.source_pair, model.SOURCE_EXTENDED)

    def test_startup_day_roll_discards_unknown_offline_delta(self):
        state = model.GridAccountingState(
            day="2026-08-23",
            today_import_kwh=8.0,
            today_export_kwh=2.0,
            last_import_total_kwh=100.0,
            last_export_total_kwh=50.0,
            source_pair=model.SOURCE_LEGACY,
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
        self.assertEqual(state.source_pair, model.SOURCE_LEGACY)
        self.assertFalse(state.bootstrap_complete)

    def test_recorder_bootstrap_seeds_existing_installation(self):
        state = model.GridAccountingState(source_pair=model.SOURCE_LEGACY)
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
            source_pair=model.SOURCE_EXTENDED,
            bootstrap_complete=True,
        )
        restored = model.GridAccountingState.from_dict(state.as_dict())
        self.assertEqual(restored, state)


if __name__ == "__main__":
    unittest.main()
