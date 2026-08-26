#!/usr/bin/env python3
"""One-shot preparation of the GW EnergyPilot v0.40 release candidate."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "custom_components" / "gw_energypilot" / "frontend"
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Missing release-prep anchor in {path}: {old[:100]!r}")
    if text.count(old) != 1:
        raise SystemExit(f"Release-prep anchor is not unique in {path}: {old[:100]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


V040 = r'''import "./gw-energy-pilot-v039.js?v=0.40-v0391";

const VERSION = "0.40";
const PANEL_NAME = "gw-energypilot-panel";
const SETTLE_CLASS = "ep-v040-render-settle";
const SETTLE_STYLE_ID = "ep-v040-render-settle-style";
const INTERACTIVE_SELECTOR =
  'button, input, select, textarea, a[href], [role="button"], [tabindex]';
const SETTLE_CSS = `
  :host(.${SETTLE_CLASS}) :is(${INTERACTIVE_SELECTOR}),
  :host(.${SETTLE_CLASS}) :is(${INTERACTIVE_SELECTOR}) *,
  :host(.${SETTLE_CLASS}) :is(${INTERACTIVE_SELECTOR})::before,
  :host(.${SETTLE_CLASS}) :is(${INTERACTIVE_SELECTOR})::after,
  :host(.${SETTLE_CLASS}) :is(${INTERACTIVE_SELECTOR}) *::before,
  :host(.${SETTLE_CLASS}) :is(${INTERACTIVE_SELECTOR}) *::after {
    transition: none !important;
  }
`;

function updateVersion(root) {
  const versionBadge = root?.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root?.querySelectorAll("footer span") || [];
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
}

function ensureFallbackSettleStyle(root) {
  if (!root || root.querySelector(`#${SETTLE_STYLE_ID}`)) return;
  const style = document.createElement("style");
  style.id = SETTLE_STYLE_ID;
  style.textContent = SETTLE_CSS;
  root.appendChild(style);
}

function ensurePersistentSettleStyle(panel, root) {
  if (!root) return false;
  const existing = panel.__epV040SettleSheet;
  if (existing && root.adoptedStyleSheets?.includes?.(existing)) return true;

  try {
    if (
      typeof globalThis.CSSStyleSheet === "function" &&
      "adoptedStyleSheets" in root
    ) {
      const sheet = existing || new globalThis.CSSStyleSheet();
      if (!existing) sheet.replaceSync(SETTLE_CSS);
      if (!root.adoptedStyleSheets.includes(sheet)) {
        root.adoptedStyleSheets = [...root.adoptedStyleSheets, sheet];
      }
      panel.__epV040SettleSheet = sheet;
      return true;
    }
  } catch (_err) {
    // The same settle contract is installed as an ordinary style below.
  }

  ensureFallbackSettleStyle(root);
  return false;
}

function scheduleSettleEnd(panel, generation) {
  const finish = () => {
    if (panel.__epV040RenderGeneration !== generation) return;
    panel.classList.remove(SETTLE_CLASS);
  };

  if (typeof globalThis.requestAnimationFrame === "function") {
    // One rAF runs before paint. The second rAF guarantees the freshly rebuilt
    // controls have painted once in their final :hover state without replaying
    // their CSS transition from the detached predecessor node.
    globalThis.requestAnimationFrame(() => {
      globalThis.requestAnimationFrame(finish);
    });
    return;
  }

  globalThis.setTimeout?.(finish, 34);
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (PanelClass && !PanelClass.prototype.__epV040Installed) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV040Render(...args) {
    const generation = (this.__epV040RenderGeneration || 0) + 1;
    this.__epV040RenderGeneration = generation;

    const rootBefore = this.shadowRoot;
    if (rootBefore) ensurePersistentSettleStyle(this, rootBefore);
    this.classList.add(SETTLE_CLASS);

    let result;
    try {
      result = previousRender.apply(this, args);
      const root = this.shadowRoot;
      if (root) {
        if (!ensurePersistentSettleStyle(this, root)) {
          ensureFallbackSettleStyle(root);
        }
        updateVersion(root);
      }
      return result;
    } finally {
      scheduleSettleEnd(this, generation);
    }
  };
  PanelClass.prototype.__epV040Installed = true;
}
'''


TEST_SOURCE = r'''from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"


class FrontendV040RenderSettleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = (FRONTEND / "gw-energy-pilot-v040.js").read_text(encoding="utf-8")

    def test_v040_is_active_and_version_synchronized(self) -> None:
        manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
        init = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        self.assertEqual(manifest["version"], "0.40")
        self.assertIn('gw-energy-pilot-v040.js?v=0.40-release1', init)
        self.assertIn('import "./gw-energy-pilot-v039.js?v=0.40-v0391"', self.source)
        self.assertIn('const VERSION = "0.40"', self.source)

    def test_v040_suppresses_only_transition_restart_during_render_settle(self) -> None:
        self.assertIn("const INTERACTIVE_SELECTOR", self.source)
        self.assertIn("button, input, select, textarea", self.source)
        self.assertIn('[role="button"], [tabindex]', self.source)
        self.assertIn("transition: none !important", self.source)
        self.assertIn(":is(${INTERACTIVE_SELECTOR}) *", self.source)
        self.assertIn(":is(${INTERACTIVE_SELECTOR})::before", self.source)
        self.assertIn(":is(${INTERACTIVE_SELECTOR})::after", self.source)
        self.assertNotIn("animation: none", self.source)
        self.assertNotIn("animation-duration", self.source)

    def test_v040_settle_style_survives_shadowroot_innerhtml_rebuild(self) -> None:
        self.assertIn('"adoptedStyleSheets" in root', self.source)
        self.assertIn("new globalThis.CSSStyleSheet()", self.source)
        self.assertIn("sheet.replaceSync(SETTLE_CSS)", self.source)
        self.assertIn("ensureFallbackSettleStyle", self.source)
        self.assertIn('const SETTLE_STYLE_ID = "ep-v040-render-settle-style"', self.source)

    def test_v040_keeps_settle_until_one_paint_and_guards_rapid_renders(self) -> None:
        self.assertIn("__epV040RenderGeneration", self.source)
        self.assertIn("panel.__epV040RenderGeneration !== generation", self.source)
        self.assertGreaterEqual(self.source.count("globalThis.requestAnimationFrame"), 3)
        self.assertIn("globalThis.setTimeout?.(finish, 34)", self.source)
        self.assertLess(
            self.source.index("this.classList.add(SETTLE_CLASS)"),
            self.source.index("previousRender.apply(this, args)"),
        )
        self.assertGreater(
            self.source.index("scheduleSettleEnd(this, generation)"),
            self.source.index("previousRender.apply(this, args)"),
        )

    def test_v040_does_not_restore_removed_hover_locks_or_stale_node_reuse(self) -> None:
        for forbidden in (
            "setPointerCapture",
            "__epV035HoverActive",
            "captureStableButtons",
            "renderedButton.replaceWith",
        ):
            self.assertNotIn(forbidden, self.source)

    def test_v040_scope_covers_known_recreated_menu_and_window_controls(self) -> None:
        menu = (FRONTEND / "gw-energy-pilot-v008.js").read_text(encoding="utf-8")
        windows = (FRONTEND / "gw-energy-pilot-v031-window-controls.js").read_text(
            encoding="utf-8"
        )
        base = (FRONTEND / "gw-energy-pilot.js").read_text(encoding="utf-8")
        self.assertIn(".ep-layout-button", menu)
        self.assertIn(".ep-menu-row input", menu)
        self.assertIn("transition: border-color .18s ease", menu)
        self.assertIn(".ep-v031-window-dot", windows)
        self.assertIn("transition:transform .12s ease", windows)
        self.assertIn(".switch-knob", base)
        self.assertIn("transition: transform .18s ease", base)


if __name__ == "__main__":
    unittest.main()
'''


CHANGELOG_ENTRY = '''## [0.40] - 2026-08-26

### Fixed

- Stabilized the remaining dashboard, menu and card-window controls that could visibly blink when a relevant Home Assistant update rebuilt the complete ShadowRoot under a stationary pointer.
- Prevented recreated layout/menu controls, switches, Automatic Control presentation and card window buttons from replaying their CSS transition from a fresh non-hovered DOM node on every telemetry-driven render.

### Changed

- Added `gw-energy-pilot-v040.js` as a thin render-settle/release layer over v0.39. It temporarily suppresses CSS **transitions** on interactive controls while the inherited synchronous ShadowRoot rebuild settles, then restores normal transitions after the rebuilt controls have painted once.
- Uses a persistent `adoptedStyleSheets` rule where supported, with an ordinary ShadowRoot style fallback, and a render-generation guard so rapid consecutive renders cannot release a newer settle window early.
- Keeps the v0.38 relevant-state render filtering, live telemetry cadence, active-press guard, mobile scroll preservation, delegated Battery Strategy actions and v0.39 strategy-hover continuity unchanged.

### Safety / compatibility

- Frontend-only release; no GoodWe register definitions, Modbus read blocks, EMS mappings, setpoint semantics or `47512 -> wait -> 47511` write ordering change.
- No Automatic Control decision, EMHASS optimization/topology/Battery Saver behavior, entity ID, unique ID, config-entry data, persistent Store key or stable device identity change.
- v0.40 does not restore the removed v0.35 hover/render lock, does not capture pointers and does not transplant old button DOM nodes/listener closures.

'''


RELEASE_V040 = '''# GW EnergyPilot v0.40 Beta

v0.40 is a focused frontend stability release. It extends the v0.39 Battery Strategy hover fix to the other dashboard controls that are still recreated by the inherited full ShadowRoot render, including the dashboard-layout menu and per-card window controls.

## Root cause

Relevant Home Assistant state updates are intentionally filtered and batched by the v0.38 runtime, but a relevant update still rebuilds the inherited dashboard DOM. Most older controls are created again during that render. Their CSS transitions then start from the new node's initial state and immediately enter `:hover` when the pointer is stationary above the same visual location. That transition restart looks like a periodic blink even though the click handler itself is working.

v0.39 solved this specifically for the reused Battery Strategy section. v0.40 solves the remaining presentation problem generically without changing action ownership.

## Render-settle behavior

During an inherited full render, v0.40:

- marks the panel as being in a short render-settle phase before the old controls are detached;
- temporarily disables CSS **transitions** for `button`, `input`, `select`, `textarea`, links, role-buttons, tabindex controls, their descendants and their pseudo-elements;
- keeps that settle state through the first paint of the rebuilt controls using two animation-frame boundaries;
- uses a generation token so a callback from an older render cannot end the settle phase of a newer render;
- keeps the rule in a ShadowRoot `adoptedStyleSheets` stylesheet where supported, so the rule survives the inherited `innerHTML` replacement; an ordinary ShadowRoot style is used as fallback.

After that first painted frame, normal hover/focus/switch transitions work again.

## What this covers

The generic interactive selector covers, among other current controls:

- the Dashboard layout button;
- menu close/reset buttons and visibility/edit/animation switches;
- Automatic Control and its switch-knob presentation;
- per-card close/minimize/maximize window controls;
- manual/controller buttons, inputs and other native interactive controls created by inherited frontend layers.

The v0.39 Battery Strategy hover-continuity logic remains unchanged.

## Deliberately not changed

v0.40 does **not**:

- defer or suppress live telemetry renders merely because the mouse is hovering a control;
- restore the removed v0.35 hover/render lock;
- transplant old button DOM nodes or their per-node event-listener closures;
- capture pointers;
- disable live-flow CSS animations;
- change GoodWe registers, Modbus reads, EMS modes/setpoints/write ordering, Automatic Control decisions or EMHASS behavior.

## Safety and compatibility

No Home Assistant entity IDs, unique IDs, config-entry data, persistent Store keys or stable device identity are changed. The release is frontend-only and retains the v0.38 active-press guard, relevant-state filtering, touch scrolling, mobile scroll restoration and delegated Battery Strategy control contract.

## Validation

The final v0.40 candidate must pass:

- JavaScript syntax validation including the active `gw-energy-pilot-v040.js` entrypoint;
- the existing executable v0.38 model/control/localization tests;
- v0.40 render-settle regression tests;
- the complete Python unit suite and repository invariant validator;
- HACS validation;
- Hassfest validation.
'''


V040_INDEX_SECTION = '''# v0.40 — Stable dashboard and menu controls across full renders

v0.40 extends the v0.39 presentation fix from Battery Strategy to the rest of the interactive dashboard. Relevant Home Assistant updates still use the established full ShadowRoot render path, but recreated controls no longer visibly replay their hover/switch transition under a stationary pointer.

The new render-settle layer disables CSS transitions only for interactive controls during the synchronous rebuild and through the first painted frame. It does not pause telemetry, capture a pointer, reuse old button nodes or restore the removed v0.35 hover/render lock. Live-flow animations remain enabled because v0.40 does not suppress CSS animations.

See `docs/RELEASE_NOTES_V040.md`.

'''


README_V040 = '''## v0.40 highlights

- Extends render stability from Battery Strategy to the other dashboard/menu/window controls that are recreated during relevant telemetry-driven full ShadowRoot renders.
- Suppresses only interactive CSS transition restart through the rebuilt controls' first painted frame; normal hover/focus transitions resume immediately afterwards.
- Keeps live telemetry rendering, live-flow animations, v0.38 click/touch protection and v0.39 strategy-hover continuity active.
- Does not restore the old hover render-lock or stale-button-node reuse mechanisms and does not change GoodWe, EMS or EMHASS control semantics.

'''


V040_ARCH = '''## v0.40 render-settle follow-up

v0.39 proved that the remaining visible blink was a presentation problem caused by a full ShadowRoot rebuild under a stationary pointer, not by control identity or click ownership. The Battery Strategy section already has explicit hover continuity because that section is intentionally reused. Older dashboard/menu/window controls are still recreated and can therefore restart their CSS transitions when the fresh node immediately matches `:hover`.

v0.40 addresses that shared cause at the render boundary instead of adding per-button patches. A persistent ShadowRoot stylesheet temporarily disables **transitions** for interactive controls while the inherited synchronous rebuild settles and until the rebuilt controls have painted once. A generation token prevents an older render callback from releasing a newer settle period. The fallback style is inserted in the same render task when constructable/adopted stylesheets are unavailable.

This mechanism intentionally does not suppress CSS animations, defer telemetry while a pointer merely hovers, capture pointers or transplant old DOM nodes/listener closures. The v0.38 interaction guard remains responsible only for a real active press, and v0.39 remains responsible for Battery Strategy hover continuity.

'''


def main() -> None:
    (FRONTEND / "gw-energy-pilot-v040.js").write_text(V040, encoding="utf-8")

    manifest_path = INTEGRATION / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if str(manifest.get("version")) != "0.39":
        raise SystemExit(f"Expected manifest 0.39, found {manifest.get('version')!r}")
    manifest["version"] = "0.40"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    replace_once(
        INTEGRATION / "__init__.py",
        'PANEL_MODULE = f"{PANEL_STATIC_URL}/gw-energy-pilot-v039.js?v=0.39-release1"',
        'PANEL_MODULE = f"{PANEL_STATIC_URL}/gw-energy-pilot-v040.js?v=0.40-release1"',
    )

    replace_once(
        ROOT / ".github" / "workflows" / "quality.yml",
        "          node --check custom_components/gw_energypilot/frontend/gw-energy-pilot-v039.js\n",
        "          node --check custom_components/gw_energypilot/frontend/gw-energy-pilot-v040.js\n"
        "          node --check custom_components/gw_energypilot/frontend/gw-energy-pilot-v039.js\n",
    )

    (ROOT / "tests" / "test_frontend_v040_render_settle.py").write_text(
        TEST_SOURCE, encoding="utf-8"
    )

    changelog = ROOT / "CHANGELOG.md"
    replace_once(
        changelog,
        "All notable changes to GW EnergyPilot are documented here.\n\n",
        "All notable changes to GW EnergyPilot are documented here.\n\n" + CHANGELOG_ENTRY,
    )

    release_index = ROOT / "docs" / "RELEASE_NOTES.md"
    replace_once(
        release_index,
        "|---|---|---|---|\n| **0.39** |",
        "|---|---|---|---|\n"
        "| **0.40** | 2026-08-26 | **Beta** | Stabilizes the remaining dashboard, menu and card-window controls across telemetry-driven full renders by suppressing transition restart for one painted frame without delaying telemetry or reusing stale button nodes. |\n"
        "| **0.39** |",
    )
    replace_once(
        release_index,
        "# v0.39 — Stable strategy hover and complete Dutch Controller copy\n",
        V040_INDEX_SECTION + "# v0.39 — Stable strategy hover and complete Dutch Controller copy\n",
    )

    (ROOT / "docs" / "RELEASE_NOTES_V040.md").write_text(
        RELEASE_V040, encoding="utf-8"
    )

    readme = ROOT / "README.md"
    replace_once(readme, "**v0.39 · Beta**", "**v0.40 · Beta**")
    replace_once(
        readme,
        "- `docs/RELEASE_NOTES.md` — current release index and Beta scope;\n"
        "- `docs/RELEASE_NOTES_V039.md` — v0.39 stable strategy hover and complete Dutch Controller copy;\n",
        "- `docs/RELEASE_NOTES.md` — current release index and Beta scope;\n"
        "- `docs/RELEASE_NOTES_V040.md` — v0.40 stable dashboard/menu controls across full renders;\n"
        "- `docs/RELEASE_NOTES_V039.md` — v0.39 stable strategy hover and complete Dutch Controller copy;\n",
    )
    replace_once(readme, "## v0.39 highlights\n", README_V040 + "## v0.39 highlights\n")

    replace_once(ROOT / "AGENTS.md", "v0.39 Beta", "v0.40 Beta")

    architecture = ROOT / "docs" / "FRONTEND_CONTROL_REBUILD.md"
    replace_once(
        architecture,
        "## Why the v0.37 control stack was replaced\n",
        V040_ARCH + "## Why the v0.37 control stack was replaced\n",
    )

    print("Prepared v0.40 release files")


if __name__ == "__main__":
    main()
