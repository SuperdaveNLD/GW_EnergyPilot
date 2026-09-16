"""GW EnergyPilot v0.33 plan-resilient Automatic Control."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from time import monotonic

from homeassistant.core import callback

from .control_decision import preview_hybrid_mapping, preview_hybrid3_mapping, resolve_control_decision
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
    CONTROL_STRATEGY_HYBRID_3,
    DEFAULT_DEADBAND,
    DEFAULT_GOODWE_AUTO_DEADBAND,
    DEFAULT_MAX_POWER,
    EV_DETECTION_METHOD_STATE,
    MODE_BATTERY_HOLD,
)
from .controller import GWEnergyPilotController as _BaseController
from .hybrid3_reference import EVReferenceRecovery
from .ev_detection import (
    EV_POWER_MAX_AGE_SECONDS,
    EV_SELF_CONSUMPTION_INTERVAL_SECONDS,
    detection_method,
    fresh_power_value_w,
)

_MISSING_STATES = {"unknown", "unavailable", "none", ""}
_HOUSE_STRATEGIES = {CONTROL_STRATEGY_HYBRID_2, CONTROL_STRATEGY_HYBRID_3}


class GWEnergyPilotController(_BaseController):
    """Keep Automatic Control usable while EMHASS HA entities are rebuilding."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._h3_reference = EVReferenceRecovery()
        self._h3_ack: tuple[int, int] | None = None
        self._h3_ack_at: float | None = None
        self._h3_readback_status = "not_attempted"
        self._h3_hold_reason: str | None = None
        self._h3_ev_stop_at: datetime | None = None

    async def async_setup(self) -> None:
        from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval

        await super().async_setup()
        self._ev_reference_task = None
        self._ev_reference_unloading = False
        # A live strategy selection need not reload the entry. Observe the
        # optional measured source now, but act on it only in Hybrid 2.0/3.0.
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
        if self.control_strategy in _HOUSE_STRATEGIES:
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
        if self.control_strategy in _HOUSE_STRATEGIES:
            power_entity = self.entry.options.get(CONF_EV_POWER_ENTITY)
            if power_entity:
                sources.add(power_entity)
        return sources

    def _ev_reference_power(self) -> float | None:
        return fresh_power_value_w(self.hass.states, self.entry.options.get(CONF_EV_POWER_ENTITY))

    def ev_is_active(self) -> bool:
        active = super().ev_is_active()
        if (active or self.control_strategy not in _HOUSE_STRATEGIES
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
                or self.control_strategy not in _HOUSE_STRATEGIES
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
            self.enabled and self.control_strategy in _HOUSE_STRATEGIES
            and event.data.get("entity_id") in self.ev_source_ids
            and self._ev_was_active and not self.ev_is_active()
            and self.entry.options.get(CONF_ENABLE_EMHASS_ORCHESTRATOR, False)
        )
        if native_ev_stop and self.control_strategy == CONTROL_STRATEGY_HYBRID_3:
            self._h3_ev_stop_at = datetime.now(timezone.utc)
        super()._async_source_changed(event)
        if native_ev_stop:
            self.hass.async_create_task(self._async_hold_after_ev_stop(), "gw-energypilot-ev-stop-hold")

    async def _async_hold_after_ev_stop(self) -> None:
        async with self._control_lock:
            if (self.enabled and self.control_strategy in _HOUSE_STRATEGIES
                    and not self.ev_is_active()
                    and self.last_command == "waiting_for_ev_stop_optimization"):
                await self._async_apply_command(
                    MODE_BATTERY_HOLD, 0, "waiting_for_ev_stop_optimization",
                    skip_if_readback_matches=True,
                )

    async def _async_evaluate_locked(self) -> None:
        if self.enabled and self.control_strategy == CONTROL_STRATEGY_HYBRID_3:
            if self.ev_is_active():
                self._ev_was_active = True
                self._h3_ev_stop_at = None
            elif self._h3_ev_stop_at is not None:
                # Repeated idle EV events must not release an old plan while
                # the native optimizer is still preparing a replacement.
                runtime = getattr(self.entry, "runtime_data", None)
                success = getattr(getattr(runtime, "orchestrator", None), "last_success", None)
                states = [self.hass.states.get(entity)
                          for entity in (self._p_batt_entity_id(), self._p_grid_entity_id())]
                reports = [getattr(state, "last_reported", None) or
                           getattr(state, "last_updated", None) for state in states]
                stop = self._h3_ev_stop_at
                now = datetime.now(timezone.utc)
                fresh = (isinstance(success, datetime) and success.tzinfo is not None
                         and stop < success <= now and all(isinstance(report, datetime)
                         and report.tzinfo is not None and stop < report <= now for report in reports)
                         and self._optim_is_ready() and not self._plan_update_suspensions
                         and all(self._raw_state_float(entity) is not None for entity in
                                 (self._p_batt_entity_id(), self._p_grid_entity_id())))
                if not fresh:
                    await self._async_hybrid3_hold("waiting_for_ev_stop_optimization",
                                                  command="waiting_for_ev_stop_optimization")
                    return
                self._h3_ev_stop_at = None
            if not self.ev_is_active():
                self._h3_hold_reason = None
            if (self._plan_update_suspensions or not self._optim_is_ready()
                    or self._state_float(self._p_batt_entity_id()) is None
                    or self._state_float(self._p_grid_entity_id()) is None):
                reason = ("plan_suspended" if self._plan_update_suspensions else
                          "optimizer_not_ready" if not self._optim_is_ready() else
                          "p_batt_unavailable" if self._state_float(self._p_batt_entity_id()) is None else
                          "p_grid_unavailable")
                await self._async_hybrid3_hold(reason, command=("ev_self_consumption_hold"
                    if self.ev_is_active() else "hybrid3_plan_hold"))
                return
        if (self.enabled and self.control_strategy in _HOUSE_STRATEGIES
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
        if self.control_strategy == CONTROL_STRATEGY_HYBRID_3:
            snapshot["hybrid3"] = self.hybrid3_diagnostics
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
        preview_function = (preview_hybrid3_mapping if self.control_strategy == CONTROL_STRATEGY_HYBRID_3
                            else preview_hybrid_mapping)
        preview = preview_function(
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
        if self.control_strategy == CONTROL_STRATEGY_HYBRID_3:
            preview["runtime_guard"] = self.hybrid3_diagnostics
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
        if strategy in {CONTROL_STRATEGY_GRID, CONTROL_STRATEGY_HYBRID, *_HOUSE_STRATEGIES}:
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
        if strategy == CONTROL_STRATEGY_HYBRID_3:
            measurements = self._hybrid3_measurements()
            if decision.command == "ev_self_consumption_hold":
                await self._async_hybrid3_hold(measurements["reason"] or "mapping_unavailable")
                return
            if decision.command == "ev_house_self_consumption":
                if measurements["reason"]:
                    await self._async_hybrid3_hold(measurements["reason"])
                    return
                pair = tuple(datetime.fromisoformat(measurements[key])
                             for key in ("load_reported_at", "ev_reported_at"))
                if not self._h3_reference.ready(pair, monotonic()):
                    self._h3_hold_reason = "recovering_fresh_measurements"
                    await self._async_apply_command(8, 0, "ev_self_consumption_hold",
                                                    skip_if_readback_matches=True)
                    return
            self._h3_hold_reason = None
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

    def _hybrid3_measurements(self) -> dict[str, object]:
        """Read-only source ages/reasons; never make a control read look fresh."""
        data = self.coordinator.data
        entity_id = self.entry.options.get(CONF_EV_POWER_ENTITY)
        state = self.hass.states.get(entity_id) if entity_id else None
        load_time = getattr(data, "source_updated_at", None)
        ev_time = getattr(state, "last_reported", None) or getattr(state, "last_updated", None)
        now = datetime.now(timezone.utc)
        def age(value):
            return ((now - value).total_seconds() if isinstance(value, datetime)
                    and value.tzinfo is not None else None)
        load_age, ev_age = age(load_time), age(ev_time)
        load, ev = self._ev_house_load_power(), self._ev_reference_power()
        reason = None
        if ev is None or ev <= 0:
            unit = (getattr(state, "attributes", {}) or {}).get("unit_of_measurement")
            reason = ("ev_missing" if state is None else "ev_units_invalid" if
                      unit not in {"W", "kW", "MW", "mW"} else "ev_timestamp_invalid" if ev_age is None else
                      "ev_timestamp_future" if ev_age < 0 else "ev_stale" if ev_age > EV_POWER_MAX_AGE_SECONDS else
                      "ev_power_invalid_or_zero")
        elif load is None:
            reason = ("load_not_local" if getattr(data, "source", None) != "modbus" else
                      "load_read_failed" if not self.coordinator.last_update_success else
                      "load_timestamp_invalid" if load_age is None else "load_timestamp_future" if load_age < 0 else
                      "load_stale" if load_age > EV_POWER_MAX_AGE_SECONDS else "load_invalid")
        elif abs(load_age - ev_age) > EV_SELF_CONSUMPTION_INTERVAL_SECONDS:
            reason = "measurement_time_skew"
        return {"reason": reason, "load_age_seconds": load_age, "ev_age_seconds": ev_age,
                "load_reported_at": load_time.isoformat() if load_age is not None else None,
                "ev_reported_at": ev_time.isoformat() if ev_age is not None else None,
                "load_w": load, "ev_w": ev}

    @property
    def hybrid3_diagnostics(self) -> dict[str, object]:
        return {**self._hybrid3_measurements(), "hold_reason": self._h3_hold_reason,
                "recovering": self._h3_reference.recovering,
                "fresh_pairs": self._h3_reference.fresh_pairs,
                "last_fault": self._h3_reference.last_fault,
                "command_readback": self._h3_readback_status}

    async def _async_hybrid3_hold(self, reason: str, *, command="ev_self_consumption_hold") -> None:
        self._h3_hold_reason = reason
        self._h3_reference.invalidate(reason)
        await self._async_apply_command(MODE_BATTERY_HOLD, 0, command, skip_if_readback_matches=True)

    def _actual_command_matches(self, mode: int, power: int) -> bool:
        if self.enabled and self.control_strategy == CONTROL_STRATEGY_HYBRID_3:
            if (self._h3_ack != (mode, power) or self._h3_ack_at is None
                    or monotonic() - self._h3_ack_at > EV_POWER_MAX_AGE_SECONDS
                    or not getattr(self.coordinator, "last_control_update_success", False)):
                return False
        return super()._actual_command_matches(mode, power)

    async def _async_apply_command(self, mode: int, power: int, command: str, *, skip_if_readback_matches=False) -> None:
        if self.enabled and self.control_strategy == CONTROL_STRATEGY_HYBRID_3:
            if not (skip_if_readback_matches and self._actual_command_matches(mode, power)):
                # Invalidate BEFORE writing: old mode-5 telemetry must never
                # skip a new mode-5 command after an unconfirmed Hold write.
                self._h3_ack = None
                self._h3_ack_at = None
                self._h3_readback_status = "pending"
                skip_if_readback_matches = False
            try:
                await super()._async_apply_command(mode, power, command, skip_if_readback_matches=skip_if_readback_matches)
            except Exception:
                if self._h3_readback_status == "pending":
                    self._h3_readback_status = "write_failed"
                raise
            if self._h3_ack is None:
                raise RuntimeError("Hybrid 3.0 command readback is not confirmed")
            return
        self._h3_ack = None
        self._h3_ack_at = None
        self._h3_ev_stop_at = None
        self._h3_reference = EVReferenceRecovery()
        await super()._async_apply_command(mode, power, command, skip_if_readback_matches=skip_if_readback_matches)

    async def _async_refresh_command_readback(self) -> None:
        if not (self.enabled and self.control_strategy == CONTROL_STRATEGY_HYBRID_3):
            await super()._async_refresh_command_readback()
            return
        try:
            # Direct canonical EMS read, not HA's debounced full-telemetry
            # refresh. At most three read attempts within this transaction;
            # never rewrite or create a competing feedback timer here.
            for attempt in range(3):
                control = await self.client.async_read_control_status()
                self.coordinator.last_control_update_success = True
                self.coordinator.last_control_exception = None
                self.coordinator.async_publish_local_readback(control)
                if ((control.mode, control.power) == (self.expected_mode, self.target_power)
                        and super()._actual_command_matches(self.expected_mode, self.target_power)):
                    self._h3_ack = (control.mode, control.power)
                    self._h3_ack_at = monotonic()
                    self._h3_readback_status = "verified"
                    return
                if attempt < 2:
                    await asyncio.sleep(0.5)
            self._h3_readback_status = "mismatch"
        except Exception as err:
            self._h3_readback_status = "unavailable"
            self.coordinator.last_control_update_success = False
            self.coordinator.last_control_exception = err
            raise
