from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = (
    ROOT / "custom_components" / "gw_energypilot" / "orchestrator_v031.py"
)


class EmhassOutputFreshnessTests(unittest.TestCase):
    def test_freshness_uses_last_reported_with_compatibility_fallback(self) -> None:
        source = ORCHESTRATOR.read_text(encoding="utf-8")

        self.assertIn(
            'return getattr(state, "last_reported", state.last_updated)',
            source,
        )
        self.assertIn(
            'reported = getattr(state, "last_reported", state.last_updated)',
            source,
        )
        self.assertIn("is_fresh = baseline is None or reported > baseline", source)

    def test_reported_baseline_is_captured_before_optimization(self) -> None:
        source = ORCHESTRATOR.read_text(encoding="utf-8")

        capture = "self._p_batt_reported_before = self._p_batt_report_timestamp()"
        optimize = "await super().async_optimize(reason=reason)"
        clear = "self._p_batt_reported_before = None"

        self.assertLess(source.index(capture), source.index(optimize))
        self.assertLess(source.index(optimize), source.index(clear))

    def test_existing_numeric_and_optimizer_ready_safety_gates_remain(self) -> None:
        source = ORCHESTRATOR.read_text(encoding="utf-8")

        self.assertIn("state is not None and self._optimization_ready()", source)
        self.assertIn("math.isfinite(value) and is_fresh", source)


if __name__ == "__main__":
    unittest.main()
