"""Owner scenarios for the read-only, grid-first EMS design."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_control_decision import _load_module

ROOT = Path(__file__).resolve().parents[1]


class EMSMappingPreviewTests(unittest.TestCase):
    def setUp(self):
        self.module = _load_module()

    def preview(self, battery=0, grid=0, **kwargs):
        options = dict(p_batt=battery, p_grid=grid, battery_deadband=100,
                       grid_deadband=1000, max_power=15000)
        options.update(kwargs)
        return self.module.preview_hybrid_mapping(**options)

    def test_owner_self_consumption_examples_and_inclusive_grid_deadband(self):
        for battery, grid in ((0, 700), (500, 0), (300, 400), (-5426, 0),
                              (0, -540), (15000, 1000), (-15000, -1000)):
            with self.subTest(battery=battery, grid=grid):
                result = self.preview(battery, grid)
                self.assertEqual((result.mode, result.power_w), (1, 0))
        directed = self.preview(300, 400, grid_deadband=300)
        self.assertEqual((directed.mode, directed.power_w), (3, 300))

    def test_pause_is_explicit_and_wins_over_missing_inputs_and_ev(self):
        result = self.preview(None, None, explicit_pause=True, plan_ready=False, ev_active=True)
        self.assertEqual((result.mode, result.power_w, result.reason), (8, 0, "explicit_pause"))
        self.assertEqual(self.preview(0, 0).mode, 1)

    def test_charging_follows_planned_watts_with_and_without_ev(self):
        for ev in (False, True):
            for grid in (2900, -4000):
                result = self.preview(-8400, grid, ev_active=ev)
                self.assertEqual((result.mode, result.power_w), (11, 8400))
        self.assertIn("mode11_charge_during_planned_export", self.preview(-8400, -4000).validation_required)

    def test_measured_discharge_is_a_candidate_with_high_pv_test_still_open(self):
        for watts in (1000, 5000, 15000):
            result = self.preview(watts, -14500)
            self.assertEqual((result.mode, result.power_w), (3, watts))
            self.assertIn("mode3_pv_priority_at_ac_limit", result.validation_required)
        self.assertEqual(self.preview(5000, -14500, ev_active=True).mode, 8)
        self.assertEqual(self.preview(5000, 4000, ev_active=True).mode, 8)

    def test_ev_house_candidate_uses_live_load_minus_ev_and_never_ev_import_target(self):
        for battery in (-5000, -100, 0, 100, 700):
            result = self.preview(battery, 0, ev_active=True, load_power_w=12500, ev_power_w=11000)
            self.assertEqual((result.mode, result.power_w, result.house_reference_w), (5, 1500, 1500))
            self.assertIn("load_35172_ev_external_pv_boundary", result.validation_required)
            self.assertIn("mode5_pv_surplus_behavior", result.validation_required)
        # A 22 kW EV is valid: only the inverter/house allowance is capped.
        result = self.preview(700, 0, ev_active=True, load_power_w=23500, ev_power_w=22000)
        self.assertEqual((result.mode, result.power_w), (5, 1500))
        result = self.preview(700, 0, ev_active=True, load_power_w=10000, ev_power_w=11000)
        self.assertEqual((result.mode, result.power_w), (5, 0))

    def test_neutral_battery_outside_grid_band_is_not_mislabelled_pause(self):
        for battery in (-100, 0, 100):
            for grid, mode in ((1001, 9), (-1001, 10)):
                result = self.preview(battery, grid)
                self.assertEqual((result.mode, result.power_w), (mode, 1001))
                self.assertTrue(result.validation_required)
                ev = self.preview(battery, grid, ev_active=True)
                self.assertIsNone(ev.mode)
                self.assertEqual(ev.reason, "ev_net_only_action_unresolved")

    def test_invalid_or_missing_inputs_never_suggest_ev_auto(self):
        for invalid in (None, True, float("nan"), float("inf"), "unknown"):
            for field in ("p_batt", "p_grid"):
                with self.subTest(field=field, invalid=invalid):
                    self.assertIsNone(self.preview(**{field: invalid}).mode)
                    self.assertEqual(self.preview(ev_active=True, **{field: invalid}).mode, 8)
            for field in ("load_power_w", "ev_power_w"):
                options = dict(load_power_w=12500, ev_power_w=11000)
                options[field] = invalid
                self.assertEqual(self.preview(ev_active=True, **options).mode, 8)
        self.assertEqual(self.preview(ev_active=True, plan_ready=False).mode, 8)
        for field in ("battery_deadband", "grid_deadband", "max_power"):
            for value in (-1, None, True, float("nan"), float("inf")):
                self.assertEqual(self.preview(**{field: value}).reason, "invalid_mapping_limits")

    def test_power_caps_and_preview_only_result_contract(self):
        for battery, expected in ((-15000, 11), (15000, 3)):
            self.assertEqual(self.preview(battery, 20000, max_power=8000).power_w, 8000)
            self.assertEqual(self.preview(battery, 20000, max_power=20000).power_w, 15000)
            result = self.preview(battery, 20000)
            self.assertEqual(result.mode, expected)
            self.assertTrue(result.as_dict()["preview_only"])
            self.assertFalse(hasattr(result, "ready"))
            json.dumps(result.as_dict(), allow_nan=False)
        self.assertEqual(self.preview(5000, -10000, max_power=0).mode, 8)

    def test_cli_keeps_all_96_rows_and_never_uses_load_forecast_for_ev(self):
        header = "index\tP_batt\tP_grid\tP_Load\n"
        rows = "".join(f"slot-{i}\t0\t700\t700\n" for i in range(96))
        text = "EMHASS results\n" + header + rows + "Summary table for latest optimization results\nVariable\tValue\n"
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "plan.txt"
            source.write_text(text)
            result = subprocess.run([sys.executable, str(ROOT / "scripts/preview_ems_mapping.py"),
                                     "--plan", str(source), "--ev-active", "--ev-power", "11000"],
                                    capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        self.assertEqual(output["row_count"], 96)
        self.assertEqual(output["rows"][-1]["time"], "slot-95")
        self.assertTrue(all(row["proposed"]["reason"] == "waiting_for_ev_house_measurements"
                            for row in output["rows"]))


if __name__ == "__main__":
    unittest.main()
