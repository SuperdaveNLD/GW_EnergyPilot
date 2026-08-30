"""Pure EMHASS-to-GoodWe control-decision mapping."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .const import (
    CONTROL_STRATEGY_BATTERY,
    CONTROL_STRATEGY_GRID,
    CONTROL_STRATEGY_HYBRID,
    MODE_AUTO,
    MODE_BATTERY_HOLD,
    MODE_CHARGE_BATTERY,
    MODE_DISCHARGE_BATTERY,
    MODE_GRID_EXPORT_TARGET,
    MODE_GRID_IMPORT_TARGET,
)


@dataclass(frozen=True)
class ControlDecision:
    """One deterministic controller outcome or explicit waiting state."""

    mode: int | None
    power: int | None
    command: str

    @property
    def ready(self) -> bool:
        """Return whether this decision can be applied to GoodWe."""
        return self.mode is not None and self.power is not None


def _finite(value: float | int | None) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _bounded_power(value: float, maximum: int) -> int:
    return min(int(abs(value)), max(0, min(int(maximum), 15000)))


def resolve_control_decision(
    *,
    strategy: str,
    p_batt: float | int | None,
    p_grid: float | int | None,
    deadband: float,
    max_power: int,
    ev_active: bool = False,
) -> ControlDecision:
    """Resolve the canonical automatic-control mapping without side effects.

    The function deliberately mirrors the safety contract used by the live
    controller. It can therefore also project future plan rows without moving
    any GoodWe actuator. Exact deadband boundaries remain neutral.
    """
    battery = _finite(p_batt)
    grid = _finite(p_grid)
    boundary = max(0.0, float(deadband))

    if battery is None:
        return ControlDecision(None, None, "waiting_for_p_batt")

    if ev_active:
        if battery >= -boundary:
            return ControlDecision(
                MODE_BATTERY_HOLD,
                0,
                "ev_anti_discharge_hold",
            )
        if strategy in {CONTROL_STRATEGY_GRID, CONTROL_STRATEGY_HYBRID}:
            if grid is not None and grid > boundary:
                return ControlDecision(
                    MODE_GRID_IMPORT_TARGET,
                    _bounded_power(grid, max_power),
                    "ev_grid_import_charge",
                )
            return ControlDecision(
                MODE_CHARGE_BATTERY,
                _bounded_power(battery, max_power),
                "ev_charge_fallback",
            )
        return ControlDecision(
            MODE_CHARGE_BATTERY,
            _bounded_power(battery, max_power),
            "ev_battery_charge",
        )

    if strategy == CONTROL_STRATEGY_BATTERY:
        if battery > boundary:
            return ControlDecision(
                MODE_DISCHARGE_BATTERY,
                _bounded_power(battery, max_power),
                "battery_discharge",
            )
        if battery < -boundary:
            return ControlDecision(
                MODE_CHARGE_BATTERY,
                _bounded_power(battery, max_power),
                "battery_charge",
            )
        return ControlDecision(MODE_BATTERY_HOLD, 0, "battery_hold")

    if grid is None:
        return ControlDecision(None, None, "waiting_for_p_grid")

    if strategy == CONTROL_STRATEGY_HYBRID:
        if abs(battery) <= boundary:
            return ControlDecision(
                MODE_BATTERY_HOLD,
                0,
                "hybrid_battery_hold",
            )
        if abs(grid) <= boundary:
            return ControlDecision(MODE_AUTO, 0, "hybrid_grid_zero_auto")
        if grid > boundary:
            return ControlDecision(
                MODE_GRID_IMPORT_TARGET,
                _bounded_power(grid, max_power),
                "hybrid_grid_import",
            )
        return ControlDecision(
            MODE_GRID_EXPORT_TARGET,
            _bounded_power(grid, max_power),
            "hybrid_grid_export",
        )

    # Explicit Grid and legacy smart-meter control share the PCC mapping.
    if grid > boundary:
        return ControlDecision(
            MODE_GRID_IMPORT_TARGET,
            _bounded_power(grid, max_power),
            "grid_import_target",
        )
    if grid < -boundary:
        return ControlDecision(
            MODE_GRID_EXPORT_TARGET,
            _bounded_power(grid, max_power),
            "grid_export_target",
        )
    return ControlDecision(MODE_AUTO, 0, "grid_zero_auto")
