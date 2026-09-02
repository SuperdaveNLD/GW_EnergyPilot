"""GW EnergyPilot v0.13 orchestration refinements."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import math
import time
from typing import Any

from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import (
    CONF_EMHASS_CUSTOM_LOAD_FORECAST,
    CONF_EMHASS_CUSTOM_LOAD_POWER,
    CONF_EMHASS_FALLBACK_LOAD,
    CONF_EMHASS_OPTIMIZATION_INTERVAL,
    CONF_EMHASS_SOC_FINAL,
    CONF_SCAN_INTERVAL,
    DEFAULT_EMHASS_CUSTOM_LOAD_FORECAST,
    DEFAULT_EMHASS_CUSTOM_LOAD_POWER,
    DEFAULT_EMHASS_FALLBACK_LOAD,
    DEFAULT_EMHASS_OPTIMIZATION_INTERVAL,
    DEFAULT_EMHASS_SOC_FINAL,
    DEFAULT_SCAN_INTERVAL,
)
from .optimization_log import GWEnergyPilotOptimizationLog
from .orchestrator_v012 import GWEnergyPilotOrchestrator as _V012Orchestrator
from .runtime_store import GWEnergyPilotRuntimeStore

_LOGGER = logging.getLogger(__name__)

LOAD_FORECAST_HOURS = 24


class GWEnergyPilotOrchestrator(_V012Orchestrator):
    """Use the G20 load registers consistently and expose refresh metadata."""

    def __init__(self, hass, entry, coordinator) -> None:
        super().__init__(hass, entry, coordinator)
        # This is intentionally not initialized from the configured target.
        # It represents only a target that completed an EnergyPilot-owned
        # optimization cycle, so manual-only installations start with None.
        self.last_runtime_soc_final: float | None = None
        self._runtime_store = GWEnergyPilotRuntimeStore(hass, entry.entry_id)
        self._optimization_log = GWEnergyPilotOptimizationLog(hass, entry.entry_id)

    async def async_setup(self) -> None:
        """Restore persistent runtime status before starting orchestration."""
        self.last_success = await self._runtime_store.async_load_last_success()
        await super().async_setup()

    def _configured_runtime_soc_final(self) -> float:
        """Return EnergyPilot's configured runtime soc_final value."""
        return float(
            self.entry.options.get(
                CONF_EMHASS_SOC_FINAL,
                DEFAULT_EMHASS_SOC_FINAL,
            )
        )

    @property
    def attributes(self) -> dict[str, Any]:
        """Return diagnostics used by Home Assistant and the dashboard."""
        attrs = super().attributes
        custom_load_forecast = bool(
            self.entry.options.get(
                CONF_EMHASS_CUSTOM_LOAD_FORECAST,
                DEFAULT_EMHASS_CUSTOM_LOAD_FORECAST,
            )
        )
        custom_load_power = float(
            self.entry.options.get(
                CONF_EMHASS_CUSTOM_LOAD_POWER,
                DEFAULT_EMHASS_CUSTOM_LOAD_POWER,
            )
        )
        # v0.12 called the power balance a calculated house load. On the tested
        # GW15K-ETA-G20, register 35172 agrees almost exactly with the sum of
        # load L1/L2/L3, while the full power balance also contains inverter,
        # conversion and auxiliary differences. Keep both concepts separate.
        balance = attrs.pop("calculated_home_power", None)
        attrs.update(
            {
                "system_balance_power": balance,
                "load_forecast_mode": "custom" if custom_load_forecast else "auto",
                "load_forecast_source": (
                    f"Fixed custom load ({custom_load_power:g} W)"
                    if custom_load_forecast
                    else "GoodWe load register 35172 + Recorder history"
                ),
                # Keep the configured EnergyPilot target separate from the last
                # value actually used by a successful EnergyPilot optimization.
                # External/manual EMHASS publishing must not make a configured
                # but never-sent value look like runtime evidence.
                "configured_runtime_soc_final": self._configured_runtime_soc_final(),
                "runtime_soc_final": self.last_runtime_soc_final,
                "telemetry_refresh_seconds": int(
                    self.entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                ),
                "optimization_interval_minutes": int(
                    self.entry.options.get(
                        CONF_EMHASS_OPTIMIZATION_INTERVAL,
                        DEFAULT_EMHASS_OPTIMIZATION_INTERVAL,
                    )
                ),
            }
        )
        return attrs

    async def _async_log_optimization(
        self,
        *,
        started_at: datetime,
        started_monotonic: float,
        reason: str,
        requested_soc_final: float,
        current_load: float | None,
        success: bool,
        error: str | None,
    ) -> None:
        """Persist one bounded diagnostic record without affecting control flow."""
        finished_at = dt_util.utcnow()
        record = {
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round(time.monotonic() - started_monotonic, 3),
            "reason": reason,
            "success": success,
            "soc_init": self.last_soc_init,
            "soc_final": requested_soc_final,
            "current_load": current_load,
            "price_source": getattr(self, "last_price_source", None),
            "price_area": self.last_price_area,
            "price_points": self.last_price_points,
            "load_forecast_points": self.last_load_points,
            "p_batt": self.last_p_batt if success else None,
            "optimize_http_status": self.optimize_http_status,
            "publish_http_status": self.publish_http_status,
            "error": error,
        }
        try:
            await self._optimization_log.async_append(record)
        except Exception:  # noqa: BLE001 - diagnostics must never break optimization
            _LOGGER.exception("Unable to persist EnergyPilot optimization history")

    async def async_optimize(self, reason: str = "manual") -> None:
        """Persist runtime evidence and a bounded log for every optimization attempt."""
        requested_soc_final = self._configured_runtime_soc_final()
        started_at = dt_util.utcnow()
        started_monotonic = time.monotonic()
        current_load = self._coordinator_number("total_load_power")

        try:
            await super().async_optimize(reason=reason)
        except Exception as err:
            await self._async_log_optimization(
                started_at=started_at,
                started_monotonic=started_monotonic,
                reason=reason,
                requested_soc_final=requested_soc_final,
                current_load=current_load,
                success=False,
                error=str(err),
            )
            raise

        if self.last_success is not None:
            await self._runtime_store.async_save_last_success(self.last_success)
        self.last_runtime_soc_final = requested_soc_final
        await self._async_log_optimization(
            started_at=started_at,
            started_monotonic=started_monotonic,
            reason=reason,
            requested_soc_final=requested_soc_final,
            current_load=current_load,
            success=True,
            error=None,
        )
        async_dispatcher_send(self.hass, self.signal)

    def _build_load_forecast(
        self,
        rows: list[dict[str, Any]],
        current_load: float | None,
    ) -> dict[str, float]:
        """Build the 24-hour forecast from GoodWe 35172 load history.

        The v0.12 power-balance value is useful as a whole-system diagnostic,
        but it should not silently replace the GoodWe load value used for the
        EMHASS load model. Register 35172 is also independently checked against
        the three load-phase registers in the diagnostics card.
        """
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
