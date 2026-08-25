"""GW EnergyPilot v0.31 EMHASS policy ownership."""

from __future__ import annotations

import asyncio
from datetime import datetime
import math
from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .battery_saver import (
    MODE_MAD_STEVE,
    apply_battery_saver_profile,
    battery_saver_price_reference,
    clamp_soc_final,
    emhass_supports_battery_stress,
    normalize_battery_saver_mode,
    number_of_batteries,
)
from .const import (
    CONF_BATTERY_SAVER_MODE,
    CONF_P_BATT_ENTITY,
    DEFAULT_P_BATT_ENTITY,
)
from .emhass_config import async_get_emhass_config, async_write_emhass_config
from .orchestrator import OUTPUT_TIMEOUT
from .orchestrator_v026 import GWEnergyPilotOrchestrator as _V026Orchestrator

GOODWE_ON_GRID_MINIMUM_SOC_KEY = "battery_discharge_depth_on_grid"


class GWEnergyPilotOrchestrator(_V026Orchestrator):
    """Own EnergyPilot-required EMHASS policy without duplicating orchestration."""

    def __init__(self, hass, entry, coordinator) -> None:
        super().__init__(hass, entry, coordinator)
        self.last_battery_saver_profile: dict[str, Any] | None = None
        self.last_effective_soc_final: float | None = None
        self._p_batt_reported_before: datetime | None = None

    @property
    def attributes(self) -> dict[str, Any]:
        """Expose the active policy separately from raw EMHASS configuration."""
        attrs = super().attributes
        configured_mode = self.entry.options.get(CONF_BATTERY_SAVER_MODE)
        attrs.update(
            {
                "battery_saver_managed": configured_mode is not None,
                "battery_saver_mode": configured_mode,
                "battery_saver_profile": self.last_battery_saver_profile,
                "effective_runtime_soc_final": self.last_effective_soc_final,
            }
        )
        return attrs

    def _goodwe_minimum_soc(self) -> float | None:
        """Return the verified coordinator value for GoodWe on-grid minimum SOC."""
        snapshot = self.coordinator.data
        if snapshot is None:
            return None
        raw = snapshot.values.get(GOODWE_ON_GRID_MINIMUM_SOC_KEY)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return None
        if not 0 <= value <= 100:
            return None
        return round(value / 100.0, 4)

    def _p_batt_report_timestamp(self) -> datetime | None:
        """Return the timestamp proving that the configured P_batt was reported."""
        entity_id = str(
            self.entry.options.get(CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY)
            or DEFAULT_P_BATT_ENTITY
        )
        state = self.hass.states.get(entity_id)
        if state is None:
            return None
        # Home Assistant updates last_reported for every state report, including
        # reports where state and attributes are unchanged. Older HA State-like
        # test doubles may not expose it, so retain last_updated as a fallback.
        return getattr(state, "last_reported", state.last_updated)

    async def _async_wait_for_fresh_output(
        self,
        before: datetime | None,
    ) -> float | None:
        """Wait for a newly reported finite P_batt while optimization is ready."""
        entity_id = str(
            self.entry.options.get(CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY)
            or DEFAULT_P_BATT_ENTITY
        )
        baseline = self._p_batt_reported_before
        if baseline is None:
            baseline = before

        deadline = self.hass.loop.time() + OUTPUT_TIMEOUT
        while self.hass.loop.time() < deadline:
            state = self.hass.states.get(entity_id)
            if state is not None and self._optimization_ready():
                try:
                    value = float(state.state)
                except (TypeError, ValueError):
                    value = math.nan
                reported = getattr(state, "last_reported", state.last_updated)
                is_fresh = baseline is None or reported > baseline
                if math.isfinite(value) and is_fresh:
                    return value
            await asyncio.sleep(0.5)
        return None

    async def _async_prepare_emhass_policy(self, payload: dict[str, Any]) -> None:
        """Synchronize required config and clamp the runtime terminal SOC.

        EMHASS v0.18.1 accepts minimum/maximum SOC at runtime but the Battery
        Saver penalty fields are configuration parameters. EnergyPilot therefore
        merges those fields through /set-config immediately before its own
        optimization call. EMHASS rebuilds params.pkl on /set-config, so the
        following dayahead action consumes the verified values without an add-on
        restart.
        """
        current = await async_get_emhass_config(self.hass, self.entry)
        updated = dict(current)

        # Core EnergyPilot/EMHASS contract. PV and inverter topology deliberately
        # remain user-owned EMHASS capabilities; battery-only installations and
        # non-hybrid inverter models are valid.
        updated["continual_publish"] = True
        updated["method_ts_round"] = "first"
        updated["set_use_battery"] = True

        battery_count = number_of_batteries(current)
        goodwe_minimum = self._goodwe_minimum_soc()
        if battery_count == 1 and goodwe_minimum is not None:
            maximum = current.get("battery_maximum_state_of_charge", 1.0)
            try:
                maximum_value = float(maximum)
            except (TypeError, ValueError):
                maximum_value = 1.0
            if 0.0 <= maximum_value <= 1.0 and goodwe_minimum > maximum_value:
                raise HomeAssistantError(
                    "GoodWe minimum SOC exceeds the configured EMHASS maximum SOC; "
                    "adjust the maximum SOC before optimizing"
                )
            updated["battery_minimum_state_of_charge"] = goodwe_minimum

        configured_mode = self.entry.options.get(CONF_BATTERY_SAVER_MODE)
        profile: dict[str, Any] | None = None
        if configured_mode is not None:
            if battery_count != 1:
                raise HomeAssistantError(
                    "Battery Saver currently supports one EMHASS battery model. "
                    "The active EMHASS configuration contains multiple batteries."
                )
            try:
                mode = normalize_battery_saver_mode(configured_mode)
            except ValueError as err:
                raise HomeAssistantError(str(err)) from err

            emhass_version = getattr(self, "emhass_version", None)
            if mode != MODE_MAD_STEVE and not emhass_supports_battery_stress(
                emhass_version
            ):
                raise HomeAssistantError(
                    "Gold Rush, Balanced and Battery Saver require EMHASS 0.18.1 "
                    "or newer because they use the battery stress cost model"
                )

            price_reference = battery_saver_price_reference(
                payload.get("load_cost_forecast"),
                current,
            )
            updated, profile = apply_battery_saver_profile(
                updated,
                mode,
                price_reference,
            )

        try:
            effective_soc_final = clamp_soc_final(
                payload.get("soc_final"),
                updated.get("battery_minimum_state_of_charge"),
                updated.get("battery_maximum_state_of_charge"),
            )
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err

        if updated != current:
            await async_write_emhass_config(self.hass, self.entry, updated)

        payload["soc_final"] = effective_soc_final
        # Passing the hard limits as runtime parameters keeps the immediately
        # following solve aligned with the verified policy even if another actor
        # edits config.json between /set-config and /action/dayahead-optim.
        if battery_count == 1:
            if "battery_minimum_state_of_charge" in updated:
                payload["battery_minimum_state_of_charge"] = updated[
                    "battery_minimum_state_of_charge"
                ]
            if "battery_maximum_state_of_charge" in updated:
                payload["battery_maximum_state_of_charge"] = updated[
                    "battery_maximum_state_of_charge"
                ]

        self.last_battery_saver_profile = profile
        self.last_effective_soc_final = effective_soc_final
        async_dispatcher_send(self.hass, self.signal)

    async def _async_post_emhass(
        self,
        endpoint: str,
        payload: dict[str, Any],
        timeout_seconds: int,
    ) -> tuple[int, str]:
        """Prepare EnergyPilot-owned policy immediately before the optimizer call."""
        if endpoint == "/action/dayahead-optim":
            await self._async_prepare_emhass_policy(payload)
        return await super()._async_post_emhass(endpoint, payload, timeout_seconds)

    async def _async_log_optimization(
        self,
        *,
        started_at: datetime,
        started_monotonic: float,
        reason: str,
        requested_soc_final: float,
        current_load: float | None,
        success: bool,
        error: str | None,
    ) -> None:
        """Record the terminal SOC actually submitted after v0.31 clamping."""
        effective_soc_final = (
            self.last_effective_soc_final
            if self.last_effective_soc_final is not None
            else requested_soc_final
        )
        await super()._async_log_optimization(
            started_at=started_at,
            started_monotonic=started_monotonic,
            reason=reason,
            requested_soc_final=effective_soc_final,
            current_load=current_load,
            success=success,
            error=error,
        )

    async def async_optimize(self, reason: str = "manual") -> None:
        """Run the existing orchestration and retain the effective terminal SOC."""
        self.last_effective_soc_final = None
        self._p_batt_reported_before = self._p_batt_report_timestamp()
        try:
            await super().async_optimize(reason=reason)
        finally:
            self._p_batt_reported_before = None
        if self.last_effective_soc_final is not None:
            # v0.13 stores the requested target. Replace the runtime diagnostic
            # with the value actually submitted after hard-limit clamping.
            self.last_runtime_soc_final = self.last_effective_soc_final
            async_dispatcher_send(self.hass, self.signal)
