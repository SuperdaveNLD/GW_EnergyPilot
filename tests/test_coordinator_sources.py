"""Coordinator separation between cloud telemetry and local EMS readback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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


def _load_module():
    for name in list(sys.modules):
        if name == "custom_components" or name.startswith(PACKAGE_NAME):
            del sys.modules[name]
        elif name == "homeassistant" or name.startswith("homeassistant."):
            del sys.modules[name]

    custom_components = _module("custom_components")
    custom_components.__path__ = [str(CUSTOM_COMPONENTS)]
    package = _module(PACKAGE_NAME)
    package.__path__ = [str(PACKAGE_DIR)]
    package.__package__ = PACKAGE_NAME

    homeassistant = _module("homeassistant")
    homeassistant.__path__ = []
    homeassistant.core = _module("homeassistant.core", HomeAssistant=object)
    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    homeassistant.helpers = helpers

    class UpdateFailed(Exception):
        pass

    class DataUpdateCoordinator:
        def __class_getitem__(cls, item):
            return cls

        def __init__(self, hass, logger, name, update_interval):
            self.hass = hass
            self.data = None
            self.update_interval = update_interval

        def async_set_updated_data(self, data):
            self.data = data

        def async_update_listeners(self):
            pass

        async def async_request_refresh(self):
            self.data = await self._async_update_data()

    helpers.update_coordinator = _module(
        "homeassistant.helpers.update_coordinator",
        DataUpdateCoordinator=DataUpdateCoordinator,
        UpdateFailed=UpdateFailed,
    )

    class GWModbusError(Exception):
        pass

    @dataclass
    class GWETAData:
        values: dict
        source: str = "modbus"
        source_updated_at: datetime | None = None

        @property
        def mode(self):
            return self.values.get("ems_mode")

        @property
        def power(self):
            return self.values.get("ems_setpoint")

    class GWModbusClient:
        pass

    _module(
        f"{PACKAGE_NAME}.client",
        GWETAData=GWETAData,
        GWModbusClient=GWModbusClient,
        GWModbusError=GWModbusError,
    )
    _module(f"{PACKAGE_NAME}.const", DOMAIN="gw_energypilot")

    class GWSemsError(Exception):
        pass

    _module(f"{PACKAGE_NAME}.sems_api", GWSemsError=GWSemsError)
    module = importlib.import_module(f"{PACKAGE_NAME}.coordinator")
    return module, GWETAData, GWModbusError, UpdateFailed, GWModbusClient


coordinator_module, GWETAData, GWModbusError, UpdateFailed, GWModbusClient = (
    _load_module()
)


class FakeTelemetry:
    def __init__(self, data):
        self.data = data

    async def async_read_data(self):
        return self.data


class FakeControl(GWModbusClient):
    def __init__(self, data=None, error=None):
        self.data = data
        self.error = error

    async def async_read_control_status(self):
        if self.error is not None:
            raise self.error
        return self.data


class CoordinatorSourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_cloud_telemetry_survives_independent_modbus_read_failure(self):
        telemetry = GWETAData({"pv_total_power": 3200}, source="sems_api")
        control_error = GWModbusError("local control offline")
        coordinator = coordinator_module.GWEnergyPilotCoordinator(
            object(),
            FakeTelemetry(telemetry),
            60,
            source="sems_api",
            control_client=FakeControl(error=control_error),
        )

        result = await coordinator._async_update_data()

        self.assertEqual(result.values, {"pv_total_power": 3200})
        self.assertFalse(coordinator.last_control_update_success)
        self.assertIs(coordinator.last_control_exception, control_error)

    async def test_cloud_refresh_merges_local_ems_readback(self):
        telemetry = GWETAData({"battery_soc": 55}, source="sems_api")
        control = FakeControl(
            GWETAData(
                {
                    "ems_mode": 8,
                    "ems_setpoint": 0,
                    "battery_discharge_depth_on_grid": 10,
                }
            )
        )
        coordinator = coordinator_module.GWEnergyPilotCoordinator(
            object(),
            FakeTelemetry(telemetry),
            60,
            source="sems_api",
            control_client=control,
        )
        coordinator.data = telemetry
        coordinator.last_update_success = False

        await coordinator.async_refresh_control_readback()

        self.assertEqual(coordinator.data.values["battery_soc"], 55)
        self.assertEqual(coordinator.data.mode, 8)
        self.assertEqual(coordinator.data.power, 0)
        self.assertEqual(
            coordinator.data.values["battery_discharge_depth_on_grid"], 10
        )
        self.assertEqual(coordinator.data.source, "sems_api")
        self.assertTrue(coordinator.last_control_update_success)
        self.assertFalse(coordinator.last_update_success)

    async def test_explicit_control_refresh_propagates_readback_failure(self):
        error = GWModbusError("timeout")
        coordinator = coordinator_module.GWEnergyPilotCoordinator(
            object(),
            FakeTelemetry(GWETAData({}, source="sems_api")),
            60,
            source="sems_api",
            control_client=FakeControl(error=error),
        )

        with self.assertRaises(GWModbusError):
            await coordinator.async_refresh_control_readback()
        self.assertFalse(coordinator.last_control_update_success)


if __name__ == "__main__":
    unittest.main()
