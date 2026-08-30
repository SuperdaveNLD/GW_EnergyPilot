"""Regression tests for isolated EV charger load balancing."""

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


class FakeStore:
    data_by_key: dict[str, dict] = {}

    def __class_getitem__(cls, _item):
        return cls

    def __init__(self, _hass, _version, key):
        self.key = key

    async def async_load(self):
        return self.data_by_key.get(self.key)

    async def async_save(self, data):
        self.data_by_key[self.key] = dict(data)


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
    core = _module(
        "homeassistant.core",
        Event=object,
        HomeAssistant=object,
        callback=lambda func: func,
    )
    homeassistant.core = core
    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    homeassistant.helpers = helpers
    dispatcher = _module(
        "homeassistant.helpers.dispatcher", async_dispatcher_send=lambda *_args: None
    )
    helpers.dispatcher = dispatcher
    scheduled = []

    def async_call_later(_hass, delay, callback):
        scheduled.append((delay, callback))
        return lambda: None

    event = _module(
        "homeassistant.helpers.event",
        async_call_later=async_call_later,
        async_track_state_change_event=lambda *_args: (lambda: None),
    )
    helpers.event = event
    storage = _module("homeassistant.helpers.storage", Store=FakeStore)
    helpers.storage = storage
    return importlib.import_module(f"{PACKAGE_NAME}.ev_load_balancing"), scheduled


class FakeState:
    def __init__(self, state, unit="A", **attributes):
        self.state = state
        self.attributes = {"unit_of_measurement": unit, **attributes}


class FakeStates:
    def __init__(self, states):
        self.states = states

    def get(self, entity_id):
        return self.states.get(entity_id)


class FakeServices:
    def __init__(self):
        self.calls = []

    async def async_call(self, domain, service, data, *, blocking):
        self.calls.append((domain, service, data, blocking))


class FakeHass:
    def __init__(self, states):
        self.states = FakeStates(states)
        self.services = FakeServices()


class FakeEntry:
    entry_id = "entry-ev"

    def __init__(self, options):
        self.options = options

    def async_create_background_task(self, *_args):
        raise AssertionError("background task not expected in direct evaluation tests")


def options(**overrides):
    values = {
        "enable_ev_load_balancing": True,
        "grid_connection_profile": "3x25",
        "grid_custom_current": 25,
        "ev_grid_current_entity": "sensor.grid_l1",
        "ev_charger_current_entity": "number.charger_limit",
        "ev_charger_min_current": 6,
        "ev_charger_max_current": 16,
        "ev_load_balance_window": 5,
    }
    values.update(overrides)
    return values


class EVLoadBalancingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeStore.data_by_key = {}

    async def test_connection_profiles_and_custom_current_are_per_phase(self):
        module, _scheduled = _load_module()
        self.assertEqual(module.grid_connection_limit(options()), 25)
        self.assertEqual(module.grid_connection_phases(options()), 3)
        self.assertEqual(
            module.grid_connection_limit(
                options(grid_connection_profile="custom_1_phase", grid_custom_current=32)
            ),
            32,
        )
        self.assertEqual(
            module.grid_connection_phases(
                options(grid_connection_profile="custom_1_phase")
            ),
            1,
        )
        self.assertEqual(
            module.grid_connection_limit(
                options(grid_connection_profile="custom_3_phase", grid_custom_current=50)
            ),
            50,
        )

    async def test_sustained_overload_reduces_only_charger_number(self):
        module, scheduled = _load_module()
        hass = FakeHass({
            "sensor.grid_l1": FakeState(28),
            "number.charger_limit": FakeState(16, min=6, max=32, step=1),
        })
        balancer = module.GWEnergyPilotEVLoadBalancer(hass, FakeEntry(options()))

        await balancer.async_evaluate()
        self.assertEqual(scheduled[0][0], 300)
        self.assertEqual(hass.services.calls, [])
        await scheduled[0][1](datetime.now(timezone.utc))

        self.assertEqual(
            hass.services.calls,
            [("number", "set_value", {"entity_id": "number.charger_limit", "value": 13.0}, True)],
        )
        self.assertFalse(balancer.diagnostics["goodwe_control"])

    async def test_headroom_uses_same_window_before_increasing(self):
        module, scheduled = _load_module()
        hass = FakeHass({
            "sensor.grid_l1": FakeState(20),
            "number.charger_limit": FakeState(10, min=6, max=32, step=1),
        })
        balancer = module.GWEnergyPilotEVLoadBalancer(hass, FakeEntry(options()))
        await balancer.async_evaluate()
        await scheduled[0][1](datetime.now(timezone.utc))
        self.assertEqual(hass.services.calls[0][2]["value"], 15.0)

    async def test_external_limit_above_configured_maximum_is_clamped_immediately(self):
        module, scheduled = _load_module()
        hass = FakeHass({
            "sensor.grid_l1": FakeState(24),
            "number.charger_limit": FakeState(20, min=6, max=32, step=1),
        })
        balancer = module.GWEnergyPilotEVLoadBalancer(hass, FakeEntry(options()))
        await balancer.async_evaluate()
        self.assertEqual(scheduled, [])
        self.assertEqual(hass.services.calls[0][2]["value"], 16.0)
        self.assertEqual(balancer.last_action, "clamped_to_configured_maximum")

    async def test_unavailable_measurement_never_writes(self):
        module, scheduled = _load_module()
        hass = FakeHass({
            "sensor.grid_l1": FakeState("unavailable"),
            "number.charger_limit": FakeState(16, min=6, max=32, step=1),
        })
        balancer = module.GWEnergyPilotEVLoadBalancer(hass, FakeEntry(options()))
        await balancer.async_evaluate()
        self.assertEqual(balancer.status, "unavailable")
        self.assertEqual(scheduled, [])
        self.assertEqual(hass.services.calls, [])

    async def test_non_current_units_never_write(self):
        module, scheduled = _load_module()
        hass = FakeHass({
            "sensor.grid_l1": FakeState(2800, unit="W"),
            "number.charger_limit": FakeState(16, min=6, max=32, step=1),
        })
        balancer = module.GWEnergyPilotEVLoadBalancer(hass, FakeEntry(options()))
        await balancer.async_evaluate()
        self.assertEqual(balancer.status, "unavailable")
        self.assertEqual(scheduled, [])
        self.assertEqual(hass.services.calls, [])

    async def test_configured_maximum_is_enforced_when_measurement_is_unavailable(self):
        module, _scheduled = _load_module()
        hass = FakeHass({
            "sensor.grid_l1": FakeState("unavailable"),
            "number.charger_limit": FakeState(20, min=6, max=32, step=1),
        })
        balancer = module.GWEnergyPilotEVLoadBalancer(hass, FakeEntry(options()))
        await balancer.async_evaluate()
        self.assertEqual(hass.services.calls[0][2]["value"], 16.0)

    async def test_high_current_audit_never_truncates_earlier_confirmations(self):
        module, _scheduled = _load_module()
        audit = module.EVLoadBalancingAudit(object(), "entry-ev")
        await audit.async_append({"maximum_a": 20})
        await audit.async_append({"maximum_a": 25})
        restored = module.EVLoadBalancingAudit(object(), "entry-ev")
        self.assertEqual(
            await restored.async_history(),
            [{"maximum_a": 20}, {"maximum_a": 25}],
        )

    def test_actuator_ownership_is_bounded_to_home_assistant_number(self):
        source = (PACKAGE_DIR / "ev_load_balancing.py").read_text(encoding="utf-8")
        self.assertNotIn("GWModbusClient", source)
        self.assertNotIn("REGISTER_EMS_", source)
        self.assertIn('"number",\n                "set_value"', source)


if __name__ == "__main__":
    unittest.main()
