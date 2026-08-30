#!/usr/bin/env python3
"""Validate and describe the GW EnergyPilot v1 release contract.

The release workflow is deliberately tag driven. This module keeps tag,
manifest, channel, source-branch and release-note rules in one testable place.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "custom_components" / "gw_energypilot" / "manifest.json"
DEFAULT_NOTES_ROOT = ROOT / "docs" / "releases"

_NUMBER = r"(?:0|[1-9]\d*)"
STABLE_TAG_RE = re.compile(rf"^v1\.{_NUMBER}\.{_NUMBER}$")
BETA_TAG_RE = re.compile(rf"^v1\.{_NUMBER}\.{_NUMBER}-beta\.[1-9]\d*$")


class ReleaseContractError(ValueError):
    """Raised when a release does not satisfy the v1 channel contract."""


@dataclass(frozen=True)
class ReleaseContract:
    """Resolved immutable release metadata."""

    tag: str
    version: str
    channel: str
    prerelease: bool
    source_branch: str
    title: str
    notes_file: Path


def release_notes_file(notes_root: Path, tag: str) -> Path:
    """Return the canonical release-note path for a v1 tag."""
    return notes_root / f"{tag}.md"


def resolve_release_contract(
    tag: str,
    manifest_version: str,
    notes_root: Path = DEFAULT_NOTES_ROOT,
    require_notes: bool = True,
) -> ReleaseContract:
    """Resolve and validate a v1 stable or beta release."""
    if BETA_TAG_RE.fullmatch(tag):
        channel = "beta"
        prerelease = True
        source_branch = "beta"
        title = f"GW EnergyPilot {tag} (Beta)"
        channel_marker = "**Channel:** Beta prerelease"
    elif STABLE_TAG_RE.fullmatch(tag):
        channel = "stable"
        prerelease = False
        source_branch = "main"
        title = f"GW EnergyPilot {tag}"
        channel_marker = "**Channel:** Stable"
    else:
        raise ReleaseContractError(
            f"Invalid release tag {tag!r}; use v1.x.x-beta.N for beta or "
            "v1.x.x for stable"
        )

    version = tag[1:]
    if manifest_version != version:
        raise ReleaseContractError(
            f"Tag {tag!r} requires manifest version {version!r}, "
            f"found {manifest_version!r}"
        )

    notes_file = release_notes_file(notes_root, tag)
    if require_notes:
        if not notes_file.is_file():
            raise ReleaseContractError(f"Missing release notes: {notes_file}")
        notes = notes_file.read_text(encoding="utf-8")
        if tag not in notes:
            raise ReleaseContractError(
                f"Release notes {notes_file} do not mention {tag}"
            )
        if channel_marker not in notes:
            raise ReleaseContractError(
                f"Release notes {notes_file} must contain {channel_marker!r}"
            )

    return ReleaseContract(
        tag=tag,
        version=version,
        channel=channel,
        prerelease=prerelease,
        source_branch=source_branch,
        title=title,
        notes_file=notes_file,
    )


def _read_manifest_version(path: Path) -> str:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        raise ReleaseContractError(f"Unable to read manifest {path}: {err}") from err
    return str(manifest.get("version", "")).strip()


def _write_github_output(path: Path, contract: ReleaseContract) -> None:
    try:
        notes_file = contract.notes_file.relative_to(ROOT)
    except ValueError:
        notes_file = contract.notes_file
    values = {
        "tag": contract.tag,
        "version": contract.version,
        "channel": contract.channel,
        "prerelease": str(contract.prerelease).lower(),
        "source_branch": contract.source_branch,
        "title": contract.title,
        "notes_file": str(notes_file),
    }
    with path.open("a", encoding="utf-8") as output:
        for key, value in values.items():
            output.write(f"{key}={value}\n")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Validate one release tag and optionally emit GitHub Actions outputs."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--notes-root", type=Path, default=DEFAULT_NOTES_ROOT)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args(argv)

    try:
        contract = resolve_release_contract(
            args.tag,
            _read_manifest_version(args.manifest),
            args.notes_root,
        )
    except ReleaseContractError as err:
        parser.error(str(err))

    if args.github_output is not None:
        _write_github_output(args.github_output, contract)

    print(
        f"Validated {contract.channel} release {contract.tag} from "
        f"{contract.source_branch}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
