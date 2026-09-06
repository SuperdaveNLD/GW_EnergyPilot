#!/usr/bin/env python3
"""Preview the Hybrid 2.0 test model; never connect to HA/GoodWe."""

from __future__ import annotations

import argparse
import csv
import importlib
import json
from math import isfinite
from pathlib import Path
import sys
import types


def _mapping_module():
    # Import the pure model without executing the Home Assistant integration.
    name = "_gw_ems_preview"
    package = types.ModuleType(name)
    package.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components" / "gw_energypilot")]
    sys.modules[name] = package
    return importlib.import_module(f"{name}.control_decision")


def _number(value):
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None
    return number if isfinite(number) else None


def _argument_number(value):
    number = _number(value)
    if number is None:
        raise argparse.ArgumentTypeError("Expected a finite number of watts")
    return number


def read_plan(path: Path) -> list[dict]:
    """Read every CSV/TSV row, including an EMHASS pasted results table."""
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    for start, line in enumerate(lines):
        delimiter = "\t" if "\t" in line else ","
        columns = next(csv.reader([line], delimiter=delimiter))
        if {"P_batt", "P_grid"}.issubset(columns):
            break
    else:
        raise ValueError("No EMHASS table with P_batt and P_grid columns found")
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].strip() == "Summary table for latest optimization results"), len(lines))
    rows = list(csv.DictReader(lines[start:end], delimiter=delimiter))
    if not rows:
        raise ValueError("The plan has no rows")
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("Malformed plan row; no rows were silently discarded")
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, help="EMHASS CSV/TSV or pasted results text; includes every row")
    parser.add_argument("--p-batt", type=_argument_number)
    parser.add_argument("--p-grid", type=_argument_number)
    parser.add_argument("--battery-deadband", type=_argument_number, default=100)
    parser.add_argument("--grid-deadband", type=_argument_number, default=1000)
    parser.add_argument("--max-power", type=_argument_number, default=15000)
    parser.add_argument("--pause", action="store_true", help="Explicit battery pause, independent of P_batt")
    parser.add_argument("--ev-active", action="store_true", help="Hypothetical EV-active scenario for every row")
    parser.add_argument("--ev-power", type=_argument_number, help="Measured/hypothetical EV watts; never inferred from a forecast")
    parser.add_argument("--load-power", type=_argument_number, help="Measured/hypothetical 35172 watts; never uses forecast P_Load")
    args = parser.parse_args(argv)
    if min(args.battery_deadband, args.grid_deadband, args.max_power) < 0:
        parser.error("Deadbands and maximum power must be non-negative")
    if args.plan and (args.p_batt is not None or args.p_grid is not None):
        parser.error("Use either --plan or a single --p-batt/--p-grid pair")
    if not args.plan and not args.pause and (args.p_batt is None or args.p_grid is None):
        parser.error("Supply --plan, --pause, or both --p-batt and --p-grid")
    try:
        rows = read_plan(args.plan) if args.plan else [{"P_batt": args.p_batt, "P_grid": args.p_grid}]
    except (OSError, ValueError, csv.Error) as err:
        parser.error(str(err))
    module = _mapping_module()
    results = []
    for row in rows:
        battery, grid = _number(row["P_batt"]), _number(row["P_grid"])
        shared = dict(p_batt=battery, p_grid=grid, battery_deadband=args.battery_deadband,
                      grid_deadband=args.grid_deadband, max_power=int(args.max_power),
                      ev_active=args.ev_active, ev_power_w=args.ev_power)
        proposed = module.preview_hybrid_mapping(
            **shared, explicit_pause=args.pause, load_power_w=args.load_power,
        )
        results.append({
            "time": row.get("index") or row.get("timestamp"),
            "p_batt_w": battery, "p_grid_w": grid,
            "proposed": proposed.as_dict(),
        })
    print(json.dumps({
        "preview_only": True, "row_count": len(results),
        "ev_scenario": "assumed_active_for_all_rows" if args.ev_active else "inactive",
        "rows": results,
    }, ensure_ascii=False, allow_nan=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
