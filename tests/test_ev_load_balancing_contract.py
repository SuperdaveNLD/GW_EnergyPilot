"""Static safety contract for EV load-balancing configuration and UI."""

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"


class EVLoadBalancingContractTests(unittest.TestCase):
    def test_backend_requires_and_audits_confirmation_above_16a(self):
        settings = (INTEGRATION / "settings_api.py").read_text(encoding="utf-8")
        runtime = (INTEGRATION / "ev_load_balancing.py").read_text(encoding="utf-8")
        self.assertIn("high_current_confirmation_required", settings)
        self.assertIn('values.pop("_confirm_high_current", False)', settings)
        self.assertIn("await audit.async_append", settings)
        self.assertNotIn("[-", runtime.split("class EVLoadBalancingAudit", 1)[1].split("class GWEnergyPilot", 1)[0])

    def test_ev_tab_has_profiles_soft_window_and_warning(self):
        settings = (INTEGRATION / "settings_api.py").read_text(encoding="utf-8")
        frontend = (
            INTEGRATION / "frontend" / "gw-energy-pilot-settings-v016.js"
        ).read_text(encoding="utf-8")
        self.assertIn('SECTION_EV = "ev"', settings)
        self.assertIn('"custom_1_phase"', settings)
        self.assertIn('"custom_3_phase"', settings)
        self.assertIn("EV_LOAD_BALANCE_WINDOW_OPTIONS", settings)
        self.assertIn("permanently audited", frontend)
        self.assertIn("window.confirm", frontend)
        self.assertIn("values._confirm_high_current = true", frontend)


if __name__ == "__main__":
    unittest.main()
