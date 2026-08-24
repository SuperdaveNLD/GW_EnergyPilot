# GW EnergyPilot v0.30 Beta

Release date: 2026-08-24

v0.30 is a packaging and branding release built directly on the v0.29 runtime. It standardizes the GW EnergyPilot visual assets without changing GoodWe, EMHASS, accounting or entity behavior.

## Branding package

- Replaces the legacy 128×128 duplicate local brand images with correctly sized GW EnergyPilot assets.
- Adds 256×256 Home Assistant light/dark icons.
- Adds 512×512 `@2x` light/dark icons.
- Adds separate 800×256 light and dark landscape logos.
- Retains the existing square frontend SVG as the canonical scalable icon source.
- Adds light and dark landscape SVG wordmarks for EnergyPilot-owned frontend/documentation use.
- Documents the canonical GW EnergyPilot palette and asset ownership in `docs/BRANDING.md`.

## Package/version wiring

- Integration manifest version is `0.30`.
- The panel entrypoint is cache-busted through `gw-energy-pilot-v030.js?v=0.30-release1`.
- The v0.30 frontend wrapper retains the complete v0.29 frontend and changes only the visible release version to `v0.30 BETA`.

## Safety and compatibility

- No GoodWe register definitions or Modbus read blocks change.
- No EMS write behavior changes; registers remain `47511` / `47512` with the established write order.
- No Automatic Control strategy mapping changes.
- No EMHASS configuration, optimization objective or orchestration behavior changes.
- No entity IDs, unique IDs, device identifiers, config entries or persistent stores change.
- EMHASS remains an external prerequisite and is not installed by GW EnergyPilot.

v0.30 remains **Beta** because it inherits the v0.29 Beta runtime status. The branding changes themselves are presentation/package-only.
