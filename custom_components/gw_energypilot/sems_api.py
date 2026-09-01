"""Asynchronous SEMS/SEMS+ telemetry client for GW EnergyPilot."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import logging
from time import monotonic
from typing import Any, Mapping

from aiohttp import ClientError

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import GWETAData
from .sems_model import (
    SemsPayloadError,
    SemsStaleDataError,
    encode_sems_plus_password,
    map_sems_telemetry,
    normalize_powerstation_api_base,
    normalize_station_ids,
)

_LOGGER = logging.getLogger(__name__)

SEMS_PLUS_LOGIN_URL = (
    "https://semsplus.goodwe.com/web/sems/sems-user/api/v1/auth/cross-login"
)
SEMS_LEGACY_LOGIN_URL = "https://www.semsportal.com/api/v3/Common/CrossLogin"
SEMS_PLUS_API_FALLBACK = "https://eu-gateway.semsportal.com/web/sems"
SEMS_STATIONS_PATH = "/PowerStation/GetPowerStationIdByOwner"
SEMS_MONITOR_PATH = "/v3/PowerStation/GetMonitorDetailByPowerstationId"
SEMS_REQUEST_TIMEOUT_SECONDS = 30
SEMS_RATE_LIMIT_BACKOFF_SECONDS = 300

_SUCCESS_CODES = {0, "0", "00000"}
_AUTH_CODES = {100001, "100001", 100002, "100002"}
_RATE_LIMIT_CODE = "GY0429"
_BASE_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}


class GWSemsError(Exception):
    """Raised when SEMS telemetry cannot be retrieved safely."""


class GWSemsAuthError(GWSemsError):
    """Raised when both supported SEMS login flows fail."""


class GWSemsRateLimitedError(GWSemsError):
    """Raised when the portal requests a local polling back-off."""


@dataclass(frozen=True, slots=True)
class GWSemsValidation:
    """Resolved SEMS station and inverter identity after validation."""

    station_id: str
    inverter_serial: str


class GWSemsClient:
    """Poll supported SEMS station-type-1 telemetry with token renewal."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        station_id: str,
        inverter_serial: str = "",
    ) -> None:
        self.hass = hass
        self.username = str(username).strip()
        self._password = password
        self.station_id = str(station_id).strip()
        self.inverter_serial = str(inverter_serial).strip()
        self._session = async_get_clientsession(hass)
        self._token: dict[str, Any] | None = None
        self._preferred_login: str | None = None
        self._retry_not_before = 0.0

    async def async_close(self) -> None:
        """Keep the Home Assistant shared HTTP session open."""

    async def _async_request_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        payload: Mapping[str, Any] | None,
        operation: str,
    ) -> dict[str, Any]:
        try:
            async with asyncio.timeout(SEMS_REQUEST_TIMEOUT_SECONDS):
                async with self._session.post(
                    url,
                    headers=dict(headers),
                    json=dict(payload) if payload is not None else None,
                ) as response:
                    status = response.status
                    try:
                        body = await response.json(content_type=None)
                    except (TypeError, ValueError) as err:
                        raise GWSemsError(
                            f"{operation} returned an invalid JSON response"
                        ) from err
        except (TimeoutError, ClientError) as err:
            raise GWSemsError(f"{operation} failed: {err}") from err

        if status < 200 or status >= 300:
            raise GWSemsError(f"{operation} returned HTTP {status}")
        if not isinstance(body, dict):
            raise GWSemsError(f"{operation} returned an invalid response object")
        return body

    @staticmethod
    def _token_from_login(
        response: Mapping[str, Any],
        *,
        fallback_api: str | None = None,
    ) -> dict[str, Any] | None:
        if response.get("code") not in _SUCCESS_CODES:
            return None
        data = response.get("data")
        if not isinstance(data, Mapping) or not data.get("token"):
            return None
        api = response.get("api") or data.get("api") or fallback_api
        if not isinstance(api, str) or not api.strip():
            return None
        token = dict(data)
        token["api"] = api.rstrip("/")
        return token

    async def _async_login_sems_plus(self) -> dict[str, Any] | None:
        response = await self._async_request_json(
            SEMS_PLUS_LOGIN_URL,
            headers=_BASE_HEADERS,
            payload={
                "account": self.username,
                "pwd": encode_sems_plus_password(self._password),
                "agreement": 1,
                "isChinese": False,
                "isLocal": False,
            },
            operation="SEMS+ login",
        )
        return self._token_from_login(response, fallback_api=SEMS_PLUS_API_FALLBACK)

    async def _async_login_legacy(self) -> dict[str, Any] | None:
        response = await self._async_request_json(
            SEMS_LEGACY_LOGIN_URL,
            headers={
                **_BASE_HEADERS,
                "token": json.dumps(
                    {"version": "3.1.1", "client": "ios", "language": "en"}
                ),
            },
            payload={"account": self.username, "pwd": self._password},
            operation="legacy SEMS login",
        )
        return self._token_from_login(response)

    async def async_authenticate(self, *, force: bool = False) -> None:
        """Authenticate with SEMS+, retaining legacy login compatibility."""
        if self._token is not None and not force:
            return
        modes = ["sems_plus", "legacy"]
        if self._preferred_login in modes:
            modes.remove(self._preferred_login)
            modes.insert(0, self._preferred_login)

        failures: list[str] = []
        for mode in modes:
            try:
                token = (
                    await self._async_login_sems_plus()
                    if mode == "sems_plus"
                    else await self._async_login_legacy()
                )
            except GWSemsError as err:
                failures.append(f"{mode}: {err}")
                continue
            if token is not None:
                self._token = token
                self._preferred_login = mode
                return
            failures.append(f"{mode}: credentials rejected")

        self._token = None
        _LOGGER.warning(
            "SEMS authentication failed for the configured account (%s)",
            "; ".join(failures),
        )
        raise GWSemsAuthError(
            "SEMS authentication failed; verify the account, password and accepted EULA"
        )

    def _authenticated_context(self, path: str) -> tuple[str, dict[str, str]]:
        token = self._token
        if token is None:
            raise GWSemsAuthError("SEMS token is unavailable")
        api = str(token.get("api") or "")
        region = token.get("region")
        base = normalize_powerstation_api_base(
            api,
            region=str(region) if isinstance(region, str) else None,
        )
        return (
            f"{base}{path}",
            {**_BASE_HEADERS, "token": json.dumps(token, separators=(",", ":"))},
        )

    async def _async_api_call(
        self,
        path: str,
        *,
        payload: Mapping[str, Any] | None,
        operation: str,
        renew_attempted: bool = False,
    ) -> Any:
        if monotonic() < self._retry_not_before:
            remaining = max(1, int(self._retry_not_before - monotonic()))
            raise GWSemsRateLimitedError(
                f"SEMS API back-off is active for another {remaining} seconds"
            )
        await self.async_authenticate()
        url, headers = self._authenticated_context(path)
        response = await self._async_request_json(
            url,
            headers=headers,
            payload=payload,
            operation=operation,
        )
        code = response.get("code")
        if str(code) == _RATE_LIMIT_CODE:
            self._retry_not_before = monotonic() + SEMS_RATE_LIMIT_BACKOFF_SECONDS
            raise GWSemsRateLimitedError(
                f"SEMS API rate limited; retry after {SEMS_RATE_LIMIT_BACKOFF_SECONDS} seconds"
            )
        if code in _AUTH_CODES and not renew_attempted:
            self._token = None
            await self.async_authenticate(force=True)
            return await self._async_api_call(
                path,
                payload=payload,
                operation=operation,
                renew_attempted=True,
            )
        if code not in _SUCCESS_CODES:
            message = str(response.get("msg") or response.get("description") or "")
            if code in _AUTH_CODES:
                raise GWSemsAuthError(
                    "SEMS accepted the login but rejected station telemetry after token "
                    "renewal; the station type may not support this beta endpoint"
                )
            raise GWSemsError(
                f"{operation} failed with SEMS code {code}: {message[:160]}"
            )
        data = response.get("data")
        if data in (None, ""):
            raise GWSemsError(f"{operation} returned no data")
        return data

    async def async_get_station_ids(self) -> tuple[str, ...]:
        """Return all stations visible to the configured account."""
        raw = await self._async_api_call(
            SEMS_STATIONS_PATH,
            payload=None,
            operation="SEMS station discovery",
        )
        return normalize_station_ids(raw)

    async def _async_get_monitor_data(self, station_id: str) -> Mapping[str, Any]:
        data = await self._async_api_call(
            SEMS_MONITOR_PATH,
            payload={"powerStationId": station_id},
            operation="SEMS monitor telemetry",
        )
        if not isinstance(data, Mapping):
            raise GWSemsError("SEMS monitor telemetry returned an invalid data object")
        return data

    async def async_validate(self) -> GWSemsValidation:
        """Validate credentials and resolve one unambiguous station/inverter."""
        await self.async_authenticate()
        station_id = self.station_id
        if not station_id:
            stations = await self.async_get_station_ids()
            if not stations:
                raise GWSemsError("The SEMS account has no visible power stations")
            if len(stations) != 1:
                raise GWSemsError(
                    "The SEMS account has multiple power stations; configure the station ID"
                )
            station_id = stations[0]

        payload = await self._async_get_monitor_data(station_id)
        try:
            try:
                mapped = map_sems_telemetry(payload, self.inverter_serial)
            except SemsStaleDataError:
                # Configuration must remain possible while an inverter is asleep or
                # offline. Runtime polling still enforces the normal 15-minute gate.
                mapped = map_sems_telemetry(
                    payload,
                    self.inverter_serial,
                    max_age_seconds=10 * 365 * 24 * 60 * 60,
                )
        except SemsPayloadError as err:
            raise GWSemsError(str(err)) from err
        return GWSemsValidation(station_id, mapped.inverter_serial)

    async def async_read_data(self) -> GWETAData:
        """Read and normalize one fresh SEMS telemetry snapshot."""
        if not self.station_id:
            raise GWSemsError("SEMS station ID is not configured")
        payload = await self._async_get_monitor_data(self.station_id)
        try:
            mapped = map_sems_telemetry(payload, self.inverter_serial)
        except SemsPayloadError as err:
            raise GWSemsError(str(err)) from err
        return GWETAData(
            values=mapped.values,
            source="sems_api",
            source_updated_at=mapped.source_updated_at,
        )
