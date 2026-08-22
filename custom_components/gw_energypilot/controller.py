"""Automatic control logic for GW EnergyPilot."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .client import GWModbusClient
from .const import (
    CONF_DEADBAND,
    CONF_ENABLE_EV_COORDINATION,
    CONF_EV_DEADBAND,
    CONF_EV_MODE_ENTITY,
    CONF_EV_POWER_ENTITY,
    CONF_MAX_POWER,
    CONF_OPTIM_REQUIRED_STATE,
    CONF_OPTIM_STATUS_ENTITY,
    CONF_P_BATT_ENTITY,
    DEFAULT_DEADBAND,
    DEFAULT_EV_DEADBAND,
    DEFAULT_MAX_POWER,
    DEFAULT_OPTIM_REQUIRED_STATE,
    MODE_AUTO,
    MODE_BATTERY_HOLD,
    MODE_CHARGE_BATTERY,
    MODE_DISCHARGE_BATTERY,
)
from .coordinator import GWEnergyPilotCoordinator


class GWEnergyPilotController:
    """Translate external EMHASS state into GoodWe EMS commands."""

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
        self._unsubs: list[Callable[[], None]] = []

    async def async_setup(self) -> None:
        """Subscribe to configured Home Assistant entities."""
        entity_ids = {
            self.entry.options.get(CONF_P_BATT_ENTITY),
            self.entry.options.get(CONF_OPTIM_STATUS_ENTITY),
            self.entry.options.get(CONF_EV_MODE_ENTITY),
            self.entry.options.get(CONF_EV_POWER_ENTITY),
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
        """Schedule reevaluation after an input entity changed."""
        if self.enabled:
            self.hass.async_create_task(self.async_evaluate(), "gw-energypilot-evaluate")

    def _state_float(self, entity_id: str | None) -> float | None:
        """Return entity state as float."""
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in {"unknown", "unavailable", "none", ""}:
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    def ev_is_active(self) -> bool:
        """Return whether configured EV charging is active."""
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
        power_active = ev_power is not None and ev_power > ev_deadband
        return mode_active or power_active

    def _optim_is_ready(self) -> bool:
        entity_id = self.entry.options.get(CONF_OPTIM_STATUS_ENTITY)
        if not entity_id:
            return True
        state = self.hass.states.get(entity_id)
        if state is None:
            return False
        required = str(self.entry.options.get(CONF_OPTIM_REQUIRED_STATE, DEFAULT_OPTIM_REQUIRED_STATE))
        return state.state == required

    async def async_enable(self) -> None:
        """Enable automatic control."""
        self.enabled = True
        await self.async_evaluate()

    async def async_disable(self) -> None:
        """Disable automatic control and return the inverter to GoodWe Auto."""
        self.enabled = False
        self.target_power = 0
        self.expected_mode = MODE_AUTO
        self.last_command = "goodwe_auto"
        await self.client.async_set_mode(MODE_AUTO, 0)
        await self.coordinator.async_request_refresh()

    async def async_manual_command(self, mode: int, power: int, command: str) -> None:
        """Apply a manual command and give manual control ownership.

        Manual quick actions deliberately disable Automatic Control before the
        new mode is written. This prevents a later P_batt state change from
        immediately overwriting a user-requested charge/export/hold command.
        Unlike async_disable(), this method does not write mode 1 first, so a
        quick action is applied with a single EMS transaction.
        """
        self.enabled = False
        self.target_power = max(0, int(power))
        self.expected_mode = mode
        self.last_command = command
        await self.client.async_set_mode(mode, self.target_power)
        await self.coordinator.async_request_refresh()

    async def async_evaluate(self) -> None:
        """Apply EMHASS-to-EMS mapping."""
        if not self.enabled:
            return

        p_batt = self._state_float(self.entry.options.get(CONF_P_BATT_ENTITY))
        if p_batt is None:
            self.last_command = "waiting_for_p_batt"
            return

        if not self._optim_is_ready():
            self.last_command = "waiting_for_optimization"
            return

        if self.ev_is_active():
            mode = MODE_BATTERY_HOLD
            power = 0
            command = "ev_hold"
        else:
            deadband = float(self.entry.options.get(CONF_DEADBAND, DEFAULT_DEADBAND))
            max_power = int(self.entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER))
            power = min(int(abs(p_batt)), max_power)

            if p_batt > deadband:
                mode = MODE_DISCHARGE_BATTERY
                command = "battery_discharge"
            elif p_batt < -deadband:
                mode = MODE_CHARGE_BATTERY
                command = "battery_charge"
            else:
                mode = MODE_BATTERY_HOLD
                power = 0
                command = "battery_hold"

        self.target_power = power
        self.expected_mode = mode
        self.last_command = command

        await self.client.async_set_mode(mode, power)
        await self.coordinator.async_request_refresh()
