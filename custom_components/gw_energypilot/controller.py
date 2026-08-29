"""Automatic control logic for GW EnergyPilot."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from math import isfinite

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event

from .client import GWModbusClient
from .const import (
    CONF_CONTROL_STRATEGY,
    CONF_DEADBAND,
    CONF_ENABLE_EMHASS_ORCHESTRATOR,
    CONF_ENABLE_EV_COORDINATION,
    CONF_EV_DEADBAND,
    CONF_EV_MODE_ENTITY,
    CONF_EV_POWER_ENTITY,
    CONF_MAX_POWER,
    CONF_OPTIM_REQUIRED_STATE,
    CONF_OPTIM_STATUS_ENTITY,
    CONF_P_BATT_ENTITY,
    CONF_P_GRID_ENTITY,
    CONF_USE_GOODWE_SMART_METER,
    CONTROL_STRATEGIES,
    CONTROL_STRATEGY_BATTERY,
    CONTROL_STRATEGY_GRID,
    CONTROL_STRATEGY_HYBRID,
    DEFAULT_DEADBAND,
    DEFAULT_EV_DEADBAND,
    DEFAULT_MAX_POWER,
    DEFAULT_OPTIM_REQUIRED_STATE,
    DEFAULT_P_BATT_ENTITY,
    DEFAULT_P_GRID_ENTITY,
    DEFAULT_USE_GOODWE_SMART_METER,
    DOMAIN,
    MODE_AUTO,
    MODE_BATTERY_HOLD,
    MODE_CHARGE_BATTERY,
    MODE_DISCHARGE_BATTERY,
    MODE_GRID_EXPORT_TARGET,
    MODE_GRID_IMPORT_TARGET,
)
from .coordinator import GWEnergyPilotCoordinator


class GWEnergyPilotController:
    """Translate the current EMHASS plan into GoodWe EMS commands.

    Automatic Control supports three strategies:

    Battery control:
      P_batt < 0 = mode 11 direct battery charge target
      P_batt > 0 = mode 12 direct battery discharge target
      P_batt ~= 0 = mode 8 Battery Hold

    Grid control:
      P_grid > 0 = mode 9 import target at the PCC
      P_grid < 0 = mode 10 export target at the PCC
      P_grid ~= 0 = mode 1 GoodWe Auto / self-use balancing

    Hybrid control:
      P_batt ~= 0 = mode 8 Battery Hold
      otherwise P_grid ~= 0 = mode 1 GoodWe Auto / self-use balancing
      otherwise P_grid > 0 = mode 9 import target at the PCC
      otherwise P_grid < 0 = mode 10 export target at the PCC

    Hybrid gives an explicit neutral battery plan first priority. For every
    non-neutral battery plan it controls the PCC: GoodWe self-use owns a
    near-zero grid plan, and modes 9/10 own non-zero import/export targets.
    The configured deadband classifies both neutral battery power and near-zero
    grid power; it is never subtracted from a non-zero setpoint.

    Existing installations without an explicit strategy retain the legacy
    smart-meter boolean mapping for backwards compatibility.
    """

    def __init__(self, hass: HomeAssistant, entry, client: GWModbusClient, coordinator: GWEnergyPilotCoordinator) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client
        self.coordinator = coordinator
        self.enabled = False
        self.target_power = 0
        self.expected_mode = MODE_AUTO
        self.last_command = "goodwe_auto"
        self.manual_power = min(DEFAULT_MAX_POWER, int(entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER)))
        self.manual_charge_limit_soc: float | None = None
        self._unsubs: list[Callable[[], None]] = []
        self._ev_was_active = False
        self._control_lock = asyncio.Lock()
        self._plan_update_suspensions = 0
        self.grid_neutral_active = False
        self.grid_neutral_charge_cap = 0
        self.grid_neutral_last_meter_power: float | None = None
        self.grid_neutral_export_samples = 0

    @property
    def signal(self) -> str:
        return f"{DOMAIN}_{self.entry.entry_id}_controller_update"

    @property
    def grid_neutral_hold_remaining(self) -> int:
        return 0

    @property
    def control_strategy(self) -> str:
        """Return configured strategy with legacy boolean fallback."""
        data = getattr(self.entry, "data", {}) or {}
        configured = data.get(CONF_CONTROL_STRATEGY)
        if configured in CONTROL_STRATEGIES:
            return str(configured)
        return CONTROL_STRATEGY_GRID if bool(data.get(CONF_USE_GOODWE_SMART_METER, DEFAULT_USE_GOODWE_SMART_METER)) else CONTROL_STRATEGY_BATTERY

    @property
    def use_goodwe_smart_meter(self) -> bool:
        """Compatibility property for older diagnostics/frontend layers."""
        return self.control_strategy != CONTROL_STRATEGY_BATTERY

    def _notify_state(self) -> None:
        async_dispatcher_send(self.hass, self.signal)

    def _p_batt_entity_id(self) -> str:
        return str(self.entry.options.get(CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY) or DEFAULT_P_BATT_ENTITY)

    def _p_grid_entity_id(self) -> str:
        return str(self.entry.options.get(CONF_P_GRID_ENTITY, DEFAULT_P_GRID_ENTITY) or DEFAULT_P_GRID_ENTITY)

    def _ev_source_ids(self) -> set[str]:
        entity_ids = {self.entry.options.get(CONF_EV_MODE_ENTITY), self.entry.options.get(CONF_EV_POWER_ENTITY)}
        entity_ids.discard(None)
        entity_ids.discard("")
        return {str(entity_id) for entity_id in entity_ids}

    async def async_setup(self) -> None:
        self._ev_was_active = self.ev_is_active()
        entity_ids = {self._p_batt_entity_id(), self._p_grid_entity_id(), self.entry.options.get(CONF_OPTIM_STATUS_ENTITY), *self._ev_source_ids()}
        entity_ids.discard(None)
        entity_ids.discard("")
        if entity_ids:
            self._unsubs.append(async_track_state_change_event(self.hass, list(entity_ids), self._async_source_changed))
        add_listener = getattr(self.coordinator, "async_add_listener", None)
        if add_listener is not None:
            self._unsubs.append(add_listener(self._async_coordinator_updated))

    async def async_unload(self) -> None:
        while self._unsubs:
            self._unsubs.pop()()

    @callback
    def _async_source_changed(self, event: Event) -> None:
        if not self.enabled:
            return
        entity_id = str(event.data.get("entity_id") or "")
        if entity_id in self._ev_source_ids():
            ev_active = self.ev_is_active()
            ev_was_active = self._ev_was_active
            self._ev_was_active = ev_active
            if ev_active:
                self.hass.async_create_task(
                    self.async_evaluate(allow_suspended=True),
                    "gw-energypilot-ev-anti-discharge",
                )
                return
            if ev_was_active and self.entry.options.get(CONF_ENABLE_EMHASS_ORCHESTRATOR, False):
                self.target_power = 0
                self.expected_mode = MODE_BATTERY_HOLD
                self.last_command = "waiting_for_ev_stop_optimization"
                self._notify_state()
                return
        if self._plan_update_suspensions:
            return
        self.hass.async_create_task(self.async_evaluate(), "gw-energypilot-evaluate")

    @callback
    def _async_coordinator_updated(self) -> None:
        """Stop the Max charge quick action when its captured SOC limit is met."""
        if self.last_command != "manual_max_charge" or self.manual_charge_limit_soc is None:
            return
        battery_soc = self._battery_soc()
        if battery_soc is None or battery_soc < self.manual_charge_limit_soc:
            return
        self.hass.async_create_task(
            self._async_stop_manual_max_charge_at_limit(),
            "gw-energypilot-max-charge-soc-limit",
        )

    def _state_float(self, entity_id: str | None) -> float | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in {"unknown", "unavailable", "none", ""}:
            return None
        try:
            value = float(state.state)
        except (TypeError, ValueError):
            return None
        return value if isfinite(value) else None

    def _battery_soc(self) -> float | None:
        """Return the latest finite GoodWe battery SOC percentage."""
        data = self.coordinator.data
        values = getattr(data, "values", {}) if data is not None else {}
        raw = values.get("battery_soc") if isinstance(values, dict) else None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        if not isfinite(value) or not 0.0 <= value <= 100.0:
            return None
        return value

    def ev_is_active(self) -> bool:
        if not self.entry.options.get(CONF_ENABLE_EV_COORDINATION, False):
            return False
        mode_entity = self.entry.options.get(CONF_EV_MODE_ENTITY)
        power_entity = self.entry.options.get(CONF_EV_POWER_ENTITY)
        ev_deadband = float(self.entry.options.get(CONF_EV_DEADBAND, DEFAULT_EV_DEADBAND))
        mode_active = False
        if mode_entity:
            state = self.hass.states.get(mode_entity)
            mode_active = state is not None and state.state.lower() == "connected_charging"
        ev_power = self._state_float(power_entity)
        return mode_active or (ev_power is not None and ev_power > ev_deadband)

    def _optim_is_ready(self) -> bool:
        entity_id = self.entry.options.get(CONF_OPTIM_STATUS_ENTITY)
        if not entity_id:
            return True
        state = self.hass.states.get(entity_id)
        if state is None:
            return False
        required = str(self.entry.options.get(CONF_OPTIM_REQUIRED_STATE, DEFAULT_OPTIM_REQUIRED_STATE))
        return state.state == required

    def _actual_command_matches(self, mode: int, power: int) -> bool:
        data = self.coordinator.data
        if data is None or getattr(data, "mode", None) != mode:
            return False
        actual_power = getattr(data, "power", None)
        return actual_power is not None and int(actual_power) == int(power)

    async def _async_apply_command(self, mode: int, power: int, command: str, *, skip_if_readback_matches: bool = False) -> None:
        power = max(0, int(power))
        self.target_power = power
        self.expected_mode = mode
        self.last_command = command
        self._notify_state()
        if skip_if_readback_matches and self._actual_command_matches(mode, power):
            return
        await self.client.async_set_mode(mode, power)
        await self.coordinator.async_request_refresh()

    async def async_enable(self) -> None:
        self.manual_charge_limit_soc = None
        self.enabled = True
        self._ev_was_active = self.ev_is_active()
        self._notify_state()
        await self.async_evaluate()

    async def async_disable(self) -> None:
        async with self._control_lock:
            self.manual_charge_limit_soc = None
            self.enabled = False
            await self._async_apply_command(MODE_AUTO, 0, "goodwe_auto")

    async def async_hold_for_plan_step(self, command: str) -> None:
        """Fail safe to Battery Hold when a scheduled plan step is unavailable."""
        async with self._control_lock:
            if not self.enabled:
                return
            await self._async_apply_command(
                MODE_BATTERY_HOLD,
                0,
                command,
                skip_if_readback_matches=True,
            )

    def suspend_plan_updates(self) -> None:
        """Defer ordinary plan-source events until publication is complete."""
        self._plan_update_suspensions += 1

    def resume_plan_updates(self) -> None:
        """Release one plan-publication suspension without going negative."""
        self._plan_update_suspensions = max(0, self._plan_update_suspensions - 1)

    async def async_manual_command(self, mode: int, power: int, command: str) -> None:
        async with self._control_lock:
            self.manual_charge_limit_soc = None
            self.enabled = False
            await self._async_apply_command(mode, power, command)

    async def async_manual_max_charge(self, power: int, maximum_soc: float) -> None:
        """Start Max charge with a telemetry-enforced EMHASS maximum-SOC ceiling."""
        try:
            limit_soc = float(maximum_soc)
        except (TypeError, ValueError) as err:
            raise ValueError("Maximum battery SOC is not numeric") from err
        if not isfinite(limit_soc) or not 0.0 <= limit_soc <= 100.0:
            raise ValueError("Maximum battery SOC must be between 0 and 100%")

        async with self._control_lock:
            battery_soc = self._battery_soc()
            if battery_soc is None:
                raise ValueError("Current GoodWe battery SOC is unavailable")

            self.enabled = False
            self.manual_charge_limit_soc = limit_soc
            if battery_soc >= limit_soc:
                await self._async_apply_command(
                    MODE_BATTERY_HOLD,
                    0,
                    "manual_max_charge_soc_limit",
                    skip_if_readback_matches=True,
                )
                return
            await self._async_apply_command(
                MODE_CHARGE_BATTERY,
                power,
                "manual_max_charge",
            )

    async def _async_stop_manual_max_charge_at_limit(self) -> None:
        """Recheck the SOC ceiling under the control lock and hold the battery."""
        async with self._control_lock:
            if self.last_command != "manual_max_charge" or self.manual_charge_limit_soc is None:
                return
            battery_soc = self._battery_soc()
            if battery_soc is None or battery_soc < self.manual_charge_limit_soc:
                return
            await self._async_apply_command(
                MODE_BATTERY_HOLD,
                0,
                "manual_max_charge_soc_limit",
                skip_if_readback_matches=True,
            )

    async def _async_apply_direct_battery_plan(self, p_batt: float, deadband: float, max_power: int) -> None:
        power = min(int(abs(p_batt)), max_power)
        if p_batt > deadband:
            await self._async_apply_command(MODE_DISCHARGE_BATTERY, power, "battery_discharge", skip_if_readback_matches=True)
            return
        if p_batt < -deadband:
            await self._async_apply_command(MODE_CHARGE_BATTERY, power, "battery_charge", skip_if_readback_matches=True)
            return
        await self._async_apply_command(MODE_BATTERY_HOLD, 0, "battery_hold", skip_if_readback_matches=True)

    async def _async_apply_ev_anti_discharge_plan(self, p_batt: float, deadband: float, max_power: int) -> None:
        if p_batt < -deadband:
            power = min(int(abs(p_batt)), max_power)
            await self._async_apply_command(MODE_CHARGE_BATTERY, power, "ev_charge_allowed", skip_if_readback_matches=True)
            return
        await self._async_apply_command(MODE_BATTERY_HOLD, 0, "ev_anti_discharge_hold", skip_if_readback_matches=True)

    async def _async_apply_smart_meter_plan(self, p_grid: float, deadband: float, max_power: int) -> None:
        if p_grid > deadband:
            power = min(int(abs(p_grid)), max_power)
            await self._async_apply_command(MODE_GRID_IMPORT_TARGET, power, "grid_import_target", skip_if_readback_matches=True)
            return
        if p_grid < -deadband:
            power = min(int(abs(p_grid)), max_power)
            await self._async_apply_command(MODE_GRID_EXPORT_TARGET, power, "grid_export_target", skip_if_readback_matches=True)
            return
        await self._async_apply_command(MODE_AUTO, 0, "grid_zero_auto", skip_if_readback_matches=True)

    async def _async_apply_hybrid_plan(self, p_batt: float, p_grid: float, deadband: float, max_power: int) -> None:
        """Hold neutral battery plans, otherwise execute the signed PCC plan."""
        if abs(p_batt) <= deadband:
            await self._async_apply_command(MODE_BATTERY_HOLD, 0, "hybrid_battery_hold", skip_if_readback_matches=True)
            return
        if abs(p_grid) <= deadband:
            await self._async_apply_command(MODE_AUTO, 0, "hybrid_grid_zero_auto", skip_if_readback_matches=True)
            return

        power = min(int(abs(p_grid)), max_power)
        if p_grid > deadband:
            await self._async_apply_command(MODE_GRID_IMPORT_TARGET, power, "hybrid_grid_import", skip_if_readback_matches=True)
            return
        await self._async_apply_command(MODE_GRID_EXPORT_TARGET, power, "hybrid_grid_export", skip_if_readback_matches=True)

    async def _async_evaluate_locked(self) -> None:
        if not self.enabled:
            return
        p_batt = self._state_float(self._p_batt_entity_id())
        if p_batt is None:
            self.last_command = "waiting_for_p_batt"
            self._notify_state()
            return
        if not self._optim_is_ready():
            self.last_command = "waiting_for_optimization"
            self._notify_state()
            return
        deadband = float(self.entry.options.get(CONF_DEADBAND, DEFAULT_DEADBAND))
        max_power = int(self.entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER))
        if self.ev_is_active():
            await self._async_apply_ev_anti_discharge_plan(p_batt, deadband, max_power)
            return
        strategy = self.control_strategy
        if strategy == CONTROL_STRATEGY_BATTERY:
            await self._async_apply_direct_battery_plan(p_batt, deadband, max_power)
            return
        p_grid = self._state_float(self._p_grid_entity_id())
        if p_grid is None:
            self.last_command = "waiting_for_p_grid"
            self._notify_state()
            return
        if strategy == CONTROL_STRATEGY_HYBRID:
            await self._async_apply_hybrid_plan(p_batt, p_grid, deadband, max_power)
            return
        await self._async_apply_smart_meter_plan(p_grid, deadband, max_power)

    async def async_evaluate(self, *, allow_suspended: bool = False) -> None:
        if self._plan_update_suspensions and not allow_suspended:
            return
        async with self._control_lock:
            await self._async_evaluate_locked()
