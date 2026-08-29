# GW EnergyPilot v0.45 Beta

v0.45 adds a display-only **PV insight** path for installations with internal GoodWe PV and optional external PV inverters, and fixes stale SOC percentages while a Battery Strategy slider is being adjusted in Chrome.

## PV sources and combined dashboard total

The dashboard settings now include a dedicated **PV** page. Operators can:

- include or exclude the canonical internal GoodWe PV total;
- select up to four Home Assistant power entities for external PV sources;
- see one combined PV total and a per-source breakdown on the PV card;
- keep live-flow presentation aligned with that display total.

The new `pv_generation_power` sensor normalizes supported W/kW/MW/mW source values and updates when either GoodWe telemetry or a configured external entity changes. Invalid, negative or unavailable external values do not contribute to the total.

This aggregate is deliberately presentation-only. It does not feed Automatic Control, EMS writes, EMHASS optimization/topology, persistent plan resilience or grid accounting. The existing `pv_total_power` entity and all existing unique IDs remain unchanged.

## Stable Battery Strategy SOC sliders

Moving a minimum/maximum SOC slider now creates an explicit local draft value. Ordinary telemetry patches keep both the range input and its percentage label on that draft, even when Chrome drops focus after the pointer becomes stationary or while the value is being saved.

The draft is cleared only after Home Assistant reports the requested value. A failed service call releases it so current backend state can become authoritative again.

## Upgrade and cache behavior

v0.45 adds `gw-energy-pilot-v045.js` as a version-only wrapper over the complete v0.44 behavior chain. Every import in the active frontend graph uses the new `0.45-pv-soc1` cache key so upgraded clients cannot retain pre-v0.45 base, settings, stable-DOM or strategy modules.

## Validation scope

- Python compile and complete unit suite;
- repository invariant validation;
- HACS and Hassfest validation on the exact release head;
- active-module cache-key traversal regression;
- desktop Chromium at 1440 × 900;
- iPad WebKit touch at 834 × 1112;
- iPhone WebKit touch at 390 × 844;
- combined/internal/external PV topology, values, settings and stable DOM;
- stationary/unfocused SOC slider draft plus Home Assistant acknowledgement;
- inherited touch controls, Optimize stability, plan refresh and native scrolling.

## Safety and compatibility

v0.45 does not change GoodWe registers, Modbus read blocks or writes, EMS mappings/write order, Automatic Control decisions, Battery Saver profile policy, EMHASS objective/configuration ownership, existing entity unique IDs, device identity or persistent Store keys.

EMHASS remains an external prerequisite and is not installed or replaced by EnergyPilot.
