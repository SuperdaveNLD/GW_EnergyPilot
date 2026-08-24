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
    MODE_MAD_STEVE,
    battery_saver_costs_are_zero,
    battery_saver_mode_payloads,
    emhass_supports_battery_stress,
    normalize_battery_saver_mode,
    number_of_batteries,
)
from .const import CONF_BATTERY_SAVER_MODE, DOMAIN
from .emhass_config import async_get_emhass_config, async_write_emhass_config

GOODWE_ON_GRID_MINIMUM_SOC_KEY = "battery_discharge_depth_on_grid"


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
    runtime = getattr(entry, "runtime_data", None)
    coordinator = getattr(runtime, "coordinator", None)
    snapshot = getattr(coordinator, "data", None)
    if snapshot is None:
        return None
    raw = snapshot.values.get(GOODWE_ON_GRID_MINIMUM_SOC_KEY)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return float(value) if 0 <= value <= 100 else None


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

    Required EnergyPilot contract corrections such as continual_publish and the
    synchronized hard minimum SOC intentionally remain in place.
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
    except HomeAssistantError as err:
        return str(err)
    return None


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
        vol.Required("mode"): vol.In(BATTERY_SAVER_MODES),
    }
)
@websocket_api.async_response
async def websocket_set_battery_saver(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Persist one mode and rebuild the EnergyPilot-owned plan immediately."""
    entry = _resolve_entry(hass, msg["entry_id"])
    if entry is None:
        connection.send_error(
            msg["id"], "not_found", "GW EnergyPilot config entry not found"
        )
        return

    mode = normalize_battery_saver_mode(msg["mode"])
    try:
        config = await async_get_emhass_config(hass, entry)
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "emhass_unavailable", str(err))
        return

    if number_of_batteries(config) != 1:
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
        mode != MODE_MAD_STEVE
        and emhass_version is not None
        and not emhass_supports_battery_stress(emhass_version)
    ):
        connection.send_error(
            msg["id"],
            "unsupported_emhass_version",
            "Gold Rush, Balanced and Battery Saver require EMHASS 0.18.1 or newer",
        )
        return

    old_options = dict(entry.options)
    previous_profile = getattr(orchestrator, "last_battery_saver_profile", None)
    previous_effective_soc = getattr(orchestrator, "last_effective_soc_final", None)
    new_options = dict(old_options)
    new_options[CONF_BATTERY_SAVER_MODE] = mode
    hass.config_entries.async_update_entry(entry, options=new_options)

    try:
        await orchestrator.async_optimize(reason="battery_saver_changed")
        refreshed_config = await async_get_emhass_config(hass, entry)
    except (HomeAssistantError, ValueError) as err:
        # Do not leave a mode or its penalty values active if the first complete
        # profile+plan cycle failed. Restore only the Battery Saver-owned fields;
        # required config repairs remain valid independently of the chosen mode.
        hass.config_entries.async_update_entry(entry, options=old_options)
        orchestrator.last_battery_saver_profile = previous_profile
        orchestrator.last_effective_soc_final = previous_effective_soc
        rollback_error = await _async_restore_battery_saver_config(
            hass, entry, config
        )
        message = str(err)
        if rollback_error:
            message += f"; Battery Saver EMHASS rollback also failed: {rollback_error}"
        connection.send_error(msg["id"], "apply_failed", message)
        return

    connection.send_result(msg["id"], _payload(entry, refreshed_config))


@callback
def async_register_battery_saver_api(hass: HomeAssistant) -> None:
    """Register Battery Saver WebSocket commands once."""
    websocket_api.async_register_command(hass, websocket_get_battery_saver)
    websocket_api.async_register_command(hass, websocket_set_battery_saver)
