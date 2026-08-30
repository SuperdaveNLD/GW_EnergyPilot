#!/usr/bin/env python3
"""Validate lightweight GW EnergyPilot repository invariants.

This script intentionally uses only the Python standard library so it can run
without installing Home Assistant or pymodbus.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
CUSTOM_COMPONENTS = ROOT / "custom_components"
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"
REGISTERS = INTEGRATION / "registers.py"
INIT = INTEGRATION / "__init__.py"
MANIFEST = INTEGRATION / "manifest.json"
CHANGELOG = ROOT / "CHANGELOG.md"
RELEASE_NOTES = ROOT / "docs" / "RELEASE_NOTES.md"
HACS = ROOT / "hacs.json"

JS_IMPORT_RE = re.compile(
    r"^\s*import\s+[\"'](?P<path>\./[^\"']+)[\"']\s*;?",
    re.MULTILINE,
)
PANEL_MODULE_RE = re.compile(
    r"PANEL_MODULE\s*=\s*f?[\"'][^\"']*/(?P<name>[^/?\"']+\.js)(?:\?[^\"']*)?[\"']"
)
FRONTEND_VERSION_RE = re.compile(
    r"\bconst\s+VERSION\s*=\s*[\"'](?P<version>[^\"']+)[\"']"
)
CHANGELOG_VERSION_RE = re.compile(
    r"^## \[(?P<version>\d+\.\d+(?:\.\d+)?(?:-beta\.[1-9]\d*)?)\]",
    re.MULTILINE,
)
LEGACY_VERSION_RE = re.compile(r"^0\.\d+(?:\.\d+)?$")
V1_VERSION_RE = re.compile(
    r"^1\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-beta\.[1-9]\d*)?$"
)
DOMAIN_RE = re.compile(r'^DOMAIN\s*=\s*["\'](?P<domain>[^"\']+)["\']', re.MULTILINE)


def _load_register_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gw_energypilot_registers", REGISTERS)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {REGISTERS}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _validate_registers(errors: list[str]) -> None:
    module = _load_register_module()

    for group_name in ("TELEMETRY_BLOCKS", "OPTIONAL_TELEMETRY_BLOCKS"):
        blocks = getattr(module, group_name)
        for start, count in blocks:
            if start < 0:
                errors.append(f"{group_name}: negative register start {start}")
            if not 1 <= count <= 125:
                errors.append(
                    f"{group_name}: block {start} has invalid count {count}; Modbus limit is 125"
                )

    uncovered = module.find_uncovered_registers()
    if uncovered:
        errors.append(
            "Register definitions are not fully covered by read blocks: "
            + ", ".join(uncovered)
        )

    keys = [definition.key for definition in module.REGISTER_DEFINITIONS]
    duplicate_keys = sorted({key for key in keys if keys.count(key) > 1})
    if duplicate_keys:
        errors.append("Duplicate register keys: " + ", ".join(duplicate_keys))


def _validate_json(errors: list[str]) -> None:
    json_files = [HACS, *INTEGRATION.rglob("*.json")]
    for path in json_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as err:
            errors.append(f"Invalid JSON in {path.relative_to(ROOT)}: {err}")


def _validate_integration_structure(errors: list[str]) -> None:
    integration_dirs = sorted(
        path
        for path in CUSTOM_COMPONENTS.iterdir()
        if path.is_dir() and not path.name.startswith(".") and path.name != "__pycache__"
    )
    if integration_dirs != [INTEGRATION]:
        names = ", ".join(path.name for path in integration_dirs) or "none"
        errors.append(
            "custom_components must contain exactly gw_energypilot; found: " + names
        )
        return

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        hacs = json.loads(HACS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    manifest_domain = str(manifest.get("domain", "")).strip()
    const_match = DOMAIN_RE.search((INTEGRATION / "const.py").read_text(encoding="utf-8"))
    const_domain = const_match.group("domain") if const_match is not None else ""
    if manifest_domain != INTEGRATION.name or const_domain != INTEGRATION.name:
        errors.append(
            "Integration directory, manifest domain and const.DOMAIN must all be "
            f"{INTEGRATION.name!r}"
        )

    manifest_version = str(manifest.get("version", "")).strip()
    if not (
        LEGACY_VERSION_RE.fullmatch(manifest_version)
        or V1_VERSION_RE.fullmatch(manifest_version)
    ):
        errors.append(
            f"Unsupported manifest version {manifest_version!r}; retain a historical 0.x "
            "version or use 1.x.x[-beta.N] for the v1 release lines"
        )

    if hacs.get("hide_default_branch") is not True:
        errors.append(
            "hacs.json must set hide_default_branch=true so users install published "
            "stable/beta releases instead of an unversioned branch"
        )


def _validate_frontend(errors: list[str]) -> None:
    init_text = INIT.read_text(encoding="utf-8")
    panel_match = PANEL_MODULE_RE.search(init_text)
    if panel_match is None:
        errors.append("Unable to determine PANEL_MODULE from __init__.py")
        return

    active_name = panel_match.group("name")
    active_path = FRONTEND / active_name
    if not active_path.is_file():
        errors.append(f"Active PANEL_MODULE does not exist: frontend/{active_name}")
        return

    for js_path in FRONTEND.rglob("*.js"):
        text = js_path.read_text(encoding="utf-8")
        for match in JS_IMPORT_RE.finditer(text):
            raw_dependency = match.group("path")
            dependency_name = raw_dependency.split("?", 1)[0].split("#", 1)[0]
            dependency = (js_path.parent / dependency_name).resolve()
            if not dependency.is_file():
                errors.append(
                    f"Missing frontend dependency: {js_path.relative_to(ROOT)} -> {raw_dependency}"
                )

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_version = str(manifest.get("version", "")).strip()
    active_text = active_path.read_text(encoding="utf-8")
    version_match = FRONTEND_VERSION_RE.search(active_text)
    if version_match is not None:
        frontend_version = version_match.group("version").strip()
        if manifest_version and frontend_version != manifest_version:
            errors.append(
                "Frontend VERSION does not match manifest version: "
                f"{frontend_version} != {manifest_version}"
            )


def _release_doc_suffix(version: str) -> str:
    """Return the compact numeric suffix used by dedicated release docs."""
    return version.replace(".", "")


def _release_doc_path(version: str) -> Path:
    """Return the canonical release-note path for a manifest version."""
    if V1_VERSION_RE.fullmatch(version):
        return ROOT / "docs" / "releases" / f"v{version}.md"
    return ROOT / "docs" / f"RELEASE_NOTES_V{_release_doc_suffix(version)}.md"


def _validate_release_docs(errors: list[str]) -> None:
    """Require central history plus explicit docs for the current release."""
    if not CHANGELOG.is_file():
        errors.append("Missing CHANGELOG.md")
        return
    if not RELEASE_NOTES.is_file():
        errors.append("Missing docs/RELEASE_NOTES.md")
        return

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_version = str(manifest.get("version", "")).strip()
    changelog_text = CHANGELOG.read_text(encoding="utf-8")
    release_text = RELEASE_NOTES.read_text(encoding="utf-8")
    changelog_versions = CHANGELOG_VERSION_RE.findall(changelog_text)

    for version in changelog_versions:
        marker = f"| **{version}** |"
        if marker not in release_text:
            errors.append(
                f"CHANGELOG version {version} is missing from docs/RELEASE_NOTES.md"
            )

    if not manifest_version:
        return

    suffix = _release_doc_suffix(manifest_version)
    dedicated_changelog = ROOT / "docs" / f"CHANGELOG_V{suffix}.md"
    dedicated_release = _release_doc_path(manifest_version)
    central_marker = f"| **{manifest_version}** |"
    central_line = next(
        (line for line in release_text.splitlines() if line.startswith(central_marker)),
        None,
    )

    if manifest_version not in changelog_versions and not dedicated_changelog.is_file():
        errors.append(
            f"Manifest version {manifest_version} is missing from CHANGELOG.md and "
            f"docs/CHANGELOG_V{suffix}.md"
        )

    if central_line is None:
        if not dedicated_release.is_file():
            errors.append(
                f"Current version {manifest_version} has neither a release-notes status row "
                f"nor docs/RELEASE_NOTES_V{suffix}.md"
            )
        else:
            dedicated_text = dedicated_release.read_text(encoding="utf-8")
            if not any(
                status in dedicated_text
                for status in ("Beta", "Stable", "Validated", "Historical")
            ):
                errors.append(
                    f"Dedicated release notes for {manifest_version} have no explicit status"
                )
    elif not any(
        status in central_line
        for status in ("**Beta**", "**Stable**", "**Validated", "**Historical**")
    ):
        errors.append(
            f"Current version {manifest_version} release-notes row has no explicit status"
        )


def main() -> int:
    errors: list[str] = []
    _validate_registers(errors)
    _validate_json(errors)
    _validate_integration_structure(errors)
    _validate_frontend(errors)
    _validate_release_docs(errors)

    if errors:
        print("GW EnergyPilot repository validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("GW EnergyPilot repository validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
