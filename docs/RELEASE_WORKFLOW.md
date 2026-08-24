# GW EnergyPilot release workflow

GW EnergyPilot uses published GitHub Releases as the canonical remote version source for HACS.

HACS uses the tag name of the latest published GitHub Release as the remote version. A Git tag without a published release is not sufficient; when no release is available, HACS can fall back to the first seven characters of the latest commit SHA. That fallback is why Home Assistant can show a value such as `e4201e6` instead of a normal GW EnergyPilot version.

## Version convention

Use numeric release tags that exactly match `custom_components/gw_energypilot/manifest.json`.

Examples:

```text
manifest version: 0.30
Git tag:          0.30
HACS/HA version:  0.30
```

Do not prefix the Git tag with `v` while the manifest uses an unprefixed version. Keeping both values identical avoids ambiguous update-version presentation.

## Automated release publishing

`.github/workflows/release.yml` runs for pushes to `main`, numeric version tags and manual workflow dispatches.

For a normal release, the manifest version is the release version. If no published GitHub Release exists for that version, the workflow validates the repository and creates the matching release/tag from the validated `main` commit. If the release already exists, publication work is skipped.

A manually pushed numeric tag remains supported. In that case the tag must exactly match the manifest version and the existing tag is verified before the GitHub Release is created.

Before a new GitHub Release is published the workflow verifies:

1. the manifest/release version is numeric;
2. a manually pushed tag, when used, exactly matches the integration manifest version;
3. Python sources compile;
4. the unit test suite passes;
5. `scripts/validate_repo.py` passes;
6. HACS validation passes;
7. Hassfest validation passes.

Only after all checks succeed is the GitHub Release created.

If `docs/RELEASE_NOTES_V<version-without-dots>.md` exists, that file is used as the GitHub release body. For version `0.30` this is:

```text
docs/RELEASE_NOTES_V030.md
```

If no dedicated release-notes file exists, GitHub generated release notes are used instead.

## Preparing a release

Before publishing a new release:

1. Set `custom_components/gw_energypilot/manifest.json` to the new numeric version.
2. Set the active frontend release wrapper/version badge to the same version.
3. Add the version entry to `CHANGELOG.md`.
4. Add the version status row and release section to `docs/RELEASE_NOTES.md`.
5. Add `docs/RELEASE_NOTES_V<version-without-dots>.md` with the user-facing release notes.
6. Merge the release changes to `main` after normal pull-request checks pass.
7. The release workflow validates the merged release commit and, when no matching release exists yet, creates the numeric Git tag and published GitHub Release.
8. Verify HACS/Home Assistant reports the numeric release as the available version instead of a commit SHA.

A manual numeric tag can still be used as a fallback, but it is no longer required for the normal release path.

## Ownership boundary

GW EnergyPilot does not add a duplicate Home Assistant `update` entity for this purpose. HACS remains responsible for installation/update discovery; GW EnergyPilot supplies a consistent manifest version and published GitHub Release for HACS to consume.
