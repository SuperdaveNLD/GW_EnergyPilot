"""Unit tests for safe EMHASS configuration synchronization."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "custom_components" / "gw_energypilot" / "emhass_sync.py"
SPEC = importlib.util.spec_from_file_location("gw_energypilot_emhass_sync", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
emhass_sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(emhass_sync)

ENTITY_IDS = {
    "pv": "sensor.energy_pilot_pv",
    "load": "sensor.energy_pilot_load",
    "battery": "sensor.energy_pilot_battery",
    "soc": "sensor.energy_pilot_soc",
}


class EMHASSSyncTests(unittest.TestCase):
    def test_runtime_contract_is_canonical_and_excludes_topology(self):
        self.assertEqual(
            emhass_sync.REQUIRED_RUNTIME_CONFIG,
            {
                "continual_publish": True,
                "method_ts_round": "first",
                "set_use_battery": True,
            },
        )
        self.assertNotIn("inverter_is_hybrid", emhass_sync.REQUIRED_RUNTIME_CONFIG)
        self.assertNotIn("set_use_pv", emhass_sync.REQUIRED_RUNTIME_CONFIG)
        self.assertNotIn("inverter_is_hybrid", emhass_sync.SYNCED_CONFIG_KEYS)

    def test_runtime_contract_preserves_topology_and_unrelated_config(self):
        original = {
            "inverter_is_hybrid": False,
            "set_use_pv": True,
            "custom": {"keep": 1},
            "continual_publish": False,
        }
        updated = emhass_sync.apply_emhass_runtime_contract(original)
        self.assertFalse(updated["inverter_is_hybrid"])
        self.assertTrue(updated["set_use_pv"])
        self.assertEqual(updated["custom"], {"keep": 1})
        self.assertTrue(updated["continual_publish"])
        self.assertEqual(updated["method_ts_round"], "first")
        self.assertTrue(updated["set_use_battery"])
        self.assertEqual(original["continual_publish"], False)
        self.assertNotIn("method_ts_round", original)

    def test_sync_replaces_managed_sensor_mappings_and_preserves_unrelated_config(self):
        original = {
            "sensor_power_photovoltaics": "sensor.old_pv",
            "sensor_power_load_no_var_loads": "sensor.old_load",
            "sensor_power_battery": ["sensor.old_battery"],
            "sensor_battery_state_of_charge": ["sensor.old_soc"],
            "sensor_power_photovoltaics_forecast": "sensor.custom_pv_forecast",
            "sensor_replace_zero": ["sensor.old_pv", "sensor.keep_zero"],
            "sensor_linear_interp": ["sensor.old_pv", "sensor.old_load", "sensor.keep_interp"],
            "var_model": "sensor.old_load",
            "continual_publish": False,
            "method_ts_round": "nearest",
            "set_use_pv": True,
            "set_use_battery": False,
            "inverter_is_hybrid": False,
            "number_of_batteries": 1,
            "custom_setting": {"preserve": [1, 2, 3]},
        }
        synced, warnings = emhass_sync.build_emhass_sync_config(original, ENTITY_IDS)
        self.assertEqual(warnings, [])
        self.assertEqual(synced["sensor_power_photovoltaics"], ENTITY_IDS["pv"])
        self.assertEqual(synced["sensor_power_load_no_var_loads"], ENTITY_IDS["load"])
        self.assertEqual(synced["sensor_power_battery"], [ENTITY_IDS["battery"]])
        self.assertEqual(synced["sensor_battery_state_of_charge"], [ENTITY_IDS["soc"]])
        self.assertEqual(synced["sensor_power_photovoltaics_forecast"], "sensor.custom_pv_forecast")
        self.assertEqual(
            synced["sensor_replace_zero"],
            [ENTITY_IDS["pv"], "sensor.keep_zero", "sensor.custom_pv_forecast"],
        )
        self.assertEqual(
            synced["sensor_linear_interp"],
            [ENTITY_IDS["pv"], ENTITY_IDS["load"], "sensor.keep_interp"],
        )
        self.assertEqual(synced["var_model"], ENTITY_IDS["load"])
        self.assertTrue(synced["continual_publish"])
        self.assertEqual(synced["method_ts_round"], "first")
        self.assertTrue(synced["set_use_pv"])
        self.assertTrue(synced["set_use_battery"])
        self.assertFalse(synced["inverter_is_hybrid"])
        self.assertEqual(synced["custom_setting"], original["custom_setting"])
        self.assertEqual(original["sensor_power_photovoltaics"], "sensor.old_pv")

    def test_hybrid_inverter_setting_is_preserved_when_enabled(self):
        original = {
            "set_use_pv": False,
            "inverter_is_hybrid": True,
        }
        synced, warnings = emhass_sync.build_emhass_sync_config(original, ENTITY_IDS)
        self.assertEqual(warnings, [])
        self.assertTrue(synced["inverter_is_hybrid"])

    def test_hybrid_inverter_setting_is_not_synthesized_when_missing(self):
        synced, warnings = emhass_sync.build_emhass_sync_config(
            {"set_use_pv": False}, ENTITY_IDS
        )
        self.assertEqual(warnings, [])
        self.assertNotIn("inverter_is_hybrid", synced)

    def test_battery_only_config_does_not_require_or_rewrite_pv(self):
        config = {
            "set_use_pv": False,
            "sensor_power_photovoltaics": "sensor.customer_optional_pv",
            "sensor_power_photovoltaics_forecast": "sensor.customer_optional_forecast",
            "sensor_power_load_no_var_loads": "sensor.old_load",
            "sensor_replace_zero": ["sensor.customer_optional_pv"],
            "sensor_linear_interp": ["sensor.old_load"],
        }
        no_pv_entities = {
            "load": ENTITY_IDS["load"],
            "battery": ENTITY_IDS["battery"],
            "soc": ENTITY_IDS["soc"],
        }
        synced, warnings = emhass_sync.build_emhass_sync_config(config, no_pv_entities)
        self.assertEqual(warnings, [])
        self.assertFalse(synced["set_use_pv"])
        self.assertEqual(
            synced["sensor_power_photovoltaics"], "sensor.customer_optional_pv"
        )
        self.assertEqual(
            synced["sensor_power_photovoltaics_forecast"],
            "sensor.customer_optional_forecast",
        )
        self.assertEqual(
            synced["sensor_replace_zero"], ["sensor.customer_optional_pv"]
        )
        self.assertEqual(synced["sensor_linear_interp"], [ENTITY_IDS["load"]])
        self.assertTrue(synced["continual_publish"])

    def test_missing_pv_forecast_uses_emhass_standard_output_when_pv_enabled(self):
        synced, warnings = emhass_sync.build_emhass_sync_config(
            {"set_use_pv": True}, ENTITY_IDS
        )
        self.assertEqual(warnings, [])
        self.assertEqual(
            synced["sensor_power_photovoltaics_forecast"], "sensor.p_pv_forecast"
        )
        self.assertEqual(
            synced["sensor_replace_zero"],
            [ENTITY_IDS["pv"], "sensor.p_pv_forecast"],
        )

    def test_custom_var_model_is_preserved_with_warning(self):
        synced, warnings = emhass_sync.build_emhass_sync_config(
            {
                "set_use_pv": False,
                "sensor_power_load_no_var_loads": "sensor.old_load",
                "var_model": "sensor.custom_model_input",
            },
            ENTITY_IDS,
        )
        self.assertEqual(synced["var_model"], "sensor.custom_model_input")
        self.assertEqual(
            warnings,
            ["Custom EMHASS var_model was preserved instead of being replaced."],
        )

    def test_multiple_battery_sensor_lists_are_not_overwritten(self):
        config = {
            "set_use_pv": False,
            "number_of_batteries": 2,
            "sensor_power_battery": ["sensor.battery_a", "sensor.battery_b"],
            "sensor_battery_state_of_charge": ["sensor.soc_a", "sensor.soc_b"],
        }
        synced, warnings = emhass_sync.build_emhass_sync_config(config, ENTITY_IDS)
        self.assertEqual(
            synced["sensor_power_battery"], config["sensor_power_battery"]
        )
        self.assertEqual(
            synced["sensor_battery_state_of_charge"],
            config["sensor_battery_state_of_charge"],
        )
        self.assertEqual(len(warnings), 1)
        self.assertIn("multiple batteries", warnings[0])

    def test_diff_contains_only_changed_managed_keys_in_stable_order(self):
        current = {
            "continual_publish": False,
            "set_use_battery": True,
            "inverter_is_hybrid": False,
            "custom": 1,
        }
        synced = {
            "continual_publish": True,
            "set_use_battery": True,
            "inverter_is_hybrid": True,
            "custom": 2,
        }
        self.assertEqual(
            emhass_sync.emhass_sync_changes(current, synced),
            [{"key": "continual_publish", "current": False, "required": True}],
        )

    def test_missing_required_battery_entity_mapping_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "battery"):
            emhass_sync.build_emhass_sync_config(
                {"set_use_pv": False},
                {"load": "sensor.load", "soc": "sensor.soc"},
            )

    def test_missing_pv_mapping_is_rejected_only_when_pv_enabled(self):
        with self.assertRaisesRegex(ValueError, "pv"):
            emhass_sync.build_emhass_sync_config(
                {"set_use_pv": True},
                {
                    "load": "sensor.load",
                    "battery": "sensor.battery",
                    "soc": "sensor.soc",
                },
            )


if __name__ == "__main__":
    unittest.main()
