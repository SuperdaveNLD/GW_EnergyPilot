# GW EnergyPilot v0.30 Beta release notes

Release date: 2026-08-24

v0.30 standardizes how GW EnergyPilot versions are published to HACS and Home Assistant. The integration now ships with manifest/frontend version `0.30`, and the repository release workflow publishes a real GitHub Release whose numeric tag matches that version.

## Home Assistant / HACS version display

Earlier repository-only builds could be shown by HACS/Home Assistant using a shortened Git commit SHA such as `e4201e6`. v0.30 establishes the release contract needed for a normal version value:

```text
manifest version: 0.30
GitHub release:   0.30
HACS / HA:        0.30
```

GW EnergyPilot does not add a second Home Assistant `update` entity. HACS remains the owner of update discovery and installation; EnergyPilot supplies a consistent manifest version and published GitHub Release.

## Release validation and publishing

The release workflow validates the intended release before publication:

- the release/tag version must be numeric and match `manifest.json`;
- Python sources must compile;
- the unit test suite must pass;
- repository invariants must pass;
- HACS validation must pass;
- Hassfest validation must pass.

When a new manifest version reaches `main` and no matching GitHub Release exists yet, the workflow can create the matching release/tag after those checks succeed. Manual numeric tag publication remains supported and is checked against the manifest version as well.

## Frontend version

The active dashboard release wrapper is `gw-energy-pilot-v030.js`. It keeps the complete v0.29 dashboard underneath and reports `v0.30 BETA` in the EnergyPilot dashboard/footer.

## Safety and compatibility

- No new or guessed GoodWe Modbus registers.
- No Modbus read-block changes.
- No EMS mode mapping or write-order changes.
- EMS remains on `47511/47512` with the established `47512 -> wait -> 47511` order.
- No Home Assistant entity IDs or unique IDs are changed.
- No EMHASS optimization objective or control semantics are changed.
- EMHASS remains an external prerequisite and is not installed by GW EnergyPilot.
- v0.30 carries forward the complete v0.29 control, EMHASS synchronization, accounting, chart and diagnostics behavior.

v0.30 remains **Beta** while the standardized release/update presentation is validated through HACS and Home Assistant installations.
