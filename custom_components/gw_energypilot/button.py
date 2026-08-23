"""Button entities for GW EnergyPilot."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GWConfigEntry
from .const import (
    CONF_DEADBAND,
    CONF_MAX_POWER,
    CONF_OPTIM_STATUS_ENTITY,
    CONF_P_BATT_ENTITY,
    DEFAULT_DEADBAND,
    DEFAULT_MAX_POWER,
    DEFAULT_OPTIM_STATUS_ENTITY,
    DEFAULT_P_BATT_ENTITY,
    MODE_BATTERY_HOLD,
    MODE_CHARGE_BATTERY,
    MODE_GRID_EXPORT_TARGET,
    MODE_NAMES,
)
from .emhass_config import async_patch_emhass_config
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
            GWEMHASSProfitButton(entry),
            GWEMHASSCostButton(entry),
            GWEMHASSSelfConsumptionButton(entry),
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
        """Subscribe to orchestrator and controller status updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self.entry.runtime_data.orchestrator.signal,
                self._async_runtime_updated,
            )
        )
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                self.entry.runtime_data.controller.signal,
                self._async_runtime_updated,
            )
        )

    @callback
    def _async_runtime_updated(self) -> None:
        self.async_write_ha_state()

    @staticmethod
    def _safe_number(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose optimizer state plus a compact troubleshooting snapshot."""
        orchestrator = self.entry.runtime_data.orchestrator
        controller = self.entry.runtime_data.controller
        coordinator = self.entry.runtime_data.coordinator
        values = coordinator.data.values if coordinator.data else {}

        p_batt_entity = str(
            self.entry.options.get(CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY)
            or DEFAULT_P_BATT_ENTITY
        )
        optim_entity = str(
            self.entry.options.get(
                CONF_OPTIM_STATUS_ENTITY,
                DEFAULT_OPTIM_STATUS_ENTITY,
            )
            or DEFAULT_OPTIM_STATUS_ENTITY
        )
        p_batt_state = self.hass.states.get(p_batt_entity)
        optim_state = self.hass.states.get(optim_entity)

        load_phases = [
            self._safe_number(values.get("load_l1_power")),
            self._safe_number(values.get("load_l2_power")),
            self._safe_number(values.get("load_l3_power")),
        ]
        load_phase_sum = (
            sum(value for value in load_phases if value is not None)
            if all(value is not None for value in load_phases)
            else None
        )

        pv = self._safe_number(values.get("pv_total_power"))
        grid = self._safe_number(values.get("meter_total_power_fast"))
        battery = self._safe_number(values.get("battery_power"))
        system_balance = (
            pv - grid + battery
            if pv is not None and grid is not None and battery is not None
            else None
        )

        mode = coordinator.data.mode if coordinator.data else None
        return {
            "orchestrator_status": orchestrator.status,
            **orchestrator.attributes,
            "controller_enabled": controller.enabled,
            "controller_command": controller.last_command,
            "controller_target_power": controller.target_power,
            "controller_expected_mode": controller.expected_mode,
            "controller_max_power": int(
                self.entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER)
            ),
            "controller_deadband": float(
                self.entry.options.get(CONF_DEADBAND, DEFAULT_DEADBAND)
            ),
            "p_batt_entity": p_batt_entity,
            "p_batt_value": p_batt_state.state if p_batt_state else None,
            "optim_status_entity": optim_entity,
            "optim_status_value": optim_state.state if optim_state else None,
            "ems_mode": mode,
            "ems_mode_name": MODE_NAMES.get(mode, "Unknown"),
            "ems_setpoint": coordinator.data.power if coordinator.data else None,
            "app_work_mode_47000": values.get("app_work_mode"),
            "battery_discharge_depth_on_grid_45356": values.get(
                "battery_discharge_depth_on_grid"
            ),
            "battery_discharge_depth_off_grid_45358": values.get(
                "battery_discharge_depth_off_grid"
            ),
            "battery_soc_protection_47500": values.get("battery_soc_protection"),
            "work_mode_35187": values.get("work_mode"),
            "operation_mode_35188": values.get("operation_mode"),
            "grid_mode_35136": values.get("grid_mode"),
            "house_load_register_35172": values.get("total_load_power"),
            "house_load_phase_sum": load_phase_sum,
            # Kept for backwards-compatible frontend/diagnostic consumers.
            "house_load_power_balance": (
                round(system_balance, 0) if system_balance is not None else None
            ),
            "system_balance_power": (
                round(system_balance, 0) if system_balance is not None else None
            ),
            "pv_total_power": values.get("pv_total_power"),
            "battery_power": values.get("battery_power"),
            "battery_soc": values.get("battery_soc"),
            "battery_soh": values.get("battery_soh"),
            "battery_charge_energy_total": values.get("battery_charge_energy_total"),
            "battery_charge_energy_today": values.get("battery_charge_energy_today"),
            "battery_discharge_energy_total": values.get("battery_discharge_energy_total"),
            "battery_discharge_energy_today": values.get("battery_discharge_energy_today"),
            "meter_total_power_fast": values.get("meter_total_power_fast"),
            "meter_total_energy_import": values.get("meter_total_energy_import"),
            "meter_total_energy_export": values.get("meter_total_energy_export"),
            "meter_total_energy_import_extended_candidate": values.get(
                "meter_total_energy_import_extended"
            ),
            "meter_total_energy_export_extended_candidate": values.get(
                "meter_total_energy_export_extended"
            ),
            "total_inverter_power": values.get("total_inverter_power"),
            "ac_active_power": values.get("ac_active_power"),
        }

    async def async_press(self) -> None:
        """Start a manual optimization."""
        await self.entry.runtime_data.orchestrator.async_optimize(reason="manual_button")


class _GWEMHASSCostFunctionButton(GWEnergyPilotEntity, ButtonEntity):
    """Base class for one-touch EMHASS cost-function selection."""

    cost_function: str

    def __init__(self, entry: GWConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_{self.entity_description_key}"

    @property
    def entity_description_key(self) -> str:
        """Return stable key used for the entity unique ID."""
        raise NotImplementedError

    async def async_press(self) -> None:
        """Persist the selected EMHASS objective and create a fresh plan."""
        await async_patch_emhass_config(
            self.hass,
            self.entry,
            {"costfun": self.cost_function},
        )
        await self.entry.runtime_data.orchestrator.async_optimize(
            reason=f"cost_function_{self.cost_function}"
        )


class GWEMHASSProfitButton(_GWEMHASSCostFunctionButton):
    """Select EMHASS profit optimization."""

    _attr_translation_key = "emhass_costfun_profit"
    _attr_icon = "mdi:cash-plus"
    cost_function = "profit"

    @property
    def entity_description_key(self) -> str:
        return "emhass_costfun_profit"


class GWEMHASSCostButton(_GWEMHASSCostFunctionButton):
    """Select EMHASS cost minimization."""

    _attr_translation_key = "emhass_costfun_cost"
    _attr_icon = "mdi:cash-minus"
    cost_function = "cost"

    @property
    def entity_description_key(self) -> str:
        return "emhass_costfun_cost"


class GWEMHASSSelfConsumptionButton(_GWEMHASSCostFunctionButton):
    """Select EMHASS self-consumption optimization."""

    _attr_translation_key = "emhass_costfun_self_consumption"
    _attr_icon = "mdi:home-battery"
    cost_function = "self-consumption"

    @property
    def entity_description_key(self) -> str:
        return "emhass_costfun_self_consumption"


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
        """Optimize first, then enable Automatic Control only on success."""
        await self.entry.runtime_data.orchestrator.async_optimize(reason="resume_auto")
        await self.entry.runtime_data.controller.async_enable()
