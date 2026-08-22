"""Config flow for GW EnergyPilot."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers import selector

from .client import GWModbusClient, GWModbusError
from .const import CONF_SCAN_INTERVAL, CONF_SLAVE, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DEFAULT_SLAVE, DOMAIN, NAME


class CannotConnect(Exception):
    """Raised when the inverter cannot be reached."""


async def _async_validate_connection(host: str, port: int, slave: int) -> None:
    """Validate connection and required EMS registers."""
    client = GWModbusClient(host, port, slave)
    try:
        await client.async_connect()
        await client.async_read_status()
    except GWModbusError as err:
        raise CannotConnect from err
    finally:
        await client.async_close()


class GWEnergyPilotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for GW EnergyPilot."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Configure the GoodWe Modbus connection."""
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
                return self.async_create_entry(
                    title=f"{NAME} ({host})",
                    data={CONF_HOST: host, CONF_PORT: port, CONF_SLAVE: slave},
                    options={CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL},
                )

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
