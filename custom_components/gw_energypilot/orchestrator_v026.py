"""Dashboard price-series support for GW EnergyPilot v0.26."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BUY_PRICE_ADDER,
    CONF_NORDPOOL_CURRENCY,
    CONF_SELL_PRICE_DEDUCTION,
    DEFAULT_BUY_PRICE_ADDER,
    DEFAULT_NORDPOOL_CURRENCY,
    DEFAULT_SELL_PRICE_DEDUCTION,
)
from .orchestrator_v013 import GWEnergyPilotOrchestrator as _V013Orchestrator
from .price_series import build_dashboard_price_points

_LOGGER = logging.getLogger(__name__)

PRICE_CHART_CACHE_AGE = timedelta(minutes=15)


class GWEnergyPilotOrchestrator(_V013Orchestrator):
    """Expose the optimizer's canonical runtime price series to the dashboard."""

    def __init__(self, hass, entry, coordinator) -> None:
        super().__init__(hass, entry, coordinator)
        self._dashboard_load_cost: dict[str, float] = {}
        self._dashboard_prod_price: dict[str, float] = {}
        self._dashboard_price_updated_at: datetime | None = None
        self._dashboard_price_lock = asyncio.Lock()

    def _cache_dashboard_prices(
        self,
        load_cost: dict[str, float],
        prod_price: dict[str, float],
    ) -> None:
        """Keep the exact effective price maps used for an EnergyPilot run."""
        self._dashboard_load_cost = dict(load_cost)
        self._dashboard_prod_price = dict(prod_price)
        self._dashboard_price_updated_at = dt_util.utcnow()

    async def _async_price_forecasts(
        self,
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Cache the same canonical price maps that are supplied to EMHASS."""
        load_cost, prod_price = await super()._async_price_forecasts()
        self._cache_dashboard_prices(load_cost, prod_price)
        return load_cost, prod_price

    def _dashboard_price_cache_fresh(self) -> bool:
        updated = self._dashboard_price_updated_at
        return bool(
            updated is not None
            and dt_util.utcnow() - updated <= PRICE_CHART_CACHE_AGE
        )

    def _dashboard_price_payload(self, error: str | None = None) -> dict[str, Any]:
        buy_adder = float(
            self.entry.options.get(CONF_BUY_PRICE_ADDER, DEFAULT_BUY_PRICE_ADDER)
        )
        sell_deduction = float(
            self.entry.options.get(
                CONF_SELL_PRICE_DEDUCTION,
                DEFAULT_SELL_PRICE_DEDUCTION,
            )
        )
        points = build_dashboard_price_points(
            self._dashboard_load_cost,
            self._dashboard_prod_price,
            buy_adder=buy_adder,
            sell_deduction=sell_deduction,
        )
        if not points and error is None:
            if getattr(self, "last_price_source", None) == "emhass_config":
                error = (
                    "Runtime Nord Pool pricing is disabled; EMHASS configuration "
                    "prices are not available as a timestamped dashboard series."
                )
            else:
                error = "No timestamped runtime price series is available yet."

        return {
            "available": bool(points),
            "updated_at": (
                self._dashboard_price_updated_at.isoformat()
                if self._dashboard_price_updated_at
                else None
            ),
            "source": getattr(self, "last_price_source", None),
            "area": self.last_price_area,
            "currency": str(
                self.entry.options.get(
                    CONF_NORDPOOL_CURRENCY,
                    DEFAULT_NORDPOOL_CURRENCY,
                )
            ),
            "buy_adder": buy_adder,
            "sell_deduction": sell_deduction,
            "points": points,
            "error": error,
        }

    async def async_dashboard_price_payload(
        self,
        *,
        force: bool = False,
    ) -> dict[str, Any]:
        """Return a cached dashboard price series, refreshing it when needed.

        Dashboard reads never launch an EMHASS optimization. They only reuse the
        existing EnergyPilot price-source path and keep a short in-memory cache.
        """
        if not force and self._dashboard_price_cache_fresh():
            return self._dashboard_price_payload()

        # An active optimization will populate this cache through the overridden
        # _async_price_forecasts method. Avoid racing a duplicate price request.
        if self._lock.locked():
            return self._dashboard_price_payload(
                None
                if self._dashboard_load_cost or self._dashboard_prod_price
                else "An EnergyPilot optimization is currently retrieving prices."
            )

        async with self._dashboard_price_lock:
            if not force and self._dashboard_price_cache_fresh():
                return self._dashboard_price_payload()
            try:
                await self._async_price_forecasts()
            except HomeAssistantError as err:
                return self._dashboard_price_payload(str(err))
            except Exception as err:  # noqa: BLE001 - read-only UI must degrade safely
                _LOGGER.exception("Unable to refresh EnergyPilot dashboard prices")
                return self._dashboard_price_payload(str(err))

        return self._dashboard_price_payload()
