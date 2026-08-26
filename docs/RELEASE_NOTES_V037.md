# GW EnergyPilot v0.37 Beta

v0.37 promotes the current dashboard-stability work into a clean numeric release for HACS/Home Assistant.

## What is included

- Retains the v0.36.2 mobile scroll-stability layer that preserves the actual Home Assistant scroll containers across relevant telemetry-driven full dashboard renders.
- Retains the interim v0.36.3 control-stability layer that reuses equivalent button DOM nodes across those renders, preventing periodic button flashing and preserving hover/focus while live values keep updating.
- Adds a dedicated v0.37 frontend wrapper and cache key so existing installations cannot retain an older 0.36.x frontend module after upgrading.
- Synchronizes the manifest, dashboard/footer version badge, changelog and release index to `0.37`.

## Why v0.37 instead of another 0.36.x patch

The 0.36.3 code reached `main`, but its manifest version was not added to the central changelog/release index. The repository release validator therefore could not publish a matching GitHub Release. v0.37 closes that metadata gap and publishes the complete current stable-control stack as one clean update.

## Compatibility and safety

- No GoodWe register definitions or Modbus read blocks change.
- No EMS mode mappings, setpoints or write ordering change.
- No Automatic Control behavior changes.
- No EMHASS optimizer/configuration ownership changes.
- No entity IDs, unique IDs, config-entry data, persistent Store keys or device identity change.
- GoodWe polling and live telemetry cadence remain unchanged.

## Validation

The normal release workflow compiles the integration, runs the unit tests and repository invariants, then runs HACS and Hassfest validation before publishing the numeric `0.37` GitHub Release.
