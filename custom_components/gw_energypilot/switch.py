"""Switch platform for GW EnergyPilot."""

from __future__ import annotations

import logging
from typing import Any, override

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import restore_state
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GWConfigEntry
from .entity import GWEnergyPilotEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GWConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up automatic control switch."""
    async_add_entities([GWAutomaticControlSwitch(entry)])


class GWAutomaticControlSwitch(
    GWEnergyPilotEntity,
    restore_state.RestoreEntity,
    SwitchEntity,
):
    """Master switch for EnergyPilot automatic control."""

    _attr_translation_key = "automatic_control"

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_automatic_control"

    @override
    async def async_added_to_hass(self) -> None:
        """Restore ownership without holding platform setup on Modbus I/O."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self.entry.runtime_data.controller.signal,
                self._async_controller_updated,
            )
        )

        previous = await self.async_get_last_state()
        restore_on = previous is not None and previous.state == STATE_ON

        # Publish the switch immediately. The inverter command is restored in a
        # background task so Home Assistant and the other EnergyPilot entities
        # do not wait for an occupied or temporarily unavailable Modbus socket.
        self.entry.runtime_data.controller.enabled = restore_on
        self.async_write_ha_state()
        self.hass.async_create_task(
            self._async_apply_restored_state(restore_on),
            f"GW EnergyPilot restore automatic control ({self.entry.entry_id})",
        )

    async def _async_apply_restored_state(self, restore_on: bool) -> None:
        """Apply the restored state after entity setup has completed."""
        try:
            if restore_on:
                await self.entry.runtime_data.controller.async_enable()
            else:
                await self.entry.runtime_data.controller.async_disable()
        except Exception:  # pragma: no cover - defensive background boundary
            _LOGGER.exception(
                "Unable to restore GW EnergyPilot automatic control to %s",
                "ON" if restore_on else "OFF",
            )

    @callback
    def _async_controller_updated(self) -> None:
        """Refresh the switch after quick actions or AUTO change ownership."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return whether EnergyPilot automatic control is enabled."""
        return self.entry.runtime_data.controller.enabled

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable automatic control."""
        await self.entry.runtime_data.controller.async_enable()
        self.async_write_ha_state()

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable automatic control and restore GoodWe Auto."""
        await self.entry.runtime_data.controller.async_disable()
        self.async_write_ha_state()
