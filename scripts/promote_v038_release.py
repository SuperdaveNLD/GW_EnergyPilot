#!/usr/bin/env python3
"""Promote the tested v0.38 frontend candidate to release metadata.

Temporary release-preparation helper. It is removed before merge.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_required(content: str, old: str, new: str, path: str) -> str:
    if new in content:
        return content
    if old not in content:
        raise RuntimeError(f"Expected marker missing in {path}: {old!r}")
    return content.replace(old, new, 1)


def promote_runtime() -> None:
    path = "custom_components/gw_energypilot/frontend/gw-energy-pilot-v038-runtime.js"
    content = read(path)
    content = replace_required(
        content,
        'const VERSION = "0.37";',
        'const VERSION = "0.38";',
        path,
    )
    write(path, content)


def promote_control_doc() -> None:
    path = "docs/FRONTEND_CONTROL_REBUILD.md"
    content = read(path)
    old = (
        "This document describes the **v0.38 frontend field-test candidate** built on the released v0.37 backend and control behavior. "
        "The candidate deliberately keeps the integration manifest at `0.37` until it has been tested on installations that reproduced the failure. "
        "It must not be presented as a validated v0.38 release before that field test succeeds."
    )
    new = (
        "This document describes the **v0.38 Beta release** frontend control and live-flow architecture. "
        "It replaces the released v0.37 presentation stack while keeping the existing GoodWe, EMS and EMHASS backend/control behavior unchanged. "
        "The rebuilt controls are covered by executable English/Dutch delegated-click tests and explicit physical flow-direction tests in the normal Quality workflow."
    )
    content = replace_required(content, old, new, path)
    content = content.replace(
        "The field-test candidate no longer derives visible movement",
        "v0.38 no longer derives visible movement",
    )
    content = content.replace(
        "GitHub-hosted Quality, HACS and Hassfest runs are still required before merge. Connector-authored commits do not currently have a workflow run attached, so this draft must not be promoted on the local checks alone.",
        "GitHub-hosted Quality, HACS and Hassfest runs are mandatory release gates. The release is merged only after those checks pass on the final v0.38 head.",
    )
    content = content.replace(
        "## Field-test matrix\n\nBefore release promotion, validate at least:",
        "## Multi-installation field-validation matrix\n\nAfter automated release gates, continue validating:",
    )
    write(path, content)


def promote_changelog() -> None:
    path = "CHANGELOG.md"
    content = read(path)
    if "## [0.38] - 2026-08-26" in content:
        return
    marker = "# Changelog\n\nAll notable changes to GW EnergyPilot are documented here.\n\n"
    if not content.startswith(marker):
        raise RuntimeError("Unexpected CHANGELOG.md header")
    section = """## [0.38] - 2026-08-26

### Fixed

- Rebuilt Battery Strategy controls around stable backend profile keys and `aria-pressed`; visible English/Dutch text no longer participates in action identity or active highlighting.
- Removed the v0.35 pointer/render lock and v0.36.3 old-button DOM-node reuse from the fresh active frontend chain instead of stacking another stability patch over v0.37.
- Replaced per-node strategy actions with one delegated listener on the persistent ShadowRoot, preventing stale listeners from being transplanted into a newly rendered dashboard.
- Added bounded pointer/keyboard completion and preserved native touch scrolling/mobile scroll restoration without pointer capture.
- Replaced stacked live-flow `inbound`/`outbound` and `animation-direction` reversal interactions with one explicit physical v0.38 motion mapping and dedicated keyframes.

### Changed

- Added the isolated `gw-energy-pilot-v038-*` frontend modules for model/localization, strategy controls, styles and runtime rendering.
- Added executable Node.js regression tests to the normal Quality workflow for Dutch/English canonical profile keys, delegated profile clicks, immediate control re-enable behavior and all physical PV/grid/house/battery flow cases.
- Fresh v0.38 sessions load the v0.38 runtime directly over the known v0.34 feature base. Historical v0.35/v0.36.x/v0.37 wrapper files remain in the repository but are not part of the fresh v0.38 active path.
- Added dedicated frontend architecture and v0.38 release documentation.

### Safety / compatibility

- Frontend-only release; no GoodWe register definitions or Modbus read blocks change.
- No EMS mode mapping, setpoint semantics or `47512 -> wait -> 47511` write ordering change.
- No Automatic Control decision or EMHASS optimization/Battery Saver backend/configuration ownership behavior change.
- No entity IDs, unique IDs, config-entry data, persistent Store keys or stable device identity changes.

"""
    write(path, marker + section + content[len(marker) :])


def promote_release_index() -> None:
    path = "docs/RELEASE_NOTES.md"
    content = read(path)
    row = "| **0.38** | 2026-08-26 | **Beta** | Rebuilds dashboard controls around language-independent mode keys/delegated actions and makes live-flow direction a single explicit physical mapping, replacing the v0.37 stale-button-node stabilization path. |\n"
    if "| **0.38** |" not in content:
        marker = "|---|---|---|---|\n"
        if marker not in content:
            raise RuntimeError("Release table marker missing")
        content = content.replace(marker, marker + row, 1)

    if "# v0.38 —" not in content:
        marker = "# v0.37 — Clean stable-control release"
        if marker not in content:
            raise RuntimeError("v0.37 release section marker missing")
        section = """# v0.38 — Rebuilt controls and canonical live-flow direction

v0.38 replaces the v0.37 dashboard-control stabilization approach instead of adding another monkey-patch layer. Fresh sessions load the new v0.38 runtime directly over the v0.34 feature base and therefore do not execute the v0.35 pointer/render lock or v0.36.3 old-button-node reuse.

Battery Strategy actions use stable backend mode keys (`mad_steve`, `gold_rush`, `balanced`, `battery_saver`, `custom`) and selected/highlight state uses `aria-pressed`. English/Dutch labels and descriptions are presentation only. A delegated ShadowRoot listener executes the existing Battery Saver API, so translated text and stale per-node listener closures cannot define control behavior.

Live-flow animation has one final physical owner: PV production flows to the hub, grid import to the hub, grid export away from the hub, house load away from the hub, battery discharge to the hub and battery charge away from the hub. Explicit geometry keyframes are selected from that mapping with normal animation direction, preventing older reversal rules from reinterpreting the final result.

Quality now executes JavaScript syntax checks plus Node regression tests for localization/profile identity, delegated clicks, control re-enable behavior and physical flow mapping, alongside the full Python unit suite and repository validator. HACS and Hassfest remain release gates.

No GoodWe register, Modbus, EMS, Automatic Control, EMHASS backend, entity-ID or persistent-state contract changes.

See `docs/RELEASE_NOTES_V038.md` and `docs/FRONTEND_CONTROL_REBUILD.md`.

"""
        content = content.replace(marker, section + marker, 1)
    write(path, content)


def promote_readme() -> None:
    path = "README.md"
    content = read(path)
    content = content.replace("**v0.35 · Beta**", "**v0.38 · Beta**", 1)

    if "`docs/RELEASE_NOTES_V038.md`" not in content:
        marker = "- `docs/RELEASE_NOTES.md` — current release index and Beta scope;\n"
        if marker not in content:
            raise RuntimeError("README release-doc marker missing")
        content = content.replace(
            marker,
            marker
            + "- `docs/RELEASE_NOTES_V038.md` — v0.38 rebuilt controls and canonical live-flow direction;\n"
            + "- `docs/FRONTEND_CONTROL_REBUILD.md` — frontend action/highlight/flow ownership;\n",
            1,
        )

    if "## v0.38 highlights" not in content:
        marker = "## v0.35 highlights\n"
        if marker not in content:
            raise RuntimeError("README v0.35 highlights marker missing")
        highlights = """## v0.38 highlights

- Battery Strategy actions and active highlighting use stable backend keys, not translated English/Dutch button text.
- Fresh v0.38 sessions skip the v0.35 pointer/render lock and v0.36.3 old-button-node reuse that caused unusable controls on some installations.
- One delegated strategy listener handles fresh rendered controls; executable tests verify the intended mode is called exactly once and buttons re-enable after completion.
- Live-flow particles use one explicit physical mapping for PV production, grid import/export, house load and battery charge/discharge.
- Mobile native scrolling, relevant-state render filtering and existing v0.34 dashboard features are retained.
- No GoodWe register, Modbus, EMS or EMHASS backend control semantics change in v0.38.

"""
        content = content.replace(marker, highlights + marker, 1)
    write(path, content)


def promote_agent_version() -> None:
    path = "AGENTS.md"
    content = read(path)
    content = content.replace("v0.35 Beta", "v0.38 Beta", 1)
    write(path, content)


def promote_architecture() -> None:
    path = "docs/ARCHITECTURE.md"
    content = read(path)
    content = content.replace(
        "current runtime architecture of **GW EnergyPilot v0.35 Beta**",
        "current runtime architecture of **GW EnergyPilot v0.38 Beta**",
        1,
    )
    old = """## Frontend

Active top-level module:

```text
gw-energy-pilot-v035.js
    -> gw-energy-pilot-v034.js
        -> gw-energy-pilot-v031-battery-saver.js
            -> gw-energy-pilot-v031-window-controls.js
                -> gw-energy-pilot-v031.js
                    -> gw-energy-pilot-v030.js
                        -> existing v0.29/v0.28/v0.27/... chain
        -> gw-energy-pilot-v027-battery-plan-core.js (v0.34 behavior retained)
```

The v0.35 wrapper is release/version presentation only. It carries forward the v0.34 Battery Saver and revision-aware Battery Plan frontend behavior without adding another behavioral monkey patch.

This layering remains technical debt: future releases should avoid adding behavioral monkey-patch layers where a bounded backend/module change is sufficient. A frontend consolidation must preserve behavior under browser/regression tests before historical assets are removed.
"""
    new = """## Frontend

Active top-level module:

```text
gw-energy-pilot-v038.js
    -> gw-energy-pilot-v038-runtime.js
        -> gw-energy-pilot-v034.js
            -> existing v0.34 feature chain
```

v0.38 deliberately bypasses the historical v0.35/v0.36.x/v0.37 stability wrappers in a fresh browser session. Their files remain for release history, but the v0.35 pointer/render lock and v0.36.3 old-button-node reuse are no longer active owners.

The v0.38 frontend is split by responsibility: `gw-energy-pilot-v038-model.js` owns pure localization/profile/physical-flow models, `gw-energy-pilot-v038-strategy.js` owns key-based delegated Battery Strategy actions and active state, `gw-energy-pilot-v038-styles.js` owns final control/particle presentation, and `gw-energy-pilot-v038-runtime.js` owns relevant-state rendering, interaction completion, scroll stability and applying physical flow motion to the live DOM.

Visible/translated text is never a control identity. Canonical profile keys plus `aria-pressed` define action and selected state. Live-flow direction is likewise single-owner through explicit physical motion instead of accumulated animation reversals. See `docs/FRONTEND_CONTROL_REBUILD.md`.

Historical frontend layering remains technical debt below the v0.34 base. Further consolidation must preserve behavior under executable browser/model regression tests before historical assets are removed.
"""
    if new not in content:
        if old not in content:
            raise RuntimeError("Expected old frontend architecture block missing")
        content = content.replace(old, new, 1)
    write(path, content)


def main() -> None:
    promote_runtime()
    promote_control_doc()
    promote_changelog()
    promote_release_index()
    promote_readme()
    promote_agent_version()
    promote_architecture()


if __name__ == "__main__":
    main()
