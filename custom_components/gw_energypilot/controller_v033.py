"""GW EnergyPilot v0.33 plan-resilient Automatic Control."""

from __future__ import annotations

from contextlib import suppress
from datetime import datetime, timedelta, timezone
from time import monotonic

from homeassistant.core import callback

from .control_decision import preview_hybrid_mapping, resolve_control_decision
from .const import (
    CONF_DEADBAND,
    CONF_ENABLE_EMHASS_ORCHESTRATOR,
    CONF_EV_MODE_ENTITY,
    CONF_EV_POWER_ENTITY,
    CONF_GOODWE_AUTO_DEADBAND,
    CONF_MAX_POWER,
    CONF_OPTIM_STATUS_ENTITY,
    CONTROL_STRATEGY_GRID,
    CONTROL_STRATEGY_HYBRID,
    CONTROL_STRATEGY_HYBRID_2,
    DEFAULT_DEADBAND,
    DEFAULT_GOODWE_AUTO_DEADBAND,
    DEFAULT_MAX_POWER,
    EV_DETECTION_METHOD_STATE,
    MODE_BATTERY_HOLD,
)
from .controller import GWEnergyPilotController as _BaseController
from .ev_detection import (
    EV_POWER_MAX_AGE_SECONDS,
    EV_SELF_CONSUMPTION_INTERVAL_SECONDS,
    detection_method,
    fresh_power_value_w,
)

_MISSING_STATES = {"unknown", "unavailable", "none", ""}


class GWEnergyPilotController(_BaseController):
    """Keep Automatic Control usable while EMHASS HA entities are rebuilding."""

    async def async_setup(self) -> None:
        from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

        await super().async_setup()
        self._ev_reference_task = None
        self._ev_reference_unloading = False
        # A live strategy selection need not reload the entry. Observe the
        # optional measured source now, but act on it only in Hybrid 2.0.
        power_entity = self.entry.options.get(CONF_EV_POWER_ENTITY)
        if power_entity and power_entity not in self.ev_source_ids:
            self._unsubs.append(async_track_state_change_event(
                self.hass, [power_entity], self._async_ev_power_reference_changed,
            ))
        self._unsubs.append(async_track_time_interval(
            self.hass, self._async_ev_reference_tick,
            timedelta(seconds=EV_SELF_CONSUMPTION_INTERVAL_SECONDS),
        ))

    @callback
    def _async_ev_power_reference_changed(self, event) -> None:
        if self.control_strategy == CONTROL_STRATEGY_HYBRID_2:
            self._async_source_changed(event)

    async def async_unload(self) -> None:
        self._ev_reference_unloading = True
        await super().async_unload()
        pending = getattr(self, "_ev_reference_task", None)
        if pending is not None:
            # Let an in-flight mode/setpoint transaction finish atomically.
            with suppress(Exception):
                await pending

    @property
    def ev_source_ids(self) -> set[str]:
        sources = super().ev_source_ids
        if self.control_strategy == CONTROL_STRATEGY_HYBRID_2:
            power_entity = self.entry.options.get(CONF_EV_POWER_ENTITY)
            if power_entity:
                sources.add(power_entity)
        return sources

    def _ev_reference_power(self) -> float | None:
        return fresh_power_value_w(self.hass.states, self.entry.options.get(CONF_EV_POWER_ENTITY))

    def ev_is_active(self) -> bool:
        active = super().ev_is_active()
        if (active or self.control_strategy != CONTROL_STRATEGY_HYBRID_2
                or not self._ev_coordination_effective() or not self._ev_was_active):
            return active
        # An unavailable reading is not a confirmed EV stop. Keep the guard
        # until the selected activity source can actually report a stop.
        if detection_method(self.entry.options) == EV_DETECTION_METHOD_STATE:
            entity_id = self.entry.options.get(CONF_EV_MODE_ENTITY)
            state = self.hass.states.get(entity_id) if entity_id else None
            return state is None or str(state.state).lower() in _MISSING_STATES
        return self._ev_reference_power() is None

    @callback
    def _async_ev_reference_tick(self, _now) -> None:
        if (getattr(self, "_ev_reference_unloading", False) or not self.enabled
                or self.control_strategy != CONTROL_STRATEGY_HYBRID_2
                or not self.ev_is_active()):
            return
        pending = getattr(self, "_ev_reference_task", None)
        if pending is not None and not pending.done():
            return
        self._ev_reference_task = self.hass.async_create_task(
            self.async_evaluate(allow_suspended=True), "gw-energypilot-ev-reference",
        )

    @callback
    def _async_source_changed(self, event) -> None:
        native_ev_stop = (
            self.enabled and self.control_strategy == CONTROL_STRATEGY_HYBRID_2
            and event.data.get("entity_id") in self.ev_source_ids
            and self._ev_was_active and not self.ev_is_active()
            and self.entry.options.get(CONF_ENABLE_EMHASS_ORCHESTRATOR, False)
        )
        super()._async_source_changed(event)
        if native_ev_stop:
            self.hass.async_create_task(self._async_hold_after_ev_stop(), "gw-energypilot-ev-stop-hold")

    async def _async_hold_after_ev_stop(self) -> None:
        async with self._control_lock:
            if (self.enabled and self.control_strategy == CONTROL_STRATEGY_HYBRID_2
                    and not self.ev_is_active()
                    and self.last_command == "waiting_for_ev_stop_optimization"):
                await self._async_apply_command(
                    MODE_BATTERY_HOLD, 0, "waiting_for_ev_stop_optimization",
                    skip_if_readback_matches=True,
                )

    async def _async_evaluate_locked(self) -> None:
        if (self.enabled and self.control_strategy == CONTROL_STRATEGY_HYBRID_2
                and self.ev_is_active()):
            self._ev_was_active = True
            if (self._plan_update_suspensions or not self._optim_is_ready()
                    or self._state_float(self._p_batt_entity_id()) is None
                    or self._state_float(self._p_grid_entity_id()) is None):
                await self._async_apply_command(
                    MODE_BATTERY_HOLD, 0, "ev_self_consumption_hold",
                    skip_if_readback_matches=True,
                )
                return
        await super()._async_evaluate_locked()

    def _actual_snapshot(self) -> dict[str, object]:
        snapshot = super()._actual_snapshot()
        snapshot["ev_reference_power_w"] = self._ev_reference_power()
        snapshot["ev_house_load_power_w"] = self._ev_house_load_power()
        return snapshot

    def _ev_house_load_power(self) -> float | None:
        """Use fresh local 35172 only; never substitute cloud load or forecasts."""
        data = self.coordinator.data
        reported = getattr(data, "source_updated_at", None)
        age = (
            (datetime.now(timezone.utc) - reported).total_seconds()
            if isinstance(reported, datetime) and reported.tzinfo is not None
            else None
        )
        load_fresh = bool(
            getattr(self.coordinator, "last_update_success", False)
            and getattr(data, "source", None) == "modbus"
            and age is not None and 0 <= age <= EV_POWER_MAX_AGE_SECONDS
        )
        values = getattr(data, "values", {}) or {}
        if not isinstance(values, dict):
            return None
        value = values.get("total_load_power")
        return self._finite_value(value) if load_fresh and not isinstance(value, bool) else None

    def mapping_preview(self) -> dict[str, object]:
        """Describe the new model without writing or scheduling any command."""
        load = self._ev_house_load_power()
        ev_power = self._ev_reference_power()
        p_batt = self._state_float(self._p_batt_entity_id())
        p_grid = self._state_float(self._p_grid_entity_id())
        ev_active = self.ev_is_active()
        plan_ready = bool(
            self._optim_is_ready() and not self._plan_update_suspensions
            and self.last_command != "waiting_for_ev_stop_optimization"
        )
        preview = preview_hybrid_mapping(
            p_batt=p_batt,
            p_grid=p_grid,
            battery_deadband=self.entry.options.get(CONF_DEADBAND, DEFAULT_DEADBAND),
            grid_deadband=self.entry.options.get(CONF_GOODWE_AUTO_DEADBAND, DEFAULT_GOODWE_AUTO_DEADBAND),
            max_power=self.entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER),
            explicit_pause=not self.enabled and self.expected_mode == MODE_BATTERY_HOLD,
            plan_ready=plan_ready,
            ev_active=ev_active,
            load_power_w=load,
            ev_power_w=ev_power,
        ).as_dict()
        preview.update({
            "owner": "automatic" if self.enabled else "manual",
            "active_strategy": self.control_strategy,
            "current_command_mode": self.expected_mode,
            "current_command_power_w": self.target_power,
            "matches_current_command": (
                preview["mode"] == self.expected_mode and preview["power_w"] == self.target_power
                if preview["mode"] is not None else None
            ),
            "inputs": {
                "p_batt_w": p_batt,
                "p_grid_w": p_grid,
                "plan_ready": plan_ready,
                "ev_active": ev_active,
                "ev_power_w": ev_power,
                "load_35172_w": load,
                "load_fresh": load is not None,
            },
        })
        return preview

    def _plan_runtime(self):
        runtime_data = getattr(self.entry, "runtime_data", None)
        return getattr(runtime_data, "plan_runtime", None)

    def _state_float(self, entity_id: str | None) -> float | None:
        """Prefer live HA state and fall back to the persisted EMHASS plan."""
        value = super()._state_float(entity_id)
        if value is not None or not entity_id:
            return value

        plan_runtime = self._plan_runtime()
        if plan_runtime is None:
            return None
        if entity_id == self._p_batt_entity_id():
            return plan_runtime.current_p_batt()
        if entity_id == self._p_grid_entity_id():
            return plan_runtime.current_p_grid()
        return None

    def _optim_is_ready(self) -> bool:
        """Accept a valid mirrored plan while optim_status is temporarily absent."""
        entity_id = self.entry.options.get(CONF_OPTIM_STATUS_ENTITY)
        if not entity_id:
            return True

        state = self.hass.states.get(entity_id)
        if state is not None and state.state.lower() not in _MISSING_STATES:
            return super()._optim_is_ready()

        plan_runtime = self._plan_runtime()
        return bool(plan_runtime is not None and plan_runtime.has_current_plan())

    async def _async_apply_ev_anti_discharge_plan(
        self,
        p_batt: float,
        battery_deadband: float,
        grid_deadband: float,
        max_power: int,
    ) -> None:
        """Block discharge during EV charging while allowing planned charging."""
        strategy = self.control_strategy
        p_grid = None
        if strategy in {CONTROL_STRATEGY_GRID, CONTROL_STRATEGY_HYBRID, CONTROL_STRATEGY_HYBRID_2}:
            p_grid = self._state_float(self._p_grid_entity_id())
        decision = resolve_control_decision(
            strategy=strategy,
            p_batt=p_batt,
            p_grid=p_grid,
            battery_deadband=battery_deadband,
            grid_deadband=grid_deadband,
            max_power=max_power,
            ev_active=True,
            ev_power_w=self._ev_reference_power(),
            load_power_w=self._ev_house_load_power(),
        )
        if not decision.ready:
            self.last_command = decision.command
            self._notify_state()
            await self._async_record_waiting(self.last_command)
            return
        if decision.command == "ev_house_self_consumption":
            now = monotonic()
            previous = getattr(self, "_last_ev_reference_at", None)
            if (self.last_command == decision.command and previous is not None
                    and now - previous < EV_SELF_CONSUMPTION_INTERVAL_SECONDS):
                return
            self._last_ev_reference_at = now
        await self._async_apply_command(
            int(decision.mode),
            int(decision.power),
            decision.command,
            skip_if_readback_matches=True,
        )
