# GW EnergyPilot v0.45 Beta

v0.45 consolidates the prepared PV insight and SOC-slider work with issues #83, #85 and #86 into one release. Issues #84 and #87 are intentionally excluded.

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

## Battery plan SOC (#85)

Battery · Plan · Price now shows actual GoodWe battery SOC from Recorder 5-minute means and forecast SOC from the exact single-battery `SOC_opt` column in the validated official EMHASS plan. Plan fractions are validated in `0..1` and normalized once to `0..100%`; invalid points and multi-battery-only columns are not guessed. Missing actual or planned SOC suppresses only the affected line.

## Static live-flow presentation (#86)

PV, grid, house and battery connectors now show fixed arrows for physical direction, relative low/medium/high pipeline thickness and explicit idle or unavailable markers. Direction continues to come from the existing physical flow model. Nodes are patched in place, expose localized accessible labels and add no animations or transitions.

## Floating Optimize action (#83)

The one canonical **Optimize now** action is safe-area-aware and fixed inside the viewport. It remains reachable during scrolling, while Settings is open and when the optional EMHASS card is hidden. It still calls the same Home Assistant button exactly once and preserves the v0.44 scoped busy/plan-refresh behavior.

## Upgrade and cache behavior

v0.45 adds `gw-energy-pilot-v045.js` as a version-only wrapper over the complete v0.44 behavior chain. Every import in the active frontend graph uses the new `0.45-integrated1` cache key so upgraded clients receive every included change as one coherent module graph.

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
- actual/forecast SOC presence, bounds and graph-only refresh;
- static-flow direction, intensity, unavailable/idle state, accessibility and node identity;
- floating Optimize viewport/safe-area/Settings reachability and one service call;
- inherited touch controls, plan refresh and native scrolling.

## Safety and compatibility

v0.45 does not change GoodWe registers, Modbus read blocks or writes, EMS mappings/write order, Automatic Control decisions, Battery Saver profile policy, EMHASS objective/configuration ownership, existing entity unique IDs, device identity or persistent Store keys.

EMHASS remains an external prerequisite and is not installed or replaced by EnergyPilot.

Issues #84 and #87 are not implemented, merged or released in v0.45.
