"""Static contracts for the administrator SEMS telemetry settings surface."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class SemsSettingsContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = (INTEGRATION / "settings_api.py").read_text(encoding="utf-8")
        self.frontend = (FRONTEND / "gw-energy-pilot-settings-v016.js").read_text(
            encoding="utf-8"
        )

    def test_menu_exposes_source_identity_credentials_and_cadence(self) -> None:
        for key in (
            "CONF_TELEMETRY_SOURCE",
            "CONF_SEMS_USERNAME",
            "CONF_SEMS_PASSWORD",
            "CONF_SEMS_STATION_ID",
            "CONF_SEMS_INVERTER_SERIAL",
            "CONF_SEMS_SCAN_INTERVAL",
        ):
            self.assertIn(key, self.backend)
        self.assertIn('"label": "SEMS+ API · Beta"', self.backend)
        self.assertIn('"title": "GoodWe data & control"', self.backend)

    def test_password_is_write_only_and_blank_preserves_existing_secret(self) -> None:
        password_field = self.backend.index('"key": CONF_SEMS_PASSWORD')
        status_field = self.backend.index('"key": "sems_password_status"')
        password_payload = self.backend[password_field:status_field]
        self.assertIn('"type": "password"', password_payload)
        self.assertIn('"value": ""', password_payload)
        self.assertNotIn("entry.data.get(CONF_SEMS_PASSWORD", password_payload)
        self.assertIn(
            "submitted_password or str(\n            entry.data.get(CONF_SEMS_PASSWORD, \"\")",
            self.backend,
        )
        self.assertIn('inputType = field.type === "password" ? "password"', self.frontend)
        self.assertIn('field.type === "password" ? "new-password"', self.frontend)

    def test_cloud_validation_does_not_remove_local_control_boundary(self) -> None:
        self.assertIn(
            "if telemetry_source == TELEMETRY_SOURCE_MODBUS or local_changed:",
            self.backend,
        )
        self.assertIn("resolved = await sems_client.async_validate()", self.backend)
        self.assertIn("Every EMS mode/setpoint command still uses the local Modbus", self.frontend)
        self.assertIn("syncGoodWeSourceFields(form)", self.frontend)


if __name__ == "__main__":
    unittest.main()
