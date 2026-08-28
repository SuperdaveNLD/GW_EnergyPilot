# GW EnergyPilot v0.42 Beta

v0.42 focuses on making the EMHASS configuration workflow easier to understand and diagnose while preserving the existing EnergyPilot, EMHASS and GoodWe control contracts.

## Operator-visible changes

- Reorganized the EMHASS settings page into **Connection & planning**, **Outputs** and **Price settings** sections.
- Added a compact **EMHASS status** summary showing connection state, configuration synchronization state and output configuration readiness.
- Moved the existing **Synchronize configuration** action into the status summary so a detected mismatch is immediately actionable.
- Added an **EMHASS configuration check** table with a friendly setting name, canonical EMHASS key, the value EnergyPilot requires, the value actually stored in EMHASS and an explicit **In sync / Differs** status.
- Kept the existing **Restore recommended defaults**, discard and save workflows intact.
- Clearly distinguishes editable EnergyPilot config-entry settings from values that are actually stored in EMHASS `config.json`, so EnergyPilot-only settings are not presented as EMHASS state.
- Retains Dutch and English presentation and responsive desktop, tablet and phone layouts.

## Architecture and ownership

The redesigned page is presentation-only. It reuses the existing `gw_energypilot/emhass_sync/get` data and the existing synchronization/default action handlers. No second EMHASS configuration reader or writer is introduced.

The active frontend entrypoint is `gw-energy-pilot-v042.js`. It is a thin release wrapper over the validated v0.41 stable-DOM runtime and the new EMHASS settings presentation layer, with fresh cache keys and a synchronized v0.42 dashboard/footer badge.

## Validation

The release candidate must pass the repository release gates before publication:

- Python/Node Quality suite and repository invariant validator;
- frontend architecture audit;
- HACS validation;
- Hassfest validation;
- real-browser stability matrix using desktop Chromium, iPad WebKit touch and iPhone WebKit touch profiles, including the redesigned EMHASS settings view.

## Safety and compatibility

v0.42 does not change:

- GoodWe register definitions or Modbus read blocks;
- EMS mode mappings, setpoint semantics or the established `47512 -> wait -> 47511` write order;
- Automatic Control decisions or Battery Saver optimization behavior;
- EMHASS synchronization ownership or introduce an additional write path;
- Home Assistant entity IDs, unique IDs, config-entry migrations, persistent Store keys or stable device identity.

EMHASS remains an external prerequisite and must already be installed and configured separately. GW EnergyPilot does not install EMHASS.
