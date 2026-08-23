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
INTEGRATION = ROOT / "custom_components" / "gw_energypilot"
FRONTEND = INTEGRATION / "frontend"
REGISTERS = INTEGRATION / "registers.py"
INIT = INTEGRATION / "__init__.py"
MANIFEST = INTEGRATION / "manifest.json"
CHANGELOG = ROOT / "CHANGELOG.md"
RELEASE_NOTES = ROOT / "docs" / "RELEASE_NOTES.md"

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
CHANGELOG_VERSION_RE = re.compile(r"^## \[(?P<version>\d+\.\d+)\]", re.MULTILINE)


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
    json_files = [ROOT / "hacs.json", *INTEGRATION.rglob("*.json")]
    for path in json_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as err:
            errors.append(f"Invalid JSON in {path.relative_to(ROOT)}: {err}")


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


def _validate_release_docs(errors: list[str]) -> None:
    """Require every changelog version to have a release-notes status row."""
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

    if manifest_version and manifest_version not in changelog_versions:
        errors.append(
            f"Manifest version {manifest_version} is missing from CHANGELOG.md"
        )

    for version in changelog_versions:
        marker = f"| **{version}** |"
        if marker not in release_text:
            errors.append(
                f"CHANGELOG version {version} is missing from docs/RELEASE_NOTES.md"
            )

    if manifest_version:
        current_marker = f"| **{manifest_version}** |"
        current_line = next(
            (line for line in release_text.splitlines() if line.startswith(current_marker)),
            None,
        )
        if current_line is None:
            errors.append(
                f"Current version {manifest_version} has no release-notes status row"
            )
        elif not any(
            status in current_line
            for status in ("**Beta**", "**Validated", "**Historical**")
        ):
            errors.append(
                f"Current version {manifest_version} release-notes row has no explicit status"
            )


def main() -> int:
    errors: list[str] = []
    _validate_registers(errors)
    _validate_json(errors)
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
