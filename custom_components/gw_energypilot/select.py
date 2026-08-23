"""Select platform for GW EnergyPilot."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from . import GWConfigEntry
from .const import MODE_NAMES, MODES_ZERO_POWER
from .emhass_config import (
    async_get_emhass_cost_function,
    async_set_emhass_cost_function,
)
from .entity import GWEnergyPilotEntity

_LOGGER = logging.getLogger(__name__)

MODE_OPTIONS = [f"{mode}: {name}" for mode, name in MODE_NAMES.items()]

EMHASS_STRATEGY_OPTIONS: dict[str, str] = {
    "Profit": "profit",
    "Cost": "cost",
    "Self-consumption": "self-consumption",
}
EMHASS_STRATEGY_REFRESH = timedelta(minutes=2)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GWConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up EnergyPilot select entities."""
    async_add_entities(
        [
            GWEMSModeSelect(entry),
            GWEMHASSCostFunctionSelect(entry),
        ]
    )


class GWEMSModeSelect(GWEnergyPilotEntity, SelectEntity):
    """Manual EMS mode selector."""

    _attr_translation_key = "manual_mode"
    _attr_options = MODE_OPTIONS
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_manual_mode"

    @property
    def current_option(self) -> str | None:
        """Return current EMS mode as an option."""
        if not self.coordinator.data:
            return None
        mode = self.coordinator.data.mode
        name = MODE_NAMES.get(mode)
        return f"{mode}: {name}" if name else None

    async def async_select_option(self, option: str) -> None:
        """Apply the selected EMS mode and switch to manual ownership."""
        mode = int(option.split(":", 1)[0])
        power = (
            0
            if mode in MODES_ZERO_POWER
            else self.entry.runtime_data.controller.manual_power
        )
        await self.entry.runtime_data.controller.async_manual_command(
            mode,
            power,
            f"manual_mode_{mode}",
        )


class GWEMHASSCostFunctionSelect(GWEnergyPilotEntity, SelectEntity):
    """Stateful selector for the active EMHASS optimization strategy."""

    _attr_translation_key = "emhass_cost_function"
    _attr_icon = "mdi:tune-variant"
    _attr_options = list(EMHASS_STRATEGY_OPTIONS)
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_emhass_cost_function"
        self._cost_function: str | None = None

    @property
    def current_option(self) -> str | None:
        """Return the user-facing option matching the active EMHASS costfun."""
        for option, value in EMHASS_STRATEGY_OPTIONS.items():
            if value == self._cost_function:
                return option
        return None

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Expose the raw EMHASS config value for diagnostics."""
        return {
            "emhass_costfun": self._cost_function,
            "source": "EMHASS /get-config",
        }

    async def async_added_to_hass(self) -> None:
        """Read the active strategy and keep it synchronized periodically."""
        await super().async_added_to_hass()
        self.entry.async_create_background_task(
            self.hass,
            self._async_refresh_from_emhass(),
            "GW EnergyPilot read EMHASS cost function",
        )
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._async_periodic_refresh,
                EMHASS_STRATEGY_REFRESH,
                name=f"GW EnergyPilot EMHASS strategy refresh ({self.entry.entry_id})",
                cancel_on_shutdown=True,
            )
        )

    async def _async_periodic_refresh(self, _now: datetime) -> None:
        """Refresh costfun so changes made in the EMHASS UI also appear here."""
        await self._async_refresh_from_emhass()

    async def _async_refresh_from_emhass(self) -> None:
        try:
            cost_function = await async_get_emhass_cost_function(self.hass, self.entry)
        except HomeAssistantError as err:
            _LOGGER.debug("Unable to refresh EMHASS cost function: %s", err)
            return

        if cost_function == self._cost_function:
            return
        self._cost_function = cost_function
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        """Save one strategy, expose it immediately, then rebuild the plan."""
        cost_function = EMHASS_STRATEGY_OPTIONS.get(option)
        if cost_function is None:
            raise HomeAssistantError(f"Unsupported EMHASS strategy option: {option}")

        await async_set_emhass_cost_function(
            self.hass,
            self.entry,
            cost_function,
        )
        self._cost_function = cost_function
        self.async_write_ha_state()

        try:
            await self.entry.runtime_data.orchestrator.async_optimize(
                reason=f"cost_function_{cost_function}"
            )
        except HomeAssistantError as err:
            raise HomeAssistantError(
                f"EMHASS strategy was saved as {option}, but the fresh "
                f"optimization failed: {err}"
            ) from err
