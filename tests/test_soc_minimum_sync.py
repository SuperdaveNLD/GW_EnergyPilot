"""Regression tests for synchronized EMHASS/GoodWe minimum SOC writes."""

from __future__ import annotations

from dataclasses import dataclass
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


def _load_number_module():
    for name in list(sys.modules):
        if name == "custom_components" or name.startswith(PACKAGE_NAME):
            del sys.modules[name]
        elif name == "homeassistant" or name.startswith("homeassistant."):
            del sys.modules[name]

    custom_components = _module("custom_components")
    custom_components.__path__ = [str(CUSTOM_COMPONENTS)]

    package = _module(PACKAGE_NAME, GWConfigEntry=object)
    package.__path__ = [str(PACKAGE_DIR)]
    package.__package__ = PACKAGE_NAME

    homeassistant = _module("homeassistant")
    homeassistant.__path__ = []

    components = _module("homeassistant.components")
    components.__path__ = []
    homeassistant.components = components

    class NumberEntity:
        pass

    class NumberMode:
        SLIDER = "slider"

    number_component = _module(
        "homeassistant.components.number",
        NumberEntity=NumberEntity,
        NumberMode=NumberMode,
    )
    components.number = number_component

    class EntityCategory:
        CONFIG = "config"

    class UnitOfPower:
        WATT = "W"

    const_module = _module(
        "homeassistant.const",
        EntityCategory=EntityCategory,
        PERCENTAGE="%",
        UnitOfPower=UnitOfPower,
    )
    homeassistant.const = const_module

    class HomeAssistant:
        pass

    def callback(func):
        return func

    core = _module(
        "homeassistant.core",
        HomeAssistant=HomeAssistant,
        callback=callback,
    )
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
    helpers.entity_platform = _module(
        "homeassistant.helpers.entity_platform",
        AddConfigEntryEntitiesCallback=object,
    )
    helpers.event = _module(
        "homeassistant.helpers.event",
        async_call_later=lambda *_args, **_kwargs: (lambda: None),
    )

    @dataclass(slots=True)
    class GWETAData:
        values: dict[str, int | float]

    class GWModbusError(Exception):
        pass

    _module(
        f"{PACKAGE_NAME}.client",
        GWETAData=GWETAData,
        GWModbusError=GWModbusError,
    )

    async def placeholder_get(*_args, **_kwargs):
        raise AssertionError("async_get_emhass_config was not replaced")

    async def placeholder_write(*_args, **_kwargs):
        raise AssertionError("async_write_emhass_config was not replaced")

    _module(
        f"{PACKAGE_NAME}.emhass_config",
        async_get_emhass_config=placeholder_get,
        async_write_emhass_config=placeholder_write,
    )

    class GWEnergyPilotEntity:
        def __init__(self, entry):
            self.entry = entry
            self.hass = object()

        async def async_added_to_hass(self):
            return None

        def async_write_ha_state(self):
            return None

    _module(
        f"{PACKAGE_NAME}.entity",
        GWEnergyPilotEntity=GWEnergyPilotEntity,
    )

    importlib.import_module(f"{PACKAGE_NAME}.const")
    number_module = importlib.import_module(f"{PACKAGE_NAME}.number")
    return number_module, HomeAssistantError, GWModbusError


number_module, HomeAssistantError, GWModbusError = _load_number_module()


class FakeCoordinatorData:
    def __init__(self, values):
        self.values = dict(values)


class FakeCoordinator:
    def __init__(self, values):
        self.data = FakeCoordinatorData(values)

    def async_set_updated_data(self, data):
        self.data = data


class FakeClient:
    def __init__(self):
        self.calls = []
        self.fail_values = set()

    async def async_set_beta_soc_floor(self, key, value):
        self.calls.append((key, value))
        if value in self.fail_values:
            raise GWModbusError(f"write failed for {value}")
        return value


class FakeRuntimeData:
    def __init__(self, values):
        self.coordinator = FakeCoordinator(values)
        self.client = FakeClient()
        self.controller = types.SimpleNamespace(manual_power=0)
        self.orchestrator = types.SimpleNamespace()


class FakeEntry:
    def __init__(self, values):
        self.entry_id = "soc-sync-test"
        self.options = {}
        self.runtime_data = FakeRuntimeData(values)


class MinimumSocSyncTests(unittest.IsolatedAsyncioTestCase):
    """Protect the cross-system minimum SOC transaction."""

    def make_entity(self, *, goodwe_floor=5):
        values = {}
        if goodwe_floor is not None:
            values[number_module.GOODWE_ON_GRID_MINIMUM_SOC_KEY] = goodwe_floor
        entry = FakeEntry(values)
        entity = number_module.GWEMHASSMinimumSOCNumber(entry)
        entity._schedule_debounced_optimization = lambda: None
        return entity, entry

    async def _run_with_emhass(self, entity, *, write_error=None, value=3):
        writes = []
        order = []

        async def fake_get(_hass, _entry):
            return {
                "battery_minimum_state_of_charge": 0.05,
                "battery_maximum_state_of_charge": 0.93,
                "preserve_me": True,
            }

        async def fake_write(_hass, _entry, config):
            order.append("emhass")
            writes.append(dict(config))
            if write_error is not None:
                raise write_error

        original_get = number_module.async_get_emhass_config
        original_write = number_module.async_write_emhass_config
        original_goodwe = entity._async_set_goodwe_on_grid_floor

        async def tracked_goodwe(requested):
            order.append(f"goodwe:{requested}")
            return await original_goodwe(requested)

        number_module.async_get_emhass_config = fake_get
        number_module.async_write_emhass_config = fake_write
        entity._async_set_goodwe_on_grid_floor = tracked_goodwe
        try:
            await entity.async_set_native_value(value)
        finally:
            number_module.async_get_emhass_config = original_get
            number_module.async_write_emhass_config = original_write
            entity._async_set_goodwe_on_grid_floor = original_goodwe
        return writes, order

    async def test_minimum_soc_updates_goodwe_first_then_emhass(self):
        entity, entry = self.make_entity(goodwe_floor=5)

        writes, order = await self._run_with_emhass(entity, value=3)

        self.assertEqual(
            entry.runtime_data.client.calls,
            [(number_module.GOODWE_ON_GRID_MINIMUM_SOC_KEY, 3)],
        )
        self.assertEqual(order, ["goodwe:3", "emhass"])
        self.assertEqual(writes[0]["battery_minimum_state_of_charge"], 0.03)
        self.assertTrue(writes[0]["preserve_me"])
        self.assertEqual(
            entry.runtime_data.coordinator.data.values[
                number_module.GOODWE_ON_GRID_MINIMUM_SOC_KEY
            ],
            3,
        )
        self.assertEqual(entity.native_value, 3.0)

    async def test_unavailable_goodwe_floor_prevents_emhass_change(self):
        entity, entry = self.make_entity(goodwe_floor=None)
        writes = []

        async def fake_get(_hass, _entry):
            return {"battery_maximum_state_of_charge": 0.93}

        async def fake_write(_hass, _entry, config):
            writes.append(dict(config))

        original_get = number_module.async_get_emhass_config
        original_write = number_module.async_write_emhass_config
        number_module.async_get_emhass_config = fake_get
        number_module.async_write_emhass_config = fake_write
        try:
            with self.assertRaises(HomeAssistantError):
                await entity.async_set_native_value(3)
        finally:
            number_module.async_get_emhass_config = original_get
            number_module.async_write_emhass_config = original_write

        self.assertEqual(entry.runtime_data.client.calls, [])
        self.assertEqual(writes, [])

    async def test_emhass_failure_rolls_goodwe_back(self):
        entity, entry = self.make_entity(goodwe_floor=5)

        with self.assertRaises(HomeAssistantError):
            await self._run_with_emhass(
                entity,
                value=3,
                write_error=HomeAssistantError("set-config failed"),
            )

        self.assertEqual(
            entry.runtime_data.client.calls,
            [
                (number_module.GOODWE_ON_GRID_MINIMUM_SOC_KEY, 3),
                (number_module.GOODWE_ON_GRID_MINIMUM_SOC_KEY, 5),
            ],
        )
        self.assertEqual(
            entry.runtime_data.coordinator.data.values[
                number_module.GOODWE_ON_GRID_MINIMUM_SOC_KEY
            ],
            5,
        )
        self.assertIsNone(entity.native_value)

    async def test_matching_goodwe_floor_skips_redundant_modbus_write(self):
        entity, entry = self.make_entity(goodwe_floor=3)

        writes, order = await self._run_with_emhass(entity, value=3)

        self.assertEqual(entry.runtime_data.client.calls, [])
        self.assertEqual(order, ["emhass"])
        self.assertEqual(writes[0]["battery_minimum_state_of_charge"], 0.03)

    async def test_fractional_minimum_soc_is_rejected_before_any_write(self):
        entity, entry = self.make_entity(goodwe_floor=5)

        with self.assertRaises(HomeAssistantError):
            await self._run_with_emhass(entity, value=3.5)

        self.assertEqual(entry.runtime_data.client.calls, [])

    async def test_managed_profile_rejects_direct_minimum_and_maximum_writes(self):
        minimum, entry = self.make_entity(goodwe_floor=5)
        maximum = number_module.GWEMHASSMaximumSOCNumber(entry)
        entry.options[number_module.CONF_BATTERY_SAVER_MODE] = "balanced"

        with self.assertRaisesRegex(HomeAssistantError, "select Custom"):
            await minimum.async_set_native_value(10)
        with self.assertRaisesRegex(HomeAssistantError, "select Custom"):
            await maximum.async_set_native_value(90)

        self.assertEqual(entry.runtime_data.client.calls, [])


if __name__ == "__main__":
    unittest.main()
