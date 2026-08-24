"""Tests for the opt-in bounded GW EnergyPilot debug session."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "custom_components" / "gw_energypilot" / "debug_log.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("gw_energypilot_debug_log_test", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load debug_log.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DebugLogTests(unittest.TestCase):
    def test_capture_is_disabled_by_default(self):
        module = _load_module()
        log = module.GWEnergyPilotDebugLog(limit=10)

        log.record("controller", "ignored", {"value": 1})

        self.assertFalse(log.snapshot()["enabled"])
        self.assertEqual(log.snapshot()["events"], [])

    def test_enable_starts_fresh_session_with_baseline(self):
        module = _load_module()
        log = module.GWEnergyPilotDebugLog(limit=10)
        log.enable({"battery_soc": 42})

        snapshot = log.snapshot()
        self.assertTrue(snapshot["enabled"])
        self.assertIsNotNone(snapshot["started_at"])
        self.assertEqual(snapshot["event_count"], 1)
        self.assertEqual(
            snapshot["events"][0]["data"]["baseline"]["battery_soc"],
            42,
        )

    def test_stop_retains_events_but_stops_capture(self):
        module = _load_module()
        log = module.GWEnergyPilotDebugLog(limit=10)
        log.enable({})
        log.record("goodwe", "poll_success", {"ems_mode": 8})
        log.disable({"ems_mode": 8})
        count_after_stop = log.snapshot()["event_count"]

        log.record("goodwe", "ignored_after_stop", {})

        snapshot = log.snapshot()
        self.assertFalse(snapshot["enabled"])
        self.assertIsNotNone(snapshot["stopped_at"])
        self.assertEqual(snapshot["event_count"], count_after_stop)
        self.assertEqual(snapshot["events"][-1]["event"], "stopped")

    def test_buffer_is_bounded_and_counts_dropped_events(self):
        module = _load_module()
        log = module.GWEnergyPilotDebugLog(limit=10)
        log.enable({})
        for index in range(15):
            log.record("source", "state_changed", {"index": index})

        snapshot = log.snapshot()
        self.assertEqual(snapshot["event_count"], 10)
        self.assertEqual(snapshot["dropped_events"], 6)
        self.assertEqual(snapshot["events"][-1]["data"]["index"], 14)

    def test_new_enable_discards_previous_session(self):
        module = _load_module()
        log = module.GWEnergyPilotDebugLog(limit=10)
        log.enable({"session": 1})
        log.record("test", "old", {})
        log.disable({})

        log.enable({"session": 2})

        snapshot = log.snapshot()
        self.assertTrue(snapshot["enabled"])
        self.assertEqual(snapshot["event_count"], 1)
        self.assertEqual(
            snapshot["events"][0]["data"]["baseline"]["session"],
            2,
        )


if __name__ == "__main__":
    unittest.main()
