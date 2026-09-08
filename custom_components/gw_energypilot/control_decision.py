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
    MODE_CHARGE_PV,
    MODE_DISCHARGE_BATTERY,
    MODE_DISCHARGE_PV,
    MODE_GRID_EXPORT_TARGET,
    MODE_GRID_IMPORT_TARGET,
    MODE_INVERTER_EXPORT,
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


@dataclass(frozen=True)
class HybridMappingPreview:
    """A proposed mapping, never a live ControlDecision or write permission.

    Validation requirements describe unresolved hardware/model assumptions.
    Serialization is read-only. Only the explicitly selected Hybrid 2.0
    strategy may translate this model into a live ControlDecision.
    """

    mode: int | None
    power_w: int | None
    reason: str
    validation_required: tuple[str, ...] = ()
    house_reference_w: float | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "model": "hybrid_grid_first_v1",
            "preview_only": True,
            "mode": self.mode,
            "power_w": self.power_w,
            "reason": self.reason,
            "validation_required": list(self.validation_required),
            "house_reference_w": self.house_reference_w,
        }


def preview_hybrid_mapping(
    *,
    p_batt: float | int | None,
    p_grid: float | int | None,
    battery_deadband: float,
    grid_deadband: float,
    max_power: int,
    explicit_pause: bool = False,
    plan_ready: bool = True,
    ev_active: bool = False,
    load_power_w: float | int | None = None,
    ev_power_w: float | int | None = None,
) -> HybridMappingPreview:
    """Calculate the owner's grid-first model without side effects.

    Inputs are watts with EMHASS signs; the caller validates measurement age
    and source. The EV house reference assumes 35172 includes EV and is net
    of external AC PV. That boundary is UNVERIFIED: never subtract external
    PV again or present the opt-in test strategy as hardware-validated.
    """
    if explicit_pause:
        return HybridMappingPreview(MODE_BATTERY_HOLD, 0, "explicit_pause")

    def waiting(reason: str) -> HybridMappingPreview:
        # Missing data during EV charging must never suggest unrestricted Auto.
        return HybridMappingPreview(
            MODE_BATTERY_HOLD if ev_active else None,
            0 if ev_active else None,
            reason,
        )

    if not plan_ready:
        return waiting("waiting_for_ready_plan")
    values = (battery_deadband, grid_deadband, max_power)
    limits = [_finite(value) if not isinstance(value, bool) else None for value in values]
    if any(value is None or value < 0 for value in limits):
        return waiting("invalid_mapping_limits")
    battery_boundary, grid_boundary, maximum = limits
    maximum = min(int(maximum), 15000)
    battery = _finite(p_batt) if not isinstance(p_batt, bool) else None
    grid = _finite(p_grid) if not isinstance(p_grid, bool) else None
    if grid is None:
        return waiting("waiting_for_p_grid")
    if battery is None:
        return waiting("waiting_for_p_batt")

    # Grid deadband comes FIRST, including P_batt = 0 and exact boundaries.
    if abs(grid) <= grid_boundary:
        if not ev_active:
            return HybridMappingPreview(MODE_AUTO, 0, "grid_deadband_self_consumption")
        load = _finite(load_power_w) if not isinstance(load_power_w, bool) else None
        ev = _finite(ev_power_w) if not isinstance(ev_power_w, bool) else None
        if load is None or ev is None or ev <= 0:
            return waiting("waiting_for_ev_house_measurements")
        house = max(0.0, load - ev)
        # Clamping an inverter-output reference down is conservative for the
        # house allowance. Unlike beta.8's mode-9 EV reference, EV itself may
        # exceed the inverter's power rating; it is not the actuator setpoint.
        return HybridMappingPreview(
            MODE_INVERTER_EXPORT,
            min(int(house), maximum),
            "ev_house_inverter_export_candidate",
            ("load_35172_ev_external_pv_boundary", "mode5_pv_surplus_behavior"),
            house,
        )

    if battery < -battery_boundary:
        if maximum == 0:
            return HybridMappingPreview(MODE_BATTERY_HOLD, 0, "zero_dispatch_limit")
        # Retain the planned watt magnitude as a grid-assistance allowance.
        # Mode 2 prioritizes PV, which can add to the resulting battery charge;
        # this is not mode 11's fixed battery-power target or maximum dispatch.
        return HybridMappingPreview(
            MODE_CHARGE_PV,
            _bounded_power(battery, maximum),
            "planned_battery_charge",
            ("mode2_pv_additive_charge",) + (
                ("mode2_charge_during_planned_export",) if grid < 0 else ()
            ),
        )
    if battery > battery_boundary:
        if ev_active:
            return HybridMappingPreview(MODE_BATTERY_HOLD, 0, "ev_planned_discharge_blocked")
        if maximum == 0:
            return HybridMappingPreview(MODE_BATTERY_HOLD, 0, "zero_dispatch_limit")
        return HybridMappingPreview(
            MODE_DISCHARGE_PV,
            _bounded_power(battery, maximum),
            "planned_pv_priority_discharge_candidate",
            ("mode3_pv_priority_at_ac_limit",),
        )

    # A neutral battery plan is not an explicit Pause. PCC targets can move
    # the battery in either direction, so EV behavior for this case stays open.
    if ev_active:
        return HybridMappingPreview(
            None, None, "ev_net_only_action_unresolved",
            ("ev_neutral_battery_nonzero_grid",),
        )
    return HybridMappingPreview(
        MODE_GRID_IMPORT_TARGET if grid > 0 else MODE_GRID_EXPORT_TARGET,
        _bounded_power(grid, maximum),
        "net_only_import_candidate" if grid > 0 else "net_only_export_candidate",
        ("grid_target_does_not_enforce_neutral_battery",),
    )


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
    load_power_w: float | int | None = None,
) -> ControlDecision:
    """Resolve the canonical automatic-control mapping without side effects.

    The function deliberately mirrors the safety contract used by the live
    controller. It can therefore also project future plan rows without moving
    any GoodWe actuator. Exact deadband boundaries remain neutral.
    """
    if strategy == CONTROL_STRATEGY_HYBRID_2:
        model = preview_hybrid_mapping(
            p_batt=p_batt, p_grid=p_grid,
            battery_deadband=battery_deadband, grid_deadband=grid_deadband,
            max_power=max_power, ev_active=ev_active,
            ev_power_w=ev_power_w, load_power_w=load_power_w,
        )
        commands = {
            "grid_deadband_self_consumption": "hybrid2_grid_zero_auto",
            "planned_battery_charge": "ev_battery_charge" if ev_active else "hybrid2_planned_battery_charge",
            "planned_pv_priority_discharge_candidate": "hybrid2_planned_battery_discharge",
            "ev_house_inverter_export_candidate": "ev_house_self_consumption",
            "ev_planned_discharge_blocked": "ev_anti_discharge_hold",
            "waiting_for_ev_house_measurements": "ev_self_consumption_hold",
            "net_only_import_candidate": "hybrid2_net_only_import",
            "net_only_export_candidate": "hybrid2_net_only_export",
        }
        if model.reason == "ev_net_only_action_unresolved":
            # A PCC target could discharge into the EV with a neutral battery
            # plan. Until that case is designed/tested, explicitly guard it.
            return ControlDecision(MODE_BATTERY_HOLD, 0, "ev_self_consumption_hold")
        return ControlDecision(model.mode, model.power_w, commands.get(model.reason, model.reason))

    battery = _finite(p_batt)
    grid = _finite(p_grid)
    battery_boundary = max(0.0, float(battery_deadband))
    grid_boundary = max(0.0, float(grid_deadband))

    if battery is None:
        return ControlDecision(None, None, "waiting_for_p_batt")

    if ev_active:
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

    if strategy == CONTROL_STRATEGY_HYBRID:
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
