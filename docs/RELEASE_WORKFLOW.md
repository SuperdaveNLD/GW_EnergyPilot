# GW EnergyPilot release workflow

GW EnergyPilot has one Home Assistant integration, one HACS repository and two
release channels. The channels are release policy; they do not create another
`custom_components` directory, domain, config entry or update entity.

## Channel contract

| Channel | Source branch | Tag | Manifest version | GitHub Release | HACS default |
|---|---|---|---|---|---|
| Beta | `beta` | `v1.x.x-beta.N` | `1.x.x-beta.N` | Prerelease, never Latest | Ignored unless the repository's prerelease switch is on |
| Stable | `main` | `v1.x.x` | `1.x.x` | Normal Release and Latest | Offered to normal users |

`N` starts at 1 and increases for a given stable target. Tags and published
releases are immutable: never move, reuse or delete a published version. Fix a
bad release by preparing the next beta number or stable patch version.

The historical `0.x` tags and release notes remain untouched. In particular,
`0.50` is the last legacy Beta published as a normal GitHub Release. The new
contract begins with the production `v1.0.0` release. Any subsequent
`v1.x.x-beta.N` candidate is always a GitHub prerelease before its stable
promotion.

## Why normal users cannot receive a new beta accidentally

- `.github/workflows/release.yml` publishes only pushed `v1.*.*` tags. A push or
  merge to `beta` or `main` never publishes a release by itself.
- `scripts/release_contract.py` derives the channel from the complete tag and
  rejects a tag that does not match the manifest version.
- A beta tag must point to the exact remote `beta` head. A stable tag must point
  to the exact remote `main` head.
- Beta publication always passes `--prerelease --latest=false`; stable
  publication passes `--latest` and never passes `--prerelease`.
- `hacs.json` hides the unversioned default branch. HACS users choose published
  releases, not whatever happens to be at the tip of `main`.
- All validation runs before the workflow receives write permission. The
  publication job alone has `contents: write`.

HACS uses published GitHub Releases as the remote version source. A tag without
a published release is not an installable channel release.

## Branch policy

`main` is the v1 production line. `beta` is the integration line for the next
candidate. Short-lived `codex/*`, feature and fix branches merge through pull
requests; they are never release sources.

Protect both `main` and `beta` on GitHub:

1. require pull requests and resolved conversations;
2. block force pushes and branch deletion;
3. require Quality, HACS validation and hassfest;
4. require the frontend audit/browser matrix for frontend changes;
5. restrict direct pushes where repository administration permits it.

Do not configure the tag workflow as a required branch check: it intentionally
runs only after a release tag is pushed. GitHub currently has no branch
protection on `main`; enabling the rules above is an external repository-owner
step.

## Version and documentation files

For every v1 release, synchronize:

- `custom_components/gw_energypilot/manifest.json` without a leading `v`;
- the active frontend `VERSION`, module and cache boundary;
- `CHANGELOG.md`;
- the version/status row in `docs/RELEASE_NOTES.md`;
- README status/highlights when the current public version changes;
- `docs/releases/<complete-tag>.md` using the channel marker documented in
  `docs/releases/README.md`.

Examples:

```text
tag                         manifest version
v1.0.0-beta.1              1.0.0-beta.1
v1.0.0                     1.0.0
```

The `v` belongs to the Git tag, not the Home Assistant manifest version.

## Prepare and publish a beta

The repository owner performs these steps only after the release changes are
merged into `beta` and all required checks are green:

```bash
git switch beta
git pull --ff-only origin beta
python -m compileall -q custom_components/gw_energypilot scripts tests
python -m unittest discover -s tests -v
python scripts/validate_repo.py
python scripts/release_contract.py --tag v1.1.0-beta.1
git tag -a v1.1.0-beta.1 -m "GW EnergyPilot v1.1.0-beta.1"
git push origin v1.1.0-beta.1
```

Push the `beta` branch before its tag. The workflow verifies the remote branch
head, repeats repository, HACS and hassfest checks on the tagged commit, and
then creates the GitHub prerelease. If validation fails, do not move the tag;
fix forward with the next beta number.

## Promote a beta to stable

Promote through a pull request from `beta` to `main`. Keep runtime behavior the
same as the approved candidate, remove only the prerelease suffix, and update
the stable release documentation/cache version. After the exact `main` commit
is green and merged:

```bash
git switch main
git pull --ff-only origin main
python -m compileall -q custom_components/gw_energypilot scripts tests
python -m unittest discover -s tests -v
python scripts/validate_repo.py
python scripts/release_contract.py --tag v1.1.0
git tag -a v1.1.0 -m "GW EnergyPilot v1.1.0"
git push origin v1.1.0
```

The workflow verifies that the tag is the exact remote `main` head and creates
a normal/latest GitHub Release only after every gate succeeds.

## HACS selection in Home Assistant

Normal users leave the GW EnergyPilot prerelease switch disabled or off. Their
HACS update entity ignores GitHub prereleases and follows the latest stable
`v1.x.x` release. During a migration they remain on the last normal release and
still ignore every new v1 beta until a newer stable is published.

Testers opt in per repository:

1. open **Settings → Devices & services → Entities** in Home Assistant;
2. display disabled entities and enable the HACS-provided prerelease switch for
   GW EnergyPilot if it is disabled;
3. turn that switch on;
4. refresh HACS/update information and install the offered
   `v1.x.x-beta.N`, or use the GW EnergyPilot HACS repository's version picker
   to select a specific published prerelease;
5. turn the switch off again to return future update checks to stable only.

Turning the switch off changes update selection; it does not automatically
downgrade an already installed beta. Select the desired stable release in the
HACS version picker if an immediate downgrade is required, then restart Home
Assistant as HACS requests.

## Ownership boundary

HACS remains responsible for install/update discovery. GW EnergyPilot does not
add a duplicate Home Assistant update entity or a second integration/domain for
the beta channel.
