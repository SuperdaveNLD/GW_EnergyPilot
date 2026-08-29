"""Regression tests for Nord Pool runtime-price source classification."""

from __future__ import annotations

from datetime import datetime, timezone
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


def _load_orchestrator():
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

    class ConfigEntry:
        pass

    config_entries = _module(
        "homeassistant.config_entries",
        ConfigEntry=ConfigEntry,
    )
    homeassistant.config_entries = config_entries

    class CoreState:
        running = object()

    class Event:
        pass

    class HomeAssistant:
        pass

    core = _module(
        "homeassistant.core",
        CoreState=CoreState,
        Event=Event,
        HomeAssistant=HomeAssistant,
        callback=lambda function: function,
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
    entity_registry = _module(
        "homeassistant.helpers.entity_registry",
        async_get=lambda _hass: object(),
        async_entries_for_config_entry=lambda _registry, _entry_id: [],
    )
    helpers.entity_registry = entity_registry
    aiohttp_client = _module(
        "homeassistant.helpers.aiohttp_client",
        async_get_clientsession=lambda _hass: None,
    )
    helpers.aiohttp_client = aiohttp_client
    dispatcher = _module(
        "homeassistant.helpers.dispatcher",
        async_dispatcher_send=lambda *_args, **_kwargs: None,
    )
    helpers.dispatcher = dispatcher
    event = _module(
        "homeassistant.helpers.event",
        async_call_later=lambda *_args, **_kwargs: lambda: None,
        async_track_state_change_event=lambda *_args, **_kwargs: lambda: None,
        async_track_time_interval=lambda *_args, **_kwargs: lambda: None,
    )
    helpers.event = event

    fixed_now = datetime(2026, 8, 29, 10, 0, tzinfo=timezone.utc)
    util = _module("homeassistant.util")
    util.__path__ = []
    dt_module = _module(
        "homeassistant.util.dt",
        as_local=lambda value: value,
        now=lambda: fixed_now,
        utcnow=lambda: fixed_now,
    )
    util.dt = dt_module
    homeassistant.util = util

    class GWEnergyPilotCoordinator:
        pass

    _module(
        f"{PACKAGE_NAME}.coordinator",
        GWEnergyPilotCoordinator=GWEnergyPilotCoordinator,
    )
    importlib.import_module(f"{PACKAGE_NAME}.const")
    return importlib.import_module(f"{PACKAGE_NAME}.orchestrator_v012")


class FakeState:
    def __init__(self, entity_id: str, attributes: dict | None = None) -> None:
        self.entity_id = entity_id
        self.attributes = dict(attributes or {})
        self.state = "0"


class FakeStates:
    def __init__(self, states: list[FakeState] | None = None) -> None:
        self._states = {state.entity_id: state for state in states or []}

    def get(self, entity_id: str):
        return self._states.get(entity_id)

    def async_all(self):
        return list(self._states.values())


class FakeServices:
    def __init__(self, *, available: bool, outcomes: list[object] | None = None):
        self.available = available
        self.outcomes = list(outcomes or [])
        self.calls = []

    def has_service(self, domain: str, service: str) -> bool:
        return (
            self.available
            and domain == "nordpool"
            and service == "get_prices_for_date"
        )

    async def async_call(self, domain, service, data, **kwargs):
        self.calls.append((domain, service, dict(data), dict(kwargs)))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeConfigEntries:
    def __init__(self) -> None:
        self.nordpool_entry = types.SimpleNamespace(entry_id="nordpool-entry")

    def async_entries(self, domain: str):
        return [self.nordpool_entry] if domain == "nordpool" else []


class FakeHass:
    def __init__(self, services: FakeServices, states: list[FakeState] | None = None):
        self.services = services
        self.states = FakeStates(states)
        self.config_entries = FakeConfigEntries()


class FakeEntry:
    entry_id = "energypilot-entry"

    def __init__(self) -> None:
        self.options = {
            "use_nordpool_prices": True,
            "nordpool_area": "NL",
            "nordpool_currency": "EUR",
        }


def _new_orchestrator(module, services, states=None):
    return module.GWEnergyPilotOrchestrator(
        FakeHass(services, states),
        FakeEntry(),
        object(),
    )


class OrchestratorPriceSourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_transient_official_service_error_is_not_reported_as_missing(self):
        module = _load_orchestrator()
        services = FakeServices(
            available=True,
            outcomes=[module.HomeAssistantError("Nord Pool connection failed")],
        )
        orchestrator = _new_orchestrator(module, services)

        with self.assertRaises(module.HomeAssistantError) as raised:
            await orchestrator._async_price_forecasts()

        self.assertEqual(
            orchestrator.last_price_source,
            "official_nordpool_unavailable",
        )
        self.assertEqual(orchestrator.status, "error_prices")
        self.assertEqual(orchestrator.last_price_points, 0)
        self.assertIsNone(orchestrator.last_price_area)
        self.assertIn("service was found", str(raised.exception))
        self.assertIn("Nord Pool connection failed", str(raised.exception))
        self.assertNotIn(
            "no usable nordpool.get_prices_for_date service",
            str(raised.exception),
        )

    async def test_empty_official_day_is_not_reported_as_missing_service(self):
        module = _load_orchestrator()
        services = FakeServices(available=True, outcomes=[{"NL": []}])
        orchestrator = _new_orchestrator(module, services)

        with self.assertRaises(module.HomeAssistantError) as raised:
            await orchestrator._async_price_forecasts()

        self.assertEqual(
            orchestrator.last_price_source,
            "official_nordpool_unavailable",
        )
        self.assertEqual(orchestrator.last_price_area, "NL")
        self.assertIn(
            "returned no usable prices for today for area NL",
            str(raised.exception),
        )

    async def test_usable_official_service_remains_the_preferred_source(self):
        module = _load_orchestrator()
        services = FakeServices(
            available=True,
            outcomes=[
                {
                    "NL": [
                        {
                            "start": "2026-08-29T10:00:00+00:00",
                            "price": 100.0,
                        }
                    ]
                }
            ],
        )
        orchestrator = _new_orchestrator(module, services)

        load_cost, prod_price = await orchestrator._async_price_forecasts()

        self.assertEqual(orchestrator.last_price_source, "official_nordpool")
        self.assertIsNone(orchestrator.last_price_entity)
        self.assertEqual(orchestrator.last_price_area, "NL")
        self.assertEqual(load_cost, {"2026-08-29T10:00:00+00:00": 0.1})
        self.assertEqual(prod_price, {"2026-08-29T10:00:00+00:00": 0.0752})

    async def test_missing_official_service_keeps_configuration_guidance(self):
        module = _load_orchestrator()
        orchestrator = _new_orchestrator(
            module,
            FakeServices(available=False),
        )

        with self.assertRaises(module.HomeAssistantError) as raised:
            await orchestrator._async_price_forecasts()

        self.assertEqual(orchestrator.last_price_source, "missing")
        self.assertIn(
            "no usable nordpool.get_prices_for_date service",
            str(raised.exception),
        )

    async def test_raw_sensor_remains_a_fallback_after_official_service_error(self):
        module = _load_orchestrator()
        services = FakeServices(
            available=True,
            outcomes=[module.HomeAssistantError("temporary upstream failure")],
        )
        raw_sensor = FakeState(
            "sensor.raw_prices",
            {
                "unit_of_measurement": "EUR/kWh",
                "raw_today": [
                    {
                        "start": "2026-08-29T10:00:00+00:00",
                        "value": 0.1,
                    }
                ],
                "raw_tomorrow": [],
            },
        )
        orchestrator = _new_orchestrator(module, services, [raw_sensor])

        load_cost, prod_price = await orchestrator._async_price_forecasts()

        self.assertEqual(orchestrator.last_price_source, "raw_price_entity")
        self.assertEqual(orchestrator.last_price_entity, "sensor.raw_prices")
        self.assertEqual(load_cost, {"2026-08-29T10:00:00+00:00": 0.1})
        self.assertEqual(prod_price, {"2026-08-29T10:00:00+00:00": 0.0752})


if __name__ == "__main__":
    unittest.main()
