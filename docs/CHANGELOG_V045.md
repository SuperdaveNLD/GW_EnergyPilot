# GW EnergyPilot v0.45 changelog

## Added

- Added a dedicated dashboard PV settings page with the backwards-compatible internal GoodWe PV toggle and four searchable external Home Assistant power-entity inputs.
- Added the event-aware `pv_generation_power` sensor with unit normalization, availability filtering and per-source diagnostics.
- Added combined PV total/source presentation to the stable dashboard DOM and live-flow input.
- Added `docs/PV_INSIGHT.md` as the display-only PV ownership contract.
- Added actual Recorder-backed GoodWe SOC and validated single-battery EMHASS `SOC_opt` forecast to Battery · Plan · Price (#85).
- Added static physical-direction arrows, relative pipeline intensity and explicit idle/unavailable flow presentation with localized accessible labels (#86).

## Fixed

- Keep Battery Strategy SOC slider inputs and percentage labels on the user's local value during ordinary telemetry patches and Chrome focus loss.
- Retain the draft through asynchronous saving and release it after matching Home Assistant state acknowledgement or a failed write.
- Keep one Optimize action safe-area-aware, fixed and reachable independently of the optional EMHASS card (#83).

## Changed

- Added `gw-energy-pilot-v045.js` as the active version presentation wrapper over v0.44.
- Refreshed every active frontend import to the `0.45-integrated1` cache key so deep base/settings/stable-DOM changes load reliably after upgrade.
- Extended the deterministic desktop Chromium, iPad WebKit and iPhone WebKit matrix with PV-source, SOC-slider, SOC chart, static-flow and floating-Optimize regressions.

## Safety and compatibility

- PV insight remains display-only and cannot influence GoodWe/EMS control, EMHASS, plans or accounting.
- Existing entity unique IDs, config entries, device identity, GoodWe registers/writes and persistent Store contracts remain compatible.
- Issues #84 and #87 are explicitly excluded from the release scope.
