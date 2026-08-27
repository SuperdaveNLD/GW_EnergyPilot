#!/usr/bin/env python3
"""Prepare v0.41.1 release documentation, then remove this one-shot helper."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    """Replace one required marker without silently damaging release history."""
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Required documentation marker missing in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(path: Path, marker: str, addition: str) -> None:
    """Append a section once."""
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    path.write_text(text.rstrip() + "\n\n" + addition.strip() + "\n", encoding="utf-8")


def update_changelog() -> None:
    path = ROOT / "CHANGELOG.md"
    text = path.read_text(encoding="utf-8")
    if "## [0.41.1] - 2026-08-27" in text:
        return
    block = """## [0.41.1] - 2026-08-27

### Fixed

- Removed the inherited Optimize-now completion render that detached the touched dashboard button after the Home Assistant button service returned and could restart Safari/WebKit blinking or break native scrolling.
- Replaced only the inherited Optimize listener with a v0.41.1 stable-DOM action that patches busy/idle state, orchestrator status, last-success details and errors in place.
- Preserved the same Optimize button, dashboard `main`, layout control, Automatic Control and Battery Strategy DOM nodes for the complete solve/publish transaction.

### Validation

- Added a real-browser Optimize regression for desktop Chromium, iPad WebKit touch and iPhone WebKit touch.
- The regression verifies one service execution, zero complete dashboard renders, stable control identities, no scroll jump, working post-optimization scrolling and targeted plan-card refresh.
- Existing Python/Node Quality, repository invariants, frontend architecture audit, HACS, Hassfest and the full v0.41 browser matrix remain required gates.

### Safety and compatibility

- Frontend-only hotfix; no GoodWe register, Modbus block, EMS mapping/write order, Automatic Control decision, EMHASS solve/publish ownership, entity ID, unique ID, config-entry or persistent-state change.

"""
    marker = "## [0.41] - 2026-08-27"
    if marker not in text:
        raise RuntimeError("v0.41 changelog marker is missing")
    path.write_text(text.replace(marker, block + marker, 1), encoding="utf-8")


def update_release_index() -> None:
    path = ROOT / "docs" / "RELEASE_NOTES.md"
    text = path.read_text(encoding="utf-8")
    row = (
        "| **0.41.1** | 2026-08-27 | **Beta** | Hotfixes Optimize now so "
        "its solve/publish transaction patches the existing control in place, never "
        "rebuilds the touched dashboard and keeps desktop/iPad/iPhone scrolling usable. |"
    )
    if row not in text:
        separator = "|---|---|---|---|\n"
        if separator not in text:
            raise RuntimeError("Release index table separator is missing")
        text = text.replace(separator, separator + row + "\n", 1)

    section = """# v0.41.1 — Optimize now stable-DOM hotfix

v0.41.1 closes the action-specific gap left in v0.41. The historical Optimize button listener still requested a complete dashboard render after the asynchronous Home Assistant button service completed. On Safari/WebKit that could detach the touched node during the interaction lifecycle, making the dashboard blink and leaving native scrolling unusable.

The v0.41.1 entrypoint replaces only that inherited listener. Busy/idle state and orchestrator details are patched on the existing nodes, while the established backend optimization, publish and plan-revision transaction remains unchanged. A dedicated real-browser matrix presses Optimize while scrolled and verifies zero full renders plus working scrolling afterward on desktop Chromium and iPad/iPhone WebKit touch profiles.

See `docs/RELEASE_NOTES_V0411.md`.

"""
    if "# v0.41.1 — Optimize now stable-DOM hotfix" not in text:
        marker = "# v0.41 — Stable DOM and native mobile scrolling"
        if marker not in text:
            raise RuntimeError("v0.41 release-index section is missing")
        text = text.replace(marker, section + marker, 1)
    path.write_text(text, encoding="utf-8")


def update_readme() -> None:
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    text = text.replace("**v0.41 · Beta**", "**v0.41.1 · Beta**", 1)

    notes_line = (
        "- `docs/RELEASE_NOTES_V0411.md` — v0.41.1 Optimize-now stable-DOM "
        "and scrolling hotfix;\n"
    )
    if notes_line not in text:
        marker = "- `docs/RELEASE_NOTES.md` — current release index and Beta scope;\n"
        if marker not in text:
            raise RuntimeError("README release-documentation marker is missing")
        text = text.replace(marker, marker + notes_line, 1)

    old_claim = (
        "- Battery Strategy and Battery · Plan · Price refreshes are scoped to their "
        "own sections/cards; a fresh optimization no longer rebuilds unrelated controls."
    )
    corrected_claim = (
        "- Battery Strategy feedback and Battery · Plan · Price refreshes are scoped "
        "to their own sections/cards; v0.41.1 separately fixes the inherited "
        "Optimize-now completion render."
    )
    if old_claim in text:
        text = text.replace(old_claim, corrected_claim, 1)

    highlights = """## v0.41.1 highlights

- Optimize now keeps the same button and dashboard DOM connected throughout the complete Home Assistant service call.
- Busy/idle state and orchestrator details update in place; the action no longer ends with `_queueRender()`.
- Desktop Chromium plus iPad/iPhone WebKit touch regressions verify zero full renders, no scroll jump and working scrolling after optimization.
- The backend EMHASS solve/publish path, GoodWe execution and all entity identities remain unchanged.

"""
    if "## v0.41.1 highlights" not in text:
        marker = "## v0.41 highlights"
        if marker not in text:
            raise RuntimeError("README v0.41 highlights marker is missing")
        text = text.replace(marker, highlights + marker, 1)
    path.write_text(text, encoding="utf-8")


def update_v041_notes() -> None:
    path = ROOT / "docs" / "RELEASE_NOTES_V041.md"
    text = path.read_text(encoding="utf-8")
    follow_up = (
        "> **Follow-up:** v0.41.1 removes an inherited action-specific full render "
        "that still ran after pressing **Optimize now**. Ordinary telemetry, strategy "
        "and plan-card stable-DOM behavior described below remains the v0.41 foundation.\n\n"
    )
    if follow_up in text:
        return
    marker = "# GW EnergyPilot v0.41 Beta\n\n"
    if marker not in text:
        raise RuntimeError("v0.41 release-note title is missing")
    path.write_text(text.replace(marker, marker + follow_up, 1), encoding="utf-8")


def update_architecture() -> None:
    path = ROOT / "docs" / "FRONTEND_STABLE_DOM.md"
    append_once(
        path,
        "## v0.41.1 action-specific render contract",
        """## v0.41.1 action-specific render contract

The stable-DOM rule also applies to asynchronous dashboard actions. A control may update its own text, disabled state, accessibility state and related status rows in place, but it must not request a complete panel render when the service promise settles.

The Optimize-now control is the first explicit regression for this rule. v0.41.1 removes the inherited completion `_queueRender()` by replacing that historical listener at the active release boundary. The backend button entity and orchestrator transaction are unchanged. Browser CI captures `main` and control identities before the click and requires zero complete renders plus usable scrolling after the new plan has refreshed.
""",
    )


def remove_one_shot_files() -> None:
    workflow = ROOT / ".github" / "workflows" / "prepare-v0411-docs.yml"
    if workflow.exists():
        workflow.unlink()
    Path(__file__).unlink()


def main() -> None:
    update_changelog()
    update_release_index()
    update_readme()
    update_v041_notes()
    update_architecture()
    remove_one_shot_files()


if __name__ == "__main__":
    main()
