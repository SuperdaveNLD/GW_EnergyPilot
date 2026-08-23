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

    Two automatic actuator strategies are intentionally supported:

    GoodWe smart meter enabled (default):
      P_grid > 0 = mode 9 import target at the PCC
      P_grid < 0 = mode 10 export target at the PCC
      P_grid ~= 0 = mode 1 GoodWe Auto / self-use balancing

    GoodWe smart meter disabled:
      P_batt < 0 = mode 11 direct battery charge target
      P_batt > 0 = mode 12 direct battery discharge target
      P_batt ~= 0 = mode 8 Battery Hold

    The smart-meter strategy lets GoodWe close the fast control loop against its
    own meter, so actual DC PV, AC-coupled generation and house load can change
    without EnergyPilot continuously trimming a battery-power setpoint.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry,
        client: GWModbusClient,
        coordinator: GWEnergyPilotCoordinator,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client
        self.coordinator = coordinator
        self.enabled = False
        self.target_power = 0
        self.expected_mode = MODE_AUTO
        self.last_command = "goodwe_auto"
        self.manual_power = min(
            DEFAULT_MAX_POWER,
            int(entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER)),
        )
        self._unsubs: list[Callable[[], None]] = []
        self._ev_was_active = False
        self._control_lock = asyncio.Lock()

        # Backwards-compatible diagnostics for v0.18-v0.21 support snapshots.
        # The old 30-second mode-11 feedback controller is not scheduled in
        # v0.22; these remain inactive so older frontend layers do not break.
        self.grid_neutral_active = False
        self.grid_neutral_charge_cap = 0
        self.grid_neutral_last_meter_power: float | None = None
        self.grid_neutral_export_samples = 0

    @property
    def signal(self) -> str:
        """Dispatcher signal for controller ownership/state changes."""
        return f"{DOMAIN}_{self.entry.entry_id}_controller_update"

    @property
    def grid_neutral_hold_remaining(self) -> int:
        """Return zero for the retired v0.18-v0.21 grid-neutral hold loop."""
        return 0

    @property
    def use_goodwe_smart_meter(self) -> bool:
        """Return whether Automatic Control should use PCC target modes 9/10."""
        data = getattr(self.entry, "data", {}) or {}
        return bool(
            data.get(
                CONF_USE_GOODWE_SMART_METER,
                DEFAULT_USE_GOODWE_SMART_METER,
            )
        )

    def _notify_state(self) -> None:
        """Notify entities that expose controller-owned state."""
        async_dispatcher_send(self.hass, self.signal)

    def _p_batt_entity_id(self) -> str:
        return str(
            self.entry.options.get(CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY)
            or DEFAULT_P_BATT_ENTITY
        )

    def _p_grid_entity_id(self) -> str:
        return str(
            self.entry.options.get(CONF_P_GRID_ENTITY, DEFAULT_P_GRID_ENTITY)
            or DEFAULT_P_GRID_ENTITY
        )

    def _ev_source_ids(self) -> set[str]:
        """Return configured EV source entity IDs."""
        entity_ids = {
            self.entry.options.get(CONF_EV_MODE_ENTITY),
            self.entry.options.get(CONF_EV_POWER_ENTITY),
        }
        entity_ids.discard(None)
        entity_ids.discard("")
        return {str(entity_id) for entity_id in entity_ids}

    async def async_setup(self) -> None:
        """Subscribe to configured Home Assistant plan and EV entities."""
        self._ev_was_active = self.ev_is_active()

        entity_ids = {
            self._p_batt_entity_id(),
            self._p_grid_entity_id(),
            self.entry.options.get(CONF_OPTIM_STATUS_ENTITY),
            *self._ev_source_ids(),
        }
        entity_ids.discard(None)
        entity_ids.discard("")
        if entity_ids:
            self._unsubs.append(
                async_track_state_change_event(
                    self.hass,
                    list(entity_ids),
                    self._async_source_changed,
                )
            )

    async def async_unload(self) -> None:
        """Remove listeners."""
        while self._unsubs:
            self._unsubs.pop()()

    @callback
    def _async_source_changed(self, event: Event) -> None:
        """Schedule reevaluation after an input entity changed.

        When EV charging stops while the native orchestrator is enabled, keep
        Battery Hold in place until a fresh EMHASS optimization publishes a new
        plan. This avoids briefly executing the stale pre-EV target.
        """
        if not self.enabled:
            return

        entity_id = str(event.data.get("entity_id") or "")
        if entity_id in self._ev_source_ids():
            ev_active = self.ev_is_active()
            ev_was_active = self._ev_was_active
            self._ev_was_active = ev_active

            if ev_active:
                self.hass.async_create_task(
                    self.async_evaluate(),
                    "gw-energypilot-ev-hold",
                )
                return

            if (
                ev_was_active
                and self.entry.options.get(
                    CONF_ENABLE_EMHASS_ORCHESTRATOR,
                    False,
                )
            ):
                self.target_power = 0
                self.expected_mode = MODE_BATTERY_HOLD
                self.last_command = "waiting_for_ev_stop_optimization"
                self._notify_state()
                return

        self.hass.async_create_task(
            self.async_evaluate(),
            "gw-energypilot-evaluate",
        )

    def _state_float(self, entity_id: str | None) -> float | None:
        """Return a finite entity state as float."""
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

    def ev_is_active(self) -> bool:
        """Return whether configured EV charging is active."""
        if not self.entry.options.get(CONF_ENABLE_EV_COORDINATION, False):
            return False

        mode_entity = self.entry.options.get(CONF_EV_MODE_ENTITY)
        power_entity = self.entry.options.get(CONF_EV_POWER_ENTITY)
        ev_deadband = float(
            self.entry.options.get(CONF_EV_DEADBAND, DEFAULT_EV_DEADBAND)
        )

        mode_active = False
        if mode_entity:
            state = self.hass.states.get(mode_entity)
            mode_active = (
                state is not None
                and state.state.lower() == "connected_charging"
            )

        ev_power = self._state_float(power_entity)
        power_active = ev_power is not None and ev_power > ev_deadband
        return mode_active or power_active

    def _optim_is_ready(self) -> bool:
        entity_id = self.entry.options.get(CONF_OPTIM_STATUS_ENTITY)
        if not entity_id:
            return True
        state = self.hass.states.get(entity_id)
        if state is None:
            return False
        required = str(
            self.entry.options.get(
                CONF_OPTIM_REQUIRED_STATE,
                DEFAULT_OPTIM_REQUIRED_STATE,
            )
        )
        return state.state == required

    def _actual_command_matches(self, mode: int, power: int) -> bool:
        """Return whether coordinator readback already matches a command."""
        data = self.coordinator.data
        if data is None or getattr(data, "mode", None) != mode:
            return False
        actual_power = getattr(data, "power", None)
        return actual_power is not None and int(actual_power) == int(power)

    async def _async_apply_command(
        self,
        mode: int,
        power: int,
        command: str,
        *,
        skip_if_readback_matches: bool = False,
    ) -> None:
        """Update controller state and write one GoodWe EMS command."""
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
        """Enable automatic control."""
        self.enabled = True
        self._ev_was_active = self.ev_is_active()
        self._notify_state()
        await self.async_evaluate()

    async def async_disable(self) -> None:
        """Disable automatic control and return the inverter to GoodWe Auto."""
        async with self._control_lock:
            self.enabled = False
            await self._async_apply_command(MODE_AUTO, 0, "goodwe_auto")

    async def async_manual_command(self, mode: int, power: int, command: str) -> None:
        """Apply a manual command and give manual control ownership.

        Manual quick actions deliberately disable Automatic Control before the
        new mode is written. This prevents a later P_batt/P_grid state change
        from immediately overwriting a user-requested command.
        """
        async with self._control_lock:
            self.enabled = False
            await self._async_apply_command(mode, power, command)

    async def _async_apply_direct_battery_plan(
        self,
        p_batt: float,
        deadband: float,
        max_power: int,
    ) -> None:
        """Apply the legacy direct P_batt mapping using modes 11/12/8."""
        power = min(int(abs(p_batt)), max_power)
        if p_batt > deadband:
            await self._async_apply_command(
                MODE_DISCHARGE_BATTERY,
                power,
                "battery_discharge",
                skip_if_readback_matches=True,
            )
            return
        if p_batt < -deadband:
            await self._async_apply_command(
                MODE_CHARGE_BATTERY,
                power,
                "battery_charge",
                skip_if_readback_matches=True,
            )
            return
        await self._async_apply_command(
            MODE_BATTERY_HOLD,
            0,
            "battery_hold",
            skip_if_readback_matches=True,
        )

    async def _async_apply_smart_meter_plan(
        self,
        p_grid: float,
        deadband: float,
        max_power: int,
    ) -> None:
        """Apply EMHASS P_grid through GoodWe PCC target modes 9/10/1."""
        if p_grid > deadband:
            power = min(int(abs(p_grid)), max_power)
            await self._async_apply_command(
                MODE_GRID_IMPORT_TARGET,
                power,
                "grid_import_target",
                skip_if_readback_matches=True,
            )
            return

        if p_grid < -deadband:
            power = min(int(abs(p_grid)), max_power)
            await self._async_apply_command(
                MODE_GRID_EXPORT_TARGET,
                power,
                "grid_export_target",
                skip_if_readback_matches=True,
            )
            return

        # Around zero planned grid flow, let GoodWe's native self-use loop
        # balance the real site. Hardware testing on the ETA-G20 showed mode 1
        # naturally absorbing PV surplus into the battery while keeping the PCC
        # close to zero without a second EnergyPilot feedback controller.
        await self._async_apply_command(
            MODE_AUTO,
            0,
            "grid_zero_auto",
            skip_if_readback_matches=True,
        )

    async def _async_evaluate_locked(self) -> None:
        """Apply one EMHASS plan evaluation with control lock held."""
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

        if self.ev_is_active():
            await self._async_apply_command(
                MODE_BATTERY_HOLD,
                0,
                "ev_hold",
                skip_if_readback_matches=True,
            )
            return

        deadband = float(self.entry.options.get(CONF_DEADBAND, DEFAULT_DEADBAND))
        max_power = int(self.entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER))

        if not self.use_goodwe_smart_meter:
            await self._async_apply_direct_battery_plan(
                p_batt,
                deadband,
                max_power,
            )
            return

        p_grid = self._state_float(self._p_grid_entity_id())
        if p_grid is None:
            self.last_command = "waiting_for_p_grid"
            self._notify_state()
            return

        await self._async_apply_smart_meter_plan(
            p_grid,
            deadband,
            max_power,
        )

    async def async_evaluate(self) -> None:
        """Apply EMHASS-to-GoodWe automatic control mapping."""
        async with self._control_lock:
            await self._async_evaluate_locked()
