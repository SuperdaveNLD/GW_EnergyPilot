"""Unit tests for safe EMHASS configuration patching."""

from __future__ import annotations

from copy import deepcopy
import importlib
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
CUSTOM_COMPONENTS = ROOT / "custom_components"
PACKAGE_DIR = CUSTOM_COMPONENTS / "gw_energypilot"
PACKAGE_NAME = "custom_components.gw_energypilot"


def _module(name: str, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_emhass_config():
    """Import emhass_config.py with minimal external dependency stubs."""
    for name in list(sys.modules):
        if name == "custom_components" or name.startswith(PACKAGE_NAME):
            del sys.modules[name]
        elif name == "homeassistant" or name.startswith("homeassistant."):
            del sys.modules[name]
        elif name == "aiohttp":
            del sys.modules[name]

    custom_components = _module("custom_components")
    custom_components.__path__ = [str(CUSTOM_COMPONENTS)]

    package = _module(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_DIR)]
    package.__package__ = PACKAGE_NAME

    class ClientError(Exception):
        pass

    _module("aiohttp", ClientError=ClientError)

    homeassistant = _module("homeassistant")
    homeassistant.__path__ = []

    class HomeAssistant:
        pass

    core = _module("homeassistant.core", HomeAssistant=HomeAssistant)
    homeassistant.core = core

    class HomeAssistantError(Exception):
        pass

    exceptions = _module(
        "homeassistant.exceptions",
        HomeAssistantError=HomeAssistantError,
    )
    homeassistant.exceptions = exceptions

    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    homeassistant.helpers = helpers

    aiohttp_client = _module(
        "homeassistant.helpers.aiohttp_client",
        async_get_clientsession=lambda hass: None,
    )
    helpers.aiohttp_client = aiohttp_client

    dispatcher = _module(
        "homeassistant.helpers.dispatcher",
        async_dispatcher_send=lambda *args, **kwargs: None,
    )
    helpers.dispatcher = dispatcher

    importlib.import_module(f"{PACKAGE_NAME}.const")
    return importlib.import_module(f"{PACKAGE_NAME}.emhass_config")


emhass_config = _load_emhass_config()


class FakeEntry:
    options = {}
    entry_id = "test-entry"


class EMHASSConfigTests(unittest.IsolatedAsyncioTestCase):
    """Verify selected updates never replace unrelated EMHASS settings."""

    async def test_costfun_patch_preserves_complete_config(self):
        original = {
            "costfun": "profit",
            "continual_publish": False,
            "battery_minimum_state_of_charge": 0.05,
            "battery_maximum_state_of_charge": 0.95,
            "number_of_deferrable_loads": 2,
            "nested_user_setting": {"keep": [1, 2, 3]},
        }
        written = []

        async def fake_get(_hass, _entry):
            return deepcopy(original)

        async def fake_write(_hass, _entry, config):
            written.append(deepcopy(config))

        previous_get = emhass_config.async_get_emhass_config
        previous_write = emhass_config.async_write_emhass_config
        emhass_config.async_get_emhass_config = fake_get
        emhass_config.async_write_emhass_config = fake_write
        try:
            result = await emhass_config.async_patch_emhass_config(
                object(),
                FakeEntry(),
                {"costfun": "cost"},
            )
        finally:
            emhass_config.async_get_emhass_config = previous_get
            emhass_config.async_write_emhass_config = previous_write

        expected = deepcopy(original)
        expected["costfun"] = "cost"
        self.assertEqual(result, expected)
        self.assertEqual(written, [expected])
        self.assertEqual(original["costfun"], "profit")

    async def test_self_consumption_patch_uses_same_safe_merge_path(self):
        original = {
            "costfun": "profit",
            "continual_publish": False,
            "custom_setting": "preserve-me",
        }
        written = []

        async def fake_get(_hass, _entry):
            return deepcopy(original)

        async def fake_write(_hass, _entry, config):
            written.append(deepcopy(config))

        previous_get = emhass_config.async_get_emhass_config
        previous_write = emhass_config.async_write_emhass_config
        emhass_config.async_get_emhass_config = fake_get
        emhass_config.async_write_emhass_config = fake_write
        try:
            result = await emhass_config.async_patch_emhass_config(
                object(),
                FakeEntry(),
                {"costfun": "self-consumption"},
            )
        finally:
            emhass_config.async_get_emhass_config = previous_get
            emhass_config.async_write_emhass_config = previous_write

        self.assertEqual(result["costfun"], "self-consumption")
        self.assertEqual(result["custom_setting"], "preserve-me")
        self.assertEqual(written, [result])

    async def test_set_cost_function_uses_canonical_safe_patch(self):
        captured = []

        async def fake_patch(_hass, _entry, updates):
            captured.append(deepcopy(updates))
            return {"costfun": updates["costfun"], "keep": True}

        previous_patch = emhass_config.async_patch_emhass_config
        emhass_config.async_patch_emhass_config = fake_patch
        try:
            result = await emhass_config.async_set_emhass_cost_function(
                object(),
                FakeEntry(),
                "self-consumption",
            )
        finally:
            emhass_config.async_patch_emhass_config = previous_patch

        self.assertEqual(captured, [{"costfun": "self-consumption"}])
        self.assertEqual(result["keep"], True)

    async def test_set_cost_function_rejects_unknown_value(self):
        with self.assertRaises(emhass_config.HomeAssistantError):
            await emhass_config.async_set_emhass_cost_function(
                object(),
                FakeEntry(),
                "unknown-strategy",
            )

    def test_cost_function_reader_only_accepts_supported_values(self):
        self.assertEqual(
            emhass_config.emhass_cost_function_from_config({"costfun": "profit"}),
            "profit",
        )
        self.assertIsNone(
            emhass_config.emhass_cost_function_from_config({"costfun": "invalid"})
        )


if __name__ == "__main__":
    unittest.main()
