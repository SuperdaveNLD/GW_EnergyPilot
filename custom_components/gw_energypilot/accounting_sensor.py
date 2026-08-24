"""Home Assistant sensor views for GW EnergyPilot accounting."""

from __future__ import annotations

from typing import Any, Literal

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfEnergy

from . import GWConfigEntry
from .accounting import EXPORT_DAILY_KEY, IMPORT_DAILY_KEY
from .accounting_model import (
    EXTENDED_EXPORT_KEY,
    EXTENDED_IMPORT_KEY,
    LEGACY_EXPORT_KEY,
    LEGACY_IMPORT_KEY,
    SOURCE_EXTENDED,
)
from .entity import GWEnergyPilotEntity


class GWGridDailyEnergySensor(GWEnergyPilotEntity, SensorEntity):
    """Expose one persistent EnergyPilot daily grid-energy counter."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 3

    def __init__(self, entry: GWConfigEntry, direction: Literal["import", "export"]) -> None:
        super().__init__(entry)
        self._direction = direction
        if direction == "import":
            self._attr_name = "Grid energy imported today"
            self._attr_unique_id = f"{entry.entry_id}_{IMPORT_DAILY_KEY}"
        else:
            self._attr_name = "Grid energy exported today"
            self._attr_unique_id = f"{entry.entry_id}_{EXPORT_DAILY_KEY}"

    @property
    def native_value(self) -> float:
        state = self.entry.runtime_data.accounting.state
        if self._direction == "import":
            return state.today_import_kwh
        return state.today_export_kwh

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        state = self.entry.runtime_data.accounting.state
        extended = state.source_pair == SOURCE_EXTENDED
        if self._direction == "import":
            last_period = state.yesterday_import_kwh
            source = EXTENDED_IMPORT_KEY if extended else LEGACY_IMPORT_KEY
        else:
            last_period = state.yesterday_export_kwh
            source = EXTENDED_EXPORT_KEY if extended else LEGACY_EXPORT_KEY
        return {
            "last_period": last_period,
            "accounting_day": state.day,
            "source": source,
            "source_pair": state.source_pair,
            "bootstrap_complete": state.bootstrap_complete,
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.entry.runtime_data.accounting.async_add_listener(
                self.async_write_ha_state
            )
        )
