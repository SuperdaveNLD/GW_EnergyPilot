"""Data update coordinator for GW EnergyPilot."""

from datetime import timedelta
import logging
from typing import Protocol

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import GWETAData, GWModbusClient, GWModbusError
from .const import DOMAIN
from .sems_api import GWSemsError

_LOGGER = logging.getLogger(__name__)


class _TelemetryClient(Protocol):
    """Runtime telemetry client contract."""

    async def async_read_data(self) -> GWETAData:
        """Return one telemetry snapshot."""


class GWEnergyPilotCoordinator(DataUpdateCoordinator[GWETAData]):
    """Coordinate polling of GoodWe ETA runtime telemetry."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: _TelemetryClient,
        scan_interval: int,
        *,
        source: str = "modbus",
        control_client: GWModbusClient | None = None,
    ) -> None:
        self.client = client
        self.source = source
        self.control_client = control_client or (
            client if isinstance(client, GWModbusClient) else None
        )
        self.last_control_update_success: bool | None = None
        self.last_control_exception: Exception | None = None
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> GWETAData:
        try:
            snapshot = await self.client.async_read_data()
        except (GWModbusError, GWSemsError) as err:
            raise UpdateFailed(str(err)) from err

        if self.source == "modbus":
            self.last_control_update_success = True
            self.last_control_exception = None
            return snapshot

        # SEMS is telemetry-only. Keep the local EMS mode/setpoint readback
        # independent: its failure must not discard a valid cloud snapshot, but
        # it remains visible to connectivity and blocks verified control status.
        if self.control_client is None:
            self.last_control_update_success = False
            self.last_control_exception = GWModbusError(
                "Local Modbus control client is unavailable"
            )
            return snapshot
        try:
            control = await self.control_client.async_read_control_status()
        except GWModbusError as err:
            self.last_control_update_success = False
            self.last_control_exception = err
            return snapshot
        self.last_control_update_success = True
        self.last_control_exception = None
        return self._merged_control_snapshot(snapshot, control)

    @staticmethod
    def _merged_control_snapshot(
        telemetry: GWETAData,
        control: GWETAData,
    ) -> GWETAData:
        values = dict(telemetry.values)
        values.update(control.values)
        return GWETAData(
            values=values,
            source=telemetry.source,
            source_updated_at=telemetry.source_updated_at,
        )

    def async_publish_local_readback(self, control: GWETAData) -> None:
        """Merge local read-back without changing cloud refresh health.

        ``async_set_updated_data`` also marks the coordinator update as
        successful.  That would let a local EMS/SOC read-back make failed SEMS
        telemetry look fresh, so control-only changes notify listeners while
        preserving the telemetry coordinator's success/error state.
        """
        if self.data is None:
            return
        self.data = self._merged_control_snapshot(self.data, control)
        self.async_update_listeners()

    async def async_refresh_control_readback(self) -> None:
        """Refresh EMS readback without forcing an extra SEMS API request."""
        if self.source == "modbus":
            await self.async_request_refresh()
            return
        if self.control_client is None:
            raise GWModbusError("Local Modbus control client is unavailable")
        try:
            control = await self.control_client.async_read_control_status()
        except GWModbusError as err:
            self.last_control_update_success = False
            self.last_control_exception = err
            raise
        self.last_control_update_success = True
        self.last_control_exception = None
        if self.data is None:
            return
        self.async_publish_local_readback(control)
