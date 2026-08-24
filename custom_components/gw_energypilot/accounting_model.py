"""Pure grid-accounting state model for GW EnergyPilot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import math
from typing import Any, Mapping


ROUND_DIGITS = 6
SOURCE_LEGACY = "legacy_36015_36017"
SOURCE_EXTENDED = "extended_36104_36120"
LEGACY_IMPORT_KEY = "meter_total_energy_import"
LEGACY_EXPORT_KEY = "meter_total_energy_export"
EXTENDED_IMPORT_KEY = "meter_total_energy_import_extended"
EXTENDED_EXPORT_KEY = "meter_total_energy_export_extended"
VALID_SOURCES = {SOURCE_LEGACY, SOURCE_EXTENDED}


def _nonnegative_number(value: Any) -> float | None:
    """Return a finite non-negative float, otherwise None."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def _rounded(value: float) -> float:
    return round(value, ROUND_DIGITS)


def select_meter_totals(
    values: Mapping[str, Any],
    current_source: str | None = None,
) -> tuple[str, float, float] | None:
    """Select one coherent GoodWe lifetime-counter pair for accounting.

    The ETA/ET upstream implementation enables the 64-bit extended meter layout
    for platform 745 and rated power >= 15 kW. Prefer that pair when available.
    Once extended accounting is active, a transient missing optional block must
    not make accounting flap back to the legacy pair; wait for the preferred
    source to return instead.
    """
    extended_import = _nonnegative_number(values.get(EXTENDED_IMPORT_KEY))
    extended_export = _nonnegative_number(values.get(EXTENDED_EXPORT_KEY))
    legacy_import = _nonnegative_number(values.get(LEGACY_IMPORT_KEY))
    legacy_export = _nonnegative_number(values.get(LEGACY_EXPORT_KEY))

    if current_source == SOURCE_EXTENDED:
        if extended_import is None or extended_export is None:
            return None
        return SOURCE_EXTENDED, extended_import, extended_export

    if extended_import is not None and extended_export is not None:
        return SOURCE_EXTENDED, extended_import, extended_export

    if legacy_import is not None and legacy_export is not None:
        return SOURCE_LEGACY, legacy_import, legacy_export

    return None


@dataclass(slots=True)
class GridAccountingState:
    """Persistent EnergyPilot grid-accounting state."""

    day: str | None = None
    today_import_kwh: float = 0.0
    today_export_kwh: float = 0.0
    yesterday_import_kwh: float | None = None
    yesterday_export_kwh: float | None = None
    last_import_total_kwh: float | None = None
    last_export_total_kwh: float | None = None
    source_pair: str | None = None
    bootstrap_complete: bool = False

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> GridAccountingState:
        """Restore state while rejecting invalid persisted values."""
        if not data:
            return cls()

        today_import = _nonnegative_number(data.get("today_import_kwh"))
        today_export = _nonnegative_number(data.get("today_export_kwh"))
        yesterday_import = _nonnegative_number(data.get("yesterday_import_kwh"))
        yesterday_export = _nonnegative_number(data.get("yesterday_export_kwh"))
        last_import = _nonnegative_number(data.get("last_import_total_kwh"))
        last_export = _nonnegative_number(data.get("last_export_total_kwh"))
        stored_day = data.get("day")
        source_pair = data.get("source_pair")

        if stored_day is not None:
            try:
                date.fromisoformat(str(stored_day))
            except ValueError:
                stored_day = None
            else:
                stored_day = str(stored_day)

        if source_pair not in VALID_SOURCES:
            source_pair = None

        return cls(
            day=stored_day,
            today_import_kwh=_rounded(today_import or 0.0),
            today_export_kwh=_rounded(today_export or 0.0),
            yesterday_import_kwh=(
                _rounded(yesterday_import) if yesterday_import is not None else None
            ),
            yesterday_export_kwh=(
                _rounded(yesterday_export) if yesterday_export is not None else None
            ),
            last_import_total_kwh=(
                _rounded(last_import) if last_import is not None else None
            ),
            last_export_total_kwh=(
                _rounded(last_export) if last_export is not None else None
            ),
            source_pair=source_pair,
            bootstrap_complete=bool(data.get("bootstrap_complete", False)),
        )

    def as_dict(self) -> dict[str, Any]:
        """Return JSON-serializable persistent state."""
        return {
            "day": self.day,
            "today_import_kwh": self.today_import_kwh,
            "today_export_kwh": self.today_export_kwh,
            "yesterday_import_kwh": self.yesterday_import_kwh,
            "yesterday_export_kwh": self.yesterday_export_kwh,
            "last_import_total_kwh": self.last_import_total_kwh,
            "last_export_total_kwh": self.last_export_total_kwh,
            "source_pair": self.source_pair,
            "bootstrap_complete": self.bootstrap_complete,
        }


def roll_to_day(state: GridAccountingState, current_day: date) -> bool:
    """Move persisted accounting to current_day without inventing offline deltas."""
    day_text = current_day.isoformat()
    if state.day == day_text:
        return False

    previous_day: date | None = None
    if state.day is not None:
        try:
            previous_day = date.fromisoformat(state.day)
        except ValueError:
            previous_day = None

    if previous_day == current_day - timedelta(days=1):
        state.yesterday_import_kwh = state.today_import_kwh
        state.yesterday_export_kwh = state.today_export_kwh
    else:
        state.yesterday_import_kwh = None
        state.yesterday_export_kwh = None

    state.day = day_text
    state.today_import_kwh = 0.0
    state.today_export_kwh = 0.0
    state.last_import_total_kwh = None
    state.last_export_total_kwh = None
    state.bootstrap_complete = False
    return True


def seed_daily_totals(
    state: GridAccountingState,
    current_day: date,
    *,
    today_import_kwh: float | None,
    today_export_kwh: float | None,
    yesterday_import_kwh: float | None,
    yesterday_export_kwh: float | None,
) -> bool:
    """Seed a new accounting store from trusted Recorder period deltas."""
    today_import = _nonnegative_number(today_import_kwh)
    today_export = _nonnegative_number(today_export_kwh)
    if today_import is None or today_export is None:
        return False

    yesterday_import = _nonnegative_number(yesterday_import_kwh)
    yesterday_export = _nonnegative_number(yesterday_export_kwh)

    state.day = current_day.isoformat()
    state.today_import_kwh = _rounded(today_import)
    state.today_export_kwh = _rounded(today_export)
    state.yesterday_import_kwh = (
        _rounded(yesterday_import) if yesterday_import is not None else None
    )
    state.yesterday_export_kwh = (
        _rounded(yesterday_export) if yesterday_export is not None else None
    )
    state.last_import_total_kwh = None
    state.last_export_total_kwh = None
    state.bootstrap_complete = True
    return True


def _delta(current: float, previous: float | None) -> float:
    if previous is None or current < previous:
        return 0.0
    return current - previous


def apply_meter_totals(
    state: GridAccountingState,
    current_day: date,
    *,
    import_total_kwh: Any,
    export_total_kwh: Any,
    source_pair: str = SOURCE_LEGACY,
) -> bool:
    """Apply one coherent pair of GoodWe lifetime-counter samples."""
    import_total = _nonnegative_number(import_total_kwh)
    export_total = _nonnegative_number(export_total_kwh)
    if import_total is None or export_total is None or source_pair not in VALID_SOURCES:
        return False

    day_text = current_day.isoformat()
    if state.day is None:
        state.day = day_text
        state.source_pair = source_pair
        state.last_import_total_kwh = _rounded(import_total)
        state.last_export_total_kwh = _rounded(export_total)
        return True

    if state.day != day_text:
        try:
            previous_day = date.fromisoformat(state.day)
        except ValueError:
            previous_day = None

        if previous_day == current_day - timedelta(days=1):
            same_source = state.source_pair == source_pair
            import_delta = (
                _delta(import_total, state.last_import_total_kwh) if same_source else 0.0
            )
            export_delta = (
                _delta(export_total, state.last_export_total_kwh) if same_source else 0.0
            )
            state.yesterday_import_kwh = state.today_import_kwh
            state.yesterday_export_kwh = state.today_export_kwh
            state.today_import_kwh = _rounded(import_delta)
            state.today_export_kwh = _rounded(export_delta)
        else:
            state.yesterday_import_kwh = None
            state.yesterday_export_kwh = None
            state.today_import_kwh = 0.0
            state.today_export_kwh = 0.0
            state.bootstrap_complete = False

        state.day = day_text
        state.source_pair = source_pair
        state.last_import_total_kwh = _rounded(import_total)
        state.last_export_total_kwh = _rounded(export_total)
        return True

    if state.source_pair != source_pair:
        state.source_pair = source_pair
        state.last_import_total_kwh = _rounded(import_total)
        state.last_export_total_kwh = _rounded(export_total)
        return True

    import_delta = _delta(import_total, state.last_import_total_kwh)
    export_delta = _delta(export_total, state.last_export_total_kwh)

    state.today_import_kwh = _rounded(state.today_import_kwh + import_delta)
    state.today_export_kwh = _rounded(state.today_export_kwh + export_delta)
    state.last_import_total_kwh = _rounded(import_total)
    state.last_export_total_kwh = _rounded(export_total)
    return import_delta > 0 or export_delta > 0 or not state.bootstrap_complete
