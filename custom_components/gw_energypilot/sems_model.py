"""Pure SEMS/SEMS+ telemetry normalization for GW EnergyPilot.

The portal API is undocumented and its payload varies between inverter and
station types.  Keep all accepted field semantics explicit here so cloud data
cannot silently acquire the meaning of a canonical GoodWe Modbus register.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import math
import re
from typing import Any, Mapping
from urllib.parse import urlparse


SEMS_MAX_SAMPLE_AGE_SECONDS = 15 * 60
SEMS_POWERSTATION_API_FALLBACK = "https://eu.semsportal.com/api"
_POWER_RE = re.compile(
    r"^\s*(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*"
    r"(?:\(?(?P<unit>k?W)\)?)?\s*$",
    re.IGNORECASE,
)


class SemsPayloadError(ValueError):
    """Raised when a SEMS payload cannot be used safely."""


class SemsSelectionError(SemsPayloadError):
    """Raised when station or inverter selection is ambiguous."""


class SemsStaleDataError(SemsPayloadError):
    """Raised when SEMS returned an old inverter sample."""


@dataclass(frozen=True, slots=True)
class SemsMappedTelemetry:
    """One validated SEMS telemetry snapshot."""

    values: dict[str, int | float]
    inverter_serial: str
    source_updated_at: datetime


def encode_sems_plus_password(password: str) -> str:
    """Encode a password as required by the SEMS+ cross-login protocol."""
    try:
        digest = hashlib.md5(
            password.encode("utf-8"), usedforsecurity=False
        ).hexdigest()
    except TypeError:  # pragma: no cover - compatibility with older Python
        digest = hashlib.md5(password.encode("utf-8")).hexdigest()
    return base64.b64encode(digest.encode("ascii")).decode("ascii")


def normalize_powerstation_api_base(
    api_base: str,
    *,
    region: str | None = None,
) -> str:
    """Resolve a login API base to the legacy PowerStation data host.

    SEMS+ cross-login may return a ``*-gateway.semsportal.com/web/sems`` base,
    while the monitor-detail route used by supported station-type-1 plants is
    still hosted below ``<region>.semsportal.com/api``.
    """
    parsed = urlparse(str(api_base or ""))
    host = (parsed.hostname or "").lower()
    path = parsed.path.rstrip("/")
    if host and "/web/sems" not in path and "-gateway.semsportal.com" not in host:
        return str(api_base).rstrip("/")

    normalized_region = str(region or "").strip().lower()
    if not normalized_region and host.endswith("-gateway.semsportal.com"):
        normalized_region = host.removesuffix("-gateway.semsportal.com")
    if normalized_region and re.fullmatch(r"[a-z0-9-]+", normalized_region):
        return f"https://{normalized_region}.semsportal.com/api"
    return SEMS_POWERSTATION_API_FALLBACK


def normalize_station_ids(raw: Any) -> tuple[str, ...]:
    """Return distinct non-empty station IDs without guessing one."""
    if isinstance(raw, str):
        candidates = [raw]
    elif isinstance(raw, list):
        candidates = raw
    else:
        candidates = []
    result: list[str] = []
    for candidate in candidates:
        value = str(candidate or "").strip()
        if value and value not in result:
            result.append(value)
    return tuple(result)


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def parse_sems_power(value: Any) -> float | None:
    """Parse a SEMS power value expressed as a number or ``123(W)`` string."""
    direct = _finite(value)
    if direct is not None:
        return direct
    if not isinstance(value, str):
        return None
    match = _POWER_RE.fullmatch(value)
    if match is None:
        return None
    number = float(match.group("value"))
    return number * 1000.0 if (match.group("unit") or "W").lower() == "kw" else number


def _bounded(value: Any, minimum: float, maximum: float) -> int | float | None:
    number = _finite(value)
    if number is None or number < minimum or number > maximum:
        return None
    return int(number) if number.is_integer() else number


def _positive_power(value: Any) -> int | float | None:
    number = parse_sems_power(value)
    if number is None or number < 0:
        return None
    return int(number) if number.is_integer() else number


def _payload_data(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Accept either the API data object or its successful response envelope."""
    nested = payload.get("data")
    if "inverter" not in payload and isinstance(nested, Mapping):
        return nested
    return payload


def _inverters(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = payload.get("inverter")
    if not isinstance(rows, list):
        raise SemsPayloadError(
            "SEMS response has no supported inverter telemetry; SEMS+ station type 2 "
            "is not yet supported by the monitor-detail endpoint"
        )
    result: list[Mapping[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        inverter = row.get("invert_full")
        if isinstance(inverter, Mapping) and str(inverter.get("sn") or "").strip():
            result.append(inverter)
    if not result:
        raise SemsPayloadError(
            "SEMS response contains no usable inverter record; SEMS+ station type 2 "
            "is not yet supported by the monitor-detail endpoint"
        )
    return result


def select_sems_inverter(
    payload: Mapping[str, Any],
    inverter_serial: str | None = None,
) -> Mapping[str, Any]:
    """Select exactly one inverter, rejecting ambiguous multi-inverter plants."""
    candidates = _inverters(_payload_data(payload))
    requested = str(inverter_serial or "").strip()
    if requested:
        for inverter in candidates:
            if str(inverter.get("sn") or "").strip() == requested:
                return inverter
        raise SemsSelectionError(
            f"Configured SEMS inverter serial {requested!r} was not returned by the station"
        )
    if len(candidates) != 1:
        serials = ", ".join(str(item.get("sn")) for item in candidates)
        raise SemsSelectionError(
            "This SEMS station contains multiple inverters; configure one inverter "
            f"serial explicitly ({serials})"
        )
    return candidates[0]


def _sample_timestamp(inverter: Mapping[str, Any]) -> datetime:
    raw = _finite(inverter.get("last_time"))
    if raw is None or raw <= 0:
        raise SemsPayloadError("SEMS inverter sample has no valid last_time timestamp")
    seconds = raw / 1000.0 if raw > 10_000_000_000 else raw
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OSError, OverflowError, ValueError) as err:
        raise SemsPayloadError("SEMS inverter last_time timestamp is invalid") from err


def _put(
    values: dict[str, int | float],
    key: str,
    value: int | float | None,
) -> None:
    if value is not None:
        values[key] = value


def map_sems_telemetry(
    payload: Mapping[str, Any],
    inverter_serial: str | None = None,
    *,
    now: datetime | None = None,
    max_age_seconds: int = SEMS_MAX_SAMPLE_AGE_SECONDS,
) -> SemsMappedTelemetry:
    """Map the evidence-backed SEMS subset to EnergyPilot telemetry keys.

    Cloud energy totals, EMS modes, SOC-floor settings and phase meter currents
    are deliberately not mapped.  Their SEMS meanings or freshness are not a
    safe substitute for the canonical local registers used by EnergyPilot.
    """
    data = _payload_data(payload)
    multi_inverter = len(_inverters(data)) > 1
    inverter = select_sems_inverter(data, inverter_serial)
    serial = str(inverter.get("sn") or "").strip()
    updated_at = _sample_timestamp(inverter)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    age = (current.astimezone(timezone.utc) - updated_at).total_seconds()
    if age > max(1, int(max_age_seconds)):
        raise SemsStaleDataError(
            f"SEMS inverter sample is {int(age)} seconds old; maximum is "
            f"{int(max_age_seconds)} seconds"
        )
    if age < -300:
        raise SemsPayloadError("SEMS inverter sample timestamp is in the future")

    powerflow = data.get("powerflow")
    powerflow = powerflow if isinstance(powerflow, Mapping) else {}
    values: dict[str, int | float] = {}

    # The monitor-detail powerflow object is station-wide. Never combine its
    # aggregates with one explicitly selected inverter at a multi-inverter
    # station; that was a recurring ambiguity in earlier SEMS integrations.
    pv_total = None if multi_inverter else _positive_power(powerflow.get("pv"))
    if pv_total is None:
        pv_total = _positive_power(inverter.get("pv_power"))
    _put(values, "pv_total_power", pv_total)
    for index in range(1, 5):
        _put(
            values,
            f"pv{index}_voltage",
            _bounded(inverter.get(f"vpv{index}"), 0, 1500),
        )
        _put(
            values,
            f"pv{index}_current",
            _bounded(inverter.get(f"ipv{index}"), 0, 200),
        )

    inverter_power = _bounded(inverter.get("pac"), -100_000, 100_000)
    _put(values, "total_inverter_power", inverter_power)
    _put(values, "ac_active_power", inverter_power)
    for index in range(1, 4):
        _put(
            values,
            f"inverter_l{index}_voltage",
            _bounded(inverter.get(f"vac{index}"), 0, 600),
        )
        _put(
            values,
            f"inverter_l{index}_current",
            _bounded(inverter.get(f"iac{index}"), 0, 200),
        )
        _put(
            values,
            f"inverter_l{index}_frequency",
            _bounded(inverter.get(f"fac{index}"), 40, 70),
        )
    _put(
        values,
        "inverter_radiator_temperature",
        _bounded(inverter.get("tempperature"), -50, 200),
    )
    if not multi_inverter:
        _put(values, "total_load_power", _positive_power(powerflow.get("load")))

    meter_power = _bounded(inverter.get("pmeter"), -100_000, 100_000)
    _put(values, "meter_total_power_fast", meter_power)

    if data.get("isShowBattery") is True:
        soc = _bounded(powerflow.get("soc"), 0, 100)
        if soc is None:
            soc = _bounded(inverter.get("soc"), 0, 100)
        _put(values, "battery_soc", soc)
        _put(values, "battery_soh", _bounded(inverter.get("soh"), 0, 100))
        _put(
            values,
            "battery_voltage",
            _bounded(inverter.get("vbattery1"), 0, 1000),
        )
        _put(
            values,
            "battery_current",
            _bounded(inverter.get("ibattery1"), -1000, 1000),
        )
        _put(
            values,
            "bms_max_charge_current",
            _bounded(inverter.get("bms_charge_i_max"), 0, 1000),
        )
        _put(
            values,
            "bms_max_discharge_current",
            _bounded(inverter.get("bms_discharge_i_max"), 0, 1000),
        )

        magnitude = (
            None
            if multi_inverter
            else _positive_power(powerflow.get("bettery"))
        )
        status = (
            None
            if multi_inverter
            else _bounded(powerflow.get("betteryStatus"), -1, 1)
        )
        # SEMS: -1 = discharging, +1 = charging. EnergyPilot intentionally
        # uses the opposite sign: negative = charging, positive = discharging.
        if magnitude is not None and status in (-1, 0, 1):
            if status == 0 and magnitude != 0:
                pass  # inconsistent direction: do not invent a sign
            else:
                battery_power = -float(status) * float(magnitude)
                values["battery_power"] = (
                    int(battery_power)
                    if battery_power.is_integer()
                    else battery_power
                )

    return SemsMappedTelemetry(
        values=values,
        inverter_serial=serial,
        source_updated_at=updated_at,
    )
