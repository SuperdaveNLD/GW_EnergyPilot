"""Regression tests for config-entry optimization-interval compatibility."""

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


def _module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_config_flow():
    for name in list(sys.modules):
        if name == "custom_components" or name.startswith(PACKAGE_NAME):
            del sys.modules[name]
        elif name == "homeassistant" or name.startswith("homeassistant."):
            del sys.modules[name]
        elif name == "voluptuous":
            del sys.modules[name]

    custom_components = _module("custom_components")
    custom_components.__path__ = [str(CUSTOM_COMPONENTS)]
    package = _module(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_DIR)]
    package.__package__ = PACKAGE_NAME

    class Invalid(Exception):
        pass

    _module("voluptuous", Invalid=Invalid, Schema=object)

    homeassistant = _module("homeassistant")
    homeassistant.__path__ = []

    class ConfigFlow:
        def __init_subclass__(cls, **_kwargs):
            return super().__init_subclass__()

    class OptionsFlowWithReload:
        pass

    config_entries = _module(
        "homeassistant.config_entries",
        ConfigFlow=ConfigFlow,
        ConfigFlowResult=dict,
        OptionsFlowWithReload=OptionsFlowWithReload,
    )
    homeassistant.config_entries = config_entries
    homeassistant.const = _module(
        "homeassistant.const",
        CONF_HOST="host",
        CONF_PORT="port",
    )
    homeassistant.core = _module(
        "homeassistant.core",
        callback=lambda function: function,
    )
    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    helpers.selector = _module("homeassistant.helpers.selector")
    homeassistant.helpers = helpers

    class GWModbusError(Exception):
        pass

    _module(
        f"{PACKAGE_NAME}.client",
        GWModbusClient=object,
        GWModbusError=GWModbusError,
    )

    config_flow = importlib.import_module(f"{PACKAGE_NAME}.config_flow")
    const = importlib.import_module(f"{PACKAGE_NAME}.const")
    return config_flow, const


config_flow, const = _load_config_flow()


class OptimizationIntervalCompatibilityTests(unittest.TestCase):
    def test_integral_legacy_numbers_match_select_options(self) -> None:
        for stored, expected in ((15.0, "15"), ("30.0", "30"), (10.0, "10")):
            with self.subTest(stored=stored):
                form_options = config_flow._options_for_form(
                    {const.CONF_EMHASS_OPTIMIZATION_INTERVAL: stored}
                )
                actual = form_options[const.CONF_EMHASS_OPTIMIZATION_INTERVAL]

                self.assertEqual(actual, expected)
                self.assertIn(
                    actual,
                    config_flow._optimization_interval_options(stored),
                )

    def test_fractional_value_remains_invalid(self) -> None:
        stored = 12.5
        form_options = config_flow._options_for_form(
            {const.CONF_EMHASS_OPTIMIZATION_INTERVAL: stored}
        )
        actual = form_options[const.CONF_EMHASS_OPTIMIZATION_INTERVAL]

        self.assertEqual(actual, "12.5")
        self.assertNotIn(
            actual,
            config_flow._optimization_interval_options(stored),
        )


if __name__ == "__main__":
    unittest.main()
