"""Pure EMHASS-to-GoodWe control-decision mapping."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .const import (
    CONTROL_STRATEGY_BATTERY,
    CONTROL_STRATEGY_GRID,
    CONTROL_STRATEGY_HYBRID,
    CONTROL_STRATEGY_HYBRID_2,
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
    battery_deadband: float,
    grid_deadband: float,
    max_power: int,
    ev_active: bool = False,
    ev_power_w: float | int | None = None,
) -> ControlDecision:
    """Resolve the canonical automatic-control mapping without side effects.

    The function deliberately mirrors the safety contract used by the live
    controller. It can therefore also project future plan rows without moving
    any GoodWe actuator. Exact deadband boundaries remain neutral.
    """
    battery = _finite(p_batt)
    grid = _finite(p_grid)
    battery_boundary = max(0.0, float(battery_deadband))
    grid_boundary = max(0.0, float(grid_deadband))

    if battery is None:
        return ControlDecision(None, None, "waiting_for_p_batt")

    if ev_active:
        if strategy == CONTROL_STRATEGY_HYBRID_2:
            if abs(battery) <= battery_boundary:
                return ControlDecision(MODE_BATTERY_HOLD, 0, "ev_anti_discharge_hold")
            if grid is None:
                return ControlDecision(None, None, "waiting_for_p_grid")
            # Self-use includes a positive P_batt with neutral P_grid: the
            # battery may supply the house. PV-charge/export plans also keep
            # local self-use, with EV demand excluded at the PCC.
            if abs(grid) <= grid_boundary or (battery < -battery_boundary and grid < 0):
                ev_power = _finite(ev_power_w)
                maximum = max(0, min(int(max_power), 15000))
                if ev_power is None or ev_power <= 0 or ev_power > maximum:
                    return ControlDecision(MODE_BATTERY_HOLD, 0, "ev_self_consumption_hold")
                return ControlDecision(MODE_GRID_IMPORT_TARGET, int(ev_power), "ev_house_self_consumption")
            if battery > battery_boundary:
                return ControlDecision(MODE_BATTERY_HOLD, 0, "ev_anti_discharge_hold")
        if battery >= -battery_boundary:
            return ControlDecision(
                MODE_BATTERY_HOLD,
                0,
                "ev_anti_discharge_hold",
            )
        # Resolve the normal plan first so missing required inputs still wait.
        decision = resolve_control_decision(
            strategy=strategy,
            p_batt=battery,
            p_grid=grid,
            battery_deadband=battery_boundary,
            grid_deadband=grid_boundary,
            max_power=max_power,
        )
        if not decision.ready:
            return decision
        command = "ev_charge_allowed"
        if decision.mode == MODE_CHARGE_BATTERY:
            command = "ev_battery_charge"
        elif decision.mode == MODE_GRID_IMPORT_TARGET:
            command = "ev_grid_import_charge"
        return ControlDecision(decision.mode, decision.power, command)

    if strategy == CONTROL_STRATEGY_BATTERY:
        if battery > battery_boundary:
            return ControlDecision(
                MODE_DISCHARGE_BATTERY,
                _bounded_power(battery, max_power),
                "battery_discharge",
            )
        if battery < -battery_boundary:
            return ControlDecision(
                MODE_CHARGE_BATTERY,
                _bounded_power(battery, max_power),
                "battery_charge",
            )
        return ControlDecision(MODE_BATTERY_HOLD, 0, "battery_hold")

    if grid is None:
        return ControlDecision(None, None, "waiting_for_p_grid")

    # Require planned import as well as battery charging: P_batt < 0 alone
    # can represent PV-only charging, including during expensive grid periods.
    if (
        strategy == CONTROL_STRATEGY_HYBRID_2
        and battery < -battery_boundary
        and grid > grid_boundary
    ):
        return ControlDecision(
            MODE_CHARGE_BATTERY,
            _bounded_power(battery, max_power),
            "hybrid2_planned_battery_charge",
        )

    if strategy in {CONTROL_STRATEGY_HYBRID, CONTROL_STRATEGY_HYBRID_2}:
        if abs(battery) <= battery_boundary:
            return ControlDecision(
                MODE_BATTERY_HOLD,
                0,
                "hybrid_battery_hold",
            )
        if abs(grid) <= grid_boundary:
            return ControlDecision(MODE_AUTO, 0, "hybrid_grid_zero_auto")
        if grid > grid_boundary:
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
    if grid > grid_boundary:
        return ControlDecision(
            MODE_GRID_IMPORT_TARGET,
            _bounded_power(grid, max_power),
            "grid_import_target",
        )
    if grid < -grid_boundary:
        return ControlDecision(
            MODE_GRID_EXPORT_TARGET,
            _bounded_power(grid, max_power),
            "grid_export_target",
        )
    return ControlDecision(MODE_AUTO, 0, "grid_zero_auto")
