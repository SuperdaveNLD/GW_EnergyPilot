"""Tests for bounded persistent controller execution evidence."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
CUSTOM_COMPONENTS = ROOT / "custom_components"
PACKAGE_DIR = CUSTOM_COMPONENTS / "gw_energypilot"
PACKAGE_NAME = "custom_components.gw_energypilot"


class FakeStore:
    data_by_key: dict[str, dict] = {}
    fail_load = False
    fail_save = False

    def __class_getitem__(cls, _item):
        return cls

    def __init__(self, _hass, _version, key):
        self.key = key

    async def async_load(self):
        if self.fail_load:
            raise OSError("simulated storage load failure")
        return self.data_by_key.get(self.key)

    async def async_save(self, data):
        if self.fail_save:
            raise OSError("simulated storage failure")
        self.data_by_key[self.key] = data


def _load_module():
    for name in list(sys.modules):
        if name == "custom_components" or name.startswith(PACKAGE_NAME):
            del sys.modules[name]
        elif name == "homeassistant" or name.startswith("homeassistant."):
            del sys.modules[name]
    custom_components = types.ModuleType("custom_components")
    custom_components.__path__ = [str(CUSTOM_COMPONENTS)]
    sys.modules["custom_components"] = custom_components
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_DIR)]
    package.__package__ = PACKAGE_NAME
    sys.modules[PACKAGE_NAME] = package
    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []
    sys.modules["homeassistant"] = homeassistant
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    sys.modules["homeassistant.core"] = core
    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    sys.modules["homeassistant.helpers"] = helpers
    storage = types.ModuleType("homeassistant.helpers.storage")
    storage.Store = FakeStore
    sys.modules["homeassistant.helpers.storage"] = storage
    return importlib.import_module(f"{PACKAGE_NAME}.execution_history")


class ExecutionHistoryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        FakeStore.data_by_key = {}
        FakeStore.fail_load = False
        FakeStore.fail_save = False
        self.module = _load_module()
        self.now = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)

    def history(self, entry="entry-1"):
        return self.module.GWEnergyPilotExecutionHistory(
            object(), entry, now_fn=lambda: self.now
        )

    async def test_event_survives_restart_with_nested_evidence(self):
        first = self.history()
        self.assertEqual(first.revision, 0)
        await first.async_append(
            {
                "occurred_at": self.now,
                "plan": {"p_batt_w": -3000, "soc_opt_pct": 55},
                "outcome": {"expected_mode": 9, "verification_status": "verified"},
            }
        )
        restored = self.history()
        await restored.async_restore()
        rows = await restored.async_history()
        self.assertEqual(restored.revision, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["plan"]["p_batt_w"], -3000)
        self.assertEqual(rows[0]["outcome"]["verification_status"], "verified")
        self.assertTrue(rows[0]["event_id"].endswith(":1"))

    async def test_revision_advances_for_each_append(self):
        history = self.history()
        await history.async_restore()
        self.assertEqual(history.revision, 0)
        await history.async_append({"occurred_at": self.now})
        await history.async_append({"occurred_at": self.now + timedelta(minutes=1)})
        self.assertEqual(history.revision, 2)

    async def test_retention_and_count_cap_are_both_enforced(self):
        history = self.history()
        self.module.EXECUTION_HISTORY_LIMIT = 3
        await history.async_append({"occurred_at": self.now - timedelta(days=8)})
        for minutes in range(5):
            await history.async_append(
                {"occurred_at": self.now - timedelta(minutes=minutes)}
            )
        rows = await history.async_history()
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["occurred_at"] >= (self.now - timedelta(days=7)).isoformat() for row in rows))

    async def test_dst_fold_instants_remain_distinct_utc_events(self):
        history = self.history()
        await history.async_append({"occurred_at": "2026-10-25T02:30:00+02:00"})
        await history.async_append({"occurred_at": "2026-10-25T02:30:00+01:00"})
        rows = await history.async_history()
        self.assertEqual(
            [row["occurred_at"] for row in rows],
            ["2026-10-25T00:30:00+00:00", "2026-10-25T01:30:00+00:00"],
        )

    async def test_store_failure_never_raises_into_control(self):
        history = self.history()
        FakeStore.fail_save = True
        await history.async_append({"occurred_at": self.now, "outcome": {"expected_mode": 9}})
        rows = await history.async_history()
        self.assertEqual(len(rows), 1)

    async def test_load_failure_and_corrupt_sequence_do_not_block_restore(self):
        FakeStore.fail_load = True
        failed = self.history("failed-load")
        await failed.async_restore()
        self.assertEqual(await failed.async_history(), [])

        FakeStore.fail_load = False
        FakeStore.data_by_key["gw_energypilot.execution.corrupt"] = {
            "history": [
                {
                    "occurred_at": self.now.isoformat(),
                    "sequence": "not-a-number",
                    "actual": {"battery_power_w": float("nan")},
                }
            ]
        }
        restored = self.history("corrupt")
        await restored.async_restore()
        rows = await restored.async_history()
        self.assertEqual(rows[0]["sequence"], "not-a-number")
        self.assertIsNone(rows[0]["actual"]["battery_power_w"])
        appended = await restored.async_append({"occurred_at": self.now})
        self.assertEqual(appended["sequence"], 1)


if __name__ == "__main__":
    unittest.main()
