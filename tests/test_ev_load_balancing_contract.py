"""Static safety contract for EV load-balancing configuration and UI."""

import ast
from pathlib import Path
from types import SimpleNamespace
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

    def test_ev_tab_offers_exclusive_power_or_status_detection(self):
        constants = (INTEGRATION / "const.py").read_text(encoding="utf-8")
        settings = (INTEGRATION / "settings_api.py").read_text(encoding="utf-8")
        frontend = (
            INTEGRATION / "frontend" / "gw-energy-pilot-settings-v016.js"
        ).read_text(encoding="utf-8")

        self.assertIn('CONF_EV_DETECTION_METHOD = "ev_detection_method"', constants)
        self.assertIn('"value": EV_DETECTION_METHOD_POWER', settings)
        self.assertIn('"value": EV_DETECTION_METHOD_STATE', settings)
        self.assertIn('data-setting-key="ev_detection_method"', frontend)
        self.assertIn('detection?.value === "state"', frontend)

    def test_goodwe_currents_feedback_and_online_entity_contract(self):
        constants = (INTEGRATION / "const.py").read_text(encoding="utf-8")
        settings = (INTEGRATION / "settings_api.py").read_text(encoding="utf-8")
        runtime = (INTEGRATION / "ev_load_balancing.py").read_text(
            encoding="utf-8"
        )

        self.assertIn('CONF_EV_CHARGER_ALLOCATED_CURRENT_ENTITY =', constants)
        self.assertIn('"meter_l1_current"', runtime)
        self.assertIn('"meter_l2_current"', runtime)
        self.assertIn('"meter_l3_current"', runtime)
        self.assertIn("max(value for value in currents.values()", runtime)
        self.assertNotIn(
            '"key": CONF_EV_GRID_CURRENT_ENTITY',
            settings,
        )
        self.assertIn('"key": CONF_EV_CHARGER_ALLOCATED_CURRENT_ENTITY', settings)
        self.assertIn("_auto_link_ev_charger_entities", settings)
        ev_keys = settings.split("EV_KEYS = {", 1)[1].split("}", 1)[0]
        self.assertIn("CONF_EV_ONLINE_ENTITY,", ev_keys)

    def test_zaptec_control_and_feedback_auto_link_by_registry_relation(self):
        source = (INTEGRATION / "settings_api.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_auto_link_ev_charger_entities"
        )

        online = SimpleNamespace(
            entity_id="binary_sensor.zorro_online",
            config_entry_id="zaptec-entry",
            device_id="charger-device",
            unique_id="zorro_online",
            translation_key="online",
        )
        control = SimpleNamespace(
            entity_id="number.zaptec_available_current",
            config_entry_id="zaptec-entry",
            device_id="installation-device",
            unique_id="installation_available_current",
            translation_key="available_current",
        )
        feedback = SimpleNamespace(
            entity_id="sensor.zorro_toegewezen_laadstroom",
            config_entry_id="zaptec-entry",
            device_id="charger-device",
            unique_id="charger_allocated_current",
            translation_key="allocated_current",
        )
        registry = SimpleNamespace(
            async_get=lambda entity_id: {
                online.entity_id: online,
                control.entity_id: control,
                feedback.entity_id: feedback,
            }.get(entity_id),
            entities={
                entry.entity_id: entry for entry in (online, control, feedback)
            },
        )
        states = {
            online.entity_id: SimpleNamespace(
                attributes={"device_class": "connectivity"}
            ),
            control.entity_id: SimpleNamespace(
                attributes={"unit_of_measurement": "A", "min": 0, "max": 32}
            ),
            feedback.entity_id: SimpleNamespace(
                attributes={
                    "unit_of_measurement": "A",
                    "device_class": "current",
                    "friendly_name": "Zorro Toegewezen laadstroom",
                }
            ),
        }
        namespace = {
            "Any": object,
            "HomeAssistant": object,
            "CONF_EV_CHARGER_CURRENT_ENTITY": "ev_charger_current_entity",
            "CONF_EV_CHARGER_ALLOCATED_CURRENT_ENTITY": (
                "ev_charger_allocated_current_entity"
            ),
            "CONF_EV_MODE_ENTITY": "ev_mode_entity",
            "CONF_EV_POWER_ENTITY": "ev_power_entity",
            "CONF_EV_ONLINE_ENTITY": "ev_online_entity",
            "er": SimpleNamespace(async_get=lambda _hass: registry),
        }
        module = ast.Module(body=[function], type_ignores=[])
        ast.fix_missing_locations(module)
        exec(compile(module, "settings_api.py", "exec"), namespace)

        linked = namespace["_auto_link_ev_charger_entities"](
            SimpleNamespace(states=SimpleNamespace(get=states.get)),
            {"ev_online_entity": online.entity_id},
        )
        self.assertEqual(
            linked["ev_charger_current_entity"], control.entity_id
        )
        self.assertEqual(
            linked["ev_charger_allocated_current_entity"], feedback.entity_id
        )


if __name__ == "__main__":
    unittest.main()
