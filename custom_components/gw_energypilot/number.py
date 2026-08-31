"""Number platform for GW EnergyPilot."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_call_later

from . import GWConfigEntry
from .const import CONF_BATTERY_SAVER_MODE, CONF_MAX_POWER, DEFAULT_MAX_POWER
from .emhass_config import async_get_emhass_config, async_write_emhass_config
from .entity import GWEnergyPilotEntity
from .soc_limits import (
    GOODWE_ON_GRID_MINIMUM_SOC_KEY,
    async_set_goodwe_minimum_soc,
    goodwe_minimum_soc_pct,
)

_LOGGER = logging.getLogger(__name__)
SOC_OPTIMIZE_DEBOUNCE_SECONDS = 3.0
SOC_STARTUP_RETRY_SECONDS = 15
SOC_STARTUP_ATTEMPTS = 4
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
        """Return the current synchronized SOC value."""
        return self._value

    async def async_added_to_hass(self) -> None:
        """Schedule the initial configuration read without blocking platform setup."""
        await super().async_added_to_hass()
        self.entry.async_create_background_task(
            self.hass,
            self._async_background_refresh(),
            f"GW EnergyPilot read {self.config_key}",
        )

    async def _async_background_refresh(self) -> None:
        """Retry startup reads while GoodWe and EMHASS are becoming ready."""
        for attempt in range(SOC_STARTUP_ATTEMPTS):
            try:
                await self._async_refresh_from_emhass()
                return
            except HomeAssistantError as err:
                if attempt == SOC_STARTUP_ATTEMPTS - 1:
                    _LOGGER.debug(
                        "Unable to synchronize %s after %s startup attempts: %s",
                        self.config_key,
                        SOC_STARTUP_ATTEMPTS,
                        err,
                    )
                    return
                await asyncio.sleep(SOC_STARTUP_RETRY_SECONDS)

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
        if self.entry.options.get(CONF_BATTERY_SAVER_MODE) is not None:
            raise HomeAssistantError(
                "Minimum and maximum SOC are managed by the active battery "
                "profile; select Custom before changing an SOC limit"
            )
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
    """Synchronize the optimizer minimum SOC and GoodWe on-grid SOC floor."""

    _attr_translation_key = "emhass_minimum_soc"
    config_key = "battery_minimum_state_of_charge"

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_emhass_minimum_soc"

    def _validate_against_peer(self, config: dict, value: float) -> None:
        try:
            maximum = float(config.get("battery_maximum_state_of_charge", 1.0)) * 100.0
        except (TypeError, ValueError):
            maximum = 100.0
        if value > maximum:
            raise HomeAssistantError(
                f"Minimum battery SOC ({value:.0f}%) cannot exceed maximum SOC ({maximum:.0f}%)"
            )

    def _goodwe_on_grid_floor(self) -> int | None:
        """Return the currently read GoodWe on-grid minimum SOC floor."""
        return goodwe_minimum_soc_pct(self.entry)

    async def _async_set_goodwe_on_grid_floor(self, value: int) -> int:
        """Write and verify the canonical GoodWe on-grid minimum SOC setting."""
        return await async_set_goodwe_minimum_soc(self.entry, value)

    async def _async_refresh_from_emhass(self) -> dict:
        """Use GoodWe as startup source of truth and mirror its floor to EMHASS."""
        config = await async_get_emhass_config(self.hass, self.entry)
        minimum_soc = self._goodwe_on_grid_floor()
        if minimum_soc is None:
            raise HomeAssistantError(
                "GoodWe on-grid minimum SOC is not available yet"
            )
        self._validate_against_peer(config, minimum_soc)
        required = round(minimum_soc / 100.0, 4)
        try:
            current = float(config.get(self.config_key))
        except (TypeError, ValueError):
            current = None
        if current != required:
            config[self.config_key] = required
            await async_write_emhass_config(self.hass, self.entry, config)
        self._value = float(minimum_soc)
        self.async_write_ha_state()
        return config

    async def async_set_native_value(self, value: float) -> None:
        """Synchronize one explicit minimum-SOC change across both systems.

        The GoodWe ETA-G20 enforces register 45356 independently of EMHASS. A
        lower optimizer constraint alone therefore cannot lower the real battery
        floor. Keep both values identical, verify the inverter write first, and
        roll that hardware setting back if the subsequent EMHASS write fails.
        """
        if self.entry.options.get(CONF_BATTERY_SAVER_MODE) is not None:
            raise HomeAssistantError(
                "Minimum and maximum SOC are managed by the active battery "
                "profile; select Custom before changing an SOC limit"
            )
        requested = min(100.0, max(0.0, float(value)))
        if not requested.is_integer():
            raise HomeAssistantError(
                "Minimum battery SOC must be a whole percentage because the "
                "GoodWe on-grid minimum SOC setting accepts whole percent values"
            )
        minimum_soc = int(requested)

        config = await async_get_emhass_config(self.hass, self.entry)
        self._validate_against_peer(config, minimum_soc)

        previous_goodwe = self._goodwe_on_grid_floor()
        if previous_goodwe is None:
            raise HomeAssistantError(
                "GoodWe on-grid minimum SOC is currently unavailable; no SOC "
                "setting was changed"
            )

        goodwe_changed = previous_goodwe != minimum_soc
        if goodwe_changed:
            await self._async_set_goodwe_on_grid_floor(minimum_soc)

        config[self.config_key] = round(minimum_soc / 100.0, 4)
        try:
            await async_write_emhass_config(self.hass, self.entry, config)
        except HomeAssistantError as err:
            if goodwe_changed:
                try:
                    await self._async_set_goodwe_on_grid_floor(previous_goodwe)
                except HomeAssistantError as rollback_err:
                    raise HomeAssistantError(
                        f"EMHASS minimum SOC update failed ({err}); GoodWe rollback "
                        f"to {previous_goodwe}% also failed ({rollback_err})"
                    ) from err
            raise

        self._value = float(minimum_soc)
        self.async_write_ha_state()
        self._schedule_debounced_optimization()


class GWEMHASSMaximumSOCNumber(_GWEMHASSSOCNumber):
    """EMHASS battery_maximum_state_of_charge as a native HA slider."""

    _attr_translation_key = "emhass_maximum_soc"
    config_key = "battery_maximum_state_of_charge"

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_emhass_maximum_soc"

    def _validate_against_peer(self, config: dict, value: float) -> None:
        try:
            minimum = float(config.get("battery_minimum_state_of_charge", 0.0)) * 100.0
        except (TypeError, ValueError):
            minimum = 0.0
        if value < minimum:
            raise HomeAssistantError(
                f"Maximum battery SOC ({value:.0f}%) cannot be below minimum SOC ({minimum:.0f}%)"
            )
