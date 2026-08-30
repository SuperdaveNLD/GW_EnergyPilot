# v1 release-note files

Every v1 GitHub Release must have one immutable, tag-specific source file in
this directory. The filename is the complete tag, including the leading `v`.

Beta example (`docs/releases/v1.1.0-beta.1.md`):

```markdown
# GW EnergyPilot v1.1.0-beta.1

**Channel:** Beta prerelease

User-visible changes, safety boundaries, upgrade notes and validation evidence.
```

Stable example (`docs/releases/v1.1.0.md`):

```markdown
# GW EnergyPilot v1.1.0

**Channel:** Stable

User-visible changes, safety boundaries, upgrade notes and validation evidence.
```

The release workflow rejects a missing file, a mismatched tag or the wrong
channel marker. Historical `0.x` notes keep their existing filenames.
