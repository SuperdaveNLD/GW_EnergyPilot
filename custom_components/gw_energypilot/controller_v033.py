"""GW EnergyPilot v0.33 plan-resilient Automatic Control."""

from __future__ import annotations

from .const import (
    CONF_OPTIM_STATUS_ENTITY,
    CONTROL_STRATEGY_BATTERY,
    CONTROL_STRATEGY_GRID,
    CONTROL_STRATEGY_HYBRID,
    MODE_BATTERY_HOLD,
    MODE_CHARGE_BATTERY,
    MODE_GRID_IMPORT_TARGET,
)
from .controller import GWEnergyPilotController as _BaseController

_MISSING_STATES = {"unknown", "unavailable", "none", ""}


class GWEnergyPilotController(_BaseController):
    """Keep Automatic Control usable while EMHASS HA entities are rebuilding."""

    def _plan_runtime(self):
        runtime_data = getattr(self.entry, "runtime_data", None)
        return getattr(runtime_data, "plan_runtime", None)

    def _state_float(self, entity_id: str | None) -> float | None:
        """Prefer live HA state and fall back to the persisted EMHASS plan."""
        value = super()._state_float(entity_id)
        if value is not None or not entity_id:
            return value

        plan_runtime = self._plan_runtime()
        if plan_runtime is None:
            return None
        if entity_id == self._p_batt_entity_id():
            return plan_runtime.current_p_batt()
        if entity_id == self._p_grid_entity_id():
            return plan_runtime.current_p_grid()
        return None

    def _optim_is_ready(self) -> bool:
        """Accept a valid mirrored plan while optim_status is temporarily absent."""
        entity_id = self.entry.options.get(CONF_OPTIM_STATUS_ENTITY)
        if not entity_id:
            return True

        state = self.hass.states.get(entity_id)
        if state is not None and state.state.lower() not in _MISSING_STATES:
            return super()._optim_is_ready()

        plan_runtime = self._plan_runtime()
        return bool(plan_runtime is not None and plan_runtime.has_current_plan())

    async def _async_apply_ev_anti_discharge_plan(
        self,
        p_batt: float,
        deadband: float,
        max_power: int,
    ) -> None:
        """Block discharge during EV charging while allowing planned charging."""
        if p_batt >= -deadband:
            await self._async_apply_command(
                MODE_BATTERY_HOLD,
                0,
                "ev_anti_discharge_hold",
                skip_if_readback_matches=True,
            )
            return

        strategy = self.control_strategy
        if strategy in {CONTROL_STRATEGY_GRID, CONTROL_STRATEGY_HYBRID}:
            p_grid = self._state_float(self._p_grid_entity_id())
            if p_grid is not None and p_grid > deadband:
                power = min(int(abs(p_grid)), max_power)
                await self._async_apply_command(
                    MODE_GRID_IMPORT_TARGET,
                    power,
                    "ev_grid_import_charge",
                    skip_if_readback_matches=True,
                )
                return

        power = min(int(abs(p_batt)), max_power)
        command = (
            "ev_battery_charge"
            if strategy == CONTROL_STRATEGY_BATTERY
            else "ev_charge_fallback"
        )
        await self._async_apply_command(
            MODE_CHARGE_BATTERY,
            power,
            command,
            skip_if_readback_matches=True,
        )
