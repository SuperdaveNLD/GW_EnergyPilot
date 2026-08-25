"""Regression coverage for EMHASS-owned inverter topology."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ORCHESTRATOR = (
    ROOT / "custom_components" / "gw_energypilot" / "orchestrator_v031.py"
)
SYNC = ROOT / "custom_components" / "gw_energypilot" / "emhass_sync.py"


class EMHASSInverterTopologyTests(unittest.TestCase):
    def test_pre_solve_policy_does_not_force_hybrid_mode(self) -> None:
        source = ORCHESTRATOR.read_text(encoding="utf-8")
        self.assertNotIn('updated["inverter_is_hybrid"] =', source)

    def test_sync_does_not_own_hybrid_mode(self) -> None:
        source = SYNC.read_text(encoding="utf-8")
        self.assertNotIn('synced["inverter_is_hybrid"] =', source)
        self.assertNotIn('    "inverter_is_hybrid",\n)', source)


if __name__ == "__main__":
    unittest.main()
