"""Runtime load-forecast selection for EnergyPilot-owned EMHASS solves."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
import math
from typing import Any

DEFAULT_FORECAST_DAYS = 1.0
MAX_FORECAST_STEPS = 10000


def _finite_number(value: Any, *, name: str) -> float:
    """Return one finite numeric configuration value."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as err:
        raise ValueError(f"EMHASS {name} must be a finite number") from err
    if not math.isfinite(number):
        raise ValueError(f"EMHASS {name} must be a finite number")
    return number


def _prediction_horizon(value: Any) -> int:
    """Validate one explicit runtime prediction horizon."""
    number = _finite_number(value, name="prediction_horizon")
    horizon = int(number)
    if number != horizon or not 1 <= horizon <= MAX_FORECAST_STEPS:
        raise ValueError(
            f"EMHASS prediction_horizon must be a whole number from 1 to {MAX_FORECAST_STEPS}"
        )
    return horizon


def forecast_step_count(
    emhass_config: Mapping[str, Any],
    runtime_parameters: Mapping[str, Any],
) -> int:
    """Return the active day-ahead horizon length in EMHASS timesteps."""
    if "prediction_horizon" in runtime_parameters:
        return _prediction_horizon(runtime_parameters["prediction_horizon"])

    time_step = _finite_number(
        emhass_config.get("optimization_time_step"),
        name="optimization_time_step",
    )
    forecast_days = _finite_number(
        emhass_config.get("delta_forecast_daily", DEFAULT_FORECAST_DAYS),
        name="delta_forecast_daily",
    )
    if time_step <= 0:
        raise ValueError("EMHASS optimization_time_step must be greater than zero")
    if forecast_days <= 0:
        raise ValueError("EMHASS delta_forecast_daily must be greater than zero")

    steps = math.ceil((forecast_days * 24 * 60) / time_step - 1e-9)
    if not 1 <= steps <= MAX_FORECAST_STEPS:
        raise ValueError(
            f"EMHASS forecast horizon must contain 1 to {MAX_FORECAST_STEPS} steps"
        )
    return steps


def apply_custom_load_forecast(
    runtime_parameters: MutableMapping[str, Any],
    emhass_config: Mapping[str, Any],
    *,
    enabled: bool,
    power_w: Any,
) -> int | None:
    """Override only ``load_power_forecast`` when CUSTOM mode is enabled."""
    if not enabled:
        return None

    power = _finite_number(power_w, name="custom load forecast")
    if not 0 <= power <= 30000:
        raise ValueError("Custom load forecast must be from 0 to 30000 W")
    normalized_power: int | float = int(power) if power.is_integer() else power
    steps = forecast_step_count(emhass_config, runtime_parameters)
    runtime_parameters["load_power_forecast"] = [normalized_power] * steps
    return steps
