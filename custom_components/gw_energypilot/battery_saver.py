"""Battery Saver presets and EMHASS profile helpers."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import math
from statistics import median
from typing import Any, Iterable, Mapping

MODE_MAD_STEVE = "mad_steve"
MODE_GOLD_RUSH = "gold_rush"
MODE_BALANCED = "balanced"
MODE_BATTERY_SAVER = "battery_saver"

BATTERY_SAVER_MODES: tuple[str, ...] = (
    MODE_MAD_STEVE,
    MODE_GOLD_RUSH,
    MODE_BALANCED,
    MODE_BATTERY_SAVER,
)

BATTERY_SAVER_CONFIG_KEYS: tuple[str, ...] = (
    "battery_soc_deficit_threshold",
    "battery_soc_deficit_cost",
    "battery_soc_surplus_threshold",
    "battery_soc_surplus_cost",
    "battery_stress_cost",
    "battery_stress_segments",
)

MINIMUM_STRESS_SAFE_EMHASS_VERSION = (0, 18, 1)
DEFAULT_PRICE_REFERENCE = 0.20


@dataclass(frozen=True, slots=True)
class BatterySaverPreset:
    """Describe one EnergyPilot Battery Saver policy."""

    key: str
    label: str
    short_description: str
    deficit_threshold: float
    deficit_cost_factor: float
    surplus_threshold: float
    surplus_cost_factor: float
    stress_cost_factor: float
    stress_segments: int = 10


PRESETS: dict[str, BatterySaverPreset] = {
    MODE_MAD_STEVE: BatterySaverPreset(
        key=MODE_MAD_STEVE,
        label="Mad-Steve",
        short_description=(
            "Maximum economic freedom. No additional low-SOC, high-SOC or power-stress cost."
        ),
        deficit_threshold=0.05,
        deficit_cost_factor=0.0,
        surplus_threshold=0.98,
        surplus_cost_factor=0.0,
        stress_cost_factor=0.0,
    ),
    MODE_GOLD_RUSH: BatterySaverPreset(
        key=MODE_GOLD_RUSH,
        label="Gold Rush",
        short_description=(
            "Profit first, while filtering low-value high-SOC dwell and unnecessary high-power cycling."
        ),
        deficit_threshold=0.05,
        deficit_cost_factor=0.0,
        surplus_threshold=0.98,
        surplus_cost_factor=0.05,
        stress_cost_factor=0.03,
    ),
    MODE_BALANCED: BatterySaverPreset(
        key=MODE_BALANCED,
        label="Balanced",
        short_description=(
            "Balances trading value with moderate high-SOC, low-SOC and high-power penalties."
        ),
        deficit_threshold=0.10,
        deficit_cost_factor=0.05,
        surplus_threshold=0.95,
        surplus_cost_factor=0.10,
        stress_cost_factor=0.08,
    ),
    MODE_BATTERY_SAVER: BatterySaverPreset(
        key=MODE_BATTERY_SAVER,
        label="Battery Saver",
        short_description=(
            "Makes marginal cycling, extended high SOC and high power materially less attractive."
        ),
        deficit_threshold=0.15,
        deficit_cost_factor=0.10,
        surplus_threshold=0.90,
        surplus_cost_factor=0.25,
        stress_cost_factor=0.20,
    ),
}


def normalize_battery_saver_mode(value: Any) -> str:
    """Return a validated Battery Saver mode key."""
    mode = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if mode not in PRESETS:
        supported = ", ".join(BATTERY_SAVER_MODES)
        raise ValueError(f"Unsupported Battery Saver mode '{value}'. Supported: {supported}")
    return mode


def battery_saver_mode_payloads() -> list[dict[str, Any]]:
    """Return frontend-safe metadata for the four public modes."""
    return [
        {
            "key": preset.key,
            "label": preset.label,
            "description": preset.short_description,
            "deficit_threshold_pct": round(preset.deficit_threshold * 100),
            "surplus_threshold_pct": round(preset.surplus_threshold * 100),
            "recommended": preset.key == MODE_BALANCED,
        }
        for preset in PRESETS.values()
    ]


def _finite_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _numeric_values(values: Iterable[Any]) -> list[float]:
    result: list[float] = []
    for raw in values:
        value = _finite_number(raw)
        if value is not None:
            result.append(value)
    return result


def _forecast_numbers(load_cost_forecast: Any) -> list[float]:
    if isinstance(load_cost_forecast, Mapping):
        return _numeric_values(load_cost_forecast.values())
    if isinstance(load_cost_forecast, list | tuple):
        return _numeric_values(load_cost_forecast)
    return []


def battery_saver_price_reference(
    load_cost_forecast: Any,
    config: Mapping[str, Any],
) -> float:
    """Return a positive price magnitude in the active EMHASS currency.

    Runtime prices are preferred. When EnergyPilot lets EMHASS own the price
    forecast, fall back to EMHASS's configured peak/off-peak values. The value
    is deliberately currency-agnostic: it scales the virtual Battery Saver
    costs in the same currency units as the optimizer's own price forecast.
    """
    values = _forecast_numbers(load_cost_forecast)
    positive = [value for value in values if value > 0]
    if positive:
        reference = median(positive)
    else:
        magnitudes = [abs(value) for value in values if value != 0]
        reference = median(magnitudes) if magnitudes else math.nan

    if not math.isfinite(reference) or reference <= 0:
        fallback_values = _numeric_values(
            config.get(key)
            for key in (
                "load_peak_hours_cost",
                "load_offpeak_hours_cost",
                "photovoltaic_production_sell_price",
            )
        )
        positive_fallback = [value for value in fallback_values if value > 0]
        if positive_fallback:
            reference = median(positive_fallback)
        else:
            fallback_magnitudes = [abs(value) for value in fallback_values if value != 0]
            reference = (
                median(fallback_magnitudes)
                if fallback_magnitudes
                else DEFAULT_PRICE_REFERENCE
            )

    return round(max(0.001, min(1000.0, float(reference))), 6)


def build_battery_saver_profile(
    mode: str,
    price_reference: float,
) -> dict[str, Any]:
    """Build the concrete EMHASS values for one Battery Saver mode."""
    normalized = normalize_battery_saver_mode(mode)
    preset = PRESETS[normalized]
    reference = battery_saver_price_reference([price_reference], {})
    return {
        "mode": preset.key,
        "label": preset.label,
        "price_reference": reference,
        "battery_soc_deficit_threshold": preset.deficit_threshold,
        "battery_soc_deficit_cost": round(reference * preset.deficit_cost_factor, 6),
        "battery_soc_surplus_threshold": preset.surplus_threshold,
        "battery_soc_surplus_cost": round(reference * preset.surplus_cost_factor, 6),
        "battery_stress_cost": round(reference * preset.stress_cost_factor, 6),
        "battery_stress_segments": preset.stress_segments,
    }


def apply_battery_saver_profile(
    config: Mapping[str, Any],
    mode: str,
    price_reference: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a complete config with the EnergyPilot Battery Saver fields applied."""
    profile = build_battery_saver_profile(mode, price_reference)
    updated = deepcopy(dict(config))
    for key in BATTERY_SAVER_CONFIG_KEYS:
        updated[key] = profile[key]
    return updated, profile


def battery_saver_costs_are_zero(config: Mapping[str, Any]) -> bool:
    """Return whether the active EMHASS config is behaviorally Mad-Steve."""
    for key in (
        "battery_soc_deficit_cost",
        "battery_soc_surplus_cost",
        "battery_stress_cost",
    ):
        value = _finite_number(config.get(key))
        if value is None or abs(value) > 1e-12:
            return False
    return True


def number_of_batteries(config: Mapping[str, Any]) -> int:
    """Return the configured EMHASS battery count, clamped to at least one."""
    try:
        value = int(config.get("number_of_batteries", 1))
    except (TypeError, ValueError):
        return 1
    return max(1, value)


def _version_tuple(version: str | None) -> tuple[int, int, int] | None:
    if not version:
        return None
    parts: list[int] = []
    for chunk in str(version).strip().split("."):
        digits = "".join(character for character in chunk if character.isdigit())
        if not digits:
            break
        parts.append(int(digits))
        if len(parts) == 3:
            break
    if not parts:
        return None
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def emhass_supports_battery_stress(version: str | None) -> bool:
    """Return whether the known EMHASS version includes the v0.18.1 stress fix."""
    parsed = _version_tuple(version)
    return parsed is None or parsed >= MINIMUM_STRESS_SAFE_EMHASS_VERSION
