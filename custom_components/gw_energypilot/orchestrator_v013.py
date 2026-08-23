"""GW EnergyPilot v0.13 orchestration refinements."""

from __future__ import annotations

from datetime import datetime, timedelta
import math
from typing import Any

from homeassistant.util import dt as dt_util

from .const import (
    CONF_EMHASS_FALLBACK_LOAD,
    CONF_EMHASS_OPTIMIZATION_INTERVAL,
    CONF_SCAN_INTERVAL,
    DEFAULT_EMHASS_FALLBACK_LOAD,
    DEFAULT_EMHASS_OPTIMIZATION_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
)
from .orchestrator_v012 import GWEnergyPilotOrchestrator as _V012Orchestrator

LOAD_FORECAST_HOURS = 24


class GWEnergyPilotOrchestrator(_V012Orchestrator):
    """Use the G20 load registers consistently and expose refresh metadata."""

    @property
    def attributes(self) -> dict[str, Any]:
        """Return diagnostics used by Home Assistant and the dashboard."""
        attrs = super().attributes
        # v0.12 called the power balance a calculated house load. On the tested
        # GW15K-ETA-G20, register 35172 agrees almost exactly with the sum of
        # load L1/L2/L3, while the full power balance also contains inverter,
        # conversion and auxiliary differences. Keep both concepts separate.
        balance = attrs.pop("calculated_home_power", None)
        attrs.update(
            {
                "system_balance_power": balance,
                "load_forecast_source": "GoodWe load register 35172 + Recorder history",
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
