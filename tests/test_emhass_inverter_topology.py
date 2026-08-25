"""Regression coverage for EMHASS-owned inverter topology."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
ORCHESTRATOR = INTEGRATION / "orchestrator_v031.py"
SYNC = INTEGRATION / "emhass_sync.py"
SYNC_API = INTEGRATION / "emhass_sync_api.py"


class EMHASSInverterTopologyTests(unittest.TestCase):
    def test_pre_solve_policy_uses_canonical_contract_without_hybrid_force(self) -> None:
        source = ORCHESTRATOR.read_text(encoding="utf-8")
        self.assertIn("apply_emhass_runtime_contract(current)", source)
        self.assertNotIn('updated["inverter_is_hybrid"] =', source)

    def test_sync_does_not_own_or_synthesize_hybrid_mode(self) -> None:
        source = SYNC.read_text(encoding="utf-8")
        self.assertNotIn('synced["inverter_is_hybrid"] =', source)
        self.assertNotIn('"inverter_is_hybrid": True', source)

    def test_sync_api_uses_canonical_managed_key_list(self) -> None:
        source = SYNC_API.read_text(encoding="utf-8")
        self.assertIn("for key in SYNCED_CONFIG_KEYS", source)
        self.assertNotIn('        "inverter_is_hybrid",', source)


if __name__ == "__main__":
    unittest.main()
