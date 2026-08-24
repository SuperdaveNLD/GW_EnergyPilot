# GW EnergyPilot v0.30 Beta

Release date: 2026-08-24

v0.30 combines the standardized GW EnergyPilot branding package with a bounded dashboard render-lifecycle fix on top of the v0.29 runtime. It does not change GoodWe, EMHASS, accounting or entity behavior.

## Dashboard stability — issue #46

A live frontend upgrade/session could create two **Battery · Plan · Price** cards after this sequence:

1. hide the chart with the red Apple/macOS-style card control;
2. open **Dashboard → Layout & visibility**;
3. re-enable **Battery & price**.

The root cause was the layered versioned frontend render chain. The v0.27 `installEnhancedCard()` helper always created a new enhanced card and only replaced the legacy v0.26 selector. If that render wrapper was invoked more than once in a cache-busted/live-upgrade browser session, a later invocation could append a second enhanced card.

v0.30 fixes the lifecycle at two levels:

- `installEnhancedCard()` is idempotent and removes extra `.ep-v027-battery-plan-card` instances before returning instead of appending another card;
- the v0.30 top-level wrapper performs a final reconciliation after the previous render chain and prefers the card already decorated with the v0.28 window controls when duplicates are already present in an open browser session.

The v0.30 wrapper also has its own prototype installation guard so it cannot stack the same release wrapper repeatedly in one session.

Existing S/M/L sizing, visibility preferences, chart refresh/data loading, detailed modal and Apple/macOS-style controls are preserved.

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
- The v0.30 frontend wrapper retains the complete v0.29 frontend, adds final duplicate-card reconciliation and reports `v0.30 BETA`.
- Regression coverage checks both the idempotent v0.27 installer and the v0.30 final reconciliation contract.

## Safety and compatibility

- No GoodWe register definitions or Modbus read blocks change.
- No EMS write behavior changes; registers remain `47511` / `47512` with the established write order.
- No Automatic Control strategy mapping changes.
- Battery remains `P_batt -> 11/12/8`; Grid remains `P_grid -> 9/10/1`; Hybrid remains mode-9 buying/import and mode-12 selling/discharge.
- No EMHASS configuration, optimization objective or orchestration behavior changes.
- No entity IDs, unique IDs, device identifiers, config entries or persistent stores change.
- EMHASS remains an external prerequisite and is not installed by GW EnergyPilot.

v0.30 remains **Beta** because it inherits the v0.29 Beta runtime status and the dashboard lifecycle fix/branding package still need live installation validation.
