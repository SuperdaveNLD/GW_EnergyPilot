"""Number platform for GW EnergyPilot."""

from __future__ import annotations

from collections.abc import Callable
import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_call_later

from . import GWConfigEntry
from .const import CONF_MAX_POWER, DEFAULT_MAX_POWER
from .emhass_config import async_get_emhass_config, async_write_emhass_config
from .entity import GWEnergyPilotEntity

_LOGGER = logging.getLogger(__name__)
SOC_OPTIMIZE_DEBOUNCE_SECONDS = 3.0
_SOC_OPTIMIZE_CANCEL: dict[str, Callable[[], None]] = {}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GWConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up EnergyPilot number entities."""
    async_add_entities(
        [
            GWManualPowerNumber(entry),
            GWEMHASSMinimumSOCNumber(entry),
            GWEMHASSMaximumSOCNumber(entry),
        ]
    )


class GWManualPowerNumber(GWEnergyPilotEntity, NumberEntity):
    """Manual power used when selecting an EMS mode."""

    _attr_translation_key = "manual_power"
    _attr_native_min_value = 0
    _attr_native_step = 100
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_manual_power"
        self._attr_native_max_value = int(
            entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER)
        )

    @property
    def native_value(self) -> int:
        """Return currently selected manual power."""
        return self.entry.runtime_data.controller.manual_power

    async def async_set_native_value(self, value: float) -> None:
        """Set manual power."""
        self.entry.runtime_data.controller.manual_power = int(value)
        self.async_write_ha_state()


class _GWEMHASSSOCNumber(GWEnergyPilotEntity, NumberEntity):
    """Base class for an EMHASS battery SOC configuration slider."""

    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:battery-cog-outline"

    config_key: str

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._value: float | None = None

    @property
    def native_value(self) -> float | None:
        """Return the current value read from EMHASS config.json."""
        return self._value

    async def async_added_to_hass(self) -> None:
        """Schedule the initial EMHASS read without blocking platform setup."""
        await super().async_added_to_hass()
        self.entry.async_create_background_task(
            self.hass,
            self._async_background_refresh(),
            f"GW EnergyPilot read {self.config_key}",
        )

    async def _async_background_refresh(self) -> None:
        """Refresh the slider when EMHASS is available."""
        try:
            await self._async_refresh_from_emhass()
        except HomeAssistantError as err:
            _LOGGER.debug(
                "Unable to read EMHASS %s during startup: %s",
                self.config_key,
                err,
            )

    async def _async_refresh_from_emhass(self) -> dict:
        config = await async_get_emhass_config(self.hass, self.entry)
        raw = config.get(self.config_key)
        try:
            value = float(raw) * 100.0
        except (TypeError, ValueError):
            self._value = None
        else:
            self._value = min(100.0, max(0.0, value))
        self.async_write_ha_state()
        return config

    async def _async_optimize_after_change(self) -> None:
        """Rebuild the plan after the user has finished changing SOC limits."""
        try:
            await self.entry.runtime_data.orchestrator.async_optimize(
                reason="soc_limits_changed"
            )
        except HomeAssistantError as err:
            _LOGGER.warning("EMHASS optimization after SOC change failed: %s", err)

    def _schedule_debounced_optimization(self) -> None:
        """Run one optimization three seconds after the final SOC change."""
        entry_id = self.entry.entry_id
        if cancel := _SOC_OPTIMIZE_CANCEL.pop(entry_id, None):
            cancel()

        @callback
        def _start_optimize(_now) -> None:
            _SOC_OPTIMIZE_CANCEL.pop(entry_id, None)
            self.entry.async_create_background_task(
                self.hass,
                self._async_optimize_after_change(),
                "GW EnergyPilot optimize after SOC limits settled",
            )

        _SOC_OPTIMIZE_CANCEL[entry_id] = async_call_later(
            self.hass,
            SOC_OPTIMIZE_DEBOUNCE_SECONDS,
            _start_optimize,
        )

    async def async_set_native_value(self, value: float) -> None:
        """Validate, save EMHASS config and debounce re-optimization."""
        value = min(100.0, max(0.0, float(value)))
        config = await async_get_emhass_config(self.hass, self.entry)
        self._validate_against_peer(config, value)
        config[self.config_key] = round(value / 100.0, 4)
        await async_write_emhass_config(self.hass, self.entry, config)
        self._value = value
        self.async_write_ha_state()
        self._schedule_debounced_optimization()

    def _validate_against_peer(self, config: dict, value: float) -> None:
        """Validate min/max ordering in subclasses."""
        raise NotImplementedError


class GWEMHASSMinimumSOCNumber(_GWEMHASSSOCNumber):
    """EMHASS battery_minimum_state_of_charge as a native HA slider."""

    _attr_translation_key = "emhass_minimum_soc"
    config_key = "battery_minimum_state_of_charge"

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_emhass_minimum_soc"

    def _validate_against_peer(self, config: dict, value: float) -> None:
        try:
            maximum = (
                float(config.get("battery_maximum_state_of_charge", 1.0)) * 100.0
            )
        except (TypeError, ValueError):
            maximum = 100.0
        if value > maximum:
            raise HomeAssistantError(
                f"Minimum battery SOC ({value:.0f}%) cannot exceed "
                f"maximum SOC ({maximum:.0f}%)"
            )


class GWEMHASSMaximumSOCNumber(_GWEMHASSSOCNumber):
    """EMHASS battery_maximum_state_of_charge as a native HA slider."""

    _attr_translation_key = "emhass_maximum_soc"
    config_key = "battery_maximum_state_of_charge"

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_emhass_maximum_soc"

    def _validate_against_peer(self, config: dict, value: float) -> None:
        try:
            minimum = (
                float(config.get("battery_minimum_state_of_charge", 0.0)) * 100.0
            )
        except (TypeError, ValueError):
            minimum = 0.0
        if value < minimum:
            raise HomeAssistantError(
                f"Maximum battery SOC ({value:.0f}%) cannot be below "
                f"minimum SOC ({minimum:.0f}%)"
            )
