"""Pure price-series helpers for the GW EnergyPilot dashboard."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import math
from typing import Any


def _finite_number(value: Any) -> float | None:
    """Return a finite float while preserving valid negative energy prices."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _timestamp(value: Any) -> float | None:
    """Return an aware ISO timestamp as Unix seconds."""
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.timestamp()


def build_dashboard_price_points(
    load_cost: Mapping[str, Any],
    prod_price: Mapping[str, Any],
    *,
    buy_adder: Any,
    sell_deduction: Any,
) -> list[dict[str, float | str | None]]:
    """Build one sorted market/buy/sell series from EnergyPilot price forecasts.

    ``load_cost`` and ``prod_price`` are the exact effective price maps supplied
    to EMHASS. The market price is reconstructed from those same maps so the
    dashboard never runs a second independent price-source implementation.
    """
    adder = _finite_number(buy_adder) or 0.0
    deduction = _finite_number(sell_deduction) or 0.0
    rows: list[tuple[float, dict[str, float | str | None]]] = []

    for start in set(load_cost) | set(prod_price):
        sort_key = _timestamp(start)
        if sort_key is None:
            continue

        buy = _finite_number(load_cost.get(start))
        sell = _finite_number(prod_price.get(start))
        if buy is None and sell is None:
            continue

        market_candidates: list[float] = []
        if buy is not None:
            market_candidates.append(buy - adder)
        if sell is not None:
            market_candidates.append(sell + deduction)
        market = sum(market_candidates) / len(market_candidates)

        rows.append(
            (
                sort_key,
                {
                    "start": start,
                    "market_price": round(market, 5),
                    "buy_price": round(buy, 5) if buy is not None else None,
                    "sell_price": round(sell, 5) if sell is not None else None,
                },
            )
        )

    rows.sort(key=lambda item: item[0])
    return [row for _, row in rows]
