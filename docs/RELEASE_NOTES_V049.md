# GW EnergyPilot v0.49 Beta

v0.49 consolidates the open reliability and operator-feedback work completed after v0.48. It makes EMHASS plan execution wall-clock deterministic, adds isolated soft EV charger load balancing and connectivity protection, strengthens Controller evidence, and closes several stable-DOM presentation gaps.

## Deterministic plan execution

- Full optimizations run on local 15-, 30- or 60-minute wall-clock boundaries at second 15; 15 minutes is recommended for new selections.
- The same serialized scheduler publishes a due saved-plan step through EMHASS `/action/publish-data` between full optimizations.
- A full optimization wins when both operations are due. Fresh finite `P_batt` and, for Grid/Hybrid, `P_grid` are required before Automatic Control evaluates the new step.
- EMHASS `continual_publish` is synchronized to `false`, leaving one schedule owner. A failed due step falls back to a still-valid mirrored point or moves enabled Automatic Control to Battery Hold.
- Nord Pool entity discovery now distinguishes an unavailable configured source from a genuinely missing source instead of misclassifying both as not configured.

## EV coordination and visibility

- Optional soft load balancing observes one configured phase-current entity and adjusts only one configured three-phase charger maximum-current NumberEntity after a continuous 1–15 minute overload or headroom window.
- Common Dutch connection profiles, custom limits, charger boundaries, an EV settings page, a diagnostic sensor and append-only acknowledgement history for configured maxima above 16 A are included.
- One compact header status reports Modbus, charger and effective coordination reachability. If an active charger becomes unavailable beyond the five-minute grace period, EV coordination is suspended rather than treating stale charging state as authoritative.
- The Controller card now states whether EV anti-discharge is blocking discharge, allowing an explicit charge request, waiting, or inactive.

The soft load balancer never writes GoodWe registers and never invokes Automatic Control or EMHASS. It is a best-effort guard, not a replacement for correctly rated wiring, breakers, charger protection or the main fuse.

## Controller and dashboard reliability

- The latest successfully completed EMS setpoint transaction is persisted and shown below the existing live setpoint. It advances only after the established `47512 -> wait -> 47511` sequence completes without a Modbus error.
- Battery · Plan · Price keeps the connected card shell, header, S/M/L controls and window bar while graph data refreshes, so a native click cannot be lost mid-refresh.
- Minimum and maximum SOC targets fall back to their canonical live Home Assistant entities when optional cached EMHASS settings data is absent.
- The Hybrid strategy explanation is no longer rebuilt by ordinary telemetry. Desktop Chromium, iPad WebKit and iPhone WebKit regressions require stable note/strong node identity, stable height and zero child-list mutations through repeated updates.

## Release scope

This release includes issues #91, #93, #94, #95, #96, #97, #98, #100 and #101. Issue #99 remains open with the `on hold` label: the reported post-background white screen could not be reproduced across the automated desktop/iPad/iPhone matrix or extended frozen/active stress probes, so v0.49 contains no speculative fix for it.

The active dashboard is `gw-energy-pilot-v049.js` over the complete v0.48 chain. Every import in the active module graph uses the fresh `0.49-consolidated1` cache boundary so upgraded browser sessions cannot retain pre-fix nested modules.

## Compatibility

No GoodWe register address, data type, sign convention, EMS mode mapping, non-negative setpoint rule or setpoint-before-mode write order changes. Existing entity unique IDs, device identity, accounting stores, plan mirror and Battery Saver ownership remain compatible. v0.49 adds only the documented controller-history and EV load-balancing audit stores.
