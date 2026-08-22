"""Automatic control logic for GW EnergyPilot."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .client import GWModbusClient
from .const import (
    CONF_DEADBAND,
    CONF_MAX_POWER,
    CONF_OPTIM_REQUIRED_STATE,
    CONF_OPTIM_STATUS_ENTITY,
    CONF_P_BATT_ENTITY,
    DEFAULT_DEADBAND,
    DEFAULT_MAX_POWER,
    DEFAULT_OPTIM_REQUIRED_STATE,
    MODE_AUTO,
    MODE_BATTERY_HOLD,
    MODE_CHARGE_BATTERY,
    MODE_DISCHARGE_BATTERY,
)
from .coordinator import GWEnergyPilotCoordinator


class GWEnergyPilotController:
    """Map an optional EMHASS P_batt entity to GoodWe battery EMS modes."""

    def __init__(self, hass: HomeAssistant, entry, client: GWModbusClient, coordinator: GWEnergyPilotCoordinator) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client
        self.coordinator = coordinator
        self.enabled = False
        self.target_power = 0
        self.command = "goodwe_auto"
        self.manual_power = int(entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER))
        self._unsubs: list[Callable[[], None]] = []

    async def async_setup(self) -> None:
        entity_ids = [
            entity_id
            for entity_id in (
                self.entry.options.get(CONF_P_BATT_ENTITY),
                self.entry.options.get(CONF_OPTIM_STATUS_ENTITY),
            )
            if entity_id
        ]
        if entity_ids:
            self._unsubs.append(async_track_state_change_event(self.hass, entity_ids, self._source_changed))

    async def async_unload(self) -> None:
        while self._unsubs:
            self._unsubs.pop()()

    @callback
    def _source_changed(self, event: Event) -> None:
        if self.enabled:
            self.hass.async_create_task(self.async_evaluate(), "gw-energypilot-evaluate")

    def _float_state(self, entity_id: str | None) -> float | None:
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in {"unknown", "unavailable", "none", ""}:
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    def _optim_ready(self) -> bool:
        entity_id = self.entry.options.get(CONF_OPTIM_STATUS_ENTITY)
        if not entity_id:
            return True
        state = self.hass.states.get(entity_id)
        required = str(self.entry.options.get(CONF_OPTIM_REQUIRED_STATE, DEFAULT_OPTIM_REQUIRED_STATE))
        return state is not None and state.state == required

    async def async_enable(self) -> None:
        self.enabled = True
        await self.async_evaluate()

    async def async_disable(self) -> None:
        self.enabled = False
        self.target_power = 0
        self.command = "goodwe_auto"
        await self.client.async_set_mode(MODE_AUTO, 0)
        await self.coordinator.async_request_refresh()

    async def async_evaluate(self) -> None:
        if not self.enabled:
            return

        p_batt = self._float_state(self.entry.options.get(CONF_P_BATT_ENTITY))
        if p_batt is None:
            self.command = "waiting_for_p_batt"
            return
        if not self._optim_ready():
            self.command = "waiting_for_optimization"
            return

        deadband = float(self.entry.options.get(CONF_DEADBAND, DEFAULT_DEADBAND))
        max_power = int(self.entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER))
        power = min(int(abs(p_batt)), max_power)

        if p_batt > deadband:
            mode = MODE_DISCHARGE_BATTERY
            self.command = "battery_discharge"
        elif p_batt < -deadband:
            mode = MODE_CHARGE_BATTERY
            self.command = "battery_charge"
        else:
            mode = MODE_BATTERY_HOLD
            power = 0
            self.command = "battery_hold"

        self.target_power = power
        await self.client.async_set_mode(mode, power)
        await self.coordinator.async_request_refresh()
