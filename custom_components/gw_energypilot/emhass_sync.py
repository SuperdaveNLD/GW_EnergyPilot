"""Pure helpers for synchronizing the required EMHASS configuration."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

DEFAULT_PV_FORECAST_ENTITY = "sensor.p_pv_forecast"

# Keep the runtime contract in one canonical definition. These values are
# required for EnergyPilot orchestration, unlike installation/model topology
# settings such as set_use_pv and inverter_is_hybrid which remain EMHASS-owned.
REQUIRED_RUNTIME_CONFIG: dict[str, Any] = {
    "continual_publish": True,
    "method_ts_round": "first",
    "set_use_battery": True,
}

SYNCED_CONFIG_KEYS: tuple[str, ...] = (
    "sensor_power_photovoltaics",
    "sensor_power_load_no_var_loads",
    "sensor_power_battery",
    "sensor_battery_state_of_charge",
    "sensor_power_photovoltaics_forecast",
    "sensor_replace_zero",
    "sensor_linear_interp",
    "var_model",
    *REQUIRED_RUNTIME_CONFIG,
)


def apply_emhass_runtime_contract(config: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copied config with only the EnergyPilot runtime contract applied."""
    updated = deepcopy(dict(config))
    updated.update(REQUIRED_RUNTIME_CONFIG)
    return updated


def _required_entity(entity_ids: Mapping[str, str], key: str) -> str:
    value = str(entity_ids.get(key, "")).strip()
    if not value:
        raise ValueError(f"Missing required EnergyPilot entity mapping: {key}")
    return value


def _string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _string_items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        normalized = _string_value(item)
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _replace_and_require(
    value: Any,
    replacements: Mapping[str, str],
    required: tuple[str, ...],
) -> list[str]:
    result: list[str] = []
    for item in _string_items(value):
        replacement = replacements.get(item, item)
        if replacement and replacement not in result:
            result.append(replacement)
    for item in required:
        if item not in result:
            result.append(item)
    return result


def _single_battery_entity_value(current: Any, entity_id: str) -> str | list[str]:
    return [entity_id] if isinstance(current, list) else entity_id


def _number_of_batteries(config: Mapping[str, Any]) -> int:
    try:
        value = int(config.get("number_of_batteries", 1))
    except (TypeError, ValueError):
        return 1
    return max(1, value)


def build_emhass_sync_config(
    config: Mapping[str, Any],
    entity_ids: Mapping[str, str],
) -> tuple[dict[str, Any], list[str]]:
    """Return a complete EMHASS config with EnergyPilot-required values synchronized.

    PV is intentionally conditional. A battery-only EMHASS installation is valid,
    so EnergyPilot preserves ``set_use_pv`` and PV mappings when PV is disabled.
    Inverter topology remains entirely EMHASS-owned; EnergyPilot never changes
    ``inverter_is_hybrid``.
    """
    load_entity = _required_entity(entity_ids, "load")
    battery_entity = _required_entity(entity_ids, "battery")
    soc_entity = _required_entity(entity_ids, "soc")
    use_pv = bool(config.get("set_use_pv", False))
    pv_entity = _required_entity(entity_ids, "pv") if use_pv else None

    synced = apply_emhass_runtime_contract(config)
    warnings: list[str] = []
    old_pv = _string_value(config.get("sensor_power_photovoltaics"))
    old_load = _string_value(config.get("sensor_power_load_no_var_loads"))
    old_forecast = _string_value(config.get("sensor_power_photovoltaics_forecast"))
    pv_forecast = old_forecast or DEFAULT_PV_FORECAST_ENTITY

    synced["sensor_power_load_no_var_loads"] = load_entity
    if use_pv and pv_entity is not None:
        synced["sensor_power_photovoltaics"] = pv_entity
        synced["sensor_power_photovoltaics_forecast"] = pv_forecast

    if _number_of_batteries(config) == 1:
        synced["sensor_power_battery"] = _single_battery_entity_value(
            config.get("sensor_power_battery"), battery_entity
        )
        synced["sensor_battery_state_of_charge"] = _single_battery_entity_value(
            config.get("sensor_battery_state_of_charge"), soc_entity
        )
    else:
        warnings.append(
            "EMHASS is configured with multiple batteries; EnergyPilot cannot safely "
            "replace per-battery power/SOC sensor lists."
        )

    replacement_pairs: list[tuple[str | None, str | None]] = [
        (old_load, load_entity),
    ]
    if use_pv:
        replacement_pairs.extend(
            [
                (old_pv, pv_entity),
                (old_forecast, pv_forecast),
            ]
        )
    replacements = {
        value: replacement
        for value, replacement in replacement_pairs
        if value and replacement
    }

    replace_required: tuple[str, ...] = (
        (pv_entity, pv_forecast)
        if use_pv and pv_entity is not None
        else ()
    )
    interp_required: tuple[str, ...] = (
        (pv_entity, load_entity)
        if use_pv and pv_entity is not None
        else (load_entity,)
    )
    synced["sensor_replace_zero"] = _replace_and_require(
        config.get("sensor_replace_zero"),
        replacements,
        replace_required,
    )
    synced["sensor_linear_interp"] = _replace_and_require(
        config.get("sensor_linear_interp"),
        replacements,
        interp_required,
    )

    current_var_model = _string_value(config.get("var_model"))
    if current_var_model in {None, old_load, "sensor.power_load_no_var_loads"}:
        synced["var_model"] = load_entity
    else:
        warnings.append(
            "Custom EMHASS var_model was preserved instead of being replaced."
        )

    return synced, warnings


def emhass_sync_changes(
    current: Mapping[str, Any],
    synced: Mapping[str, Any],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for key in SYNCED_CONFIG_KEYS:
        before = current.get(key)
        after = synced.get(key)
        if before != after:
            changes.append({"key": key, "current": before, "required": after})
    return changes
