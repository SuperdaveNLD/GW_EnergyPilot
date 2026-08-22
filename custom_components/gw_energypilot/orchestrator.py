"""Native EMHASS orchestration for GW EnergyPilot."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import date, datetime, timedelta
import logging
import math
from typing import Any

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BUY_PRICE_ADDER,
    CONF_EMHASS_URL,
    CONF_ENABLE_EMHASS_ORCHESTRATOR,
    CONF_EMHASS_FALLBACK_LOAD,
    CONF_EMHASS_OPTIMIZATION_INTERVAL,
    CONF_EMHASS_SOC_FINAL,
    CONF_NORDPOOL_AREA,
    CONF_NORDPOOL_CURRENCY,
    CONF_OPTIM_REQUIRED_STATE,
    CONF_OPTIM_STATUS_ENTITY,
    CONF_P_BATT_ENTITY,
    CONF_SELL_PRICE_DEDUCTION,
    CONF_USE_NORDPOOL_PRICES,
    DEFAULT_BUY_PRICE_ADDER,
    DEFAULT_EMHASS_FALLBACK_LOAD,
    DEFAULT_EMHASS_OPTIMIZATION_INTERVAL,
    DEFAULT_EMHASS_SOC_FINAL,
    DEFAULT_EMHASS_URL,
    DEFAULT_NORDPOOL_AREA,
    DEFAULT_NORDPOOL_CURRENCY,
    DEFAULT_OPTIM_REQUIRED_STATE,
    DEFAULT_OPTIM_STATUS_ENTITY,
    DEFAULT_P_BATT_ENTITY,
    DEFAULT_SELL_PRICE_DEDUCTION,
    DEFAULT_USE_NORDPOOL_PRICES,
    DOMAIN,
)
from .coordinator import GWEnergyPilotCoordinator

_LOGGER = logging.getLogger(__name__)

LOAD_HISTORY_DAYS = 7
LOAD_FORECAST_HOURS = 48
OUTPUT_TIMEOUT = 30


class GWEnergyPilotOrchestrator:
    """Run EMHASS optimization and publish its result safely."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: GWEnergyPilotCoordinator,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator

        self.status = "idle"
        self.last_error: str | None = None
        self.last_success: datetime | None = None
        self.last_reason: str | None = None
        self.last_p_batt: float | None = None
        self.last_soc_init: float | None = None
        self.last_price_area: str | None = None
        self.last_price_points = 0
        self.last_load_points = 0
        self.optimize_http_status: int | None = None
        self.publish_http_status: int | None = None

        self._lock = asyncio.Lock()
        self._unsubs: list[Callable[[], None]] = []

    @property
    def signal(self) -> str:
        """Dispatcher signal used by orchestrator entities."""
        return f"{DOMAIN}_{self.entry.entry_id}_orchestrator_update"

    @property
    def enabled(self) -> bool:
        """Return whether automatic native orchestration is enabled."""
        return bool(self.entry.options.get(CONF_ENABLE_EMHASS_ORCHESTRATOR, False))

    @property
    def attributes(self) -> dict[str, Any]:
        """Return diagnostics for Home Assistant and the dashboard."""
        return {
            "automatic_schedule": self.enabled,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_error": self.last_error,
            "last_reason": self.last_reason,
            "last_p_batt": self.last_p_batt,
            "soc_init": self.last_soc_init,
            "price_area": self.last_price_area,
            "price_points": self.last_price_points,
            "load_forecast_points": self.last_load_points,
            "optimize_http_status": self.optimize_http_status,
            "publish_http_status": self.publish_http_status,
        }

    async def async_setup(self) -> None:
        """Start the optional recurring optimization schedule."""
        if not self.enabled:
            self._set_status("manual_only")
            return

        if self._legacy_yaml_present():
            self._set_status(
                "legacy_yaml_detected",
                "Legacy EnergyPilot EMHASS YAML is still loaded. Remove or disable it before enabling the built-in schedule.",
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
        self._unsubs.append(async_call_later(self.hass, 60, self._async_initial_optimize))
        self._set_status("scheduled")

    async def async_unload(self) -> None:
        """Stop scheduler callbacks."""
        while self._unsubs:
            self._unsubs.pop()()

    def _legacy_yaml_present(self) -> bool:
        """Prevent two schedulers from running at the same time."""
        return any(
            self.hass.states.get(entity_id) is not None
            for entity_id in (
                "script.energypilot_emhass_optimize_now",
                "automation.energypilot_emhass_orchestrator",
            )
        )

    async def _async_initial_optimize(self, _now: datetime) -> None:
        await self._async_scheduled_optimize(_now)

    async def _async_scheduled_optimize(self, _now: datetime) -> None:
        try:
            await self.async_optimize(reason="scheduled")
        except HomeAssistantError as err:
            _LOGGER.warning("Scheduled EMHASS optimization failed: %s", err)

    def _set_status(self, status: str, error: str | None = None) -> None:
        self.status = status
        self.last_error = error
        async_dispatcher_send(self.hass, self.signal)

    def _coordinator_number(self, key: str) -> float | None:
        if not self.coordinator.data:
            return None
        value = self.coordinator.data.values.get(key)
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    def _load_entity_id(self) -> str:
        registry = er.async_get(self.hass)
        entity_id = registry.async_get_entity_id(
            "sensor",
            DOMAIN,
            f"{self.entry.entry_id}_total_load_power",
        )
        return entity_id or "sensor.gw_energypilot_total_load_power"

    async def _async_load_history(self, load_entity_id: str) -> list[dict[str, Any]]:
        if not self.hass.services.has_service("recorder", "get_statistics"):
            return []

        now_utc = dt_util.utcnow()
        try:
            response = await self.hass.services.async_call(
                "recorder",
                "get_statistics",
                {
                    "statistic_ids": [load_entity_id],
                    "start_time": now_utc - timedelta(days=LOAD_HISTORY_DAYS),
                    "end_time": now_utc,
                    "period": "hour",
                    "types": ["mean"],
                },
                blocking=True,
                return_response=True,
            )
        except HomeAssistantError as err:
            _LOGGER.debug("Recorder load history unavailable: %s", err)
            return []

        statistics = response.get("statistics", {}) if isinstance(response, dict) else {}
        rows = statistics.get(load_entity_id, []) if isinstance(statistics, dict) else []
        return rows if isinstance(rows, list) else []

    def _build_load_forecast(
        self,
        rows: list[dict[str, Any]],
        current_load: float | None,
    ) -> dict[str, float]:
        fallback = float(
            self.entry.options.get(
                CONF_EMHASS_FALLBACK_LOAD,
                DEFAULT_EMHASS_FALLBACK_LOAD,
            )
        )
        if current_load is None or current_load < 50 or current_load > 20000:
            current_load = fallback

        parsed_rows: list[tuple[datetime, float]] = []
        for row in rows:
            try:
                row_dt = datetime.fromisoformat(str(row["start"]))
                mean = float(row["mean"])
            except (KeyError, TypeError, ValueError):
                continue
            if not math.isfinite(mean) or mean < 50 or mean > 20000:
                continue
            parsed_rows.append((dt_util.as_local(row_dt), mean))

        start = dt_util.now().replace(minute=0, second=0, microsecond=0)
        forecast: dict[str, float] = {}
        for offset in range(LOAD_FORECAST_HOURS + 1):
            target = start + timedelta(hours=offset)
            matching = [mean for row_dt, mean in parsed_rows if row_dt.hour == target.hour]
            value = sum(matching) / len(matching) if matching else current_load
            forecast[target.isoformat()] = round(value, 0)
        return forecast

    async def _async_nordpool_day(self, config_entry_id: str, target_date: date) -> dict[str, Any]:
        data: dict[str, Any] = {
            "config_entry": config_entry_id,
            "date": target_date.isoformat(),
        }
        area = str(self.entry.options.get(CONF_NORDPOOL_AREA, DEFAULT_NORDPOOL_AREA)).strip()
        currency = str(
            self.entry.options.get(CONF_NORDPOOL_CURRENCY, DEFAULT_NORDPOOL_CURRENCY)
        ).strip()
        if area:
            data["areas"] = [area]
        if currency:
            data["currency"] = currency

        response = await self.hass.services.async_call(
            "nordpool",
            "get_prices_for_date",
            data,
            blocking=True,
            return_response=True,
        )
        return response if isinstance(response, dict) else {}

    def _select_price_area(self, response: dict[str, Any]) -> tuple[str | None, list[dict[str, Any]]]:
        configured = str(
            self.entry.options.get(CONF_NORDPOOL_AREA, DEFAULT_NORDPOOL_AREA)
        ).strip()
        if configured and isinstance(response.get(configured), list):
            return configured, response[configured]
        for area, values in response.items():
            if isinstance(values, list):
                return str(area), values
        return None, []

    async def _async_price_forecasts(
        self,
    ) -> tuple[dict[str, float], dict[str, float]]:
        if not bool(
            self.entry.options.get(
                CONF_USE_NORDPOOL_PRICES,
                DEFAULT_USE_NORDPOOL_PRICES,
            )
        ):
            self.last_price_area = None
            self.last_price_points = 0
            return {}, {}

        if not self.hass.services.has_service("nordpool", "get_prices_for_date"):
            self.last_price_area = None
            self.last_price_points = 0
            return {}, {}

        entries = self.hass.config_entries.async_entries("nordpool")
        if not entries:
            self.last_price_area = None
            self.last_price_points = 0
            return {}, {}

        today = dt_util.now().date()
        responses: list[dict[str, Any]] = []
        try:
            responses.append(await self._async_nordpool_day(entries[0].entry_id, today))
        except HomeAssistantError as err:
            _LOGGER.warning("Unable to retrieve today's Nord Pool prices: %s", err)
            return {}, {}

        # Tomorrow is normally published around 13:00 CET/CEST. Failure to get
        # tomorrow must never invalidate today's optimization.
        if dt_util.now().hour >= 13:
            try:
                responses.append(
                    await self._async_nordpool_day(
                        entries[0].entry_id,
                        today + timedelta(days=1),
                    )
                )
            except HomeAssistantError as err:
                _LOGGER.debug("Tomorrow Nord Pool prices not available yet: %s", err)

        buy_adder = float(
            self.entry.options.get(CONF_BUY_PRICE_ADDER, DEFAULT_BUY_PRICE_ADDER)
        )
        sell_deduction = float(
            self.entry.options.get(
                CONF_SELL_PRICE_DEDUCTION,
                DEFAULT_SELL_PRICE_DEDUCTION,
            )
        )

        load_cost: dict[str, float] = {}
        prod_price: dict[str, float] = {}
        selected_area: str | None = None

        for response in responses:
            area, rows = self._select_price_area(response)
            if selected_area is None and area is not None:
                selected_area = area
            if selected_area is not None and area != selected_area:
                rows = response.get(selected_area, []) if isinstance(response.get(selected_area), list) else []

            for row in rows:
                try:
                    timestamp = str(row["start"])
                    spot = float(row["price"]) / 1000.0
                except (KeyError, TypeError, ValueError):
                    continue
                if not math.isfinite(spot):
                    continue
                load_cost[timestamp] = round(spot + buy_adder, 5)
                prod_price[timestamp] = round(spot - sell_deduction, 5)

        self.last_price_area = selected_area
        self.last_price_points = len(load_cost)
        return load_cost, prod_price

    async def _async_post_emhass(
        self,
        endpoint: str,
        payload: dict[str, Any],
        timeout_seconds: int,
    ) -> tuple[int, str]:
        base_url = str(self.entry.options.get(CONF_EMHASS_URL, DEFAULT_EMHASS_URL)).strip().rstrip("/")
        if not base_url:
            raise HomeAssistantError("EMHASS URL is empty")

        session = async_get_clientsession(self.hass)
        url = f"{base_url}{endpoint}"
        try:
            async with asyncio.timeout(timeout_seconds):
                async with session.post(url, json=payload) as response:
                    content = await response.text()
                    return response.status, content
        except (TimeoutError, ClientError) as err:
            raise HomeAssistantError(f"Unable to reach EMHASS at {base_url}: {err}") from err

    def _optimization_ready(self) -> bool:
        entity_id = str(
            self.entry.options.get(
                CONF_OPTIM_STATUS_ENTITY,
                DEFAULT_OPTIM_STATUS_ENTITY,
            )
            or ""
        )
        if not entity_id:
            return True
        state = self.hass.states.get(entity_id)
        required = str(
            self.entry.options.get(
                CONF_OPTIM_REQUIRED_STATE,
                DEFAULT_OPTIM_REQUIRED_STATE,
            )
        )
        return state is not None and state.state == required

    async def _async_wait_for_fresh_output(self, before: datetime | None) -> float | None:
        entity_id = str(
            self.entry.options.get(CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY)
            or DEFAULT_P_BATT_ENTITY
        )
        deadline = self.hass.loop.time() + OUTPUT_TIMEOUT
        while self.hass.loop.time() < deadline:
            state = self.hass.states.get(entity_id)
            if state is not None and self._optimization_ready():
                try:
                    value = float(state.state)
                except (TypeError, ValueError):
                    value = math.nan
                is_fresh = before is None or state.last_updated > before
                if math.isfinite(value) and is_fresh:
                    return value
            await asyncio.sleep(0.5)
        return None

    async def async_optimize(self, reason: str = "manual") -> None:
        """Run one complete optimization and publish cycle."""
        if self._lock.locked():
            raise HomeAssistantError("An EnergyPilot EMHASS optimization is already running")

        async with self._lock:
            self.last_reason = reason
            self.optimize_http_status = None
            self.publish_http_status = None
            self._set_status("preparing")

            soc = self._coordinator_number("battery_soc")
            if soc is None or soc < 0 or soc > 100:
                self._set_status("error_input", "EnergyPilot battery SOC is unavailable or invalid")
                raise HomeAssistantError(self.last_error)

            soc_init = min(1.0, max(0.0, soc / 100.0))
            self.last_soc_init = round(soc_init, 4)
            current_load = self._coordinator_number("total_load_power")

            p_batt_entity = str(
                self.entry.options.get(CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY)
                or DEFAULT_P_BATT_ENTITY
            )
            p_batt_before_state = self.hass.states.get(p_batt_entity)
            p_batt_before = (
                p_batt_before_state.last_updated if p_batt_before_state is not None else None
            )

            self._set_status("reading_history")
            load_entity_id = self._load_entity_id()
            history = await self._async_load_history(load_entity_id)
            load_forecast = self._build_load_forecast(history, current_load)
            self.last_load_points = len(load_forecast)

            self._set_status("getting_prices")
            load_cost, prod_price = await self._async_price_forecasts()

            payload: dict[str, Any] = {
                "load_power_forecast": load_forecast,
                "soc_init": self.last_soc_init,
                "soc_final": float(
                    self.entry.options.get(
                        CONF_EMHASS_SOC_FINAL,
                        DEFAULT_EMHASS_SOC_FINAL,
                    )
                ),
            }
            if load_cost and prod_price:
                payload["load_cost_forecast"] = load_cost
                payload["prod_price_forecast"] = prod_price

            self._set_status("optimizing")
            optimize_status, optimize_content = await self._async_post_emhass(
                "/action/dayahead-optim",
                payload,
                180,
            )
            self.optimize_http_status = optimize_status
            async_dispatcher_send(self.hass, self.signal)
            if not 200 <= optimize_status < 300:
                error = f"EMHASS optimization HTTP {optimize_status}: {optimize_content[:300]}"
                self._set_status("error_optimization", error)
                raise HomeAssistantError(error)

            self._set_status("publishing")
            publish_status, publish_content = await self._async_post_emhass(
                "/action/publish-data",
                {},
                60,
            )
            self.publish_http_status = publish_status
            async_dispatcher_send(self.hass, self.signal)
            if not 200 <= publish_status < 300:
                error = f"EMHASS publish HTTP {publish_status}: {publish_content[:300]}"
                self._set_status("error_publish", error)
                raise HomeAssistantError(error)

            self._set_status("waiting_for_output")
            p_batt = await self._async_wait_for_fresh_output(p_batt_before)
            if p_batt is None:
                error = "EMHASS published successfully but no fresh numeric P_batt output became available"
                self._set_status("stale_output", error)
                raise HomeAssistantError(error)

            self.last_p_batt = p_batt
            self.last_success = dt_util.utcnow()
            self._set_status("ready")
            _LOGGER.info(
                "EnergyPilot EMHASS optimization successful: reason=%s soc_init=%.3f p_batt=%.1f W",
                reason,
                self.last_soc_init,
                p_batt,
            )
