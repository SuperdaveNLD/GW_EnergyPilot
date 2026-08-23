"""Automatic control logic for GW EnergyPilot."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
from math import isfinite
from time import monotonic

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

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
    DEFAULT_DEADBAND,
    DEFAULT_EV_DEADBAND,
    DEFAULT_MAX_POWER,
    DEFAULT_OPTIM_REQUIRED_STATE,
    DEFAULT_P_BATT_ENTITY,
    DEFAULT_P_GRID_ENTITY,
    DOMAIN,
    GRID_NEUTRAL_CONTROL_INTERVAL_SECONDS,
    GRID_NEUTRAL_HOLD_SECONDS,
    GRID_NEUTRAL_RAMP_UP_STEP,
    GRID_NEUTRAL_RESTART_SAMPLES,
    MODE_AUTO,
    MODE_BATTERY_HOLD,
    MODE_CHARGE_BATTERY,
    MODE_DISCHARGE_BATTERY,
)
from .coordinator import GWEnergyPilotCoordinator


class GWEnergyPilotController:
    """Translate external EMHASS state into GoodWe EMS commands."""

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

        # Runtime state for planned zero-grid charging. EMHASS remains the
        # source of direction/cap; the GoodWe smart meter is slow feedback that
        # prevents a PV forecast miss from silently becoming grid charging.
        self.grid_neutral_active = False
        self.grid_neutral_charge_cap = 0
        self.grid_neutral_last_meter_power: float | None = None
        self.grid_neutral_export_samples = 0
        self._grid_neutral_hold_until = 0.0

    @property
    def signal(self) -> str:
        """Dispatcher signal for controller ownership/state changes."""
        return f"{DOMAIN}_{self.entry.entry_id}_controller_update"

    @property
    def grid_neutral_hold_remaining(self) -> int:
        """Return remaining anti-flap hold time in seconds."""
        return max(0, int(round(self._grid_neutral_hold_until - monotonic())))

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
        """Subscribe to configured Home Assistant entities and feedback timer."""
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

        self._unsubs.append(
            async_track_time_interval(
                self.hass,
                self._async_grid_neutral_feedback,
                timedelta(seconds=GRID_NEUTRAL_CONTROL_INTERVAL_SECONDS),
                name=f"GW EnergyPilot grid-neutral charge ({self.entry.entry_id})",
                cancel_on_shutdown=True,
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
        the already-active Battery Hold command in place until a fresh EMHASS
        optimization publishes a new P_batt target. The new P_batt state change
        will then call async_evaluate(). This avoids briefly executing the stale
        pre-EV battery target before the EV-stop optimization finishes.
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
                self._reset_grid_neutral_state()
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

    def _grid_meter_power(self) -> float | None:
        """Return GoodWe smart-meter power; positive export, negative import."""
        data = self.coordinator.data
        values = getattr(data, "values", None) if data is not None else None
        if not isinstance(values, dict):
            return None
        try:
            value = float(values.get("meter_total_power_fast"))
        except (TypeError, ValueError):
            return None
        return value if isfinite(value) else None

    def _actual_charge_power(self) -> int:
        """Return best known current GoodWe mode-11 setpoint."""
        data = self.coordinator.data
        if data is not None and getattr(data, "mode", None) == MODE_CHARGE_BATTERY:
            power = getattr(data, "power", None)
            if power is not None:
                return max(0, int(power))
        if self.expected_mode == MODE_CHARGE_BATTERY:
            return max(0, int(self.target_power))
        return 0

    def _reset_grid_neutral_state(self) -> None:
        self.grid_neutral_active = False
        self.grid_neutral_charge_cap = 0
        self.grid_neutral_last_meter_power = None
        self.grid_neutral_export_samples = 0
        self._grid_neutral_hold_until = 0.0

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

    async def _async_apply_command(self, mode: int, power: int, command: str) -> None:
        """Update controller state and write only when inverter readback differs."""
        power = max(0, int(power))
        self.target_power = power
        self.expected_mode = mode
        self.last_command = command
        self._notify_state()

        if self._actual_command_matches(mode, power):
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
            self._reset_grid_neutral_state()
            await self._async_apply_command(MODE_AUTO, 0, "goodwe_auto")

    async def async_manual_command(self, mode: int, power: int, command: str) -> None:
        """Apply a manual command and give manual control ownership.

        Manual quick actions deliberately disable Automatic Control before the
        new mode is written. This prevents a later P_batt/P_grid state change
        from immediately overwriting a user-requested command.
        """
        async with self._control_lock:
            self.enabled = False
            self._reset_grid_neutral_state()
            await self._async_apply_command(mode, power, command)

    async def _async_enter_grid_neutral_hold(self, command: str) -> None:
        """Stop charging and enforce a minimum dwell before restarting."""
        now = monotonic()
        if self._grid_neutral_hold_until <= now:
            self._grid_neutral_hold_until = now + GRID_NEUTRAL_HOLD_SECONDS
        self.grid_neutral_export_samples = 0
        await self._async_apply_command(MODE_BATTERY_HOLD, 0, command)

    @staticmethod
    def _round_charge_power(power: float, cap: int) -> int:
        """Round feedback setpoints to 50 W and clamp to the EMHASS cap."""
        rounded = int(round(max(0.0, power) / 50.0) * 50)
        return min(max(0, rounded), max(0, int(cap)))

    async def _async_apply_grid_neutral_charge(
        self,
        p_batt: float,
        deadband: float,
        *,
        feedback_tick: bool,
    ) -> None:
        """Follow actual AC-coupled surplus without importing to meet forecast.

        EMHASS decides that the battery should charge and publishes a near-zero
        P_grid target. EnergyPilot treats abs(P_batt) as a maximum only. The
        actual mode-11 setpoint is trimmed from GoodWe meter register 36008.

        GoodWe meter convention here is positive export / negative import.
        Reductions happen immediately. Increases are limited to 1 kW per 30 s.
        If charging reaches zero, mode 8 is held for at least two minutes and
        requires two consecutive feedback ticks with clear export before mode
        11 can resume. This prevents charge/hold flapping under passing clouds.
        """
        max_power = int(self.entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER))
        cap = min(int(abs(p_batt)), max_power)
        self.grid_neutral_active = True
        self.grid_neutral_charge_cap = cap

        meter = self._grid_meter_power()
        self.grid_neutral_last_meter_power = meter
        if meter is None:
            await self._async_enter_grid_neutral_hold(
                "grid_neutral_meter_unavailable"
            )
            return

        now = monotonic()
        if self._grid_neutral_hold_until > now:
            await self._async_apply_command(
                MODE_BATTERY_HOLD,
                0,
                "grid_neutral_hold",
            )
            return

        # Once a protective hold was entered, only the 30-second feedback tick
        # may count restart evidence. Normal HA state events cannot bypass the
        # anti-flap dwell/restart requirement.
        if self._grid_neutral_hold_until > 0.0:
            if not feedback_tick:
                await self._async_apply_command(
                    MODE_BATTERY_HOLD,
                    0,
                    "grid_neutral_hold",
                )
                return

            restart_threshold = max(float(deadband) * 2.0, 600.0)
            if meter > restart_threshold:
                self.grid_neutral_export_samples += 1
            else:
                self.grid_neutral_export_samples = 0

            if self.grid_neutral_export_samples < GRID_NEUTRAL_RESTART_SAMPLES:
                await self._async_apply_command(
                    MODE_BATTERY_HOLD,
                    0,
                    "grid_neutral_waiting_for_surplus",
                )
                return

            self._grid_neutral_hold_until = 0.0
            self.grid_neutral_export_samples = 0
            restart_power = min(
                GRID_NEUTRAL_RAMP_UP_STEP,
                max(0.0, meter - float(deadband)),
            )
            restart_power = self._round_charge_power(restart_power, cap)
            if restart_power <= deadband:
                await self._async_enter_grid_neutral_hold("grid_neutral_hold")
                return
            await self._async_apply_command(
                MODE_CHARGE_BATTERY,
                restart_power,
                "grid_neutral_charge",
            )
            return

        current = self._actual_charge_power()
        if current <= 0:
            if meter <= deadband:
                await self._async_enter_grid_neutral_hold("grid_neutral_hold")
                return
            proposed = min(
                float(cap),
                float(GRID_NEUTRAL_RAMP_UP_STEP),
                max(0.0, meter - float(deadband)),
            )
        elif current > cap:
            proposed = float(cap)
        elif meter < -deadband:
            # Import is unsafe in a planned-zero-grid charge interval. Reduce
            # by the full observed import in one correction instead of ramping.
            proposed = max(0.0, float(current) + meter)
        elif meter > deadband:
            desired = min(float(cap), float(current) + meter)
            proposed = min(
                desired,
                float(current + GRID_NEUTRAL_RAMP_UP_STEP),
            )
        else:
            proposed = float(current)

        proposed_power = self._round_charge_power(proposed, cap)
        if proposed_power <= deadband:
            await self._async_enter_grid_neutral_hold("grid_neutral_hold")
            return

        await self._async_apply_command(
            MODE_CHARGE_BATTERY,
            proposed_power,
            "grid_neutral_charge",
        )

    async def _async_evaluate_locked(self) -> None:
        """Apply one EMHASS-to-EMS evaluation with control lock held."""
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
            self._reset_grid_neutral_state()
            await self._async_apply_command(MODE_BATTERY_HOLD, 0, "ev_hold")
            return

        deadband = float(self.entry.options.get(CONF_DEADBAND, DEFAULT_DEADBAND))
        max_power = int(self.entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER))
        power = min(int(abs(p_batt)), max_power)

        if p_batt > deadband:
            self._reset_grid_neutral_state()
            await self._async_apply_command(
                MODE_DISCHARGE_BATTERY,
                power,
                "battery_discharge",
            )
            return

        if p_batt < -deadband:
            p_grid = self._state_float(self._p_grid_entity_id())
            if p_grid is None:
                self._reset_grid_neutral_state()
                await self._async_apply_command(
                    MODE_BATTERY_HOLD,
                    0,
                    "waiting_for_p_grid",
                )
                return

            if abs(p_grid) <= deadband:
                await self._async_apply_grid_neutral_charge(
                    p_batt,
                    deadband,
                    feedback_tick=False,
                )
                return

            # EMHASS explicitly planned non-zero grid flow. Preserve the legacy
            # direct battery-power execution so intentional grid charging still
            # works; only near-zero P_grid charging is meter-limited.
            self._reset_grid_neutral_state()
            await self._async_apply_command(
                MODE_CHARGE_BATTERY,
                power,
                "battery_charge",
            )
            return

        self._reset_grid_neutral_state()
        await self._async_apply_command(MODE_BATTERY_HOLD, 0, "battery_hold")

    async def async_evaluate(self) -> None:
        """Apply EMHASS-to-EMS mapping."""
        async with self._control_lock:
            await self._async_evaluate_locked()

    async def _async_grid_neutral_feedback(self, _now: datetime) -> None:
        """Trim active planned-zero-grid charging every 30 seconds."""
        async with self._control_lock:
            if not self.enabled or not self.grid_neutral_active:
                return

            p_batt = self._state_float(self._p_batt_entity_id())
            p_grid = self._state_float(self._p_grid_entity_id())
            deadband = float(
                self.entry.options.get(CONF_DEADBAND, DEFAULT_DEADBAND)
            )

            if (
                p_batt is None
                or p_batt >= -deadband
                or p_grid is None
                or abs(p_grid) > deadband
                or not self._optim_is_ready()
                or self.ev_is_active()
            ):
                await self._async_evaluate_locked()
                return

            await self._async_apply_grid_neutral_charge(
                p_batt,
                deadband,
                feedback_tick=True,
            )
