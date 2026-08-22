"""Config flow for GW EnergyPilot."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult, OptionsFlowWithReload
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers import selector

from .client import GWModbusClient, GWModbusError
from .const import (
    CONF_DEADBAND,
    CONF_ENABLE_EV_COORDINATION,
    CONF_EV_DEADBAND,
    CONF_EV_MODE_ENTITY,
    CONF_EV_POWER_ENTITY,
    CONF_MAX_POWER,
    CONF_OPTIM_REQUIRED_STATE,
    CONF_OPTIM_STATUS_ENTITY,
    CONF_P_BATT_ENTITY,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE,
    DEFAULT_DEADBAND,
    DEFAULT_EV_DEADBAND,
    DEFAULT_MAX_POWER,
    DEFAULT_OPTIM_REQUIRED_STATE,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE,
    DOMAIN,
    NAME,
)


class CannotConnect(Exception):
    """Raised when the inverter cannot be reached."""


async def _async_validate_connection(host: str, port: int, slave: int) -> None:
    """Validate the Modbus TCP connection and EMS registers."""
    client = GWModbusClient(host, port, slave)
    try:
        await client.async_connect()
        await client.async_read_status()
    except GWModbusError as err:
        raise CannotConnect from err
    finally:
        await client.async_close()


def _controller_schema() -> vol.Schema:
    """Return controller options schema."""
    return vol.Schema(
        {
            vol.Optional(CONF_P_BATT_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(multiple=False)
            ),
            vol.Optional(CONF_OPTIM_STATUS_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(multiple=False)
            ),
            vol.Optional(
                CONF_OPTIM_REQUIRED_STATE,
                default=DEFAULT_OPTIM_REQUIRED_STATE,
            ): selector.TextSelector(),
            vol.Required(CONF_MAX_POWER, default=DEFAULT_MAX_POWER): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=500,
                    max=15000,
                    step=100,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="W",
                )
            ),
            vol.Required(CONF_DEADBAND, default=DEFAULT_DEADBAND): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=2000,
                    step=50,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="W",
                )
            ),
            vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5,
                    max=60,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Required(CONF_ENABLE_EV_COORDINATION, default=False): selector.BooleanSelector(),
            vol.Optional(CONF_EV_MODE_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(multiple=False)
            ),
            vol.Optional(CONF_EV_POWER_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(multiple=False)
            ),
            vol.Required(CONF_EV_DEADBAND, default=DEFAULT_EV_DEADBAND): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=3000,
                    step=50,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="W",
                )
            ),
        }
    )


class GWEnergyPilotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GW EnergyPilot."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._connection_data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure Modbus connection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(user_input[CONF_HOST])
            port = int(user_input[CONF_PORT])
            slave = int(user_input[CONF_SLAVE])
            try:
                await _async_validate_connection(host, port, slave)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{host}:{slave}")
                self._abort_if_unique_id_configured()
                self._connection_data = {
                    CONF_HOST: host,
                    CONF_PORT: port,
                    CONF_SLAVE: slave,
                }
                return await self.async_step_controller()

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): selector.TextSelector(),
                vol.Required(CONF_PORT, default=DEFAULT_PORT): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=65535, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Required(CONF_SLAVE, default=DEFAULT_SLAVE): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=247, mode=selector.NumberSelectorMode.BOX)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_controller(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure optional controller inputs."""
        if user_input is not None:
            host = self._connection_data[CONF_HOST]
            return self.async_create_entry(
                title=f"{NAME} ({host})",
                data=self._connection_data,
                options=user_input,
            )

        return self.async_show_form(step_id="controller", data_schema=_controller_schema())

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> "GWOptionsFlow":
        """Return options flow."""
        return GWOptionsFlow()


class GWOptionsFlow(OptionsFlowWithReload):
    """Manage GW EnergyPilot options."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema = self.add_suggested_values_to_schema(
            _controller_schema(),
            self.config_entry.options,
        )
        return self.async_show_form(step_id="init", data_schema=schema)
