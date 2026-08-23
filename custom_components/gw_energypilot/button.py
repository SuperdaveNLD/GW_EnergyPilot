"""Button entities for GW EnergyPilot."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GWConfigEntry
from .const import (
    CONF_MAX_POWER,
    DEFAULT_MAX_POWER,
    MODE_BATTERY_HOLD,
    MODE_CHARGE_BATTERY,
    MODE_GRID_EXPORT_TARGET,
)
from .entity import GWEnergyPilotEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GWConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up EnergyPilot button entities."""
    async_add_entities(
        [
            GWOptimizeNowButton(entry),
            GWMaxExportButton(entry),
            GWBatteryPauseButton(entry),
            GWMaxChargeButton(entry),
            GWResumeAutoButton(entry),
        ]
    )


class GWOptimizeNowButton(GWEnergyPilotEntity, ButtonEntity):
    """Run one complete EMHASS optimization and publish cycle."""

    _attr_translation_key = "optimize_now"
    _attr_icon = "mdi:play-circle-outline"

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_optimize_now"

    async def async_added_to_hass(self) -> None:
        """Subscribe to native orchestrator status updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self.entry.runtime_data.orchestrator.signal,
                self._async_orchestrator_updated,
            )
        )

    @callback
    def _async_orchestrator_updated(self) -> None:
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose current optimizer status on the same native entity."""
        orchestrator = self.entry.runtime_data.orchestrator
        return {
            "orchestrator_status": orchestrator.status,
            **orchestrator.attributes,
        }

    async def async_press(self) -> None:
        """Start a manual optimization."""
        await self.entry.runtime_data.orchestrator.async_optimize(reason="manual_button")


class _GWManualBatteryButton(GWEnergyPilotEntity, ButtonEntity):
    """Base class for one-touch GoodWe battery commands."""

    mode: int
    command: str
    use_max_power = False

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_{self.entity_description_key}"

    @property
    def entity_description_key(self) -> str:
        """Return stable key used for the entity unique ID."""
        raise NotImplementedError

    async def async_press(self) -> None:
        """Take manual ownership and apply the requested GoodWe EMS command."""
        power = (
            int(self.entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER))
            if self.use_max_power
            else 0
        )
        await self.entry.runtime_data.controller.async_manual_command(
            self.mode,
            power,
            self.command,
        )


class GWMaxExportButton(_GWManualBatteryButton):
    """Request the configured maximum export at the grid connection."""

    _attr_translation_key = "max_export"
    _attr_icon = "mdi:transmission-tower-export"
    mode = MODE_GRID_EXPORT_TARGET
    command = "manual_max_export"
    use_max_power = True

    @property
    def entity_description_key(self) -> str:
        return "max_export"


class GWBatteryPauseButton(_GWManualBatteryButton):
    """Hold battery power at approximately zero watts."""

    _attr_translation_key = "battery_pause"
    _attr_icon = "mdi:pause-circle-outline"
    mode = MODE_BATTERY_HOLD
    command = "manual_battery_hold"

    @property
    def entity_description_key(self) -> str:
        return "battery_pause"


class GWMaxChargeButton(_GWManualBatteryButton):
    """Charge the battery at the configured maximum power."""

    _attr_translation_key = "max_charge"
    _attr_icon = "mdi:battery-charging-high"
    mode = MODE_CHARGE_BATTERY
    command = "manual_max_charge"
    use_max_power = True

    @property
    def entity_description_key(self) -> str:
        return "max_charge"


class GWResumeAutoButton(GWEnergyPilotEntity, ButtonEntity):
    """Create a fresh EMHASS plan and resume automatic battery control."""

    _attr_translation_key = "resume_auto"
    _attr_icon = "mdi:autorenew"

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_resume_auto"

    async def async_press(self) -> None:
        """Optimize first, then enable Automatic Control only on success.

        Keeping the controller in its current manual state until EMHASS has
        produced a fresh P_batt target prevents an old plan from being applied
        during the transition back to automatic control. If optimization fails,
        automatic control remains off and the existing manual state is kept.
        """
        await self.entry.runtime_data.orchestrator.async_optimize(
            reason="resume_auto"
        )
        await self.entry.runtime_data.controller.async_enable()
