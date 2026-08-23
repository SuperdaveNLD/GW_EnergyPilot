"""Number platform for GW EnergyPilot."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GWConfigEntry
from .const import CONF_MAX_POWER, DEFAULT_MAX_POWER
from .emhass_config import async_get_emhass_config, async_write_emhass_config
from .entity import GWEnergyPilotEntity


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
        """Read the current EMHASS value when the entity is added."""
        await super().async_added_to_hass()
        try:
            await self._async_refresh_from_emhass()
        except HomeAssistantError:
            # EMHASS may still be starting. The entity remains available with an
            # unknown value and will be updated when the user changes it or the
            # integration is reloaded.
            return

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

    async def async_set_native_value(self, value: float) -> None:
        """Validate, save the full EMHASS config and update this slider."""
        value = min(100.0, max(0.0, float(value)))
        config = await async_get_emhass_config(self.hass, self.entry)
        self._validate_against_peer(config, value)
        config[self.config_key] = round(value / 100.0, 4)
        await async_write_emhass_config(self.hass, self.entry, config)
        self._value = value
        self.async_write_ha_state()

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
            maximum = float(config.get("battery_maximum_state_of_charge", 1.0)) * 100.0
        except (TypeError, ValueError):
            maximum = 100.0
        if value > maximum:
            raise HomeAssistantError(
                f"Minimum battery SOC ({value:.0f}%) cannot exceed maximum SOC ({maximum:.0f}%)"
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
            minimum = float(config.get("battery_minimum_state_of_charge", 0.0)) * 100.0
        except (TypeError, ValueError):
            minimum = 0.0
        if value < minimum:
            raise HomeAssistantError(
                f"Maximum battery SOC ({value:.0f}%) cannot be below minimum SOC ({minimum:.0f}%)"
            )
