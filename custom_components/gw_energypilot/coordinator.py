"""Data update coordinator for GW EnergyPilot."""

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import GWETAData, GWModbusClient, GWModbusError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class GWEnergyPilotCoordinator(DataUpdateCoordinator[GWETAData]):
    """Coordinate polling of GoodWe ETA runtime telemetry."""

    def __init__(self, hass: HomeAssistant, client: GWModbusClient, scan_interval: int) -> None:
        self.client = client
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> GWETAData:
        try:
            return await self.client.async_read_data()
        except GWModbusError as err:
            raise UpdateFailed(str(err)) from err
