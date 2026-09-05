from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"


class PlanRefreshWiringTests(unittest.TestCase):
    def test_successful_optimization_publishes_plan_revision(self) -> None:
        source = (INTEGRATION / "orchestrator_v033.py").read_text(encoding="utf-8")
        active = (INTEGRATION / "orchestrator_v044.py").read_text(encoding="utf-8")
        init_source = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")

        self.assertIn("from .orchestrator_v044 import GWEnergyPilotOrchestrator", init_source)
        self.assertIn("from .orchestrator_v033 import", active)
        self.assertIn("self.plan_revision = 0", source)
        self.assertIn("self.plan_revision += 1", source)
        self.assertIn("await plan_runtime.async_refresh", source)
        self.assertIn("async_dispatcher_send(self.hass, self.signal)", source)

    def test_chart_payload_contains_plan_revision(self) -> None:
        source = (INTEGRATION / "battery_price_api.py").read_text(encoding="utf-8")

        self.assertIn('"plan_revision": int(getattr(orchestrator, "plan_revision", 0) or 0)', source)
        self.assertIn('"chart_schema_version": 7', source)
        self.assertIn('"chart_time": build_chart_time_payload(', source)
        self.assertIn('"battery_soc_plan": _battery_soc_plan_payload(entry)', source)
        self.assertIn('"pv_plan": _pv_plan_payload(entry)', source)
        self.assertIn('"source_column": "P_PV"', source)
        self.assertIn('"timestamp_semantics": "interval_end"', source)
        self.assertIn("soc_interval_end_points", source)


if __name__ == "__main__":
    unittest.main()
