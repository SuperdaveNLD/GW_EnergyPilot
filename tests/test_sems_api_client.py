"""SEMS+ authentication, token renewal and rate-limit regressions."""

from __future__ import annotations

from dataclasses import dataclass
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


def _load_module():
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
    core = _module("homeassistant.core", HomeAssistant=object)
    homeassistant.core = core
    helpers = _module("homeassistant.helpers")
    helpers.__path__ = []
    homeassistant.helpers = helpers
    helpers.aiohttp_client = _module(
        "homeassistant.helpers.aiohttp_client",
        async_get_clientsession=lambda hass: hass.session,
    )

    @dataclass
    class GWETAData:
        values: dict
        source: str = "modbus"
        source_updated_at: datetime | None = None

    _module(f"{PACKAGE_NAME}.client", GWETAData=GWETAData)
    importlib.import_module(f"{PACKAGE_NAME}.sems_model")
    return importlib.import_module(f"{PACKAGE_NAME}.sems_api")


sems_api = _load_module()


class FakeResponse:
    def __init__(self, body, status=200):
        self.body = body
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def json(self, content_type=None):
        return self.body


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if not self.responses:
            raise AssertionError(f"Unexpected HTTP call to {url}")
        return self.responses.pop(0)


class FakeHass:
    def __init__(self, session):
        self.session = session


def _login(token="token-1"):
    return FakeResponse(
        {
            "code": "00000",
            "data": {"token": token, "uid": "user", "region": "eu"},
            "api": "https://eu-gateway.semsportal.com/web/sems",
        }
    )


def _monitor(code="0"):
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    return FakeResponse(
        {
            "code": code,
            "msg": "ok" if code == "0" else "expired",
            "data": {
                "inverter": [
                    {
                        "invert_full": {
                            "sn": "ETA15TEST0001",
                            "last_time": now_ms,
                            "pac": 2200,
                            "pv_power": 2400,
                            "pmeter": -200,
                        }
                    }
                ],
                "isShowBattery": False,
                "powerflow": {"pv": "2400(W)", "load": "2200(W)"},
            },
        }
    )


class SemsApiClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_sems_plus_login_and_cloud_mapping(self) -> None:
        session = FakeSession(_login(), _monitor())
        client = sems_api.GWSemsClient(
            FakeHass(session),
            "visitor@example.com",
            "secret",
            "station-1",
            "ETA15TEST0001",
        )

        snapshot = await client.async_read_data()

        self.assertEqual(snapshot.source, "sems_api")
        self.assertEqual(snapshot.values["pv_total_power"], 2400)
        self.assertEqual(snapshot.values["meter_total_power_fast"], -200)
        self.assertEqual(len(session.calls), 2)
        self.assertNotIn("secret", str(session.calls))
        self.assertIn("eu.semsportal.com/api", session.calls[1][0])

    async def test_expired_token_is_renewed_once(self) -> None:
        session = FakeSession(
            _login("token-1"),
            _monitor("100002"),
            _login("token-2"),
            _monitor(),
        )
        client = sems_api.GWSemsClient(
            FakeHass(session), "user@example.com", "secret", "station-1"
        )

        snapshot = await client.async_read_data()

        self.assertEqual(snapshot.values["total_load_power"], 2200)
        self.assertEqual(len(session.calls), 4)

    async def test_rate_limit_activates_local_backoff_without_new_http(self) -> None:
        session = FakeSession(
            _login(),
            FakeResponse({"code": "GY0429", "msg": "too many requests"}),
        )
        client = sems_api.GWSemsClient(
            FakeHass(session), "user@example.com", "secret", "station-1"
        )

        with self.assertRaises(sems_api.GWSemsRateLimitedError):
            await client.async_read_data()
        with self.assertRaises(sems_api.GWSemsRateLimitedError):
            await client.async_read_data()
        self.assertEqual(len(session.calls), 2)

    async def test_multiple_stations_require_explicit_station_id(self) -> None:
        session = FakeSession(
            _login(),
            FakeResponse({"code": 0, "data": ["station-a", "station-b"]}),
        )
        client = sems_api.GWSemsClient(
            FakeHass(session), "user@example.com", "secret", ""
        )

        with self.assertRaisesRegex(sems_api.GWSemsError, "multiple power stations"):
            await client.async_validate()
        self.assertEqual(len(session.calls), 2)


if __name__ == "__main__":
    unittest.main()
