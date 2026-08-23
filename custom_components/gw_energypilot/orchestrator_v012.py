"""Reliability refinements for the native GW EnergyPilot EMHASS orchestrator."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import html
import json
import logging
import math
import re
from typing import Any

from aiohttp import ClientError

from homeassistant.core import CoreState, Event, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BUY_PRICE_ADDER,
    CONF_EMHASS_FALLBACK_LOAD,
    CONF_EMHASS_OPTIMIZATION_INTERVAL,
    CONF_EMHASS_URL,
    CONF_SELL_PRICE_DEDUCTION,
    CONF_USE_NORDPOOL_PRICES,
    DEFAULT_BUY_PRICE_ADDER,
    DEFAULT_EMHASS_FALLBACK_LOAD,
    DEFAULT_EMHASS_OPTIMIZATION_INTERVAL,
    DEFAULT_EMHASS_URL,
    DEFAULT_SELL_PRICE_DEDUCTION,
    DEFAULT_USE_NORDPOOL_PRICES,
)
from .orchestrator import GWEnergyPilotOrchestrator as _BaseOrchestrator

_LOGGER = logging.getLogger(__name__)

LOAD_FORECAST_HOURS = 24
PRICE_LISTENER_RETRY_SECONDS = 90


class GWEnergyPilotOrchestrator(_BaseOrchestrator):
    """Run EMHASS with startup guards, compatible prices and concise errors."""

    def __init__(self, hass, entry, coordinator) -> None:
        super().__init__(hass, entry, coordinator)
        self.last_price_source = "not_checked"
        self.last_price_entity: str | None = None
        self.emhass_health_status: str | None = None
        self.emhass_version: str | None = None

    @property
    def attributes(self) -> dict[str, Any]:
        """Return base diagnostics plus v0.12 troubleshooting context."""
        attrs = super().attributes
        attrs.update(
            {
                "price_runtime_source": self.last_price_source,
                "price_entity": self.last_price_entity,
                "emhass_health": self.emhass_health_status,
                "emhass_version": self.emhass_version,
                "calculated_home_power": self._calculated_home_power(),
                "parallel_goodwe_entries": [
                    config_entry.title
                    for config_entry in self.hass.config_entries.async_entries("goodwe")
                    if config_entry.disabled_by is None
                ],
            }
        )
        return attrs

    async def async_setup(self) -> None:
        """Start recurring and event-driven optimization without a startup run."""
        if not self.enabled:
            self._set_status("manual_only")
            return

        if self._legacy_yaml_present():
            self._set_status(
                "legacy_yaml_detected",
                "A legacy EnergyPilot EMHASS YAML scheduler is still loaded.",
            )
            return

        interval = int(
            self.entry.options.get(
                CONF_EMHASS_OPTIMIZATION_INTERVAL,
                DEFAULT_EMHASS_OPTIMIZATION_INTERVAL,
            )
        )
        interval = max(5, min(60, interval))
        self._unsubs.append(
            async_track_time_interval(
                self.hass,
                self._async_scheduled_optimize,
                timedelta(minutes=interval),
                name=f"GW EnergyPilot EMHASS optimization ({self.entry.entry_id})",
                cancel_on_shutdown=True,
            )
        )

        # Do not optimize during Home Assistant startup. EMHASS may query HA
        # entities while other integrations are still unavailable. The first
        # plan is created by Optimize now, AUTO, an event trigger, or the first
        # normal interval after Home Assistant reaches RUNNING.
        if self.price_automation_enabled:
            self._register_price_trigger_listener()
            self._unsubs.append(
                async_call_later(
                    self.hass,
                    PRICE_LISTENER_RETRY_SECONDS,
                    self._async_refresh_price_trigger_listener,
                )
            )

        self._set_status("scheduled")

    @staticmethod
    def _safe_number(value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    def _calculated_home_power(self) -> float | None:
        """Calculate whole-home demand from PV, grid and battery power."""
        if not self.coordinator.data:
            return None
        values = self.coordinator.data.values
        pv = self._safe_number(values.get("pv_total_power"))
        grid = self._safe_number(values.get("meter_total_power_fast"))
        battery = self._safe_number(values.get("battery_power"))
        if pv is None or grid is None or battery is None:
            return None

        # GoodWe convention used by EnergyPilot:
        # grid positive = export, negative = import
        # battery positive = discharge, negative = charge
        home = pv - grid + battery
        if not math.isfinite(home) or home < 0 or home > 30000:
            return None
        return round(home, 0)

    def _build_load_forecast(
        self,
        rows: list[dict[str, Any]],
        current_load: float | None,
    ) -> dict[str, float]:
        """Build the tested 24-hour forecast with an inclusive end point."""
        calculated_home = self._calculated_home_power()
        if calculated_home is not None:
            current_load = calculated_home

        fallback = float(
            self.entry.options.get(
                CONF_EMHASS_FALLBACK_LOAD,
                DEFAULT_EMHASS_FALLBACK_LOAD,
            )
        )
        if current_load is None or current_load < 50 or current_load > 30000:
            current_load = fallback

        parsed_rows: list[tuple[datetime, float]] = []
        for row in rows:
            try:
                row_dt = datetime.fromisoformat(str(row["start"]))
                mean = float(row["mean"])
            except (KeyError, TypeError, ValueError):
                continue
            if not math.isfinite(mean) or mean < 50 or mean > 30000:
                continue
            parsed_rows.append((dt_util.as_local(row_dt), mean))

        start = dt_util.now().replace(minute=0, second=0, microsecond=0)
        forecast: dict[str, float] = {}
        for offset in range(LOAD_FORECAST_HOURS + 1):
            target = start + timedelta(hours=offset)
            matching = [
                mean for row_dt, mean in parsed_rows if row_dt.hour == target.hour
            ]
            value = sum(matching) / len(matching) if matching else current_load
            forecast[target.isoformat()] = round(value, 0)
        return forecast

    def _discover_raw_price_entity(self) -> str | None:
        """Find a Nord Pool sensor exposing raw_today/raw_tomorrow attributes."""
        preferred = "sensor.nordpool_kwh_nl_eur_3_10_021"
        preferred_state = self.hass.states.get(preferred)
        if preferred_state is not None and isinstance(
            preferred_state.attributes.get("raw_today"), list
        ):
            return preferred

        for state in self.hass.states.async_all():
            if not state.entity_id.startswith("sensor."):
                continue
            if isinstance(state.attributes.get("raw_today"), list):
                return state.entity_id
        return None

    def _raw_price_forecasts(
        self, entity_id: str
    ) -> tuple[dict[str, float], dict[str, float]]:
        state = self.hass.states.get(entity_id)
        if state is None:
            return {}, {}

        rows = list(state.attributes.get("raw_today") or []) + list(
            state.attributes.get("raw_tomorrow") or []
        )
        buy_adder = float(
            self.entry.options.get(CONF_BUY_PRICE_ADDER, DEFAULT_BUY_PRICE_ADDER)
        )
        sell_deduction = float(
            self.entry.options.get(
                CONF_SELL_PRICE_DEDUCTION,
                DEFAULT_SELL_PRICE_DEDUCTION,
            )
        )
        unit = str(state.attributes.get("unit_of_measurement", "")).lower()

        load_cost: dict[str, float] = {}
        prod_price: dict[str, float] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            timestamp = row.get("start")
            raw_price = row.get("value", row.get("price"))
            price = self._safe_number(raw_price)
            if timestamp is None or price is None:
                continue
            if "mwh" in unit or (not unit and abs(price) > 5):
                price /= 1000.0
            key = str(timestamp)
            load_cost[key] = round(price + buy_adder, 5)
            prod_price[key] = round(price - sell_deduction, 5)
        return load_cost, prod_price

    async def _async_price_forecasts(
        self,
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Prefer official Nord Pool, then support raw_today/raw_tomorrow."""
        if not bool(
            self.entry.options.get(
                CONF_USE_NORDPOOL_PRICES,
                DEFAULT_USE_NORDPOOL_PRICES,
            )
        ):
            self.last_price_source = "emhass_config"
            self.last_price_entity = None
            return {}, {}

        load_cost, prod_price = await super()._async_price_forecasts()
        if load_cost and prod_price:
            self.last_price_source = "official_nordpool"
            self.last_price_entity = None
            return load_cost, prod_price

        entity_id = self._discover_raw_price_entity()
        if entity_id:
            load_cost, prod_price = self._raw_price_forecasts(entity_id)
            if load_cost and prod_price:
                self.last_price_source = "raw_price_entity"
                self.last_price_entity = entity_id
                self.last_price_area = entity_id
                self.last_price_points = len(load_cost)
                return load_cost, prod_price

        self.last_price_source = "missing"
        self.last_price_entity = entity_id
        self.last_price_points = 0
        error = (
            "Official Nord Pool runtime pricing is enabled, but no usable "
            "nordpool.get_prices_for_date service or raw_today/raw_tomorrow "
            "price sensor was found. Configure a supported Nord Pool source or "
            "disable runtime prices so EMHASS uses its own price configuration."
        )
        self._set_status("error_prices", error)
        raise HomeAssistantError(error)

    def _discover_tomorrow_price_entities(self) -> list[str]:
        entity_ids = set(super()._discover_tomorrow_price_entities())
        if raw_entity := self._discover_raw_price_entity():
            entity_ids.add(raw_entity)
        return sorted(entity_ids)

    def _tomorrow_prices_available(self) -> bool:
        for entity_id in self.price_trigger_entities:
            state = self.hass.states.get(entity_id)
            if state is None:
                continue
            if state.state == "on":
                return True
            if len(state.attributes.get("raw_tomorrow") or []) > 0:
                return True
        return False

    @callback
    def _async_tomorrow_price_changed(self, event: Event) -> None:
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        became_available = False
        if new_state.entity_id.startswith("binary_sensor."):
            became_available = new_state.state == "on" and (
                old_state is None or old_state.state != "on"
            )
        else:
            old_rows = (
                old_state.attributes.get("raw_tomorrow") or []
                if old_state
                else []
            )
            new_rows = new_state.attributes.get("raw_tomorrow") or []
            became_available = len(new_rows) > 0 and len(old_rows) == 0

        if not became_available:
            return

        self.last_price_trigger = dt_util.utcnow()
        async_dispatcher_send(self.hass, self.signal)
        self.hass.async_create_task(
            self._async_price_trigger_optimize(),
            "gw-energypilot-tomorrow-prices",
        )

    @staticmethod
    def _clean_response(content: str) -> str:
        """Convert EMHASS JSON logs or HTML errors to a compact message."""
        text = content.strip()
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            parsed = None

        if isinstance(parsed, list):
            lines = [str(item).strip() for item in parsed if str(item).strip()]
            error_lines = [line for line in lines if "ERROR" in line.upper()]
            text = " | ".join((error_lines or lines)[-3:])
        elif isinstance(parsed, dict):
            text = str(parsed.get("message") or parsed.get("error") or parsed)

        text = html.unescape(re.sub(r"<[^>]+>", " ", text))
        text = re.sub(r"\s+", " ", text).strip()
        return text[:600]

    async def _async_post_emhass(
        self,
        endpoint: str,
        payload: dict[str, Any],
        timeout_seconds: int,
    ) -> tuple[int, str]:
        status, content = await super()._async_post_emhass(
            endpoint, payload, timeout_seconds
        )
        return status, self._clean_response(content)

    async def _async_probe_emhass(self) -> None:
        """Confirm that the EMHASS server is reachable before a heavy run."""
        base_url = str(
            self.entry.options.get(CONF_EMHASS_URL, DEFAULT_EMHASS_URL)
        ).strip().rstrip("/")
        if not base_url:
            raise HomeAssistantError("EMHASS URL is empty")

        session = async_get_clientsession(self.hass)
        try:
            async with asyncio.timeout(10):
                async with session.get(f"{base_url}/healthz") as response:
                    self.emhass_health_status = str(response.status)
                    try:
                        payload = await response.json(content_type=None)
                    except (ValueError, TypeError):
                        payload = {}
        except (TimeoutError, ClientError) as err:
            self.emhass_health_status = "unreachable"
            raise HomeAssistantError(
                f"Unable to reach EMHASS health endpoint at {base_url}: {err}"
            ) from err

        versions = payload.get("versions", {}) if isinstance(payload, dict) else {}
        self.emhass_version = (
            str(versions.get("emhass"))
            if isinstance(versions, dict) and versions.get("emhass")
            else None
        )
        async_dispatcher_send(self.hass, self.signal)

    async def async_optimize(self, reason: str = "manual") -> None:
        """Guard optimization until HA and EnergyPilot telemetry are ready."""
        if self.hass.state is not CoreState.running:
            error = (
                "Home Assistant startup is still in progress. Wait until startup "
                "has finished before running EMHASS optimization."
            )
            self._set_status("waiting_for_home_assistant", error)
            raise HomeAssistantError(error)

        if self.coordinator.data is None or not self.coordinator.last_update_success:
            error = (
                "GoodWe telemetry is not ready yet; wait for the first "
                "successful refresh."
            )
            self._set_status("waiting_for_goodwe", error)
            raise HomeAssistantError(error)

        await self._async_probe_emhass()
        try:
            await super().async_optimize(reason=reason)
        except HomeAssistantError as err:
            if not (
                self.status.startswith("error")
                or self.status.startswith("waiting")
                or self.status == "stale_output"
            ):
                self._set_status("error_optimization", str(err))
            raise
