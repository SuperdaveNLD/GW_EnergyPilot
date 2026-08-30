"""Read-only battery/price/plan dashboard API for GW EnergyPilot."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .battery_plan import (
    emhass_schedule_attribute,
    finite_number,
    nonnegative_number,
    normalize_emhass_forecasts,
    normalized_timestamp,
)
from .control_decision import resolve_control_decision
from .const import (
    CONF_DEADBAND,
    CONF_MAX_POWER,
    CONF_P_BATT_ENTITY,
    DEFAULT_DEADBAND,
    DEFAULT_MAX_POWER,
    DEFAULT_P_BATT_ENTITY,
    DOMAIN,
    MODE_NAMES,
)
from .execution_history import (
    EXECUTION_HISTORY_LIMIT,
    EXECUTION_HISTORY_RETENTION_DAYS,
)


def _resolve_entry(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry | None:
    """Resolve one EnergyPilot config entry, defaulting to the first entry."""
    if entry_id:
        entry = hass.config_entries.async_get_entry(entry_id)
        return entry if entry and entry.domain == DOMAIN else None
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


def _battery_energy_payload(runtime_data: Any) -> dict[str, Any]:
    """Return GoodWe's native current-day battery energy counters."""
    coordinator = getattr(runtime_data, "coordinator", None)
    data = getattr(coordinator, "data", None)
    values = getattr(data, "values", {}) if data is not None else {}
    return {
        "charged_today_kwh": nonnegative_number(
            values.get("battery_charge_energy_today")
        ),
        "discharged_today_kwh": nonnegative_number(
            values.get("battery_discharge_energy_today")
        ),
        "source": "goodwe_35208_35211",
    }


def _battery_plan_payload(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return live P_batt plus the canonical persisted EMHASS horizon."""
    entity_id = str(
        entry.options.get(CONF_P_BATT_ENTITY, DEFAULT_P_BATT_ENTITY)
        or DEFAULT_P_BATT_ENTITY
    )
    state = hass.states.get(entity_id)
    schedule_attribute = (
        emhass_schedule_attribute(state.attributes) if state is not None else None
    )
    live_points = (
        normalize_emhass_forecasts(entity_id, state.attributes)
        if state is not None
        else []
    )

    runtime_data = getattr(entry, "runtime_data", None)
    plan_runtime = getattr(runtime_data, "plan_runtime", None)
    cached_points = plan_runtime.points("p_batt") if plan_runtime is not None else []
    points = cached_points or live_points

    live_current = finite_number(state.state) if state is not None else None
    cached_current = (
        plan_runtime.current_p_batt() if plan_runtime is not None else None
    )
    diagnostics = dict(plan_runtime.diagnostics) if plan_runtime is not None else {}
    current_w = live_current if live_current is not None else cached_current
    forecast_source = (
        diagnostics.get("source")
        if cached_points
        else f"home_assistant_{schedule_attribute}"
        if live_points and schedule_attribute
        else None
    )

    return {
        "entity_id": entity_id,
        "available": current_w is not None or bool(points),
        "current_w": current_w,
        "current_source": (
            "home_assistant"
            if live_current is not None
            else "persistent_plan"
            if cached_current is not None
            else None
        ),
        "last_updated": state.last_updated.isoformat() if state is not None else None,
        "schedule_attribute": schedule_attribute,
        "forecast_source": forecast_source,
        "generated_at": diagnostics.get("generated_at"),
        "valid_until": diagnostics.get("valid_until"),
        "restored_from_store": diagnostics.get("restored_from_store", False),
        "points": points,
    }


def _battery_soc_plan_payload(entry: ConfigEntry) -> dict[str, Any]:
    """Return validated planned SOC percentages from the official plan mirror."""
    runtime_data = getattr(entry, "runtime_data", None)
    plan_runtime = getattr(runtime_data, "plan_runtime", None)
    points = plan_runtime.points("soc_opt") if plan_runtime is not None else []
    diagnostics = dict(plan_runtime.diagnostics) if plan_runtime is not None else {}
    source = diagnostics.get("source") if points else None
    return {
        "available": bool(points),
        "unit": "%",
        "source": source,
        "source_column": "SOC_opt" if source == "emhass_api_v1_plan" else None,
        "source_unit": "fraction_0_1" if source == "emhass_api_v1_plan" else None,
        "points": points,
    }


def _points_by_start(
    points: list[dict[str, Any]],
    value_key: str,
) -> dict[float, tuple[str, float]]:
    result: dict[float, tuple[str, float]] = {}
    for point in points:
        parsed = normalized_timestamp(point.get("start"))
        value = finite_number(point.get(value_key))
        if parsed is not None and value is not None:
            result[parsed[1]] = (parsed[0], value)
    return result


def _future_execution_rows(
    entry: ConfigEntry,
    *,
    now: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    """Project future plan rows through the same pure controller mapping."""
    runtime_data = getattr(entry, "runtime_data", None)
    plan_runtime = getattr(runtime_data, "plan_runtime", None)
    controller = getattr(runtime_data, "controller", None)
    orchestrator = getattr(runtime_data, "orchestrator", None)
    if plan_runtime is None or controller is None:
        return []

    p_batt = _points_by_start(plan_runtime.points("p_batt"), "value_w")
    p_grid = _points_by_start(plan_runtime.points("p_grid"), "value_w")
    p_pv = _points_by_start(plan_runtime.points("p_pv"), "value_w")
    p_load = _points_by_start(plan_runtime.points("p_load"), "value_w")
    soc_opt = _points_by_start(plan_runtime.points("soc_opt"), "value_pct")
    deadband = float(entry.options.get(CONF_DEADBAND, DEFAULT_DEADBAND))
    max_power = int(entry.options.get(CONF_MAX_POWER, DEFAULT_MAX_POWER))
    start_seconds = now.timestamp()
    end_seconds = end.timestamp()
    diagnostics = dict(plan_runtime.diagnostics)
    rows: list[dict[str, Any]] = []
    for timestamp in sorted(p_batt):
        if timestamp < start_seconds or timestamp >= end_seconds:
            continue
        start, battery = p_batt[timestamp]
        grid = p_grid.get(timestamp, (start, None))[1]
        decision = resolve_control_decision(
            strategy=controller.control_strategy,
            p_batt=battery,
            p_grid=grid,
            deadband=deadband,
            max_power=max_power,
            # EV/manual/failsafe state is intentionally not forecast.
            ev_active=False,
        )
        rows.append(
            {
                "kind": "projection",
                "occurred_at": start,
                "owner": "automatic" if controller.enabled else "manual",
                "plan": {
                    "p_batt_w": battery,
                    "p_grid_w": grid,
                    "p_pv_w": p_pv.get(timestamp, (start, None))[1],
                    "p_load_w": p_load.get(timestamp, (start, None))[1],
                    "soc_opt_pct": soc_opt.get(timestamp, (start, None))[1],
                    "mirror_source": diagnostics.get("source"),
                    "generated_at": diagnostics.get("generated_at"),
                    "valid_until": diagnostics.get("valid_until"),
                    "revision": int(
                        getattr(orchestrator, "plan_revision", 0) or 0
                    ),
                },
                "configuration": {
                    "strategy": controller.control_strategy,
                    "deadband_w": deadband,
                    "max_power_w": max_power,
                    "ev_active": False,
                },
                "actual": {},
                "outcome": {
                    "command": decision.command,
                    "expected_mode": decision.mode,
                    "expected_mode_name": MODE_NAMES.get(
                        decision.mode, "Waiting"
                    ),
                    "expected_setpoint_w": decision.power,
                    "write_status": "projected",
                    "verification_status": "future",
                },
            }
        )
    return rows


async def _execution_payload(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return exact 48-hour history plus a conditional 24-hour projection."""
    now = datetime.now(timezone.utc)
    history_start = now - timedelta(hours=48)
    future_end = now + timedelta(hours=24)
    runtime_data = getattr(entry, "runtime_data", None)
    execution_history = getattr(runtime_data, "execution_history", None)
    history = (
        await execution_history.async_history(start=history_start, end=now)
        if execution_history is not None
        else []
    )
    return {
        "schema_version": 1,
        "available": execution_history is not None,
        "history_start": history_start.isoformat(),
        "now": now.isoformat(),
        "future_end": future_end.isoformat(),
        "time_zone": getattr(hass.config, "time_zone", "UTC"),
        "retention_days": EXECUTION_HISTORY_RETENTION_DAYS,
        "event_limit": EXECUTION_HISTORY_LIMIT,
        "history": history,
        "future": _future_execution_rows(entry, now=now, end=future_end),
        "future_assumptions": {
            "configuration_unchanged": True,
            "control_ownership_unchanged": True,
            "ev_override_not_predicted": True,
            "readback_not_predicted": True,
        },
    }


@websocket_api.websocket_command(
    {
        vol.Required("type"): "gw_energypilot/battery_price/get",
        vol.Optional("entry_id"): str,
        vol.Optional("force", default=False): bool,
    }
)
@websocket_api.async_response
async def websocket_get_battery_price(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return canonical prices, native energy totals and the EMHASS plan."""
    entry = _resolve_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(
            msg["id"], "not_found", "GW EnergyPilot config entry not found"
        )
        return

    runtime_data = getattr(entry, "runtime_data", None)
    orchestrator = getattr(runtime_data, "orchestrator", None)
    plan_runtime = getattr(runtime_data, "plan_runtime", None)
    price_reader = getattr(orchestrator, "async_dashboard_price_payload", None)
    if not callable(price_reader):
        connection.send_error(
            msg["id"], "not_loaded", "GW EnergyPilot price runtime is not loaded"
        )
        return

    force = bool(msg.get("force", False))
    refresh_plan = bool(
        plan_runtime is not None and (force or not plan_runtime.has_current_plan())
    )
    if refresh_plan:
        price_payload, _plan_refreshed = await asyncio.gather(
            price_reader(force=force),
            plan_runtime.async_refresh(reason="dashboard"),
        )
    else:
        price_payload = await price_reader(force=force)

    connection.send_result(
        msg["id"],
        {
            "entry_id": entry.entry_id,
            "chart_schema_version": 6,
            "plan_revision": int(getattr(orchestrator, "plan_revision", 0) or 0),
            **price_payload,
            "battery_energy": _battery_energy_payload(runtime_data),
            "battery_plan": _battery_plan_payload(hass, entry),
            "battery_soc_plan": _battery_soc_plan_payload(entry),
            "execution": await _execution_payload(hass, entry),
        },
    )


@callback
def async_register_battery_price_api(hass: HomeAssistant) -> None:
    """Register the read-only EnergyPilot battery chart command."""
    websocket_api.async_register_command(hass, websocket_get_battery_price)
