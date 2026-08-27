#!/usr/bin/env python3
"""Prepare the v0.41 release wiring and existing documentation in place."""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def replace_once(path: Path, old: str, new: str) -> None:
    text = read(path)
    if new in text and old not in text:
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"Expected exactly one occurrence in {path}: {old!r}; found {count}"
        )
    write(path, text.replace(old, new, 1))


def insert_before(path: Path, marker: str, block: str, sentinel: str) -> None:
    text = read(path)
    if sentinel in text:
        return
    if marker not in text:
        raise SystemExit(f"Marker not found in {path}: {marker!r}")
    clean = dedent(block).strip()
    write(path, text.replace(marker, clean + "\n\n" + marker, 1))


def update_frontend_wiring() -> None:
    replace_once(
        INTEGRATION / "__init__.py",
        'PANEL_MODULE = f"{STATIC_URL}/gw-energy-pilot-v040.js?v=0.40-mobile-scroll1"',
        'PANEL_MODULE = f"{STATIC_URL}/gw-energy-pilot-v041.js?v=0.41-stable1"',
    )
    replace_once(
        FRONTEND / "gw-energy-pilot-v039.js",
        'import "./gw-energy-pilot-v038.js?v=0.40-mobile-scroll1";',
        'import "./gw-energy-pilot-v038.js?v=0.41-stable1";',
    )
    replace_once(
        FRONTEND / "gw-energy-pilot-v038.js",
        'import "./gw-energy-pilot-v038-runtime.js?v=0.40-mobile-scroll1";',
        'import "./gw-energy-pilot-v038-runtime.js?v=0.41-stable1";',
    )
    replace_once(
        FRONTEND / "gw-energy-pilot-v038-runtime.js",
        '} from "./gw-energy-pilot-v038-strategy.js?v=0.38-strategy3";',
        '} from "./gw-energy-pilot-v038-strategy.js?v=0.41-stable1";',
    )
    replace_once(
        FRONTEND / "gw-energy-pilot-v041.js",
        'import "./gw-energy-pilot-v039.js?v=0.41-stable-dom2";',
        'import "./gw-energy-pilot-v039.js?v=0.41-stable1";',
    )
    replace_once(
        FRONTEND / "gw-energy-pilot-v041.js",
        'import { loadChartData } from "./gw-energy-pilot-v027-battery-plan-data.js?v=0.28-chart1";',
        'import { loadChartData } from "./gw-energy-pilot-v027-battery-plan-data.js?v=0.41-stable1";',
    )
    replace_once(
        FRONTEND / "gw-energy-pilot-v041.js",
        'import { refreshBatteryPlanCard } from "./gw-energy-pilot-v027-battery-plan-core.js?v=0.34-planrefresh1";',
        'import { refreshBatteryPlanCard } from "./gw-energy-pilot-v027-battery-plan-core.js?v=0.41-stable1";',
    )
    replace_once(
        FRONTEND / "gw-energy-pilot-v027-battery-plan-core.js",
        '} from "./gw-energy-pilot-v027-battery-plan-data.js?v=0.28-chart1";',
        '} from "./gw-energy-pilot-v027-battery-plan-data.js?v=0.41-stable1";',
    )
    (FRONTEND / "gw-energy-pilot-v041-release.js").unlink(missing_ok=True)


def update_manifest() -> None:
    path = INTEGRATION / "manifest.json"
    manifest = json.loads(read(path))
    version = manifest.get("version")
    if version not in {"0.40", "0.41"}:
        raise SystemExit(f"Unexpected manifest version: {version!r}")
    manifest["version"] = "0.41"
    write(path, json.dumps(manifest, indent=2, ensure_ascii=False))


def update_changelog() -> None:
    insert_before(
        ROOT / "CHANGELOG.md",
        "## [0.40] - 2026-08-26",
        """
        ## [0.41] - 2026-08-27

        ### Fixed

        - Replaced normal telemetry-driven full ShadowRoot rebuilds with in-place updates of existing dashboard values, classes, attributes and meter widths, so the page, buttons and scroll container remain stable while GoodWe and EMHASS states change.
        - Removed the inherited v0.38 pointer/render guard and mobile scroll snapshot restoration from the active v0.41 telemetry path. Native browser/WebView scrolling now owns the viewport without delayed EnergyPilot writes of an older `scrollTop`.
        - Scoped Battery Strategy loading/apply feedback to the strategy section and scoped Battery · Plan · Price updates to the graph card, preventing either action from rebuilding unrelated controls.
        - Fixed re-entrant graph refresh while a plan request is starting by treating both the loading flag and active promise as one busy state.
        - Disabled EnergyPilot animations, transitions, moving flow particles and modal backdrop filters in v0.41, including pseudo-elements and late-added graph/modal content.

        ### Changed

        - Added `gw-energy-pilot-v041.js` as the active frontend entrypoint with a stable-DOM telemetry contract.
        - Limited complete structural renders to first initialization and genuine context/structure changes such as language, user/theme, entity-registry or optional-card topology changes.
        - Added fresh nested module cache keys for every modified runtime, strategy and graph module so a v0.40 browser cache cannot retain an older implementation after upgrade.
        - Added deterministic real-browser regressions for desktop Chromium, iPad WebKit touch and iPhone WebKit touch.
        - Added `docs/FRONTEND_STABLE_DOM.md` as the persistent frontend architecture decision.

        ### Validation

        - Desktop Chromium: 1440 × 900.
        - iPad WebKit touch profile: 834 × 1112.
        - iPhone WebKit touch profile: 390 × 844.
        - The matrix verifies stable DOM identity during telemetry, monotonic scrolling, zero idle scroll drift, menu open/close, two Automatic Control toggles, Battery Strategy apply, graph-only plan refresh, Dutch structural localization, controls after a deliberate structural render, zero active EnergyPilot animations/transitions, no JavaScript errors and no unknown WebSocket calls.
        - Full Python/Node Quality suite, repository validator, frontend architecture audit, HACS validation and Hassfest validation remain required gates.

        ### Safety and compatibility

        - No GoodWe register, Modbus read block, EMS mode/setpoint/write order, Automatic Control decision, EMHASS optimization/configuration ownership, entity ID, unique ID, config-entry data, persistent Store key or stable device identity changes.
        - v0.38-v0.40 compatibility behavior remains available in its historical modules; only the active v0.41 runtime bypasses their legacy interaction and scroll-restoration guards.
        """,
        "## [0.41] - 2026-08-27",
    )


def update_release_index() -> None:
    path = ROOT / "docs" / "RELEASE_NOTES.md"
    insert_before(
        path,
        "| **0.40** | 2026-08-26 | **Beta** |",
        """
        | **0.41** | 2026-08-27 | **Beta** | Replaces normal telemetry full renders with stable in-place DOM updates, targeted plan/strategy refreshes, native touch scrolling and a no-motion dashboard validated in Chromium and WebKit desktop/iPad/iPhone profiles. |
        """,
        "| **0.41** | 2026-08-27 |",
    )
    insert_before(
        path,
        "# v0.40 — Stable dashboard and menu controls across full renders",
        """
        # v0.41 — Stable DOM and native mobile scrolling

        v0.41 replaces the active dashboard's normal telemetry-driven full ShadowRoot rebuild with in-place updates of the existing DOM. Live values, status classes, labels, diagnostics and meter widths still follow current Home Assistant state, but the page, layout menu, Automatic Control button and Battery Strategy controls are not detached during an ordinary GoodWe/EMHASS refresh.

        Battery Strategy feedback is updated inside the strategy section and a new EMHASS plan refresh replaces only the Battery · Plan · Price card. Genuine structure changes — first initialization, language/user/theme changes, entity-registry changes and optional-card topology changes — still use a complete render. The active v0.41 path no longer writes saved scroll positions back into the Home Assistant scroll container and does not use the inherited v0.38 pointer/render guard.

        EnergyPilot motion is deliberately disabled in this release: no moving flow particles, CSS animations, CSS transitions or modal backdrop filters remain active. This is a reliability decision, not a presentation fallback.

        The candidate was exercised with a deterministic Playwright matrix using desktop Chromium plus WebKit touch profiles at iPad and iPhone dimensions. The matrix verifies scroll movement, stable control identity, menu operation, Automatic Control, Battery Strategy, graph-only plan refresh, Dutch localization, deliberate structural rerender recovery, zero active motion and clean JavaScript/WebSocket diagnostics. Physical-device/firmware diversity remains Beta field scope.

        No GoodWe, Modbus, EMS, Automatic Control, EMHASS backend, entity identity or persistent-state contract changes.

        See `docs/RELEASE_NOTES_V041.md` and `docs/FRONTEND_STABLE_DOM.md`.
        """,
        "# v0.41 — Stable DOM and native mobile scrolling",
    )


def update_readme() -> None:
    path = ROOT / "README.md"
    replace_once(path, "**v0.40 · Beta**", "**v0.41 · Beta**")
    insert_before(
        path,
        "- `docs/RELEASE_NOTES_V040.md` — v0.40 stable dashboard/menu controls across full renders;",
        """
        - `docs/RELEASE_NOTES_V041.md` — v0.41 stable DOM, native scrolling and no-motion dashboard;
        - `docs/FRONTEND_STABLE_DOM.md` — structural-render, telemetry-patch, interaction and browser-regression contract;
        """,
        "`docs/RELEASE_NOTES_V041.md`",
    )
    insert_before(
        path,
        "## v0.40 highlights",
        """
        ## v0.41 highlights

        - Normal GoodWe and EMHASS telemetry updates mutate the existing dashboard DOM instead of rebuilding the complete ShadowRoot, preserving button identity, focus, hover and the Home Assistant scroll container.
        - Battery Strategy and Battery · Plan · Price refreshes are scoped to their own sections/cards; a fresh optimization no longer rebuilds unrelated controls.
        - The active v0.41 path removes inherited pointer/render guarding and delayed mobile scroll restoration, leaving vertical pan and momentum scrolling under native browser/WebView ownership.
        - All EnergyPilot animations, transitions, flow particles and modal backdrop filters are intentionally disabled for deterministic desktop, iPad and iPhone behavior.
        - Real-browser CI covers desktop Chromium, iPad WebKit touch and iPhone WebKit touch, including telemetry during scrolling, menu/buttons, plan refresh, Dutch localization and deliberate structural rerender recovery.
        - No GoodWe register, Modbus, EMS, Automatic Control or EMHASS backend semantics change.
        """,
        "## v0.41 highlights",
    )


def update_agent_contract() -> None:
    path = ROOT / "AGENTS.md"
    replace_once(
        path,
        "The current release is **v0.40 Beta**.",
        "The current release is **v0.41 Beta**.",
    )
    insert_before(
        path,
        "## Purpose",
        """
        ## Frontend stability contract (v0.41)

        - Normal Home Assistant telemetry updates must patch the existing dashboard DOM; they must not replace `main`, controls, cards or the ShadowRoot.
        - A complete structural render is reserved for first initialization and genuine context/structure changes: language/user/theme, entity registry or optional-card topology.
        - The active v0.41 telemetry path must not write `scrollTop` or `scrollLeft`, capture touch pointers, cancel native vertical gestures or use a hover/render lock.
        - Battery Strategy feedback must remain scoped to `.ep-v038-strategy`; plan changes must remain scoped to the Battery · Plan · Price card.
        - EnergyPilot animations, transitions, moving particle layers and modal backdrop filters remain disabled unless a later release introduces a separately proven, browser-tested motion contract.
        - Every frontend change affecting rendering, interaction or CSS must pass desktop Chromium, iPad WebKit touch and iPhone WebKit touch regressions before release.
        - `docs/FRONTEND_STABLE_DOM.md` is the canonical architecture decision for this contract.
        """,
        "## Frontend stability contract (v0.41)",
    )


def update_control_rebuild_note() -> None:
    insert_before(
        ROOT / "docs" / "FRONTEND_CONTROL_REBUILD.md",
        "## v0.40 render-settle follow-up",
        """
        > **v0.41 supersession:** the v0.38-v0.40 control/scroll mechanisms below remain historical compatibility behavior, but the active v0.41 runtime no longer uses a complete render for ordinary telemetry. It patches stable DOM nodes in place, scopes strategy/graph refreshes and disables EnergyPilot motion. See `docs/FRONTEND_STABLE_DOM.md`.
        """,
        "**v0.41 supersession:**",
    )


def write_release_documents() -> None:
    write(
        ROOT / "docs" / "RELEASE_NOTES_V041.md",
        dedent(
            """
            # GW EnergyPilot v0.41 Beta

            v0.41 is the frontend stability release requested after repeated mobile scroll and control failures. It changes the active dashboard render architecture rather than adding another visual or pointer patch.

            ## Operator-visible behavior

            - The dashboard remains scrollable while GoodWe and EMHASS telemetry updates arrive.
            - The Dashboard menu, Automatic Control button and Battery Strategy buttons keep the same DOM identity during ordinary telemetry updates.
            - Selecting a Battery Strategy updates only the strategy section while the existing Battery Saver API applies the mode and starts the established optimization/publish transaction.
            - A changed EMHASS plan refreshes only the Battery · Plan · Price card. The rest of the dashboard is not rebuilt.
            - EnergyPilot animations, transitions, moving flow particles and modal backdrop filters are disabled. Static direction/state labels remain available.

            ## Stable-DOM architecture

            The active entrypoint is `gw-energy-pilot-v041.js`.

            Normal telemetry follows this path:

            1. accept the new Home Assistant `hass` object;
            2. compare context and structural signatures;
            3. when structure is unchanged, batch a small live patch;
            4. update existing text, classes, attributes, slider values, status pills, diagnostics and meter widths;
            5. leave `main`, cards and interactive controls connected.

            A full render remains valid only for:

            - first panel initialization;
            - Home Assistant language, user or theme changes;
            - entity-registry changes;
            - optional-card topology changes, such as PV4 becoming structurally present/absent;
            - an explicit layout/narrow-mode structural change.

            The inherited v0.38 pointer/render guard and mobile scroll snapshot restoration remain available to historical v0.38-v0.40 entrypoints. The active v0.41 runtime explicitly bypasses them. It does not write an old `scrollTop` back during a pan or momentum scroll.

            ## Scoped refresh ownership

            ### Battery Strategy

            `gw-energy-pilot-v038-strategy.js` uses a v0.41 callback to rerender only `.ep-v038-strategy` for loading, pending, success/error and Custom-SOC feedback. Older entrypoints retain the existing full-render fallback.

            ### Battery · Plan · Price

            `gw-energy-pilot-v027-battery-plan-data.js` and `gw-energy-pilot-v027-battery-plan-core.js` expose a targeted graph-card refresh. A loading flag and active-promise check form one busy state, preventing re-entrant refresh while a request is being registered.

            ## Motion policy

            v0.41 intentionally enforces a no-motion dashboard:

            - zero active EnergyPilot CSS animations;
            - zero active EnergyPilot CSS transitions;
            - no moving flow particle layers;
            - no animated pseudo-elements;
            - no modal backdrop filters;
            - `scroll-behavior: auto` for EnergyPilot-owned content.

            This policy is applied to initial content and late-added strategy, graph and modal content.

            ## Browser validation

            The release matrix runs the exact v0.41 entrypoint in real browser engines:

            | Profile | Engine | Viewport / input |
            |---|---|---|
            | Desktop | Chromium | 1440 × 900, mouse/keyboard |
            | iPad | WebKit | 834 × 1112, mobile + touch |
            | iPhone | WebKit | 390 × 844, mobile + touch |

            Each profile verifies scroll range, idle scroll stability, monotonic telemetry scrolling, stable control identity, menu open/close, Automatic Control OFF/ON, Battery Strategy apply, graph-only plan refresh, Dutch localization, post-structure controls, zero active motion and clean JavaScript/WebSocket diagnostics.

            These are browser-engine/viewport regressions, not a claim of broad physical-device, firmware or Home Assistant Companion App validation. That wider field validation remains part of the Beta status.

            ## Upgrade notes

            1. Install v0.41 through HACS after the release is published.
            2. Restart Home Assistant as requested by HACS.
            3. Reload the dashboard/browser so the new `0.41-stable1` frontend cache keys are used.
            4. Verify scrolling and the Dashboard menu before enabling Automatic Control.
            5. Confirm Battery Strategy and Optimize now update the plan graph without moving the page.

            ## Safety and compatibility

            v0.41 is frontend-only. It does not change GoodWe register definitions or Modbus read blocks; EMS modes, setpoints or write ordering; Automatic Control decisions; EMHASS optimization/configuration ownership; entity IDs or unique IDs; config-entry data or migrations; persistent Store keys; or stable device identity.
            """
        ),
    )
    write(
        ROOT / "docs" / "FRONTEND_STABLE_DOM.md",
        dedent(
            """
            # Frontend stable-DOM architecture

            ## Status

            This document is the canonical frontend render/interaction decision for **GW EnergyPilot v0.41 Beta**. It supersedes the normal telemetry/render behavior documented for v0.38-v0.40 while preserving those older modules for backwards-compatible historical entrypoints.

            No GoodWe register, Modbus, EMS or EMHASS backend behavior is defined here.

            ## Problem statement

            The inherited base panel builds its complete ShadowRoot with `innerHTML`. Older release layers filtered and batched relevant Home Assistant updates, but an accepted update still ran the complete render chain. That detached and recreated cards and controls while WebKit could simultaneously be processing a touch pan or momentum scroll.

            The v0.38-v0.40 stack attempted to compensate with interaction guards, delayed renders, button reuse, scroll snapshots/restoration and transition suppression. Those mechanisms reduced individual symptoms but could not make a destructive telemetry render equivalent to a stable page.

            ## Active entrypoint chain

            ```text
            Home Assistant PANEL_MODULE
              -> gw-energy-pilot-v041.js?v=0.41-stable1
              -> gw-energy-pilot-v039.js?v=0.41-stable1
              -> gw-energy-pilot-v038.js?v=0.41-stable1
              -> gw-energy-pilot-v038-runtime.js?v=0.41-stable1
              -> gw-energy-pilot-v038-strategy.js?v=0.41-stable1
            ```

            The v0.41 entrypoint also imports the modified plan data/core modules with `0.41-stable1` cache keys. A new top-level file alone is insufficient when modified nested modules retain a v0.40 URL.

            ## Render ownership

            ### Initial structural render

            The inherited complete renderer is allowed when the panel is first created or entity discovery has not completed.

            ### Context/structure render

            A complete render is allowed for Home Assistant language/locale, user/admin context, theme/dark-mode context, entity-registry mapping, optional-card topology or explicit narrow/layout structural changes.

            ### Normal telemetry patch

            When context and structure signatures are unchanged, the `hass` setter does not queue the inherited complete render. It batches a live patch and mutates existing power/SOC/energy text, status classes, controller/EMHASS metrics, sliders, meter widths, diagnostics, static flow semantics and thermal values. The existing `main`, cards and controls remain connected.

            ### Battery Strategy refresh

            Loading, pending, success/error and Custom-SOC feedback rerender only `.ep-v038-strategy`. Stable backend mode keys, not translated labels, remain the control identity.

            ### Plan graph refresh

            A changed `plan_revision` or configured `P_batt` state invalidates graph data. Only `.ep-v027-battery-plan-card` is replaced.

            ## Native interaction and scroll contract

            The active v0.41 normal telemetry path never writes `scrollTop` or `scrollLeft`, captures a touch pointer, cancels a vertical pan, delays telemetry because of hover, restores an earlier viewport snapshot or reuses a detached control to compensate for a full telemetry render. The Home Assistant browser/WebView owns pan and momentum scrolling.

            Legacy v0.38 interaction and scroll-restoration functions remain available for historical entrypoints, but `__epV041StableRuntime` bypasses them before installation or use.

            ## Motion contract

            EnergyPilot-owned content has no CSS animations, CSS transitions, moving flow particles, animated pseudo-elements or modal backdrop filters. The policy is applied after complete renders and after scoped strategy, graph and modal updates.

            ## Required invariants

            A normal telemetry burst must preserve `main`, Dashboard layout-button, Automatic Control button and Battery Strategy button identity; keep idle scroll drift within two pixels; produce no backward controlled-scroll samples; emit no JavaScript/page errors or unknown WebSocket calls; and have zero computed active EnergyPilot animations and transitions. A plan refresh may replace the graph card, but none of those four persistent nodes.

            ## Regression matrix

            The required release gate uses desktop Chromium at 1440 × 900, iPad WebKit touch at 834 × 1112 and iPhone WebKit touch at 390 × 844. It is implemented in `tests/browser/test_frontend_stability.py` and selected for v0.41 by `tests/browser/test_frontend_stability_v041.py`.

            ## Contributor rules

            - Do not call `_queueRender()` for normal v0.41 telemetry feedback when an existing scoped callback owns the update.
            - Do not add scroll-position writes as a visual correction for render movement.
            - Do not add pointer capture or global gesture cancellation to protect a control from telemetry.
            - Do not re-enable motion without a separately documented ownership model and browser regressions on all three profiles.
            - Preserve entity IDs, unique IDs, settings, backend APIs and GoodWe/EMHASS semantics unless a separate change explicitly requires them.
            """
        ),
    )


def verify() -> None:
    manifest = json.loads(read(INTEGRATION / "manifest.json"))
    assert manifest["version"] == "0.41"
    assert "gw-energy-pilot-v041.js?v=0.41-stable1" in read(
        INTEGRATION / "__init__.py"
    )
    assert "## [0.41] - 2026-08-27" in read(ROOT / "CHANGELOG.md")
    assert "| **0.41** | 2026-08-27 | **Beta** |" in read(
        ROOT / "docs" / "RELEASE_NOTES.md"
    )
    assert not (FRONTEND / "gw-energy-pilot-v041-release.js").exists()


def main() -> None:
    update_frontend_wiring()
    update_manifest()
    update_changelog()
    update_release_index()
    update_readme()
    update_agent_contract()
    update_control_rebuild_note()
    write_release_documents()
    verify()


if __name__ == "__main__":
    main()
