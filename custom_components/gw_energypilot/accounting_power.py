"""Pure signed-power integration helpers for EnergyPilot grid accounting."""

from __future__ import annotations

import math

KWH_DIVISOR = 3_600_000.0


def interpolate_power(start_w: float, end_w: float, fraction: float) -> float:
    """Return linearly interpolated power inside one telemetry interval."""
    fraction = min(1.0, max(0.0, float(fraction)))
    return start_w + (end_w - start_w) * fraction


def integrate_signed_power(
    start_w: float,
    end_w: float,
    seconds: float,
) -> tuple[float, float]:
    """Integrate one signed GoodWe grid-power interval into import/export kWh.

    GoodWe meter convention used by EnergyPilot:
      negative power = grid import
      positive power = grid export

    Linear interpolation is used between samples. If the sign changes inside
    the interval, the import and export triangles are integrated separately so
    opposite flows do not cancel each other out.
    """
    try:
        start = float(start_w)
        end = float(end_w)
        duration = float(seconds)
    except (TypeError, ValueError):
        return 0.0, 0.0

    if (
        not math.isfinite(start)
        or not math.isfinite(end)
        or not math.isfinite(duration)
        or duration <= 0
    ):
        return 0.0, 0.0

    if start <= 0 and end <= 0:
        import_kwh = -(start + end) * 0.5 * duration / KWH_DIVISOR
        return max(0.0, import_kwh), 0.0

    if start >= 0 and end >= 0:
        export_kwh = (start + end) * 0.5 * duration / KWH_DIVISOR
        return 0.0, max(0.0, export_kwh)

    crossing_fraction = -start / (end - start)
    before_seconds = duration * crossing_fraction
    after_seconds = duration - before_seconds

    if start < 0:
        import_kwh = (-start) * 0.5 * before_seconds / KWH_DIVISOR
        export_kwh = end * 0.5 * after_seconds / KWH_DIVISOR
    else:
        export_kwh = start * 0.5 * before_seconds / KWH_DIVISOR
        import_kwh = (-end) * 0.5 * after_seconds / KWH_DIVISOR

    return max(0.0, import_kwh), max(0.0, export_kwh)
