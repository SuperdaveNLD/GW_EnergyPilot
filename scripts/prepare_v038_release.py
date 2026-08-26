#!/usr/bin/env python3
"""Prepare v0.38 release metadata without rewriting historical documentation."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def insert_once(content: str, marker: str, insertion: str, identity: str) -> str:
    if identity in content:
        return content
    if marker not in content:
        raise RuntimeError(f"Marker not found for {identity!r}: {marker!r}")
    return content.replace(marker, marker + insertion, 1)


def prepare_changelog() -> None:
    path = "CHANGELOG.md"
    content = read(path)
    header = "# Changelog\n\nAll notable changes to GW EnergyPilot are documented here.\n\n"
    section = """## [0.38] - 2026-08-26

### Fixed

- Replaced the active v0.37 equivalent-button DOM-node reuse. Fresh renders now keep fresh button nodes/listeners instead of reinserting old translated controls after the dashboard rebuilds.
- Rebuilt Battery Strategy actions and active highlighting around stable backend mode keys plus `aria-pressed`; English/Dutch labels and descriptions are presentation only and no longer participate in control identity.
- Removed the v0.35 pointer-capture/render-lock stack from the fresh v0.38 active import chain. A short 300 ms render quiet window delays only HASS-triggered telemetry rebuilds after a press and does not block native click/service behavior.
- Replaced inherited live-flow reversal layers with one final semantic mapping and explicit v0.38 geometry keyframes: PV to hub, grid import to hub, grid export from hub, hub to house, battery discharge to hub and battery charge from hub.

### Changed

- Added `gw-energy-pilot-v038.js` as a consolidated post-v0.34 frontend layer. Fresh v0.38 sessions no longer import the historical v0.35/v0.36.x/v0.37 stabilization wrappers.
- Retained relevant Home Assistant state filtering with 80 ms batching and consolidated the v0.36.2 mobile scroll-position protection into the v0.38 layer.
- Added compatibility handling for an already-open browser realm that previously executed v0.37 so the historical v0.36.3 layer cannot restore stale button nodes during the transition.
- Added dedicated regression coverage and `docs/FRONTEND_V038.md` for language-independent control identity and canonical flow-direction ownership.

### Safety / compatibility

- Frontend-only release; no GoodWe register definitions or Modbus read blocks change.
- No EMS mode mapping, setpoint semantics or `47512 -> wait -> 47511` write ordering change.
- No Automatic Control or EMHASS optimization/Battery Saver backend behavior changes.
- No entity IDs, unique IDs, config-entry data, persistent Store keys or stable device identity changes.

"""
    if "## [0.38] - 2026-08-26" not in content:
        if not content.startswith(header):
            raise RuntimeError("Unexpected CHANGELOG.md header")
        content = header + section + content[len(header) :]
        write(path, content)


def prepare_release_index() -> None:
    path = "docs/RELEASE_NOTES.md"
    content = read(path)
    row = "| **0.38** | 2026-08-26 | **Beta** | Rebuilds dashboard controls around language-independent mode keys and delegated actions, removes stale button-node/pointer-lock behavior from the fresh active path, and makes live-flow direction a single canonical v0.38 mapping. |\n"
    content = insert_once(
        content,
        "|---|---|---|---|\n",
        row,
        "| **0.38** |",
    )

    section = """# v0.38 — Rebuilt controls and canonical live-flow direction

v0.38 replaces the v0.37 dashboard-control stabilization approach instead of stacking another fix on top of it. A fresh session now loads `gw-energy-pilot-v038.js` directly over the v0.34 chain; the v0.35 pointer/render lock and v0.36.3 old-button-node reuse are historical files and are no longer in the fresh active import path.

Battery Strategy actions use stable backend keys (`mad_steve`, `gold_rush`, `balanced`, `battery_saver`, `custom`) and selected state uses `aria-pressed`. Dutch/English labels and descriptions are presentation only. Actions are delegated from the persistent ShadowRoot, so translated text, button order and old per-node listener closures cannot define behavior.

Relevant Home Assistant state filtering remains and batches relevant bursts for 80 ms. A short 300 ms press quiet window only postpones a telemetry-triggered render; it does not pointer-capture, prevent the click, stop propagation or block explicit action renders. Mobile scroll-position preservation is consolidated into the same v0.38 layer.

Live-flow animation also gets one final owner: PV production flows to the hub, grid import to the hub, grid export from the hub, house load from the hub, battery discharge to the hub and battery charge from the hub. Explicit v0.38 geometry keyframes are selected from this semantic mapping with `animation-direction: normal`, so inherited reversal rules cannot reinterpret the final direction.

No GoodWe register, Modbus, EMS, Automatic Control, EMHASS backend, entity-ID or persistence contract changes.

See `docs/RELEASE_NOTES_V038.md` and `docs/FRONTEND_V038.md`.

"""
    if "# v0.38 —" not in content:
        marker = "# v0.37 —"
        if marker not in content:
            raise RuntimeError("v0.37 section marker missing from release index")
        content = content.replace(marker, section + marker, 1)
    write(path, content)


def prepare_readme() -> None:
    path = "README.md"
    content = read(path)
    content = content.replace("**v0.35 · Beta**", "**v0.38 · Beta**", 1)
    if "`docs/RELEASE_NOTES_V038.md`" not in content:
        marker = "- `docs/RELEASE_NOTES.md` — current release index and Beta scope;\n"
        insertion = "- `docs/RELEASE_NOTES_V038.md` — v0.38 rebuilt control path and canonical live-flow direction;\n"
        content = insert_once(content, marker, insertion, "`docs/RELEASE_NOTES_V038.md`")
    if "## v0.38 highlights" not in content:
        marker = "## v0.35 highlights\n"
        highlights = """## v0.38 highlights

- Battery Strategy buttons use stable backend mode keys for actions and `aria-pressed` for selected/highlight state; translated labels no longer affect behavior.
- Fresh v0.38 sessions skip the v0.35 pointer/render lock and v0.36.3 old-button-node reuse layers.
- Relevant-state render filtering and mobile scroll preservation remain, without pointer capture or blocking native click behavior.
- Live-flow direction is owned by one final mapping: PV/grid import/battery discharge flow toward the hub; grid export/house load/battery charge flow away from it.
- v0.38 is frontend-only and does not change GoodWe, Modbus, EMS or EMHASS backend control semantics.

"""
        if marker not in content:
            raise RuntimeError("README highlight marker missing")
        content = content.replace(marker, highlights + marker, 1)
    write(path, content)


def prepare_small_version_docs() -> None:
    replacements = {
        "AGENTS.md": ("v0.35 Beta", "v0.38 Beta"),
        "docs/ARCHITECTURE.md": (
            "GW EnergyPilot v0.35 Beta",
            "GW EnergyPilot v0.38 Beta",
        ),
    }
    for path, (old, new) in replacements.items():
        content = read(path)
        if new not in content:
            if old not in content:
                raise RuntimeError(f"Expected version marker missing in {path}")
            content = content.replace(old, new, 1)
            write(path, content)


if __name__ == "__main__":
    prepare_changelog()
    prepare_release_index()
    prepare_readme()
    prepare_small_version_docs()
