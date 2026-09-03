"""SEMS+ Beta telemetry and selection regressions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "custom_components" / "gw_energypilot" / "sems_model.py"
SPEC = importlib.util.spec_from_file_location("gw_energypilot_sems_model", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Unable to load sems_model.py")
sems_model = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sems_model
SPEC.loader.exec_module(sems_model)

SemsPayloadError = sems_model.SemsPayloadError
SemsSelectionError = sems_model.SemsSelectionError
SemsStaleDataError = sems_model.SemsStaleDataError
encode_sems_plus_password = sems_model.encode_sems_plus_password
map_sems_telemetry = sems_model.map_sems_telemetry
normalize_powerstation_api_base = sems_model.normalize_powerstation_api_base
normalize_station_ids = sems_model.normalize_station_ids
parse_sems_power = sems_model.parse_sems_power


NOW = datetime(2026, 8, 31, 10, 0, tzinfo=timezone.utc)


def _inverter(serial: str = "ETA15TEST0001", **updates):
    values = {
        "sn": serial,
        "last_time": int(NOW.timestamp() * 1000),
        "pac": 3100,
        "pv_power": 3200,
        "pmeter": -700,
        "vpv1": 420.5,
        "ipv1": 7.4,
        "vac1": 230.1,
        "iac1": 4.2,
        "fac1": 50.01,
        "tempperature": 36.4,
        "soc": 67,
        "soh": 98,
        "vbattery1": 402.1,
        "ibattery1": -3.0,
        "bms_charge_i_max": 30,
        "bms_discharge_i_max": 35,
        "total_buy": 1234.5,
        "total_sell": 456.7,
    }
    values.update(updates)
    return {"invert_full": values}


def _payload(*inverters, battery_status: int = 1, show_battery: bool = True):
    return {
        "inverter": list(inverters or [_inverter()]),
        "isShowBattery": show_battery,
        "powerflow": {
            "pv": "3.2(kW)",
            "load": "2700(W)",
            "bettery": "1200(W)",
            "betteryStatus": battery_status,
            "soc": 67,
        },
    }


class SemsProtocolHelpersTests(unittest.TestCase):
    def test_sems_plus_password_uses_md5_hex_then_base64(self) -> None:
        self.assertEqual(
            encode_sems_plus_password("secret"),
            "NWViZTIyOTRlY2QwZTBmMDhlYWI3NjkwZDJhNmVlNjk=",
        )

    def test_gateway_base_is_rewritten_for_legacy_powerstation_routes(self) -> None:
        self.assertEqual(
            normalize_powerstation_api_base(
                "https://eu-gateway.semsportal.com/web/sems"
            ),
            "https://eu.semsportal.com/api",
        )
        self.assertEqual(
            normalize_powerstation_api_base("https://eu.semsportal.com/api/"),
            "https://eu.semsportal.com/api",
        )

    def test_station_ids_are_deduplicated_without_selecting_one(self) -> None:
        self.assertEqual(normalize_station_ids("station-a"), ("station-a",))
        self.assertEqual(
            normalize_station_ids(["station-a", "", "station-b", "station-a"]),
            ("station-a", "station-b"),
        )

    def test_power_parser_handles_portal_units_and_rejects_noise(self) -> None:
        self.assertEqual(parse_sems_power("1200(W)"), 1200)
        self.assertEqual(parse_sems_power("1.25 kW"), 1250)
        self.assertIsNone(parse_sems_power("SOC: 50%"))


class SemsTelemetryMappingTests(unittest.TestCase):
    def test_charge_sign_is_converted_to_energypilot_convention(self) -> None:
        charge = map_sems_telemetry(_payload(battery_status=1), now=NOW)
        discharge = map_sems_telemetry(_payload(battery_status=-1), now=NOW)

        self.assertEqual(charge.values["battery_power"], -1200)
        self.assertEqual(discharge.values["battery_power"], 1200)
        self.assertEqual(charge.values["meter_total_power_fast"], -700)

    def test_only_evidence_backed_runtime_subset_is_mapped(self) -> None:
        mapped = map_sems_telemetry(_payload(), now=NOW)

        self.assertEqual(mapped.inverter_serial, "ETA15TEST0001")
        self.assertEqual(mapped.values["pv_total_power"], 3200)
        self.assertEqual(mapped.values["total_load_power"], 2700)
        self.assertEqual(mapped.values["battery_soc"], 67)
        self.assertEqual(mapped.values["inverter_l1_frequency"], 50.01)
        self.assertNotIn("meter_total_energy_import", mapped.values)
        self.assertNotIn("meter_total_energy_export", mapped.values)
        self.assertNotIn("ems_mode", mapped.values)
        self.assertNotIn("battery_discharge_depth_on_grid", mapped.values)

    def test_non_battery_station_does_not_publish_false_soc(self) -> None:
        mapped = map_sems_telemetry(
            _payload(_inverter(soc=536), show_battery=False),
            now=NOW,
        )
        self.assertNotIn("battery_soc", mapped.values)
        self.assertNotIn("battery_power", mapped.values)

    def test_zero_powerflow_soc_falls_back_to_positive_inverter_soc(self) -> None:
        payload = _payload(_inverter(soc=66))
        payload["powerflow"]["soc"] = 0

        mapped = map_sems_telemetry(payload, now=NOW)

        self.assertEqual(mapped.values["battery_soc"], 66)
        self.assertEqual(
            mapped.diagnostics["decisions"]["battery_soc_source"],
            "inverter.soc",
        )
        self.assertEqual(
            mapped.diagnostics["decisions"]["rejected_battery_soc_sources"],
            ["powerflow.soc"],
        )

    def test_zero_soc_placeholders_are_unavailable_not_zero_percent(self) -> None:
        payload = _payload(_inverter(soc=0))
        payload["powerflow"]["soc"] = 0

        mapped = map_sems_telemetry(payload, now=NOW)

        self.assertNotIn("battery_soc", mapped.values)
        self.assertIsNone(
            mapped.diagnostics["decisions"]["battery_soc_source"]
        )
        self.assertEqual(
            mapped.diagnostics["decisions"]["rejected_battery_soc_sources"],
            ["powerflow.soc", "inverter.soc"],
        )

    def test_diagnostics_allowlist_excludes_unknown_payload_fields(self) -> None:
        payload = _payload(_inverter())
        payload["token"] = "portal-token"
        payload["powerflow"]["password"] = "cloud-secret"
        payload["inverter"][0]["invert_full"]["account"] = "owner@example.com"

        mapped = map_sems_telemetry(payload, now=NOW)
        diagnostics = str(mapped.diagnostics)

        self.assertNotIn("portal-token", diagnostics)
        self.assertNotIn("cloud-secret", diagnostics)
        self.assertNotIn("owner@example.com", diagnostics)
        self.assertEqual(mapped.diagnostics["raw"]["powerflow"]["soc"], 67)
        json.dumps(mapped.diagnostics, allow_nan=False)

    def test_sentinel_ac_values_are_rejected(self) -> None:
        mapped = map_sems_telemetry(
            _payload(_inverter(vac1=6553.5, iac1=6553.5, fac1=655.35)),
            now=NOW,
        )
        self.assertNotIn("inverter_l1_voltage", mapped.values)
        self.assertNotIn("inverter_l1_current", mapped.values)
        self.assertNotIn("inverter_l1_frequency", mapped.values)

    def test_old_or_future_samples_are_not_runtime_telemetry(self) -> None:
        old = _inverter(last_time=int((NOW - timedelta(minutes=16)).timestamp() * 1000))
        with self.assertRaises(SemsStaleDataError):
            map_sems_telemetry(_payload(old), now=NOW)

        future = _inverter(last_time=int((NOW + timedelta(minutes=6)).timestamp() * 1000))
        with self.assertRaises(SemsPayloadError):
            map_sems_telemetry(_payload(future), now=NOW)

    def test_multi_inverter_station_requires_explicit_serial(self) -> None:
        payload = _payload(
            _inverter("SERIAL-A", pv_power=1100),
            _inverter("SERIAL-B", pv_power=2200),
        )
        with self.assertRaises(SemsSelectionError):
            map_sems_telemetry(payload, now=NOW)

        selected = map_sems_telemetry(payload, "SERIAL-B", now=NOW)
        self.assertEqual(selected.inverter_serial, "SERIAL-B")
        self.assertEqual(selected.values["pv_total_power"], 2200)
        self.assertNotIn("total_load_power", selected.values)
        self.assertNotIn("battery_power", selected.values)

    def test_station_type_without_invert_full_fails_explicitly(self) -> None:
        with self.assertRaisesRegex(SemsPayloadError, "station type 2"):
            map_sems_telemetry({"inverter": [{"sn": "NEW-TYPE"}]}, now=NOW)


if __name__ == "__main__":
    unittest.main()
