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
    CONF_BATTERY_SAVER_MODE,
    CONF_BUY_PRICE_ADDER,
    CONF_DEADBAND,
    CONF_EMHASS_FALLBACK_LOAD,
    CONF_EMHASS_OPTIMIZATION_INTERVAL,
    CONF_EMHASS_SOC_FINAL,
    CONF_EMHASS_URL,
    CONF_ENABLE_EMHASS_ORCHESTRATOR,
    CONF_ENABLE_EV_COORDINATION,
    CONF_EV_DEADBAND,
    CONF_EV_MODE_ENTITY,
    CONF_EV_POWER_ENTITY,
    CONF_MAX_POWER,
    CONF_NORDPOOL_AREA,
    CONF_NORDPOOL_CURRENCY,
    CONF_OPTIMIZE_ON_TOMORROW_PRICES,
    CONF_OPTIM_REQUIRED_STATE,
    CONF_OPTIM_STATUS_ENTITY,
    CONF_P_BATT_ENTITY,
    CONF_P_GRID_ENTITY,
    CONF_SCAN_INTERVAL,
    CONF_SELL_PRICE_DEDUCTION,
    CONF_SLAVE,
    CONF_USE_NORDPOOL_PRICES,
    DEFAULT_BUY_PRICE_ADDER,
    DEFAULT_DEADBAND,
    DEFAULT_EMHASS_FALLBACK_LOAD,
    DEFAULT_EMHASS_OPTIMIZATION_INTERVAL,
    DEFAULT_EMHASS_SOC_FINAL,
    DEFAULT_EMHASS_URL,
    DEFAULT_EV_DEADBAND,
    DEFAULT_MAX_POWER,
    DEFAULT_NORDPOOL_AREA,
    DEFAULT_NORDPOOL_CURRENCY,
    DEFAULT_OPTIMIZE_ON_TOMORROW_PRICES,
    DEFAULT_OPTIM_REQUIRED_STATE,
    DEFAULT_OPTIM_STATUS_ENTITY,
    DEFAULT_P_BATT_ENTITY,
    DEFAULT_P_GRID_ENTITY,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SELL_PRICE_DEDUCTION,
    DEFAULT_SLAVE,
    DEFAULT_USE_NORDPOOL_PRICES,
    DOMAIN,
    NAME,
)

CONF_MAX_POWER_KW = "max_power_kw"
CONF_EMHASS_SOC_FINAL_PCT = "emhass_soc_final_pct"


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


def _controller_schema(*, orchestrator_default: bool = True) -> vol.Schema:
    """Return controller and native orchestrator options schema."""
    return vol.Schema(
        {
            # These output entities are often created only after the first
            # successful EMHASS publish. Text fields allow the standard IDs to
            # be configured before they exist in Home Assistant.
            vol.Optional(
                CONF_P_BATT_ENTITY,
                default=DEFAULT_P_BATT_ENTITY,
            ): selector.TextSelector(),
            vol.Optional(
                CONF_P_GRID_ENTITY,
                default=DEFAULT_P_GRID_ENTITY,
            ): selector.TextSelector(),
            vol.Optional(
                CONF_OPTIM_STATUS_ENTITY,
                default=DEFAULT_OPTIM_STATUS_ENTITY,
            ): selector.TextSelector(),
            vol.Optional(
                CONF_OPTIM_REQUIRED_STATE,
                default=DEFAULT_OPTIM_REQUIRED_STATE,
            ): selector.TextSelector(),
            vol.Required(
                CONF_MAX_POWER_KW,
                default=DEFAULT_MAX_POWER / 1000,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.5,
                    max=15,
                    step=0.1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="kW",
                )
            ),
            vol.Required(
                CONF_DEADBAND,
                default=DEFAULT_DEADBAND,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=2000,
                    step=50,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="W",
                )
            ),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=DEFAULT_SCAN_INTERVAL,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5,
                    max=60,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Required(
                CONF_ENABLE_EMHASS_ORCHESTRATOR,
                default=orchestrator_default,
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_EMHASS_URL,
                default=DEFAULT_EMHASS_URL,
            ): selector.TextSelector(),
            vol.Required(
                CONF_EMHASS_OPTIMIZATION_INTERVAL,
                default=DEFAULT_EMHASS_OPTIMIZATION_INTERVAL,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5,
                    max=60,
                    step=5,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="min",
                )
            ),
            vol.Required(
                CONF_EMHASS_SOC_FINAL_PCT,
                default=DEFAULT_EMHASS_SOC_FINAL * 100,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="%",
                )
            ),
            vol.Required(
                CONF_EMHASS_FALLBACK_LOAD,
                default=DEFAULT_EMHASS_FALLBACK_LOAD,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=100,
                    max=20000,
                    step=50,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="W",
                )
            ),
            vol.Required(
                CONF_USE_NORDPOOL_PRICES,
                default=DEFAULT_USE_NORDPOOL_PRICES,
            ): selector.BooleanSelector(),
            vol.Required(
                CONF_OPTIMIZE_ON_TOMORROW_PRICES,
                default=DEFAULT_OPTIMIZE_ON_TOMORROW_PRICES,
            ): selector.BooleanSelector(),
            vol.Optional(
                CONF_NORDPOOL_AREA,
                default=DEFAULT_NORDPOOL_AREA,
            ): selector.TextSelector(),
            vol.Optional(
                CONF_NORDPOOL_CURRENCY,
                default=DEFAULT_NORDPOOL_CURRENCY,
            ): selector.TextSelector(),
            vol.Required(
                CONF_BUY_PRICE_ADDER,
                default=DEFAULT_BUY_PRICE_ADDER,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-1,
                    max=2,
                    step=0.0001,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="EUR/kWh",
                )
            ),
            vol.Required(
                CONF_SELL_PRICE_DEDUCTION,
                default=DEFAULT_SELL_PRICE_DEDUCTION,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-1,
                    max=2,
                    step=0.0001,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="EUR/kWh",
                )
            ),
            vol.Required(
                CONF_ENABLE_EV_COORDINATION,
                default=False,
            ): selector.BooleanSelector(),
            vol.Optional(CONF_EV_MODE_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(multiple=False)
            ),
            vol.Optional(CONF_EV_POWER_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(multiple=False)
            ),
            vol.Required(
                CONF_EV_DEADBAND,
                default=DEFAULT_EV_DEADBAND,
            ): selector.NumberSelector(
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


def _options_from_form(user_input: dict[str, Any]) -> dict[str, Any]:
    """Convert user-facing values to runtime/storage values."""
    options = dict(user_input)
    max_power_kw = float(options.pop(CONF_MAX_POWER_KW))
    options[CONF_MAX_POWER] = int(round(max_power_kw * 1000))
    soc_final_pct = float(options.pop(CONF_EMHASS_SOC_FINAL_PCT))
    options[CONF_EMHASS_SOC_FINAL] = min(
        1.0,
        max(0.0, soc_final_pct / 100.0),
    )
    return options


def _options_for_form(options: dict[str, Any]) -> dict[str, Any]:
    """Convert stored runtime values to user-facing values."""
    form_options = dict(options)
    form_options.setdefault(CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY)
    form_options.setdefault(CONF_P_GRID_ENTITY, DEFAULT_P_GRID_ENTITY)
    form_options.setdefault(CONF_OPTIM_STATUS_ENTITY, DEFAULT_OPTIM_STATUS_ENTITY)
    form_options.setdefault(CONF_OPTIM_REQUIRED_STATE, DEFAULT_OPTIM_REQUIRED_STATE)
    form_options.setdefault(CONF_ENABLE_EMHASS_ORCHESTRATOR, True)
    form_options.setdefault(CONF_EMHASS_URL, DEFAULT_EMHASS_URL)
    form_options.setdefault(
        CONF_EMHASS_OPTIMIZATION_INTERVAL,
        DEFAULT_EMHASS_OPTIMIZATION_INTERVAL,
    )
    form_options.setdefault(
        CONF_EMHASS_FALLBACK_LOAD,
        DEFAULT_EMHASS_FALLBACK_LOAD,
    )
    form_options.setdefault(CONF_USE_NORDPOOL_PRICES, DEFAULT_USE_NORDPOOL_PRICES)
    form_options.setdefault(
        CONF_OPTIMIZE_ON_TOMORROW_PRICES,
        DEFAULT_OPTIMIZE_ON_TOMORROW_PRICES,
    )
    form_options.setdefault(CONF_NORDPOOL_AREA, DEFAULT_NORDPOOL_AREA)
    form_options.setdefault(CONF_NORDPOOL_CURRENCY, DEFAULT_NORDPOOL_CURRENCY)
    form_options.setdefault(CONF_BUY_PRICE_ADDER, DEFAULT_BUY_PRICE_ADDER)
    form_options.setdefault(CONF_SELL_PRICE_DEDUCTION, DEFAULT_SELL_PRICE_DEDUCTION)

    max_power_w = float(form_options.pop(CONF_MAX_POWER, DEFAULT_MAX_POWER))
    form_options[CONF_MAX_POWER_KW] = max_power_w / 1000
    soc_final = float(
        form_options.pop(CONF_EMHASS_SOC_FINAL, DEFAULT_EMHASS_SOC_FINAL)
    )
    form_options[CONF_EMHASS_SOC_FINAL_PCT] = soc_final * 100
    return form_options


class GWEnergyPilotConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow for GW EnergyPilot."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._connection_data: dict[str, Any] = {}

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure Modbus connection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
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
                vol.Required(
                    CONF_PORT,
                    default=DEFAULT_PORT,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=65535,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_SLAVE,
                    default=DEFAULT_SLAVE,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=247,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_controller(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Configure controller and native EMHASS orchestration."""
        if user_input is not None:
            host = self._connection_data[CONF_HOST]
            return self.async_create_entry(
                title=f"{NAME} ({host})",
                data=self._connection_data,
                options=_options_from_form(user_input),
            )

        return self.async_show_form(
            step_id="controller",
            data_schema=_controller_schema(orchestrator_default=True),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> "GWOptionsFlow":
        """Return options flow."""
        return GWOptionsFlow()


class GWOptionsFlow(OptionsFlowWithReload):
    """Manage GW EnergyPilot options."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            stored_options = _options_from_form(user_input)
            # Battery Saver is intentionally managed from the EnergyPilot
            # dashboard EMHASS tab. Preserve that option when the standard Home
            # Assistant options flow updates unrelated controller settings.
            if CONF_BATTERY_SAVER_MODE in self.config_entry.options:
                stored_options[CONF_BATTERY_SAVER_MODE] = self.config_entry.options[
                    CONF_BATTERY_SAVER_MODE
                ]
            return self.async_create_entry(data=stored_options)

        schema = self.add_suggested_values_to_schema(
            _controller_schema(
                orchestrator_default=bool(
                    self.config_entry.options.get(
                        CONF_ENABLE_EMHASS_ORCHESTRATOR,
                        True,
                    )
                )
            ),
            _options_for_form(dict(self.config_entry.options)),
        )
        return self.async_show_form(step_id="init", data_schema=schema)
