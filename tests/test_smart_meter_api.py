"""Exercise strategy persistence and payloads without a Home Assistant server."""

from __future__ import annotations

import ast
import importlib
from math import isfinite
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

from test_control_decision import _load_module, PACKAGE_NAME


class SmartMeterStrategyApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        _load_module()
        self.const = importlib.import_module(f"{PACKAGE_NAME}.const")
        path = Path(__file__).resolve().parents[1] / "custom_components/gw_energypilot/smart_meter_api.py"
        tree = ast.parse(path.read_text())
        # Run the actual handler/helper bodies; HA owns their WebSocket decorators.
        nodes = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for node in nodes:
            node.decorator_list = []
        future = ast.parse("from __future__ import annotations").body
        namespace = {**vars(self.const), "isfinite": isfinite}
        exec(compile(ast.Module(body=future + nodes, type_ignores=[]), str(path), "exec"), namespace)
        self.api = SimpleNamespace(**{key: value for key, value in namespace.items() if key != "__name__"})
        self.controller = SimpleNamespace(enabled=True, async_evaluate=AsyncMock())
        self.entry = SimpleNamespace(
            entry_id="test-entry", domain=self.const.DOMAIN, data={"unrelated": "preserved"},
            options={"unchanged": 42}, runtime_data=SimpleNamespace(controller=self.controller))
        def update(entry, *, data):
            entry.data = data
        self.hass = SimpleNamespace(config_entries=SimpleNamespace(
            async_get_entry=lambda entry_id: self.entry,
            async_update_entry=Mock(side_effect=update)))
        self.connection = SimpleNamespace(send_result=Mock(), send_error=Mock())

    async def set_strategy(self, **values):
        await self.api.websocket_set_smart_meter(self.hass, self.connection, {
            "id": 1, "entry_id": self.entry.entry_id, **values})
        self.connection.send_error.assert_not_called()
        return self.connection.send_result.call_args.args[1]

    async def test_hybrid2_round_trip_preserves_other_config_and_reevaluates(self):
        self.assertIn("hybrid_2", self.const.CONTROL_STRATEGIES)
        result = await self.set_strategy(strategy="hybrid_2")
        self.assertEqual(result["strategy"], "hybrid_2")
        self.assertEqual(result["strategies"]["hybrid_2"], "Hybrid 2.0 Beta")
        self.assertTrue(result["enabled"])
        self.assertEqual(self.entry.data["unrelated"], "preserved")
        self.assertEqual(self.entry.options, {"unchanged": 42})
        self.assertTrue(self.entry.data[self.const.CONF_USE_GOODWE_SMART_METER])
        self.controller.async_evaluate.assert_awaited_once()
        # Fresh runtime/API payload after reload still resolves the persisted key.
        self.entry.runtime_data = None
        self.assertEqual(self.api._payload(self.entry)["strategy"], "hybrid_2")

    async def test_manual_ownership_is_retained_when_strategy_is_selected(self):
        self.controller.enabled = False
        await self.set_strategy(strategy="hybrid_2")
        self.controller.async_evaluate.assert_not_awaited()
        self.assertFalse(self.controller.enabled)

    async def test_hybrid3_round_trip_and_tibber_description(self):
        result = await self.set_strategy(strategy="hybrid_3")
        self.assertIn("hybrid_3", self.const.CONTROL_STRATEGIES)
        self.assertEqual(result["strategy"], "hybrid_3")
        self.assertEqual(result["strategies"]["hybrid_3"], "Hybrid 3.0 excl. EV")
        self.assertIn("Tibber Grid Rewards", result["hybrid_3_strategy"])
        self.assertEqual(self.entry.data["unrelated"], "preserved")
        self.assertEqual(self.entry.options, {"unchanged": 42})
        self.controller.async_evaluate.assert_awaited_once()
        self.entry.runtime_data = None
        self.assertEqual(self.api._payload(self.entry)["strategy"], "hybrid_3")

    async def test_switching_back_to_hybrid_preserves_existing_mapping_key(self):
        await self.set_strategy(strategy="hybrid_2")
        result = await self.set_strategy(strategy="hybrid")
        self.assertEqual(result["strategy"], "hybrid")
        self.assertTrue(result["enabled"])

    async def test_legacy_boolean_requests_still_resolve_to_grid_or_battery(self):
        for enabled, expected in ((True, "grid"), (False, "battery")):
            with self.subTest(enabled=enabled):
                result = await self.set_strategy(enabled=enabled)
                self.assertEqual(result["strategy"], expected)

    def test_missing_and_legacy_saved_values_never_opt_in_to_hybrid2(self):
        for saved, expected in (({}, "battery"),
                                ({self.const.CONF_USE_GOODWE_SMART_METER: False}, "battery"),
                                ({self.const.CONF_USE_GOODWE_SMART_METER: True}, "grid")):
            self.entry.data = saved
            self.assertEqual(self.api._control_strategy(self.entry), expected)


if __name__ == "__main__":
    unittest.main()
