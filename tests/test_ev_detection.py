"""Regression tests for selectable EV charging detection."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
CUSTOM_COMPONENTS = ROOT / "custom_components"
PACKAGE_DIR = CUSTOM_COMPONENTS / "gw_energypilot"
PACKAGE_NAME = "custom_components.gw_energypilot"


def _load_modules():
    for name in list(sys.modules):
        if name == "custom_components" or name.startswith(PACKAGE_NAME):
            del sys.modules[name]

    custom_components = types.ModuleType("custom_components")
    custom_components.__path__ = [str(CUSTOM_COMPONENTS)]
    sys.modules["custom_components"] = custom_components

    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_DIR)]
    package.__package__ = PACKAGE_NAME
    sys.modules[PACKAGE_NAME] = package

    return (
        importlib.import_module(f"{PACKAGE_NAME}.const"),
        importlib.import_module(f"{PACKAGE_NAME}.ev_detection"),
    )


const, ev_detection = _load_modules()


class FakeState:
    def __init__(self, state, **attributes):
        self.state = state
        self.attributes = attributes


class EVDetectionTests(unittest.TestCase):
    def test_legacy_form_default_follows_available_source(self):
        self.assertEqual(
            ev_detection.default_detection_method(
                {const.CONF_EV_MODE_ENTITY: "sensor.zaptec_mode"}
            ),
            const.EV_DETECTION_METHOD_STATE,
        )
        self.assertEqual(
            ev_detection.default_detection_method(
                {const.CONF_EV_POWER_ENTITY: "sensor.charger_power"}
            ),
            const.EV_DETECTION_METHOD_POWER,
        )
        self.assertEqual(
            ev_detection.default_detection_method(
                {
                    const.CONF_EV_MODE_ENTITY: "sensor.zaptec_mode",
                    const.CONF_EV_POWER_ENTITY: "sensor.charger_power",
                }
            ),
            const.EV_DETECTION_METHOD_POWER,
        )

    def test_selected_method_uses_only_its_source(self):
        options = {
            const.CONF_EV_DETECTION_METHOD: const.EV_DETECTION_METHOD_STATE,
            const.CONF_EV_MODE_ENTITY: "binary_sensor.charging",
            const.CONF_EV_POWER_ENTITY: "sensor.charger_power",
        }
        self.assertEqual(
            ev_detection.source_entity_ids(options),
            {"binary_sensor.charging"},
        )

        options[const.CONF_EV_DETECTION_METHOD] = const.EV_DETECTION_METHOD_POWER
        self.assertEqual(
            ev_detection.source_entity_ids(options),
            {"sensor.charger_power"},
        )

    def test_attached_tesla_opladen_history_maps_on_only_to_charging(self):
        entity_id = "binary_sensor.tesla_wall_connector_opladen"
        states = {entity_id: FakeState("off")}
        self.assertFalse(ev_detection.status_is_active(states, entity_id))

        states[entity_id] = FakeState("on")
        self.assertTrue(ev_detection.status_is_active(states, entity_id))

        states[entity_id] = FakeState("unknown")
        self.assertFalse(ev_detection.status_is_active(states, entity_id))

    def test_status_supports_zaptec_and_boolean_active_values(self):
        entity_id = "sensor.zaptec_mode"
        for active in ("on", "true", "charging", "connected_charging"):
            with self.subTest(active=active):
                self.assertTrue(
                    ev_detection.status_is_active(
                        {entity_id: FakeState(active)}, entity_id
                    )
                )
        for inactive in ("off", "false", "connected_finished", "requesting"):
            with self.subTest(inactive=inactive):
                self.assertFalse(
                    ev_detection.status_is_active(
                        {entity_id: FakeState(inactive)}, entity_id
                    )
                )

    def test_power_detection_normalizes_kw(self):
        entity_id = "sensor.charger_power"
        states = {
            entity_id: FakeState("0.8", unit_of_measurement="kW"),
        }
        self.assertTrue(ev_detection.power_is_active(states, entity_id, 500))
        self.assertFalse(ev_detection.power_is_active(states, entity_id, 1000))

    def test_legacy_entry_keeps_exact_previous_behavior(self):
        options = {
            const.CONF_EV_MODE_ENTITY: "binary_sensor.charging",
            const.CONF_EV_POWER_ENTITY: "sensor.charger_power",
        }
        self.assertIsNone(ev_detection.detection_method(options))
        self.assertEqual(
            ev_detection.source_entity_ids(options),
            {"binary_sensor.charging", "sensor.charger_power"},
        )
        states = {"binary_sensor.charging": FakeState("on")}
        self.assertFalse(
            ev_detection.legacy_status_is_active(
                states, "binary_sensor.charging"
            )
        )


if __name__ == "__main__":
    unittest.main()
