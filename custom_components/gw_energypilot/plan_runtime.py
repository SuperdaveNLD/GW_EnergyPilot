"""Persistent canonical EMHASS plan cache for GW EnergyPilot."""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from typing import Any, Mapping

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .battery_plan import (
    finite_number,
    infer_plan_step_seconds,
    normalize_emhass_api_plan,
    normalize_emhass_forecasts,
    normalized_timestamp,
    plan_percentage_at,
    plan_valid_until,
    plan_value_at,
)
from .const import (
    CONF_EMHASS_URL,
    CONF_P_BATT_ENTITY,
    CONF_P_GRID_ENTITY,
    DEFAULT_EMHASS_URL,
    DEFAULT_P_BATT_ENTITY,
    DEFAULT_P_GRID_ENTITY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLAN_STORE_VERSION = 1
PLAN_STORE_KEY = f"{DOMAIN}.plan"
PLAN_API_TIMEOUT_SECONDS = 8
STARTUP_REFRESH_DELAYS = (0, 5, 15, 30, 60)


class GWEnergyPilotPlanRuntime:
    """Mirror the latest valid EMHASS plan across HA reloads and restarts.

    EMHASS remains the canonical owner of optimization results. EnergyPilot reads
    the official persistent ``GET /api/v1/plan`` snapshot and keeps a local
    mirror only so controller/dashboard operation is not coupled to the
    lifecycle of externally published Home Assistant entities.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._store = Store[dict[str, Any]](
            hass,
            PLAN_STORE_VERSION,
            f"{PLAN_STORE_KEY}.{entry.entry_id}",
        )
        self._snapshot: dict[str, Any] | None = None
        self._lock = asyncio.Lock()
        self.last_error: str | None = None
        self.restored_from_store = False

    async def async_restore(self) -> None:
        """Restore the last mirrored plan without contacting EMHASS."""
        stored = await self._store.async_load()
        snapshot = self._validated_snapshot(stored)
        if snapshot is None:
            return
        self._snapshot = snapshot
        self.restored_from_store = True

    async def async_startup_refresh(self) -> None:
        """Refresh from EMHASS after startup, retrying while dependencies settle."""
        for delay in STARTUP_REFRESH_DELAYS:
            if delay:
                await asyncio.sleep(delay)
            if await self.async_refresh(reason="startup"):
                return

    def _emhass_url(self) -> str:
        return str(
            self.entry.options.get(CONF_EMHASS_URL, DEFAULT_EMHASS_URL)
            or DEFAULT_EMHASS_URL
        ).strip().rstrip("/")

    def _p_batt_entity_id(self) -> str:
        return str(
            self.entry.options.get(CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY)
            or DEFAULT_P_BATT_ENTITY
        )

    def _p_grid_entity_id(self) -> str:
        return str(
            self.entry.options.get(CONF_P_GRID_ENTITY, DEFAULT_P_GRID_ENTITY)
            or DEFAULT_P_GRID_ENTITY
        )

    @staticmethod
    def _iso_timestamp(value: Any) -> str | None:
        parsed = normalized_timestamp(value)
        return parsed[0] if parsed is not None else None

    @staticmethod
    def _timestamp_seconds(value: Any) -> float | None:
        parsed = normalized_timestamp(value)
        return parsed[1] if parsed is not None else None

    def _build_snapshot(
        self,
        *,
        source: str,
        generated_at: Any,
        emhass_schema_version: str | None,
        p_batt: list[dict[str, Any]],
        p_grid: list[dict[str, Any]],
        p_pv: list[dict[str, Any]],
        p_load: list[dict[str, Any]],
        soc_opt: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not p_batt:
            return None
        validated_soc: list[dict[str, Any]] = []
        for point in soc_opt:
            parsed = normalized_timestamp(point.get("start"))
            percentage = finite_number(point.get("value_pct"))
            if (
                parsed is None
                or percentage is None
                or not 0.0 <= percentage <= 100.0
            ):
                continue
            validated_soc.append(
                {"start": parsed[0], "value_pct": round(percentage, 3)}
            )
        step_seconds = infer_plan_step_seconds(p_batt, p_grid, validated_soc)
        valid_until = plan_valid_until(p_batt, step_seconds)
        if step_seconds is None or valid_until is None:
            return None
        generated = self._iso_timestamp(generated_at) or dt_util.utcnow().isoformat()
        return {
            "source": source,
            "generated_at": generated,
            "emhass_schema_version": emhass_schema_version,
            "step_seconds": step_seconds,
            "valid_until": valid_until.isoformat(),
            "p_batt_entity_id": self._p_batt_entity_id(),
            "p_grid_entity_id": self._p_grid_entity_id(),
            "p_batt": [dict(point) for point in p_batt],
            "p_grid": [dict(point) for point in p_grid],
            "p_pv": [dict(point) for point in p_pv],
            "p_load": [dict(point) for point in p_load],
            "soc_opt": validated_soc,
        }

    def _validated_snapshot(self, value: Any) -> dict[str, Any] | None:
        if not isinstance(value, Mapping):
            return None
        p_batt = value.get("p_batt")
        p_grid = value.get("p_grid", [])
        p_pv = value.get("p_pv", [])
        p_load = value.get("p_load", [])
        soc_opt = value.get("soc_opt", [])
        if (
            not isinstance(p_batt, list)
            or not isinstance(p_grid, list)
            or not isinstance(p_pv, list)
            or not isinstance(p_load, list)
            or not isinstance(soc_opt, list)
        ):
            return None
        snapshot = self._build_snapshot(
            source=str(value.get("source") or "store"),
            generated_at=value.get("generated_at"),
            emhass_schema_version=(
                str(value.get("emhass_schema_version"))
                if value.get("emhass_schema_version") is not None
                else None
            ),
            p_batt=[dict(point) for point in p_batt if isinstance(point, Mapping)],
            p_grid=[dict(point) for point in p_grid if isinstance(point, Mapping)],
            p_pv=[dict(point) for point in p_pv if isinstance(point, Mapping)],
            p_load=[dict(point) for point in p_load if isinstance(point, Mapping)],
            soc_opt=[dict(point) for point in soc_opt if isinstance(point, Mapping)],
        )
        return snapshot

    def _snapshot_valid_until_seconds(self, snapshot: Mapping[str, Any] | None) -> float | None:
        if not snapshot:
            return None
        return self._timestamp_seconds(snapshot.get("valid_until"))

    async def _async_accept_snapshot(
        self,
        snapshot: dict[str, Any] | None,
        *,
        official: bool,
    ) -> bool:
        if snapshot is None:
            return False

        current = self._snapshot
        if current is not None and not official:
            # Continual HA publication exposes an ever-shrinking remainder of
            # the same plan. Never replace a longer canonical snapshot merely
            # because its current-row entity was republished later.
            current_until = self._snapshot_valid_until_seconds(current) or 0
            candidate_until = self._snapshot_valid_until_seconds(snapshot) or 0
            if candidate_until <= current_until:
                return False

        self._snapshot = snapshot
        self.restored_from_store = False
        await self._store.async_save(dict(snapshot))
        return True

    async def _async_official_snapshot(self) -> dict[str, Any] | None:
        base_url = self._emhass_url()
        if not base_url:
            self.last_error = "EMHASS URL is empty"
            return None

        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(PLAN_API_TIMEOUT_SECONDS):
                async with session.get(f"{base_url}/api/v1/plan") as response:
                    if response.status != 200:
                        self.last_error = f"EMHASS plan HTTP {response.status}"
                        return None
                    payload = await response.json(content_type=None)
        except (TimeoutError, ClientError, ValueError) as err:
            self.last_error = str(err)
            return None

        if not isinstance(payload, Mapping):
            self.last_error = "EMHASS plan response is not an object"
            return None
        if payload.get("status") != "ok":
            self.last_error = "EMHASS has no persisted optimization plan yet"
            return None

        schema_version = str(payload.get("emhass_schema_version") or "")
        try:
            schema_major = int(schema_version.split(".", 1)[0])
        except (TypeError, ValueError):
            schema_major = 0
        if schema_major != 1:
            self.last_error = (
                f"Unsupported EMHASS plan schema {schema_version or 'unknown'}"
            )
            return None

        normalized = normalize_emhass_api_plan(payload)
        snapshot = self._build_snapshot(
            source="emhass_api_v1_plan",
            generated_at=payload.get("generated_at"),
            emhass_schema_version=schema_version,
            p_batt=normalized["p_batt"],
            p_grid=normalized["p_grid"],
            p_pv=normalized["p_pv"],
            p_load=normalized["p_load"],
            soc_opt=normalized["soc_opt"],
        )
        if snapshot is None:
            self.last_error = "EMHASS plan contains no usable P_batt horizon"
        return snapshot

    def _ha_snapshot(self) -> dict[str, Any] | None:
        p_batt_state = self.hass.states.get(self._p_batt_entity_id())
        p_grid_state = self.hass.states.get(self._p_grid_entity_id())
        if p_batt_state is None:
            return None
        p_batt = normalize_emhass_forecasts(
            self._p_batt_entity_id(), p_batt_state.attributes
        )
        p_grid = (
            normalize_emhass_forecasts(self._p_grid_entity_id(), p_grid_state.attributes)
            if p_grid_state is not None
            else []
        )
        if not p_batt:
            return None
        generated_at = max(
            (
                state.last_updated
                for state in (p_batt_state, p_grid_state)
                if state is not None
            ),
            default=dt_util.utcnow(),
        )
        return self._build_snapshot(
            source="home_assistant_schedule_fallback",
            generated_at=generated_at,
            emhass_schema_version=None,
            p_batt=p_batt,
            p_grid=p_grid,
            p_pv=[],
            p_load=[],
            # The HA fallback does not expose a configured SOC-forecast entity.
            # Do not guess the default/custom EMHASS output entity here.
            soc_opt=[],
        )

    async def async_refresh(self, *, reason: str) -> bool:
        """Refresh the mirror without deleting a still-valid cached plan on failure."""
        async with self._lock:
            official = await self._async_official_snapshot()
            if official is not None:
                accepted = await self._async_accept_snapshot(official, official=True)
                self.last_error = None
                _LOGGER.debug(
                    "Refreshed EnergyPilot EMHASS plan from official API: reason=%s",
                    reason,
                )
                return accepted or self.has_current_plan()

            fallback = self._ha_snapshot()
            if fallback is not None:
                accepted = await self._async_accept_snapshot(fallback, official=False)
                if accepted:
                    self.last_error = None
                    _LOGGER.debug(
                        "Refreshed EnergyPilot EMHASS plan from HA fallback: reason=%s",
                        reason,
                    )
                return accepted or self.has_current_plan()

            return self.has_current_plan()

    def current_value(self, key: str, now: datetime | None = None) -> float | None:
        """Return the current cached P_batt/P_grid target while the plan is valid."""
        snapshot = self._snapshot
        if snapshot is None:
            return None
        points = snapshot.get(key)
        if not isinstance(points, list):
            return None
        step_seconds = snapshot.get("step_seconds")
        try:
            step = int(step_seconds)
        except (TypeError, ValueError):
            return None
        return plan_value_at(points, now or dt_util.utcnow(), step)

    def current_p_batt(self) -> float | None:
        """Return the current persisted P_batt target."""
        return self.current_value("p_batt")

    def current_p_grid(self) -> float | None:
        """Return the current persisted P_grid target."""
        return self.current_value("p_grid")

    def current_soc_opt(self) -> float | None:
        """Return the current persisted desired SOC percentage."""
        snapshot = self._snapshot
        if snapshot is None:
            return None
        points = snapshot.get("soc_opt")
        if not isinstance(points, list):
            return None
        try:
            step = int(snapshot.get("step_seconds"))
        except (TypeError, ValueError):
            return None
        return plan_percentage_at(points, dt_util.utcnow(), step)

    def current_step_seconds(self) -> int | None:
        """Return the inferred timestep for a plan that is valid now."""
        if not self.has_current_plan() or self._snapshot is None:
            return None
        try:
            step = int(self._snapshot.get("step_seconds"))
        except (TypeError, ValueError):
            return None
        return step if step > 0 else None

    def has_current_plan(self) -> bool:
        """Return whether the mirrored battery plan contains a target for now."""
        return self.current_p_batt() is not None

    def points(self, key: str) -> list[dict[str, Any]]:
        """Return a copy of a still-current full plan series for dashboard use."""
        if not self.has_current_plan() or self._snapshot is None:
            return []
        points = self._snapshot.get(key)
        return [dict(point) for point in points] if isinstance(points, list) else []

    @property
    def diagnostics(self) -> dict[str, Any]:
        """Return plan-source evidence without exposing EMHASS connection details."""
        snapshot = self._snapshot or {}
        return {
            "available": self.has_current_plan(),
            "source": snapshot.get("source"),
            "generated_at": snapshot.get("generated_at"),
            "valid_until": snapshot.get("valid_until"),
            "step_seconds": snapshot.get("step_seconds"),
            "p_batt_points": len(snapshot.get("p_batt") or []),
            "p_grid_points": len(snapshot.get("p_grid") or []),
            "p_pv_points": len(snapshot.get("p_pv") or []),
            "p_load_points": len(snapshot.get("p_load") or []),
            "soc_opt_points": len(snapshot.get("soc_opt") or []),
            "restored_from_store": self.restored_from_store,
            "last_error": self.last_error,
        }
