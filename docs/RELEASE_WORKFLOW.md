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

`.github/workflows/release.yml` runs when a version-like Git tag is pushed.

Before a GitHub Release is published it verifies:

1. the tag is a numeric release version;
2. the tag exactly matches the integration manifest version;
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

## Preparing v0.30

Before publishing v0.30:

1. Set `custom_components/gw_energypilot/manifest.json` to `0.30`.
2. Set the active frontend release wrapper/version badge to `0.30`.
3. Add the `0.30` entry to `CHANGELOG.md`.
4. Add the `0.30` status row and release section to `docs/RELEASE_NOTES.md`.
5. Add `docs/RELEASE_NOTES_V030.md` with the user-facing release notes.
6. Merge the release changes to `main` and confirm normal CI is green.
7. Create and push tag `0.30` on the intended `main` commit.
8. Let the release workflow publish the GitHub Release.
9. Verify HACS/Home Assistant reports `0.30` as the available version instead of a commit SHA.

## Ownership boundary

GW EnergyPilot does not add a duplicate Home Assistant `update` entity for this purpose. HACS remains responsible for installation/update discovery; GW EnergyPilot supplies a consistent manifest version and published GitHub Release for HACS to consume.
