"""Admin API for EnergyPilot Battery Saver mode selection."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .battery_saver import (
    BATTERY_SAVER_CONFIG_KEYS,
    BATTERY_SAVER_MODES,
    CUSTOM_BATTERY_COST_KEYS,
    battery_saver_minimum_soc_pct,
    battery_saver_costs_are_zero,
    battery_saver_mode_requires_stress_support,
    battery_saver_mode_payloads,
    custom_battery_cost_updates,
    emhass_supports_battery_stress,
    normalize_battery_saver_mode,
    number_of_batteries,
)
from .const import (
    CONF_BATTERY_SAVER_MODE,
    CONF_BATTERY_SAVER_SOC_LIMITS_MANAGED,
    DOMAIN,
)
from .emhass_config import async_get_emhass_config, async_write_emhass_config
from .soc_limits import async_set_goodwe_minimum_soc, goodwe_minimum_soc_pct

CUSTOM_MODE = "custom"
SELECTABLE_MODES: tuple[str, ...] = (*BATTERY_SAVER_MODES, CUSTOM_MODE)
CUSTOM_BATTERY_COST_SCHEMA = {
    vol.Required(key): vol.Coerce(float) for key in CUSTOM_BATTERY_COST_KEYS
}


def _resolve_entry(hass: HomeAssistant, entry_id: str | None) -> ConfigEntry | None:
    if entry_id:
        entry = hass.config_entries.async_get_entry(entry_id)
        return entry if entry and entry.domain == DOMAIN else None
    entries = hass.config_entries.async_entries(DOMAIN)
    return entries[0] if entries else None


def _percentage(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not 0.0 <= number <= 1.0:
        return None
    return round(number * 100.0, 1)


def _goodwe_minimum_soc(entry: ConfigEntry) -> float | None:
    value = goodwe_minimum_soc_pct(entry)
    return float(value) if value is not None else None


def _payload(entry: ConfigEntry, config: dict[str, Any]) -> dict[str, Any]:
    configured_mode = entry.options.get(CONF_BATTERY_SAVER_MODE)
    mode = None
    if configured_mode is not None:
        try:
            mode = normalize_battery_saver_mode(configured_mode)
        except ValueError:
            mode = None

    runtime = getattr(entry, "runtime_data", None)
    orchestrator = getattr(runtime, "orchestrator", None)
    goodwe_minimum = _goodwe_minimum_soc(entry)
    config_minimum = _percentage(config.get("battery_minimum_state_of_charge"))
    hard_minimum = goodwe_minimum if goodwe_minimum is not None else config_minimum
    current_values = {key: config.get(key) for key in BATTERY_SAVER_CONFIG_KEYS}

    return {
        "entry_id": entry.entry_id,
        "managed": mode is not None,
        "soc_limits_managed": bool(
            mode is not None
            and entry.options.get(CONF_BATTERY_SAVER_SOC_LIMITS_MANAGED)
        ),
        "mode": mode,
        "legacy_behavior": (
            "mad_steve"
            if mode is None and battery_saver_costs_are_zero(config)
            else "custom"
            if mode is None
            else None
        ),
        "modes": battery_saver_mode_payloads(),
        "hard_minimum_soc_pct": hard_minimum,
        "hard_maximum_soc_pct": _percentage(
            config.get("battery_maximum_state_of_charge")
        ),
        "current_emhass_values": current_values,
        "effective_profile": getattr(
            orchestrator, "last_battery_saver_profile", None
        ),
        "effective_soc_final": getattr(
            orchestrator, "last_effective_soc_final", None
        ),
        "emhass_version": getattr(orchestrator, "emhass_version", None),
        "battery_count": number_of_batteries(config),
    }


async def _async_payload(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    config = await async_get_emhass_config(hass, entry)
    return _payload(entry, config)


async def _async_restore_battery_saver_config(
    hass: HomeAssistant,
    entry: ConfigEntry,
    previous: dict[str, Any],
) -> str | None:
    """Restore only Battery Saver-owned EMHASS fields after a failed apply.

    Required EnergyPilot runtime-contract corrections such as continual_publish
    intentionally remain in place. Both managed SOC limits are restored here.
    """
    try:
        current = await async_get_emhass_config(hass, entry)
        changed = False
        for key in BATTERY_SAVER_CONFIG_KEYS:
            if key in previous:
                if current.get(key) != previous[key]:
                    current[key] = previous[key]
                    changed = True
            elif key in current:
                current.pop(key, None)
                changed = True
        if changed:
            await async_write_emhass_config(hass, entry, current)
    except (HomeAssistantError, ValueError) as err:
        return str(err)
    return None


def _successful_config_fallback(
    previous: dict[str, Any],
    orchestrator: Any,
) -> dict[str, Any]:
    """Build a truthful-enough UI payload if the post-success GET is unavailable."""
    config = dict(previous)
    profile = getattr(orchestrator, "last_battery_saver_profile", None)
    if isinstance(profile, dict):
        for key in BATTERY_SAVER_CONFIG_KEYS:
            if key in profile:
                config[key] = profile[key]
    goodwe_minimum = _goodwe_minimum_soc(orchestrator.entry)
    if goodwe_minimum is not None:
        config["battery_minimum_state_of_charge"] = round(goodwe_minimum / 100.0, 4)
    return config


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "gw_energypilot/battery_saver/get",
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def websocket_get_battery_saver(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return Battery Saver state without changing EMHASS."""
    entry = _resolve_entry(hass, msg.get("entry_id"))
    if entry is None:
        connection.send_error(
            msg["id"], "not_found", "GW EnergyPilot config entry not found"
        )
        return
    try:
        payload = await _async_payload(hass, entry)
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "emhass_unavailable", str(err))
        return
    connection.send_result(msg["id"], payload)


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "gw_energypilot/battery_saver/set",
        vol.Required("entry_id"): str,
        vol.Required("mode"): vol.In(SELECTABLE_MODES),
    }
)
@websocket_api.async_response
async def websocket_set_battery_saver(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Select a managed preset or Custom and rebuild the plan immediately."""
    entry = _resolve_entry(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(
            msg["id"], "not_found", "GW EnergyPilot config entry not found"
        )
        return

    requested_mode = str(msg["mode"])
    mode = None if requested_mode == CUSTOM_MODE else normalize_battery_saver_mode(
        requested_mode
    )
    try:
        config = await async_get_emhass_config(hass, entry)
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "emhass_unavailable", str(err))
        return

    # Managed presets currently own one EMHASS battery model. Custom deliberately
    # releases that ownership and therefore must remain available even when an
    # installation uses a configuration the managed presets do not support.
    if mode is not None and number_of_batteries(config) != 1:
        connection.send_error(
            msg["id"],
            "unsupported_battery_count",
            "Battery Saver currently supports one EMHASS battery model; the active configuration contains multiple batteries",
        )
        return

    runtime = getattr(entry, "runtime_data", None)
    orchestrator = getattr(runtime, "orchestrator", None)
    if orchestrator is None:
        connection.send_error(
            msg["id"], "not_ready", "EnergyPilot orchestrator is not ready"
        )
        return

    emhass_version = getattr(orchestrator, "emhass_version", None)
    if (
        mode is not None
        and battery_saver_mode_requires_stress_support(mode)
        and emhass_version is not None
        and not emhass_supports_battery_stress(emhass_version)
    ):
        connection.send_error(
            msg["id"],
            "unsupported_emhass_version",
            "Chargegasm, Balanced and Battery Saver require EMHASS 0.18.1 or newer",
        )
        return

    old_options = dict(entry.options)
    previous_profile = getattr(orchestrator, "last_battery_saver_profile", None)
    previous_effective_soc = getattr(orchestrator, "last_effective_soc_final", None)
    previous_goodwe_minimum = goodwe_minimum_soc_pct(entry)
    goodwe_changed = False
    new_options = dict(old_options)
    if mode is None:
        # Custom starts from the exact currently effective EMHASS values. Only
        # release EnergyPilot's preset ownership; do not reset any battery field.
        new_options.pop(CONF_BATTERY_SAVER_MODE, None)
        new_options.pop(CONF_BATTERY_SAVER_SOC_LIMITS_MANAGED, None)
    else:
        new_options[CONF_BATTERY_SAVER_MODE] = mode
        new_options[CONF_BATTERY_SAVER_SOC_LIMITS_MANAGED] = True

    try:
        if mode is not None:
            if previous_goodwe_minimum is None:
                raise HomeAssistantError(
                    "GoodWe on-grid minimum SOC is unavailable; no profile setting was changed"
                )
            requested_minimum = battery_saver_minimum_soc_pct(mode)
            if previous_goodwe_minimum != requested_minimum:
                await async_set_goodwe_minimum_soc(entry, requested_minimum)
                goodwe_changed = True
        hass.config_entries.async_update_entry(entry, options=new_options)
        await orchestrator.async_optimize(reason="battery_saver_changed")
    except Exception as err:  # noqa: BLE001 - rollback must cover all failed runs
        # Do not leave a mode transition active if the first complete policy+plan
        # cycle failed. Restore only Battery Saver-owned fields; required config
        # repairs remain valid independently of the chosen mode.
        hass.config_entries.async_update_entry(entry, options=old_options)
        orchestrator.last_battery_saver_profile = previous_profile
        orchestrator.last_effective_soc_final = previous_effective_soc
        rollback_error = await _async_restore_battery_saver_config(
            hass, entry, config
        )
        goodwe_rollback_error = None
        if goodwe_changed and previous_goodwe_minimum is not None:
            try:
                await async_set_goodwe_minimum_soc(entry, previous_goodwe_minimum)
            except HomeAssistantError as rollback_err:
                goodwe_rollback_error = str(rollback_err)
        message = str(err)
        if rollback_error:
            message += f"; Battery Saver EMHASS rollback also failed: {rollback_error}"
        if goodwe_rollback_error:
            message += (
                "; Battery Saver GoodWe minimum-SOC rollback also failed: "
                f"{goodwe_rollback_error}"
            )
        connection.send_error(msg["id"], "apply_failed", message)
        return

    # The optimize+initial publish is the transaction boundary. A transient
    # diagnostics read failure after that success must not undo a valid plan.
    try:
        refreshed_config = await async_get_emhass_config(hass, entry)
    except HomeAssistantError:
        refreshed_config = _successful_config_fallback(config, orchestrator)

    connection.send_result(msg["id"], _payload(entry, refreshed_config))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "gw_energypilot/battery_saver/custom_set",
        vol.Required("entry_id"): str,
        vol.Required("values"): CUSTOM_BATTERY_COST_SCHEMA,
    }
)
@websocket_api.async_response
async def websocket_set_custom_battery_costs(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Persist validated Custom costs and rebuild the EMHASS plan."""
    entry = _resolve_entry(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(
            msg["id"], "not_found", "GW EnergyPilot config entry not found"
        )
        return

    try:
        config = await async_get_emhass_config(hass, entry)
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "emhass_unavailable", str(err))
        return

    if number_of_batteries(config) != 1:
        connection.send_error(
            msg["id"],
            "unsupported_battery_count",
            "Custom Battery Saver editing supports one EMHASS battery model; the active configuration contains multiple batteries",
        )
        return

    try:
        updates = custom_battery_cost_updates(msg["values"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_custom_values", str(err))
        return

    runtime = getattr(entry, "runtime_data", None)
    orchestrator = getattr(runtime, "orchestrator", None)
    if orchestrator is None:
        connection.send_error(
            msg["id"], "not_ready", "EnergyPilot orchestrator is not ready"
        )
        return

    emhass_version = getattr(orchestrator, "emhass_version", None)
    if updates["battery_stress_cost"] > 0 and not emhass_supports_battery_stress(
        emhass_version
    ):
        connection.send_error(
            msg["id"],
            "unsupported_emhass_version",
            "A non-zero battery power-stress cost requires EMHASS 0.18.1 or newer",
        )
        return

    old_options = dict(entry.options)
    previous_profile = getattr(orchestrator, "last_battery_saver_profile", None)
    previous_effective_soc = getattr(orchestrator, "last_effective_soc_final", None)
    new_options = dict(old_options)
    new_options.pop(CONF_BATTERY_SAVER_MODE, None)
    new_options.pop(CONF_BATTERY_SAVER_SOC_LIMITS_MANAGED, None)
    hass.config_entries.async_update_entry(entry, options=new_options)

    updated_config = dict(config)
    updated_config.update(updates)
    try:
        await async_write_emhass_config(hass, entry, updated_config)
        await orchestrator.async_optimize(reason="battery_saver_custom_changed")
    except Exception as err:  # noqa: BLE001 - restore the complete custom transaction
        hass.config_entries.async_update_entry(entry, options=old_options)
        orchestrator.last_battery_saver_profile = previous_profile
        orchestrator.last_effective_soc_final = previous_effective_soc
        rollback_error = await _async_restore_battery_saver_config(
            hass, entry, config
        )
        message = str(err)
        if rollback_error:
            message += f"; Custom Battery Saver rollback also failed: {rollback_error}"
        connection.send_error(msg["id"], "apply_failed", message)
        return

    try:
        refreshed_config = await async_get_emhass_config(hass, entry)
    except HomeAssistantError:
        refreshed_config = _successful_config_fallback(updated_config, orchestrator)

    connection.send_result(msg["id"], _payload(entry, refreshed_config))


@callback
def async_register_battery_saver_api(hass: HomeAssistant) -> None:
    """Register Battery Saver WebSocket commands once."""
    websocket_api.async_register_command(hass, websocket_get_battery_saver)
    websocket_api.async_register_command(hass, websocket_set_battery_saver)
    websocket_api.async_register_command(hass, websocket_set_custom_battery_costs)
