# Changelog

All notable changes to GW EnergyPilot are documented here.

## [Unreleased]

## [0.51] - 2026-08-30

### Added

- Added a bounded per-entry execution-history Store and one stable-DOM
  EMHASS → GOODWE card with a compact ±6-hour view plus full 48-hour history
  and conditional 24-hour projection (#108).
- Added immutable plan/config/actual/write/read-back snapshots and explicit
  completed, verified, mismatched, unavailable, failed, skipped and waiting
  outcomes.
- Added Recorder-based grid/solar charge and battery/solar export attribution
  in Large/expanded chart views, retaining unknown residuals.
- Added historical wanted-SOC snapshots to the existing dashed line.

### Changed

- Shared one pure Battery/Grid/Hybrid/EV decision mapping between live control
  and future read-only projections without changing its established outputs.
- Advanced the battery/plan chart payload to schema 6 and added optional
  dashboard-only official-plan `P_PV`/`P_Load` values.
- Added `gw-energy-pilot-v051.js` and the complete `0.51-h1` frontend cache
  boundary.

### Safety and compatibility

- Keep EMHASS as plan owner and preserve GoodWe registers, setpoint-before-mode
  ordering, controller ownership, entity/device identity, accounting and
  Battery Saver policy.
- Treat source attribution as an estimate and execution persistence as
  non-controlling evidence. Existing installs start with empty history and
  require no migration.

## [0.50] - 2026-08-30

### Changed

- EV load balancing now reads GoodWe meter L1/L2/L3 automatically. One-phase
  chargers use the configured phase and three-phase chargers guard the highest
  phase, removing the former manual phase-current entity.
- Charger current-limit control and allocated-current feedback are separate.
  Applied commands are checked with a tolerance and report a feedback mismatch
  after the bounded confirmation window.
- New/unset load-balancing windows default to 15 minutes to respect Zaptec's
  recommended maximum update frequency; existing stored windows are unchanged.

### Fixed

- Accept `ev_online_entity` in the EV settings API and auto-link unambiguous
  Zaptec control/feedback entities through Home Assistant registry relations.

## [0.49] - 2026-08-30

### Added

- Added opt-in soft house-connection load balancing for one three-phase EV
  charger. It observes one configured phase-current entity, waits for a
  continuous configurable 1–15 minute overload/headroom window, and adjusts only
  one configured charger maximum-current NumberEntity (#94).
- Added an EV settings tab with common Dutch one-/three-phase connection
  profiles, custom profiles, charger minimum/maximum boundaries and a dedicated
  diagnostic sensor.
- Added a second confirmation gate and append-only per-entry audit history for
  newly configured charger maxima above the normal 16 A boundary.
- Persist the timestamp and context of the latest successfully completed EMS setpoint write, expose it through existing controller diagnostics and LOG/support output, and show the localized time beneath the live EMS setpoint without rebuilding the Controller card (#96).
- Added one serialized wall-clock scheduler for 15/30/60-minute full optimizations and due saved-plan publication, with fresh-output gates and Battery Hold failure safety (#98).
- Added compact Modbus/charger/coordination reachability plus a five-minute stale-charger EV-coordination suspension guard (#95).
- Added explicit Controller feedback for blocking, charging, waiting and inactive EV anti-discharge decisions (#91).

### Fixed

- Distinguish a configured-but-unavailable Nord Pool price entity from a source that is not configured (#93).
- Preserve the Battery · Plan · Price card shell, header, S/M/L controls and window bar through scoped graph refresh (#97).
- Use canonical live Home Assistant minimum/maximum SOC entities when cached EMHASS settings data is absent (#100).
- Keep the Hybrid strategy explanation node and height stable during ordinary telemetry while still refreshing it for real language/strategy changes (#101).

### Safety and compatibility

- The EV load balancer never calls GoodWe, Modbus EMS, Automatic Control or
  EMHASS. Invalid measurements fail without a charger write; unrelated settings
  saves preserve all EV load-balancing options.
- This is a best-effort soft guard, not a replacement for correctly rated wiring,
  breakers, charger protection or the main fuse. The first implementation sees
  one phase and controls all three charger phases together.
- The EMS timestamp advances only after the established `47512 -> wait -> 47511` command completes without a Modbus error. Read-back-matched no-op evaluations and failed commands do not advance it; EMS mapping, write order, entity unique IDs and controller ownership are unchanged.
- EMHASS `continual_publish` is synchronized to `false`; EnergyPilot is the sole plan schedule owner and never evaluates a partially published `P_batt`/`P_grid` pair.
- Issue #99 remains open/on hold and is intentionally excluded because the reported white screen could not be reproduced.

## [0.48] - 2026-08-30

### Fixed

- Corrected Hybrid Automatic Control so a neutral `P_batt` plan is evaluated first and always selects mode `8` Hold, regardless of ordinary forecast/actual grid import or PV export.
- Corrected every non-neutral Hybrid plan to follow signed `P_grid`: mode `1` inside the configured deadband, mode `9` for import and mode `10` for export.
- Kept the control deadband fully variable per config entry. Exact positive/negative boundaries remain neutral, and the deadband selects the branch without being subtracted from the mode-9/10 setpoint.
- Added regressions for neutral-plan import/export, zero-grid self-use, signed mode-9/10 targets, configurable exact boundaries, complete setpoint magnitude and maximum-power clamping.
- Replaced the inherited 9/12 Hybrid operator text with current English and Dutch 8/1/9/10 guidance.

### Safety and compatibility

- EV anti-discharge remains a higher-priority override. Battery/Grid strategies, manual EMS commands, GoodWe registers, non-negative setpoints, write ordering, entity identity, Store keys, EMHASS policy and v0.47 Battery Saver behavior are unchanged.

## [0.47] - 2026-08-29

### Added

- Added a first-class **Custom / Aangepast** Battery Saver editor to both the dashboard and Settings → EMHASS. Administrators can edit the five non-negative EMHASS battery cost values in one transaction and immediately rebuild the plan; the complete previous Battery Saver configuration is restored if saving or the first optimization fails.
- Archived the preserved Gold Rush field baseline used to validate the profile tuning.

### Changed

- Increased Battery Strategy and Battery Saver settings typography, including profile descriptions, status text, custom field labels and values, while retaining the stable-DOM and native touch-scroll contracts.
- Retuned Gold Rush after preserved baseline and follow-up field comparisons: its per-direction anti-churn factor increases from `2.25%` to `6% × dynamic price reference`, while its battery power-stress factor decreases from `3%` to `1% × dynamic price reference`. The 6% run removed the low-value 765 W, 857 W and 426 W short reversals, retained profitable 15 kW dispatch and reduced the comparable modeled objective by `0.026`.
- Applied the same 6% anti-churn floor to the preservation-oriented Balanced and Battery Saver profiles while retaining their existing low-SOC and 8%/20% power-stress policy. Mad-Steve deliberately remains at 2.25% for maximum economic freedom.
- Replaced the profile-specific 96%/95%/90% hard upper limits with a 100% hard maximum for every managed profile and a shared soft red zone above 95%. The hourly EMHASS surplus-cost factors are now 5% / 10% / 25% / 50% for Mad-Steve / Gold Rush / Balanced / Battery Saver, allowing a profitable move to 100% while discouraging prolonged high-SOC dwell.
- Kept `battery_charge_efficiency` and `battery_discharge_efficiency` installation-owned and unchanged by profile selection.
- Added the presentation-only `gw-energy-pilot-v047.js` wrapper and refreshed the complete active frontend graph with the `0.47-custom-battery1` cache key.

### Safety and compatibility

- Custom editing remains administrator-only and single-battery-only, validates finite non-negative values, preserves EMHASS scalar/list shapes and writes the complete merged configuration.
- Minimum/Maximum SOC entities, unrelated EMHASS configuration, inverter topology, battery efficiency, GoodWe registers/writes, EMS control, entity identity, Store keys, plan resilience and accounting remain under their existing owners.

## [0.46] - 2026-08-29

### Added

- Added an independent **Include external PV** master switch with backwards-compatible activation for existing v0.45 external-source configurations.

### Fixed

- Keep native dashboard presses connected when Home Assistant repeats `narrow` or assigns a cloned-but-equivalent panel configuration; genuine nested configuration changes still trigger a structural render (#84).
- Keep Battery quick actions, EMHASS cost-function selection/busy state and manual EMS feedback stable through delayed or split entity publication, including duplicate-tap prevention during an active EMHASS optimization (#84).

### Changed

- Grouped all four external PV entity fields inside one panel and made their enabled/dimmed state follow the master switch immediately without a full dashboard render.
- Preserved configured external entity IDs while external PV is disabled; disabled sources are not tracked or added to `pv_generation_power`.
- Refined static live-flow connectors with integrated arrowheads, directional brightness, restrained 3/4/5-pixel intensity steps and quieter idle/unavailable styling while preserving the no-motion contract.
- Compacted the twelve-mode manual EMS pad under automatic ownership while preserving and correctly re-enabling the same controls after Automatic Control is turned off (#87).
- Added the v0.46 release wrapper, fresh `0.46-external-pv1` active-graph cache key and Chromium/WebKit switch/layout regressions.

### Safety and compatibility

- The v0.46 changes are limited to dashboard presentation, source selection and interaction stability. No GoodWe register/write, EMS/Automatic Control decision, EMHASS objective/topology, plan, entity identity, Store or accounting behavior changes.

## [0.45] - 2026-08-29

### Added

- Added a dedicated dashboard **PV** configuration tab with the backwards-compatible internal GoodWe PV toggle and four searchable external Home Assistant power-entity inputs.
- Added one event-aware `pv_generation_power` sensor that normalizes valid non-negative W/kW/MW/mW sources, exposes a per-source breakdown and drives the dashboard PV total/source presentation.
- Added `docs/PV_INSIGHT.md` and English/Dutch entity/dashboard copy for the read-only PV insight contract.
- Added actual GoodWe SOC and validated single-battery EMHASS `SOC_opt` forecast to Battery · Plan · Price on a fixed 0–100% axis (#85).
- Added static, accessible live-flow arrows with relative intensity and explicit idle/unavailable presentation (#86).

### Fixed

- Keep the locally selected Battery Strategy SOC slider value and percentage visible during normal telemetry patches, including after Chrome drops range-input focus, until Home Assistant confirms the saved value.
- Keep one Optimize action viewport-reachable as a safe-area-aware floating control, independent of the optional EMHASS card (#83).

### Changed

- Added `gw-energy-pilot-v045.js` as the active version-only wrapper and refreshed the complete active frontend dependency graph with the `0.45-integrated1` cache key.
- Extended the desktop Chromium, iPad WebKit and iPhone WebKit matrix with PV-source/settings and stationary SOC-slider acknowledgement regressions.
- Extended the same matrix with actual/forecast SOC, static-flow direction/state/accessibility and floating-Optimize reachability regressions.

### Safety and compatibility

- PV insight is presentation-only. It does not change GoodWe registers/read blocks, EMS writes, Automatic Control, EMHASS optimization/topology, persistent plan behavior or grid accounting.
- Existing installations keep internal GoodWe PV enabled by default, retain all existing entity unique IDs and receive one new deterministic `{config_entry_id}_pv_generation_power` entity.
- Ordinary PV telemetry patches existing dashboard nodes; only a configured PV-source topology change is structural.
- Issues #84 and #87 are explicitly excluded from this release and remain outside the v0.45 code scope.

## [0.44] - 2026-08-28

### Fixed

- Replaced the inherited Optimize-now listener that requested a complete dashboard render after the solve/publish service returned. v0.44 calls the same Home Assistant button entity exactly once and patches busy/idle state, orchestrator diagnostics and errors in place.
- Added a real first post-restart optimization callback for native orchestration. The previous candidate contained retry behavior but never scheduled its initial invocation through the active `orchestrator_v012 -> v033` chain.

### Changed

- Added `gw-energy-pilot-v044.js` over the complete v0.43 chain. A targeted Battery · Plan · Price refresh may still replace the canonical graph card, but `main`, Optimize now, layout, Automatic Control and Battery Strategy remain connected throughout the transaction.
- Added `orchestrator_v044.py`, which schedules one non-blocking recovery attempt after 60 seconds and retries transient Home Assistant/GoodWe/EMHASS startup dependency failures after 15, 30 and 60 seconds.
- Skip the remaining startup recovery sequence when any manual, scheduled or event-driven EnergyPilot optimization has already succeeded after setup. Exhausted retries fall back to the unchanged periodic schedule.
- Extended the deterministic desktop Chromium, iPad WebKit and iPhone WebKit matrix with exact Optimize service-count, zero-full-render, stable-node, native-scroll-anchor and post-optimization scroll assertions.

### Safety and compatibility

- No GoodWe register, Modbus read/write, EMS mode/setpoint/write order, Automatic Control decision, Battery Saver/EMHASS objective, entity ID, unique ID, config-entry data or persistent Store contract change.
- Home Assistant config-entry setup remains non-blocking; the delayed optimization uses the existing readiness, telemetry, health, finite-output, optimization-lock, plan-mirror and `plan_revision` contracts.

## [0.43] - 2026-08-28

### Fixed

- Prevented sticky native `:hover` on coarse-pointer/touch devices from making Optimize now, EMHASS Profit/Cost/Self-consumption, Battery Strategy, quick-action/max-export and layout-menu controls look active after the actual selection had moved elsewhere.
- Restored each affected inactive control's base presentation inside a touch-only media query, so `.active` and `aria-pressed="true"` remain the only selected-state owners.

### Changed

- Added `gw-energy-pilot-v043.js` as a frontend-only release layer over the unchanged v0.42 entrypoint, with a fresh cache key and v0.43 dashboard/footer version presentation.
- Extended the deterministic browser harness with repeated real taps, action-call evidence, exactly-one-selection assertions, menu cycles, concurrent telemetry and a deliberate structural render during a press.

### Safety and compatibility

- Does not intercept touch/pointer events, capture pointers, cancel native scrolling or change click/service/WebSocket handlers.
- No backend API, GoodWe register or Modbus path, EMS mode/write order, Automatic Control decision, EMHASS optimization/configuration ownership, entity identity, config-entry data or persistent state change.

## [0.41] - 2026-08-27

### Fixed

- Replaced normal telemetry-driven full ShadowRoot rebuilds with in-place updates of existing dashboard values, classes, attributes and meter widths, so the page, buttons and scroll container remain stable while GoodWe and EMHASS states change.
- Removed the inherited v0.38 pointer/render guard and mobile scroll snapshot restoration from the active v0.41 telemetry path. Native browser/WebView scrolling now owns the viewport without delayed EnergyPilot writes of an older `scrollTop`.
- Scoped Battery Strategy loading/apply feedback to the strategy section and scoped Battery · Plan · Price updates to the graph card, preventing either action from rebuilding unrelated controls.
- Fixed re-entrant graph refresh while a plan request is starting by treating both the loading flag and active promise as one busy state.
- Disabled EnergyPilot animations, transitions, moving flow particles and modal backdrop filters in v0.41, including pseudo-elements and late-added graph/modal content.

### Changed

- Added `gw-energy-pilot-v041.js` as the active frontend entrypoint with a stable-DOM telemetry contract.
- Limited complete structural renders to first initialization and genuine context/structure changes such as language, user/theme, entity-registry or optional-card topology changes.
- Added fresh nested module cache keys for every modified runtime, strategy and graph module so a v0.40 browser cache cannot retain an older implementation after upgrade.
- Added deterministic real-browser regressions for desktop Chromium, iPad WebKit touch and iPhone WebKit touch.
- Added `docs/FRONTEND_STABLE_DOM.md` as the persistent frontend architecture decision.

### Validation

- Desktop Chromium: 1440 × 900.
- iPad WebKit touch profile: 834 × 1112.
- iPhone WebKit touch profile: 390 × 844.
- The matrix verifies stable DOM identity during telemetry, monotonic scrolling, zero idle scroll drift, menu open/close, two Automatic Control toggles, Battery Strategy apply, graph-only plan refresh, Dutch structural localization, controls after a deliberate structural render, zero active EnergyPilot animations/transitions, no JavaScript errors and no unknown WebSocket calls.
- Full Python/Node Quality suite, repository validator, frontend architecture audit, HACS validation and Hassfest validation remain required gates.

### Safety and compatibility

- No GoodWe register, Modbus read block, EMS mode/setpoint/write order, Automatic Control decision, EMHASS optimization/configuration ownership, entity ID, unique ID, config-entry data, persistent Store key or stable device identity changes.
- v0.38-v0.40 compatibility behavior remains available in its historical modules; only the active v0.41 runtime bypasses their legacy interaction and scroll-restoration guards.

## [0.40] - 2026-08-26

### Fixed

- Stabilized the remaining dashboard, menu and card-window controls that could visibly blink when a relevant Home Assistant update rebuilt the complete ShadowRoot under a stationary pointer.
- Prevented recreated layout/menu controls, switches, Automatic Control presentation and card window buttons from replaying their CSS transition from a fresh non-hovered DOM node on every telemetry-driven render.

### Changed

- Added `gw-energy-pilot-v040.js` as a thin render-settle/release layer over v0.39. It temporarily suppresses CSS **transitions** on interactive controls while the inherited synchronous ShadowRoot rebuild settles, then restores normal transitions after the rebuilt controls have painted once.
- Uses a persistent `adoptedStyleSheets` rule where supported, with an ordinary ShadowRoot style fallback, and a render-generation guard so rapid consecutive renders cannot release a newer settle window early.
- Keeps the v0.38 relevant-state render filtering, live telemetry cadence, active-press guard, mobile scroll preservation, delegated Battery Strategy actions and v0.39 strategy-hover continuity unchanged.

### Safety / compatibility

- Frontend-only release; no GoodWe register definitions, Modbus read blocks, EMS mappings, setpoint semantics or `47512 -> wait -> 47511` write ordering change.
- No Automatic Control decision, EMHASS optimization/topology/Battery Saver behavior, entity ID, unique ID, config-entry data, persistent Store key or stable device identity change.
- v0.40 does not restore the removed v0.35 hover/render lock, does not capture pointers and does not transplant old button DOM nodes/listener closures.

## [0.39] - 2026-08-26

### Fixed

- Fixed the remaining Battery Strategy hover flicker caused by native CSS `:hover` dropping while the inherited full ShadowRoot render briefly detaches and reinserts the reused v0.38 strategy node.
- Completed Dutch localization of the customer Controller card, including inherited controller labels, GoodWe mode names/tooltips, manual EMS status copy, automatic-strategy fallback text, profile descriptions and telemetry presentation.

### Changed

- Added `gw-energy-pilot-v039.js` as a thin release/version wrapper over the merged v0.38 control/localization chain with a fresh browser cache key.
- Kept the hover continuity presentation-only: it does not defer telemetry renders, capture pointers or restore the removed v0.35 hover/render lock.
- Updated release regression coverage and maintainer documentation for the active v0.39 -> v0.38 frontend chain.

### Safety / compatibility

- Frontend-only release; no GoodWe register definitions, Modbus read blocks, EMS mappings, setpoint semantics or `47512 -> wait -> 47511` write ordering change.
- No Automatic Control decision, EMHASS optimization/topology/Battery Saver behavior, entity ID, unique ID, config-entry data, persistent Store key or stable device identity change.

## [0.38] - 2026-08-26

### Fixed

- Rebuilt Battery Strategy controls around stable backend profile keys and `aria-pressed`; visible English/Dutch text no longer participates in action identity or active highlighting.
- Removed the v0.35 pointer/render lock and v0.36.3 old-button DOM-node reuse from the fresh active frontend chain instead of stacking another stability patch over v0.37.
- Replaced per-node strategy actions with one delegated listener on the persistent ShadowRoot, preventing stale listeners from being transplanted into a newly rendered dashboard.
- Added bounded pointer/keyboard completion and preserved native touch scrolling/mobile scroll restoration without pointer capture.
- Replaced stacked live-flow `inbound`/`outbound` and `animation-direction` reversal interactions with one explicit physical v0.38 motion mapping and dedicated keyframes.

### Changed

- Added the isolated `gw-energy-pilot-v038-*` frontend modules for model/localization, strategy controls, styles and runtime rendering.
- Added executable Node.js regression tests to the normal Quality workflow for Dutch/English canonical profile keys, delegated profile clicks, immediate control re-enable behavior and all physical PV/grid/house/battery flow cases.
- Fresh v0.38 sessions load the v0.38 runtime directly over the known v0.34 feature base. Historical v0.35/v0.36.x/v0.37 wrapper files remain in the repository but are not part of the fresh v0.38 active path.
- Added dedicated frontend architecture and v0.38 release documentation.

### Safety / compatibility

- Frontend-only release; no GoodWe register definitions or Modbus read blocks change.
- No EMS mode mapping, setpoint semantics or `47512 -> wait -> 47511` write ordering change.
- No Automatic Control decision or EMHASS optimization/Battery Saver backend/configuration ownership behavior change.
- No entity IDs, unique IDs, config-entry data, persistent Store keys or stable device identity changes.

## [0.37] - 2026-08-26

### Changed

- Promoted the complete current dashboard-stability stack to a clean numeric `0.37` release for HACS/Home Assistant.
- Added `gw-energy-pilot-v037.js` as a release wrapper over the existing v0.36.3 control-stability layer, with a fresh cache key and synchronized dashboard/footer badge.
- Synchronized the integration manifest, release notes and release workflow inputs to `0.37`.
- The interim v0.36.3 code that reached `main` is carried forward unchanged; v0.37 fixes the missing release metadata that prevented that interim manifest version from passing the repository release validator and becoming a GitHub Release.

### Retained fixes

- Retains v0.36.2 mobile scroll-position preservation across relevant telemetry-driven full dashboard renders.
- Retains the v0.36.3 equivalent-button DOM-node reuse that prevents periodic control flashing while preserving hover/focus and live state updates.

### Safety / compatibility

- No GoodWe register definitions or Modbus read blocks change.
- No EMS mode mappings, setpoints or `47512 -> wait -> 47511` write ordering change.
- No Automatic Control or EMHASS optimization/configuration ownership behavior changes.
- No entity IDs, unique IDs, config-entry data, persistent Store keys or stable device identity changes.
- GoodWe polling and live telemetry cadence remain unchanged.

## [0.36.2] - 2026-08-26

### Fixed

- Fixed the remaining mobile viewport jump caused by periodic relevant Home Assistant state refreshes rebuilding the complete dashboard Shadow DOM while the user was scrolled around SOC Forecast / Battery Plan / strategy content.
- Added a top-level narrow/mobile scroll-stability layer that captures the actual composed Home Assistant scroll containers before a complete dashboard render and restores their exact positions after the full v0.36 customer-controller render chain.
- Restores scroll position immediately and across two animation frames so late layout and `ResizeObserver` settling cannot select a new browser/WebView scroll anchor.
- Disabled browser scroll anchoring for the EnergyPilot panel subtree on narrow/mobile layouts with `overflow-anchor: none`.

### Changed

- GoodWe coordinator polling and live telemetry refresh cadence remain unchanged; the hotfix stabilizes the viewport instead of slowing or suppressing inverter updates.
- The active frontend release is `gw-energy-pilot-v0362-scroll-stability.js`, layered over the complete v0.36.1 customer-controller and touch-interaction stack.
- Manifest/frontend cache wiring is bumped to `0.36.2` with regression coverage for composed scroll-container capture, post-render restoration and release wiring.

### Safety / compatibility

- Frontend-only hotfix; no GoodWe register definitions, Modbus read blocks, EMS mappings, Automatic Control behavior, EMHASS optimization/config ownership, entity IDs, unique IDs, config-entry data or stable device identity changes.

## [0.36.1] - 2026-08-26

### Fixed

- Fixed mobile Home Assistant scrolling over the v0.36 Battery strategy buttons by keeping touch gestures on the native vertical-pan path instead of pointer-capturing them as button presses.
- Deferred destructive dashboard rebuilds through a moved-touch settle window and added a pointer safety timeout so interrupted gestures cannot leave the frontend render-locked.

### Changed

- Touch movement at or above 8 px is classified as a scroll gesture for the v0.35 interaction guard; desktop mouse click protection is retained.
- Battery strategy buttons explicitly allow native vertical panning with `touch-action: pan-y`.
- Bumped manifest/frontend cache wiring to 0.36.1 and added mobile-scroll regression coverage.

### Safety / compatibility

- Frontend-only hotfix; no GoodWe register definitions, Modbus read blocks, EMS mappings, Automatic Control behavior, EMHASS optimization/config ownership, entity IDs, unique IDs or stable device identity changes.

## [0.36] - 2026-08-25

### Added

- Added a customer-facing **Battery strategy** selector to the Controller card with **Mad-Steve**, **Gold Rush**, **Balanced**, **Battery Saver** and **Custom** choices.
- Added an explicit **Custom** transition that releases EnergyPilot Battery Saver preset ownership while preserving the currently effective EMHASS battery values.
- Custom mode reuses the existing Home Assistant minimum/maximum SOC NumberEntities and shows the active low-SOC, high-SOC, power-stress and charge/discharge EMHASS battery costs read-only for transparency.
- Added regression coverage for strategy/Custom API ownership, immediate optimization, rollback, consolidated release wiring, live-flow responsiveness and render-storm protection.

### Fixed

- Fixed installation-dependent dashboard render storms by keeping every Home Assistant snapshot available while rebuilding the dashboard only for relevant EnergyPilot/EMHASS or locale/user/theme changes. Relevant bursts are batched for 80 ms.
- Fixed controls losing clicks during a concurrent relevant state update by deferring destructive Shadow DOM replacement only while an actual pointer/keyboard press is active.
- Fixed remaining live-flow double reversal by matching the specificity of the legacy two-class `animation-direction: reverse !important` selectors and leaving the established geometry-specific keyframes as the single direction mechanism.
- Fixed live-flow sizing on narrow Home Assistant panels by deriving node, hub, connector, stage and particle travel geometry from the measured card width. Compact/tight layouts track resize and phone rotation through `ResizeObserver` while wide desktop geometry remains unchanged.

### Changed

- The low-level controller command such as `hybrid_battery_discharge` is removed from the normal customer Controller presentation and remains available through Diagnostics/support output.
- Selecting any managed Battery Saver profile or Custom runs the existing complete EnergyPilot optimization/publish transaction. The existing `plan_revision` contract then invalidates the Battery · Plan · Price cache so the graph follows the fresh plan after every successful optimization.
- The active frontend release is `gw-energy-pilot-v036-customer-controller.js`, layered over the consolidated render guard and mobile live-flow fixes.
- The integration manifest version is `0.36` and the v0.36 frontend import chain uses release-specific cache keys.

### Safety / compatibility

- No new or guessed GoodWe register definitions or Modbus read blocks.
- EMS remains on `47511/47512` with the established `47512 -> wait -> 47511` write order.
- No Automatic Control EMS-mode mapping changes are introduced by the customer strategy UI or dashboard reliability work.
- No entity ID, unique ID or stable Home Assistant device identity changes.
- Existing SOC NumberEntities are reused; no duplicate sensors, settings or control paths are introduced.
- EMHASS remains the canonical optimizer and plan owner; Custom preserves current EMHASS values rather than silently resetting them.
- v0.36 remains **Beta** while the consolidated customer strategy UI and high-update/mobile frontend behavior receive broader field validation.

## [0.35] - 2026-08-25

### Fixed

- Stopped EnergyPilot from forcing EMHASS `inverter_is_hybrid = true` during explicit **Synchronize required config** operations.
- Stopped the automatic pre-optimization policy from re-forcing `inverter_is_hybrid = true` before every EnergyPilot-owned solve.
- Removed `inverter_is_hybrid` from the EMHASS synchronization API's managed-value list so the dashboard no longer presents installation topology as an EnergyPilot-owned requirement.

### Changed

- Added one canonical EnergyPilot EMHASS runtime contract shared by required-config synchronization and the automatic pre-solve path: `continual_publish = true`, `method_ts_round = first` and `set_use_battery = true`.
- `set_use_pv` and `inverter_is_hybrid` are explicitly installation-specific EMHASS settings. Existing `false`, `true` and missing topology values are preserved instead of inferred from the GoodWe hardware model.
- Added regression coverage for both configuration-write paths and for false/true/missing inverter-topology values.
- Added the v0.35 release wrapper and release documentation without changing the existing v0.34 dashboard behavior.

### Safety / compatibility

- No GoodWe register definition or Modbus read-block changes.
- No EMS mode mapping or `47512 -> wait -> 47511` write-order changes.
- No Automatic Control strategy changes.
- No entity ID, unique ID, stable device identity or persistent Store-key changes.
- Battery Saver v0.34 profile tuning, hard maximum SOC ownership and anti-churn settings remain unchanged.
- EMHASS remains the canonical optimizer and plan owner; v0.35 only corrects configuration ownership.

## [0.34] - 2026-08-25

### Added

- Added an explicit optimization `plan_revision` to the existing orchestrator/dashboard contract so every successful EnergyPilot optimization can deterministically invalidate the Battery · Plan · Price cache after the persistent EMHASS plan refresh attempt.
- Added a v0.34 frontend release wrapper that cache-busts both the updated Battery Saver module and the Battery Plan core for already-open Home Assistant browser sessions.
- Added profile-owned EMHASS hard maximum SOC values for explicitly managed Battery Saver modes: Mad-Steve 100%, Gold Rush 96%, Balanced 95% and Battery Saver/Eco 90%.

### Fixed

- Fixed Battery · Plan · Price not updating deterministically when the canonical persistent plan changed after an optimization without a sufficiently distinct `P_batt.last_updated` signal. The explicit plan revision now forces a read-only refresh while retaining the existing timestamp fallback for externally changed plans.
- Fixed EV anti-discharge behavior so an active EV session still pauses battery discharge/neutral operation through mode `8`, but no longer pauses a legitimate home-battery charge request.
- Fixed strategy bypass during EV charging: Battery control charges through mode `11`; Grid/Hybrid use mode `9` when a positive planned `P_grid` import target is available, with mode `11` as the explicit-charge fallback when required.

### Changed

- Increased the common Battery Saver charge/discharge anti-churn floor from `1.5%` to `2.25% × dynamic price reference` per direction based on field comparison, reducing low-value quarter-hour reversals while preserving high-value battery operation.
- Battery Saver maximum SOC is now part of the existing profile apply/rollback transaction. The verified GoodWe on-grid minimum SOC remains a separate lower-limit ownership layer.
- The active frontend release module is `gw-energy-pilot-v034.js` and reports v0.34 while loading fresh v0.34 cache keys for the modified nested frontend modules.

### Safety / compatibility

- No new or guessed GoodWe register definitions or Modbus read blocks.
- EMS remains on `47511/47512` with the established `47512 -> wait -> 47511` write order.
- No entity ID, unique ID or stable Home Assistant device identity changes.
- EMHASS remains the canonical optimizer and plan owner; the persistent EnergyPilot plan remains a resilience mirror only.
- The v0.33 optimizer-readiness, persistent-plan expiry and EV-stop fresh-optimization protections remain intact.
- EV coordination remains an anti-discharge guard only and does not control the EV charger or add a second fast power-control loop.
- v0.34 remains **Beta** while the combined chart-refresh, Battery Saver and EV-control changes receive broader live installation validation.

## [0.33] - 2026-08-25

### Added

- Added a per-config-entry persistent EMHASS plan mirror backed by Home Assistant Store. EnergyPilot reads the official EMHASS `GET /api/v1/plan` contract, validates `P_batt` / `P_grid` horizon points, infers the active timestep and stores an explicit `valid_until` boundary.
- Added plan continuity across Home Assistant restart, integration reload and temporary EMHASS Home Assistant entity publication gaps. Live configured `P_batt` / `P_grid` states remain first priority; the still-valid mirror is only a fallback.
- Added common Battery Saver anti-churn costs through EMHASS `weight_battery_charge` and `weight_battery_discharge`. All four EnergyPilot profiles apply `1.5% × dynamic price reference` per direction so very small quarter-hour spreads are less likely to cause a charge/discharge reversal.
- Added diagnostics for persistent-plan source, generation/validity timestamps and resolved plan values.

### Fixed

- Fixed false EMHASS `stale_output` failures when a newly published `P_batt` report has the same numeric state/attributes as the previous report. Freshness now prefers Home Assistant `State.last_reported`, with `last_updated` retained as a compatibility fallback.
- Fixed the Battery · Plan · Price card not rebuilding after a fresh optimization because the duplicate-card guard returned permanently on the existing canonical card. A newer active-plan timestamp now bypasses the normal chart cache and refreshes the canonical card without creating duplicates.
- Changed the **Gold Rush** high-SOC soft threshold from `98%` to **`96%`** while preserving its existing high-SOC penalty and hard-SOC ownership model.
- Current Mad-Steve no longer means unrestricted zero-cost micro-arbitrage: it keeps maximum economic freedom and zero SOC/power-stress penalties while still using the shared anti-churn transaction cost.

### Changed

- Battery Saver ownership expands from six to eight EMHASS fields by adding `weight_battery_charge` and `weight_battery_discharge`. Existing unmanaged/custom EMHASS values remain untouched until a user explicitly selects a profile, and failed first-apply transactions roll back all eight owned fields.
- Legacy all-zero EMHASS battery costs/weights are now identified as unrestricted legacy behavior rather than being described as behaviorally identical to current Mad-Steve.
- The battery chart payload uses schema `4` and prefers the validated persistent EMHASS plan horizon, with the existing Home Assistant schedule attributes retained as compatibility fallback.
- The active runtime uses `controller_v033.py` and `orchestrator_v033.py` on top of the existing controller/orchestrator contracts, and the active frontend wrapper is `gw-energy-pilot-v033.js`.

### Safety / compatibility

- No GoodWe register definition, Modbus read block, EMS mode mapping or `47512 -> wait -> 47511` write order changes.
- No existing entity ID, unique ID or stable Home Assistant device identity changes.
- EMHASS remains the canonical plan owner. `gw_energypilot.plan.<config_entry_id>` is a resilience mirror, not a second optimizer or configuration database.
- A persistent plan is never extrapolated beyond its final inferred timestep. An expired plan becomes unavailable rather than repeating a stale battery/grid command.
- An explicit live non-ready optimization status remains authoritative and is never bypassed by the mirror.
- Battery Saver still refuses multi-battery EMHASS ownership rather than scalar-overwriting heterogeneous battery configuration.
- v0.33 remains **Beta** while the persistent-plan recovery path and revised Battery Saver tuning receive broader live restart/reload and multi-installation validation.

## [0.32] - 2026-08-25

### Fixed

- Fixed the v0.31 EMHASS settings save regression caused by configuring Home Assistant `NumberSelector` with `step=0.0001`. Current Home Assistant requires a numeric selector step of at least `0.001`.
- Restored the supported `0.001` selector step without rounding typed BOX values, so tariff adjustments such as `0.0248` remain valid and are preserved.

### Changed

- The dashboard keeps a browser input increment of `0.0001` for convenient four-decimal tariff entry while the Home Assistant backend selector uses its supported `0.001` configuration step.
- Added a v0.32 frontend release wrapper and regression coverage for the split frontend/backend precision contract.

### Safety / compatibility

- No GoodWe register, Modbus block, EMS mapping, controller behavior, EMHASS optimization model, Battery Saver tuning, entity ID or unique ID changes.
- v0.32 is a focused compatibility hotfix on top of v0.31.

## [0.31] - 2026-08-24

### Added

- Added **Battery Saver** to dashboard Settings → EMHASS with four EnergyPilot-owned modes: **Mad-Steve**, **Gold Rush**, **Balanced** and **Battery Saver**.
- Added price-relative soft penalties for low SOC, high SOC and battery power stress while keeping the existing Minimum/Maximum SOC controls as hard limits.
- Added admin-only `gw_energypilot/battery_saver/get` and `gw_energypilot/battery_saver/set` APIs, explicit legacy/custom detection and failed-apply rollback for Battery Saver-owned EMHASS fields.
- Added `docs/BATTERY_SAVER.md` with the profile values, LFP design rationale, ownership model and runtime flow.
- Added an administrator-only **Debug session** to the existing dashboard LOG tab for high-detail problem analysis.
- Added a bounded, memory-only 1200-event debug buffer that is disabled by default, starts each capture with a complete runtime baseline and retains a stopped session until clear/reload/restart.
- Added observer hooks for full decoded GoodWe coordinator telemetry, poll health/errors, controller command/target/read-back, configured source state changes and EMHASS/orchestrator status transitions.
- Added canonical register address/type/scale metadata to the support snapshot without introducing any new or guessed register definitions.
- Added admin-only `gw_energypilot/debug_log/get`, `gw_energypilot/debug_log/set_enabled` and `gw_energypilot/debug_log/clear` WebSocket commands.
- Added **Copy debug report**, combining the debug session/current runtime snapshot with the existing persistent optimization history.
- Added EnergyPilot-styled traffic-light controls to all normal dashboard cards: hide, collapse and full-width.
- Added regression coverage for Battery Saver profile calculations, SOC clamping, EMHASS-version gating, zero-cost legacy detection, continual publication and battery-only EMHASS synchronization.

### Fixed

- Fixed stale 15-minute EMHASS targets by changing the required contract from `continual_publish = false` to **`continual_publish = true`**. EnergyPilot continues to own full optimization timing while EMHASS advances and republishes the saved plan at each optimization timestep.
- Fixed startup Minimum SOC ownership: the existing synchronized slider now uses the verified GoodWe on-grid minimum SOC as its source of truth and mirrors that floor to EMHASS instead of initializing from an arbitrary EMHASS value.
- Fixed runtime terminal SOC requests below/above hard limits by clamping EnergyPilot `soc_final` to the effective EMHASS minimum/maximum SOC before an owned solve.
- Fixed required EMHASS synchronization for battery-only installations. `set_use_pv` is no longer forced; PV mappings are required/synchronized only when the customer's EMHASS configuration enables PV.
- Fixed settings persistence so the separately managed Battery Saver mode survives normal Home Assistant options changes and generic EnergyPilot settings saves.

### Changed

- EnergyPilot-owned EMHASS optimizations now enforce the small runtime contract `continual_publish = true`, `method_ts_round = first`, `set_use_battery = true` and `inverter_is_hybrid = true` immediately before solving.
- `set_use_pv` remains customer/install-specific and is not an EnergyPilot-required value.
- Existing zero-penalty EMHASS installations are treated as Mad-Steve-like but remain unmanaged until a user explicitly selects a Battery Saver mode. Existing custom non-zero penalty settings are preserved on upgrade.
- Non-zero Battery Saver power-stress modes require EMHASS 0.18.1 or newer when the EMHASS version is known.
- The active v0.31 frontend is `gw-energy-pilot-v031-battery-saver.js`, layered over the debug and dashboard-window-control stack.
- The existing persistent 50-run optimization history remains unchanged and is presented below the temporary debug-session controls.

### Safety / compatibility

- Battery Saver changes EMHASS optimization preferences; it never directly writes a GoodWe EMS mode. Published targets continue through the existing Automatic Control path.
- No second EnergyPilot 15-minute publisher is added; EMHASS `continual_publish` owns current-row publication.
- Battery Saver refuses multi-battery EMHASS ownership rather than guessing per-battery mappings.
- Existing GoodWe EMS registers, write ordering, controller strategies, entity IDs, unique IDs and stable device identity are preserved.
- No new or guessed GoodWe register definitions or Modbus read blocks are introduced.
- Debug capture observes existing coordinator/controller/orchestrator signals; it does not add a second Modbus poller or control loop.
- Debug data is not written to Home Assistant Store, Recorder or config-entry data and disappears on integration unload/reload or Home Assistant restart.
- The configured GoodWe host/IP and EMHASS base URL are intentionally excluded from the debug report; configured entity IDs and diagnostic values are included for mapping/problem analysis.
- v0.31 remains **Beta** while Battery Saver tuning and the expanded support/dashboard workflow receive broader field validation.

## [0.30] - 2026-08-24

### Added

- Added standardized GitHub Release publishing so HACS/Home Assistant can use the numeric GW EnergyPilot release version instead of falling back to a shortened commit SHA.
- Added the v0.30 frontend release wrapper and synchronized dashboard/footer version badge.
- Added dedicated `docs/RELEASE_NOTES_V030.md` and `docs/RELEASE_WORKFLOW.md` documentation for the release/update contract.

### Changed

- The integration manifest version is now `0.30`.
- The release workflow validates that the release/tag version matches `manifest.json`, then runs compile, unit, repository, HACS and Hassfest checks before publication.
- A new manifest version merged to `main` can publish its matching numeric GitHub Release automatically; manually pushed numeric tags remain supported and are validated against the manifest version.
- HACS remains the owner of update discovery/installations; GW EnergyPilot does not add a duplicate Home Assistant `update` entity.

### Safety / compatibility

- No new or guessed GoodWe register definitions or Modbus read blocks.
- EMS remains on `47511/47512` with the established `47512 -> wait -> 47511` write order.
- No existing entity IDs, unique IDs, stable device identity, accounting/runtime/log store or EMHASS optimization contracts are changed.
- v0.30 carries forward the complete v0.29 control and dashboard behavior and remains **Beta** while the standardized release/update presentation is validated through HACS/Home Assistant.

## [0.29] - 2026-08-24

### Added

- Added **Restore recommended defaults** to the EMHASS settings page. It fills the EnergyPilot form with the current canonical defaults for review without saving automatically.
- Added administrator-triggered **Synchronize required config** for EMHASS. The workflow reads the complete live configuration, merges only EnergyPilot-required mappings, writes the complete configuration and verifies it with a second read.
- Added runtime Home Assistant entity-registry resolution for EnergyPilot PV total power, GoodWe load power, battery power and battery SOC so renamed entity IDs are synchronized instead of guessed.
- Added dedicated `docs/EMHASS_CONFIG_SYNC.md` and `docs/RELEASE_NOTES_V029.md` documentation for the synchronization contract, upgrade path and release scope.
- Added a v0.29 frontend release wrapper so HACS installations already on v0.28 receive an explicit new integration version.

### Fixed

- Added a final live-flow animation guard that forces the existing geometry-correct particle keyframes to use `animation-direction: normal`, preventing later frontend layers from reversing an already-correct direction a second time.
### Changed

- Canonical EnergyPilot EMHASS outputs remain `sensor.p_batt_forecast`, `sensor.p_grid_forecast` and `sensor.optim_status` with required state `Optimal`.
- EMHASS synchronization preserves unrelated configuration, custom PV forecast mappings and custom `var_model` values where safe; multi-battery sensor lists are not rewritten.
- Issue #22 is closed without a new EnergyPilot residual-grid-capacity allocator because the dynamic grid/import limit is already enforced by GoodWe itself.
- Issue #30 remains open: negative raw EMHASS SOC-related values are not guessed into percentages or silently rewritten until their exact semantics/source is established.
- v0.29 includes the complete v0.28 Hybrid 9/12 control, Battery · Plan · Price repairs, Max Charge SOC guard and Apple-style Battery/Plan window controls.

### Safety / compatibility

- No new or guessed GoodWe register definitions or Modbus read blocks.
- EMS remains on `47511/47512` with the established `47512 -> wait -> 47511` write order.
- EMHASS synchronization is an explicit administrator action and does not automatically run an optimization or write a GoodWe register.
- Existing entity IDs, unique IDs, stable device identity and persistent accounting/runtime/log store contracts remain unchanged.
- Battery control remains `P_batt -> 11/12/8`; Grid control remains `P_grid -> 9/10/1`; EV anti-discharge remains a higher-priority safety override.
- v0.29 remains **Beta** while the new EMHASS synchronization workflow and final flow-animation guard receive live installation validation.

## [0.28] - 2026-08-24

### Fixed

- Corrected **Hybrid control** to the intended asymmetric mapping: buying/import uses GoodWe mode `9` with the EMHASS `P_grid` import magnitude, while selling/discharging uses mode `12` with the EMHASS `P_batt` discharge magnitude.
- Hybrid no longer interprets buying as direct mode-11 battery charging or selling as mode-10 PCC export control.
- A neutral Hybrid battery plan remains mode `8` Battery Hold.
- A Hybrid battery-charge plan without planned grid import falls back to GoodWe mode `1` self-use so locally available PV can be absorbed without forcing the forecast-sized `P_batt` charge target.
- Fixed the Battery · Plan · Price future-plan parser to use current EMHASS `battery_scheduled_power`; legacy/custom `forecasts` remains a compatibility fallback.
- Fixed historical plan continuity at local midnight by retaining Home Assistant's `include_start_time_state` even when that state originated before 00:00.
- Fixed the active EMHASS schedule interval at NOW so a block that began a few minutes earlier is clipped rather than discarded.
- Fixed plan visibility by rendering dashed historical/future plan overlays above solid actual bars.
- Fixed missing-plan summaries so they show `—` rather than a fabricated `0.00 kWh`.
- Fixed zero/near-zero actual samples being shown as tiny discharge bars/tooltips.
- Changed timestamped market-price rendering to an interval step series instead of diagonal interpolation between discrete prices.
- Updated Hybrid and battery-plan regression coverage, chart schema/documentation and nested frontend cache-busting.

### Changed

- Native GoodWe `35208/35211` battery-day counters remain the headline charged/discharged values. Recorder 5-minute integration of instantaneous `35182` battery power is explicitly a separate comparison path and is not calibrated to force a match.
- The read-only battery chart payload uses schema version `3` and reports the detected EMHASS schedule attribute.

### Safety / compatibility

- Battery control remains `P_batt -> 11/12/8`; Grid control remains `P_grid -> 9/10/1`.
- EV anti-discharge remains a higher-priority safety override; manual EMS commands remain direct operator commands.
- No GoodWe register definitions, Modbus read blocks or `client.py` write ordering change. EMS remains `47511/47512` with `47512 -> wait -> 47511`.
- Chart/API changes are read-only; no EMHASS objective, entity ID/unique ID, stable device identity or accounting/runtime/log store changes.
- v0.28 remains **Beta** while the corrected Hybrid mapping and repaired plan/actual chart receive real-installation field validation.

## [0.27] - 2026-08-24

### Added

- Added **S / M / L** sizing for the Battery & Price dashboard card using an Apple-style segmented control stored in the existing browser-local dashboard preferences.
- Added historical active-plan visualization from the configured EnergyPilot `P_batt` entity history, showing the target that was actually published at each point in the day.
- Added the first future battery-plan visualization; v0.28 later corrects the current EMHASS schedule attribute contract to `battery_scheduled_power`.
- Added native GoodWe current-day battery energy values to the read-only chart payload using the already-decoded `35208` charge and `35211` discharge counters.
- Added pure battery-plan normalization helpers, regression tests and `docs/BATTERY_PLAN_CHART.md` / `docs/BATTERY_PLAN_CHART_TEST.md`.
- Added the compact Support presentation from the staged support-cleanup work: GoodWe telemetry, control ownership, optimizer health and minimum-SOC synchronization are visible at a glance while deep diagnostics remain in the copyable support report.

### Fixed

- Fixed Hybrid Automatic Control neutral battery plans. When `P_batt` is inside the deadband and there is no stronger grid-export request, EnergyPilot now uses GoodWe mode `8` Battery Hold instead of handing battery behavior back to mode `1` Auto.
- The Hybrid export branch remains higher priority, so an explicit planned export still uses mode `10` while `P_batt` is neutral.
- Battery graph energy integration now clips the still-active final Recorder 5-minute bucket at the current time instead of treating a partial bucket as a complete five minutes.

### Changed

- **Charged today** and **Discharged today** now prefer the inverter-native GoodWe day counters when available; the Recorder-integrated graph value remains visible as a comparison rather than being presented as authoritative accounting.
- The Battery & Price chart now distinguishes solid actual GoodWe battery-power bars from translucent/dashed historical and future plan blocks while keeping the market-price line and NOW marker on the same local-day timeline.
- The legacy direct minimum-SOC field-test panel is removed from the normal dashboard. The synchronized on-grid minimum-SOC NumberEntity remains the supported operator path; the existing low-level Beta SOC API is retained for diagnostics/backwards-compatible tooling.
- The Support card becomes a compact operational summary with GoodWe telemetry, control ownership, optimizer state and EMHASS/GoodWe minimum-SOC synchronization at a glance. Deep raw-register and lifetime diagnostics remain available through the support-report copy action.
- The active frontend is `gw-energy-pilot-v027-battery-plan.js`, which layers the v0.26 support cleanup underneath the v0.27 plan-versus-actual chart.

### Safety / compatibility

- No new GoodWe register definition or Modbus read block is introduced.
- EMS registers remain `47511` / `47512` with the existing write order.
- Battery and Grid Automatic Control strategies are unchanged; only the diagnosed Hybrid neutral branch changes to the already-supported mode `8` hold behavior.
- No existing entity ID, unique ID, stable device identity, persistent grid-accounting store or optimization-log contract changes.
- No EMHASS optimization objective changes.
- The chart remains read-only. Future financial accounting must consume backend accounting deltas and effective prices rather than reconstructing money from frontend graph samples.
- v0.27 remains **Beta** while the resizable layout and plan-versus-actual overlays receive live field exposure.

## [0.26] - 2026-08-24

### Added

- Added a full-width **Battery & Price** dashboard card that overlays actual battery charging/discharging with the timestamped electricity market price for the current local day.
- Added a centered zero-line chart: GoodWe battery charging (`battery_power < 0`) is shown below zero, discharging (`battery_power > 0`) above zero, and a thin cyan market-price line uses the right-hand currency/kWh axis.
- Added an expandable read-only detail graph, a dashboard visibility toggle, a current-time marker, and summary chips for approximately charged/discharged energy plus the current market price.
- Added the read-only `gw_energypilot/battery_price/get` WebSocket command and a short in-memory orchestrator price cache.
- Added Dutch/English chart text alongside the broader Home Assistant language-aware v0.26 frontend.
- Added pure regression coverage for timestamp sorting, configured buy/sell adjustments, negative market prices, partial series and invalid price rows.
- Added `docs/BATTERY_PRICE_CHART.md` as the chart/data-ownership contract.

### Changed

- Battery bars use the existing GoodWe `battery_power` entity through Home Assistant Recorder 5-minute mean statistics; no duplicate battery-power entity or Modbus path is introduced.
- The market-price line is reconstructed from the exact effective `load_cost` and `prod_price` maps produced by the existing EnergyPilot price-source path, rather than discovering or calculating prices independently in the browser.
- The price payload also keeps effective buy and sell values for later tooltip and financial-accounting work, while the visible line remains the direction-neutral market price.
- The chart covers local 00:00–24:00. Actual battery history stops at the current time, while available price points can continue through the remainder of the day.
- The active frontend is `gw-energy-pilot-v026-battery-price.js`, layered over the complete language-aware v0.26 dashboard.

### Data-quality boundary

- **Charged today** and **Discharged today** are approximate integrations of the displayed Recorder 5-minute mean battery-power buckets. They are visualization summaries, not replacement accounting entities.
- If Recorder battery history is unavailable, the price line can still render. If timestamped runtime prices are unavailable, the battery bars remain usable and the card explains why the line is absent.
- Dashboard reads never start an EMHASS optimization. A stale price cache is refreshed through the same orchestrator price method only when no optimization is already retrieving prices.

### Safety / compatibility

- No GoodWe register definition, Modbus read block, EMS mode/write, Automatic Control mapping or EMHASS optimization objective changes.
- No existing entity ID, unique ID, device identity, accounting store or optimization-log contract changes.
- Price display is read-only. Future persistent import-cost/export-revenue counters must consume selected grid-accounting deltas and effective prices in the backend, not reconstruct financial totals from this chart.
- v0.26 remains **Beta** while localization and the new Recorder/price visualization receive multi-installation field exposure.

## [0.25] - 2026-08-24

### Added

- Added three explicit Automatic Control strategies in the GOODWE settings: **Battery control**, **Grid control** and **Hybrid control**.
- Added **Hybrid control**: an EMHASS battery-charge request uses GoodWe mode `11`, a planned grid export uses mode `10`, and other situations return to GoodWe mode `1` self-use/Auto.
- Added a per-config-entry persistent optimization history containing the newest 50 EnergyPilot-owned manual, scheduled and event-triggered optimization attempts.
- Added the admin-only `gw_energypilot/optimization_log/get` WebSocket API and a read-only **LOG** page in EnergyPilot Settings.
- Added persistent accounting-source selection so derived Today/Yesterday accounting can use the populated extended 64-bit GoodWe meter pair `36104/36120` on applicable 15 kW+ ETA/ET installations.
- Added regression coverage for hybrid strategy selection/execution, optimization history persistence/failures, extended-meter selection and safe accounting source migration.

### Changed

- Existing installations without an explicit `control_strategy` keep the backwards-compatible legacy mapping: `use_goodwe_smart_meter=false` or missing selects Battery control; `true` selects Grid control.
- Battery control remains `P_batt -> 11/12/8`; Grid control remains `P_grid -> 9/10/1`.
- Hybrid control prioritizes an explicit battery-charge plan (`P_batt < -deadband`) through mode `11`; otherwise an export plan (`P_grid < -deadband`) uses mode `10`; otherwise mode `1` lets GoodWe perform self-use balancing.
- EV anti-discharge protection remains a higher-priority directional safety override and is not replaced by the new strategy selector.
- Daily grid accounting now prefers a coherent populated `36104/36120` pair, keeps legacy `36015/36017` when the extended block is empty or unavailable, and persists the selected source pair.
- Any accounting source-pair change re-baselines before accumulation so absolute totals from different GoodWe layouts are never subtracted from one another. Existing Today/Yesterday values are preserved during a same-day migration.
- Optimization history is stored separately from `gw_energypilot.runtime.<config_entry_id>`; failed runs are logged without overwriting the existing `last_success` contract.
- The active frontend is `gw-energy-pilot-v025.js`, layered on the v0.24 hybrid-control frontend and adding the LOG view plus the v0.25 version wrapper.

### Safety / compatibility

- No new GoodWe register definitions or Modbus read blocks are introduced by v0.25; `36104/36120` were already existing optional Beta diagnostics.
- EMS registers remain `47511`/`47512` and write ordering remains `47512 -> wait -> 47511`.
- Manual EMS modes remain direct operator commands and are not remapped by the automatic strategy selector.
- Existing entity unique IDs, device identity, physical lifetime grid-energy entities and daily accounting entity IDs remain unchanged.
- When an existing installation first switches accounting to `36104/36120`, the first extended sample is a safe baseline; EnergyPilot does not fabricate energy for the part of the day before that baseline.
- Diagnostic log persistence failures are non-fatal to optimization/control.
- v0.25 remains **Beta** while the hybrid strategy, extended-meter accounting selection and optimization history receive broader field exposure.

## [0.24] - 2026-08-23

### Fixed

- Restored the backwards-compatible automatic-control default for installations that do not have an explicit `use_goodwe_smart_meter` config-entry value. Missing configuration now follows EMHASS `P_batt` through direct GoodWe modes `11/12/8` instead of silently switching to PCC `P_grid` control.
- Fixed the field-reported case where EMHASS requested battery discharge (`P_batt = +962 W`) while planned grid flow remained inside the control deadband: v0.23 selected `grid_zero_auto` / mode `1`; v0.24 now selects direct mode `12` at the requested battery power unless PCC control was explicitly enabled.
- Added regression coverage for both missing-setting charge/discharge behavior and explicit Smart Meter/PCC opt-in.

### Changed

- **GoodWe smart meter active** remains available and hardware-validated as an explicit opt-in strategy. An explicit `true` still maps `P_grid` to modes `9/10/1`; an explicit `false` or missing value maps `P_batt` to modes `11/12/8`.
- The active frontend is `gw-energy-pilot-v024.js`, a thin release wrapper over the complete v0.23 dashboard stack.

### Log review

- The supplied Home Assistant startup log contained no GW EnergyPilot runtime exception, Modbus transport failure or failed `47511/47512` write attributable to this regression.
- A separate legacy Home Assistant script named `GoodWe ETA EMS normaal` was rejected by Home Assistant because its YAML structure was invalid. That script is outside GW EnergyPilot and is not part of this controller fix.
- Unrelated Audi, OpenAI dependency, ONVIF, template-sensor and other custom-integration warnings/errors were not changed by this release.

### Safety / compatibility

- No GoodWe register definitions or Modbus read blocks change.
- EMS registers remain `47511/47512`; write order remains `47512 -> wait -> 47511`.
- Explicit PCC-control installations retain their selected strategy.
- Manual EMS modes, entity unique IDs, device identity, accounting stores and orchestrator runtime state are unchanged.
- v0.24 remains **Beta** while the restored default is field-verified after upgrade from v0.23.

## [0.23] - 2026-08-23

### Added

- A per-config-entry **persistent EnergyPilot grid-accounting runtime** backed by Home Assistant storage.
- Native daily `total_increasing` energy sensors `grid_energy_imported_today` and `grid_energy_exported_today`, each exposing the completed previous local day as `last_period`.
- One-time Recorder boundary bootstrap for existing installations so upgrades can recover current-day and previous-day totals when canonical `36017/36015` history is available.
- **EV anti-discharge protection** as the clarified user-facing EV behavior while retaining the existing `enable_ev_coordination` config key for backwards compatibility.
- A persistent runtime store for the orchestrator's last successful EnergyPilot-owned optimize + publish timestamp.
- Regression coverage for accounting persistence/rollover, EV directional protection and orchestrator runtime-state persistence.
- `docs/ACCOUNTING.md`, `docs/EV_ANTI_DISCHARGE.md` and `docs/RUNTIME_STATE.md` as explicit architecture/ownership contracts.

### Changed

- Grid Today/Yesterday values now come from the persistent EnergyPilot accounting backend instead of being independently reconstructed by the dashboard from Recorder statistic changes.
- The 24-hour Grid modal keeps Recorder for its signed power graph, while its daily import/export values come from the same accounting entities as the main Grid card.
- During active EV charging, discharge and neutral battery plans hold the home battery, while an explicit EMHASS battery-charge plan is allowed through direct GoodWe mode 11. EV-stop fresh-optimization protection remains.
- The previous successful orchestrator timestamp is restored across config-entry reloads and Home Assistant restarts. Failed later optimizations do not erase the last success.
- The active frontend is `gw-energy-pilot-v023.js`. It layers persistent Grid accounting on the final flow-direction overlay, which in turn imports the complete v0.22 control/dashboard stack.

### Fixed

- Live-flow particles no longer suffer a layered **double reversal**. The geometry-correct Forward/Reverse keyframe selected from live power direction is authoritative; particle `animation-direction` is forced to normal.
- Expected visual directions are PV → hub, Grid import → hub, hub → Grid export, hub → Battery charge, Battery discharge → hub, and hub → House.

### Accounting/runtime contract

- GoodWe `36017` remains the canonical lifetime grid-import source and `36015` remains the canonical lifetime grid-export source.
- EnergyPilot accumulates only positive per-refresh lifetime-counter deltas; a counter decrease re-baselines instead of creating negative energy or guessing reset semantics.
- Recorder is optional bootstrap/history infrastructure, not part of the live accounting loop.
- Persistent runtime history is separate from user configuration: `ConfigEntry.data/options` remain configuration, while `gw_energypilot.runtime.<config_entry_id>` stores small EnergyPilot-owned runtime evidence such as `last_success`.

### Safety boundary

- No new GoodWe register definitions or Modbus read blocks are introduced by the v0.23 consolidation.
- EMS registers remain `47511`/`47512` and the `47512 -> wait -> 47511` write order is unchanged.
- The v0.22 automatic actuator strategy remains unchanged: smart-meter ON uses `P_grid -> 9/10/1`; smart-meter OFF uses `P_batt -> 11/12/8`.
- Existing lifetime grid-energy unique IDs/statistics remain unchanged; the new daily accounting entities use new deterministic unique IDs.
- Beta `36104/36120` counters remain diagnostics and are not promoted into canonical accounting.
- v0.23 remains **Beta** until persistent accounting, EV protection, flow visuals and the already-Beta PCC strategy have broader multi-installation exposure.

## [0.22] - 2026-08-23

### Added

- A **GoodWe smart meter active** switch in the GOODWE dashboard settings. The setting is stored with the GoodWe config-entry data rather than in EMHASS configuration.
- A dedicated admin WebSocket settings API for reading/updating the smart-meter actuator strategy and showing whether live GoodWe meter telemetry is currently available.
- Automated regression coverage for both supported automatic strategies.

### Changed

- With **GoodWe smart meter active = ON** (default), Automatic Control now executes the EMHASS `P_grid` plan through GoodWe's own PCC control loop:
  - `P_grid > deadband` → mode `9` Grid import target, setpoint = planned import magnitude;
  - `P_grid < -deadband` → mode `10` Grid export target, setpoint = planned export magnitude;
  - `P_grid` inside the deadband → mode `1` GoodWe Auto / AI at `0 W`.
- With **GoodWe smart meter active = OFF**, Automatic Control keeps the direct battery fallback:
  - `P_batt < -deadband` → mode `11` Battery charge power;
  - `P_batt > deadband` → mode `12` Battery discharge power;
  - `P_batt` inside the deadband → mode `8` Battery Hold.
- The v0.18-v0.21 30-second mode-11 grid-neutral feedback loop is retired. GoodWe modes 9/10 now perform the fast closed-loop regulation against the inverter's own smart meter/PCC when smart-meter control is enabled.
- The Controller target label now distinguishes PCC/grid targets from direct battery targets.
- Flow particles are reasserted at the active frontend layer using explicit **to hub / from hub** semantics so visual direction follows the validated sign conventions instead of depending on older layered CSS direction rules.
- The active frontend is `gw-energy-pilot-v022.js`, layered on top of v0.21.

### Hardware evidence used

- Mode `10` with a `400 W` setpoint produced approximately `395 W` export at the GoodWe smart meter.
- Mode `9` with a `400 W` setpoint produced approximately `331 W` import at the GoodWe smart meter.
- Mode `9` with a `15 kW` setpoint held approximately `15 kW` grid import while directly connected DC PV was added on top and the battery charged at roughly `16.9 kW`.
- Mode `11` with a `15 kW` setpoint held the battery near `15 kW` charging while PV reduced the grid import needed to supply that battery target.
- Mode `1` was observed naturally absorbing available PV surplus while keeping grid flow near zero on the reference ETA-G20.

### Safety boundary

- The existing EMS registers remain `47511`/`47512`; the `47512 -> wait -> 47511` write order is unchanged.
- Manual EMS buttons/modes remain available exactly as operator commands and are not remapped by the Smart Meter setting.
- BMS, inverter, SOC and grid limits remain authoritative regardless of requested PCC or battery targets.
- v0.22 remains **Beta** because automatic mode-9/10 execution and the new strategy switch still have limited multi-installation field exposure.

## [0.21] - 2026-08-23

### Added

- A compact **12-mode manual EMS test pad** inside the Controller card, using the same mode numbering and labels as the Home Assistant manual EMS select.
- Hover descriptions for all twelve GoodWe EMS modes so the operator can distinguish PV-priority limits, inverter-level grid scheduling, PCC grid targets and direct battery-power modes.
- A manual power slider from `0 W` to the configured EnergyPilot `max_power` value, backed by the existing `manual_power` Home Assistant number entity.
- Live highlighting of the actual GoodWe EMS mode read back from register `47511`, including while Automatic Control is active.

### Changed

- When Automatic Control is ON, the new manual mode pad and slider are visually locked/greyed while the actual active mode remains highlighted.
- When Automatic Control is OFF, clicking a mode uses the existing `manual_mode` select and existing controller manual-ownership path; no second Modbus control API is introduced.
- Modes `1`, `6`, `7` and `8` continue to force `0 W`. Mode `7` adds a dedicated confirmation before forced off-grid operation.
- The active frontend is `gw-energy-pilot-v021.js`, layered on top of v0.20.

### Beta test focus

- Primary field test: Automatic Control OFF, manual setpoint `0 W`, mode `10` (**Grid export target**) to observe zero-export behavior at the GoodWe smart meter/PCC.
- Mode `1` (**GoodWe Auto / AI**) can be compared manually with mode 10, but this release does not change automatic PV-only/grid-neutral behavior based on that observation.

### Safety boundary

- No GoodWe register definition changes.
- No change to the existing `47512 -> wait -> 47511` EMS write order.
- No change to Automatic Control mapping, grid-neutral charging, EMHASS ownership, sign conventions or power clamps.
- The test pad is only a UI surface over the existing `manual_power` and `manual_mode` entities.

## [0.20] - 2026-08-23

### Fixed

- EMHASS SOC values read from `/get-config` are now treated as percentages only when their raw values are inside the documented `0..1` range. Invalid finite values remain visible as raw support diagnostics instead of appearing as misleading values such as `-90%` or `-690%`.
- **Configured EnergyPilot final SOC target** is now separated from **Last sent runtime final SOC (`soc_final`)**. Manual-only or externally orchestrated EMHASS installations therefore no longer show an EnergyPilot setting as if EnergyPilot had actually sent it.
- The SOC diagnostics copy action uses the same validated/raw distinction shown on screen.

### Changed

- The active frontend is `gw-energy-pilot-v020.js`, layered on top of the complete consolidated v0.19 frontend so grid-neutral charging feedback and all v0.19 controls remain unchanged.
- The EMHASS setting label **Target final SOC** is clarified as **EnergyPilot runtime final SOC target** and explicitly notes that externally orchestrated/manual-only EMHASS may use a different runtime target.
- Unit tests now cover the field-observed invalid raw values `battery_target_state_of_charge=-0.9` and `battery_soc_deficit_threshold=-6.9` without accepting them as valid SOC percentages.

### Safety boundary

- No EMHASS optimizer objective, constraint, configured value or runtime payload is changed by this release.
- No GoodWe register definition or write path changes.
- Automatic Control, grid-neutral charging, EMS modes/registers, `P_batt` mapping and the manual `45356/45358` field-test path are unchanged.

## [0.19] - 2026-08-23

### Added

- A dedicated **SOC / CONSTRAINT LAYERS** diagnostics group that shows current battery SOC, last optimization `soc_init`, EnergyPilot runtime `soc_final`, EMHASS minimum SOC, EMHASS `battery_target_state_of_charge`, EMHASS SOC-deficit threshold/cost and GoodWe on-grid minimum SOC register `45356` side by side.
- SOC-related EMHASS config diagnostics are decoded from the same `/get-config` response already used by the stateful cost-function selector; no additional periodic HTTP request is introduced.
- Unit tests for explicit percentage/numeric decoding and invalid/missing EMHASS SOC diagnostic values.

### Changed

- The EMHASS settings label **Target final SOC** is clarified in the dashboard as **Runtime final SOC target**.
- The setting description now states explicitly that EnergyPilot sends this value as runtime `soc_final`, that the runtime value overrides the configured target for that optimization, and that it does not rewrite EMHASS `battery_target_state_of_charge` in `config.json`.
- The active frontend is `gw-energy-pilot-v019.js`, layered on top of the complete v0.18 G20 field-test controls.

### Safety boundary

- No EMHASS optimization objective, constraint or payload semantics are changed; v0.19 only exposes values that already exist in EnergyPilot or EMHASS.
- No additional GoodWe registers are read or written.
- The v0.18 manual Beta write path for `45356/45358`, Automatic Control ownership, EMS modes/registers and `P_batt` mapping are unchanged.

## [0.18] - 2026-08-23

### Added

- Manual **G20 Beta battery minimum-SOC** controls inside the GOODWE settings page for register `45356` (on-grid) and `45358` (off-grid).
- Admin-only WebSocket commands `gw_energypilot/beta_soc/get` and `gw_energypilot/beta_soc/set` for the dedicated field-test controls.
- Verified write support that writes exactly one selected Beta SOC-floor register and immediately reads the same register back before reporting success.
- Hardware-independent tests for the `45356/45358` write whitelist, bounds validation and verified read-back path.

### Changed

- The current `45356` interpretation is refined from ambiguous "discharge depth" wording to the raw **minimum SOC floor** used by the tested G20. This matches current upstream GoodWe handling where on-grid DoD is `100 - register 45356`.
- `45358` is treated as the corresponding off-grid minimum-SOC floor for field validation.
- A successful Beta write updates the coordinator snapshot immediately so the existing Diagnostic entity reflects the verified read-back without waiting for the next normal poll.
- The active frontend is `gw-energy-pilot-v018.js`, layered on top of the complete v0.17 settings/strategy implementation.

### Beta safety boundary

- The new write path is **manual field-test only** and is not used by Automatic Control, EMHASS, event triggers or any scheduled task.
- Only the two already-known canonical register definitions `45356` and `45358` are accepted; arbitrary register writes are not exposed.
- Values are limited to whole percentages from `0` through `100` and the register must already be readable on the current inverter before a write is allowed.
- Each user action changes exactly one register and requires a separate dashboard confirmation.
- Register `47500` remains read-only because its G20 semantics are still unresolved and the tested inverter has returned the sentinel-like value `65535`, which is not treated as a valid percentage.
- EMS modes `8/11/12`, registers `47511/47512`, sign conventions, control ownership and canonical grid-energy accounting remain unchanged.

## [0.17] - 2026-08-23

### Added

- A settings gear in the EnergyPilot dashboard header for Home Assistant administrators.
- Dedicated **EP**, **EMHASS** and **GOODWE** configuration pages backed by the existing Home Assistant config entry.
- Admin-only WebSocket settings commands for reading/updating the existing configuration.
- GoodWe connection validation before host, Modbus TCP port or unit-ID changes are saved.
- Multi-entry selection for installations with more than one GW EnergyPilot config entry.
- Enabled-by-default Home Assistant Diagnostic sensors for the Beta SOC candidates `45356`, `45358` and `47500`.
- A device-registry migration from the legacy mutable host:slave identifier to the stable config-entry ID.
- A stateful **EMHASS optimization strategy** select that reads the active `costfun` from EMHASS `/get-config`.

### Changed

- GoodWe host/port/unit-ID changes can now be made from the dashboard and reload the existing integration after successful validation.
- EP controller/telemetry/EV options and EnergyPilot-owned EMHASS orchestration/price options can be maintained from the dashboard settings pages.
- The dashboard now highlights the active Profit / Cost / Self-consumption strategy instead of presenting three ambiguous stateless actions.
- The strategy select refreshes after EnergyPilot EMHASS config writes and periodically so direct EMHASS UI changes are reflected in Home Assistant.
- Existing v0.15 cost-function button unique IDs remain available for backwards-compatible automations and are classified as explicit configuration actions.
- A successful `costfun` save is distinguished from a later fresh-optimization failure; the saved strategy remains visible even when re-optimization fails.
- The active frontend is `gw-energy-pilot-v017.js`, layering the settings UI on top of all v0.16 Beta diagnostics and strategy readback behavior.
- Home Assistant device identity no longer depends on mutable inverter connection data after migration.

### Beta status

- v0.17 remains **Beta** because the new settings UI/device migration has only limited real-installation exposure and the G20 candidate register semantics are still being correlated across the active tester installations.
- The G20 Beta registers remain read-only and optional.
- The settings pages and stateful strategy selector do not change GoodWe EMS modes, register write ordering, `P_batt` mapping, sign conventions or controller ownership.

## [0.16] - 2026-08-23

### Added

- Read-only beta diagnostics for candidate GoodWe SOC-protection registers `45356`, `45358` and `47500`.
- Read-only beta diagnostics for the extended 15 kW+ smart-meter lifetime counters at `36104` (export) and `36120` (import).
- Unsigned 64-bit Modbus decoding for the extended meter counters.
- A dedicated BETA diagnostics block and Copy beta diagnostics action in the dashboard.
- Unit tests for UINT64 decoding, four-word register coverage and beta optional-read block coverage.

### Changed

- Candidate registers are now shipped to the small active tester group instead of remaining isolated in draft branches.
- Every candidate remains optional and read-only; unsupported firmware cannot make the main inverter telemetry unavailable.
- Legacy `36015/36017` remain the canonical grid-energy source until the extended counters are validated against physical SEMS lifetime totals.

### Safety boundary

- `45356`, `45358` and `47500` are not used by controller logic and are never written by EnergyPilot.
- `36104/36120` are diagnostics only and do not alter Recorder-facing grid energy entities.
- EMS modes, setpoints, sign conventions, write ordering and automatic-control ownership are unchanged.

## [0.15] - 2026-08-23

### Added

- Three native EMHASS cost-function buttons for `profit`, `cost` and `self-consumption`.
- Matching one-touch strategy controls in the EnergyPilot EMHASS dashboard card.
- Regression tests proving selected EMHASS configuration patches preserve unrelated settings.

### Changed

- Selecting an EMHASS cost function reads the complete active configuration, changes only `costfun`, writes the complete configuration back through `/set-config`, and immediately runs/publishes a fresh optimization.
- Dashboard frontend moved to `gw-energy-pilot-v015.js`, layering the new strategy controls on top of the existing v0.14 battery diagnostics.

### Notes

- GoodWe Automatic Control remains `P_batt`-driven and still uses the existing EMS modes 8, 11 and 12.
- No GoodWe register definitions, sign conventions, EMS write ordering or control ownership behaviour are changed by v0.15.
- Candidate SOC-protection and extended-meter register work remained in draft validation PRs until v0.16.

## [0.14] - 2026-08-23

### Added

- Optional GoodWe battery energy accounting telemetry from registers `35206` (lifetime charge), `35208` (today charge), `35209` (lifetime discharge), and `35211` (today discharge).
- Battery SOH and charge/discharge energy values in the Diagnostics snapshot and copied support report.
- Internal battery accounting groundwork for later cost, revenue, throughput and degradation calculations.

### Changed

- Battery accounting telemetry is intentionally kept out of the normal dashboard and exposed only through diagnostics for now.
- The `35206-35211` telemetry block is optional so unsupported firmware does not make the main inverter telemetry unavailable.
- No estimated cycle count or equivalent-full-cycle value is generated yet; EnergyPilot will only add that once usable battery capacity/model semantics are validated.
- Dashboard frontend moved to `gw-energy-pilot-v014.js`.

## [0.13] - 2026-08-23

### Added

- Tested-hardware documentation centered on the **GoodWe GW15K-ETA-G20** and a request for model/firmware feedback from other ETA-G20 users.
- Native GoodWe smart-meter cumulative grid energy sensors from registers `36015` (export) and `36017` (import).
- Interactive Grid card with a Recorder-backed previous-24-hour power graph.
- Today and yesterday grid import/export energy totals using Recorder statistic changes.
- Lifetime GoodWe grid import/export totals in the Grid detail view.
- Refresh-frequency labels on dashboard cards.
- SOC guidance `i` popup explaining the recommended 5–95% normal on-grid operating range and the separate GoodWe/SEMS+/BMS protection layers.
- Dashboard groundwork for future Nord Pool cost/revenue accounting without repeated history scans.

### Changed

- Home card again treats GoodWe register `35172` as the primary load value because it matches the G20 load-phase sum; `PV - grid + battery` is now labelled **system power balance**, not house load.
- Registers `35138` and `35140` are labelled inverter-side diagnostics and are no longer presented as inverter self-consumption.
- The EMHASS load forecast consistently uses GoodWe load register `35172` plus Recorder history.
- Grid hero value is shown as an absolute number because the Importing/Exporting badge already communicates direction; diagnostics retain the signed value.
- Modbus offline handling uses shorter retries and reconnects on the normal polling cycle instead of holding a dead connection for a long time.
- EMHASS SOC changes are debounced for 3 seconds, so moving a slider results in one optimization after it settles.
- Flow particles now animate the individual CSS `translate` property, avoiding the v0.12 `transform:none!important` conflict that suppressed visible movement.
- Dashboard frontend moved to `gw-energy-pilot-v013.js`.

## [0.12] - 2026-08-23

### Added

- EMHASS `/healthz` probe and EMHASS version/health diagnostics.
- Nord Pool fallback support for sensors with `raw_today` and `raw_tomorrow`.
- Clear runtime-price error state and additional GoodWe/EMHASS diagnostics.
- Diagnostics card visibility toggle.

### Changed

- No EMHASS optimization is started during Home Assistant startup.
- First Modbus refresh, Automatic Control restore and EMHASS SOC reads run in background tasks.
- EMHASS output IDs can be configured before those entities exist.
- Native load forecast uses a 24-hour inclusive horizon.
- HTTP/HTML EMHASS errors are reduced to concise messages.
- Dashboard rerenders only for relevant entity changes.
- Hover effects no longer move controls.

## [0.11] - 2026-08-23

### Added

- Native EMHASS minimum/maximum battery SOC number entities.
- SOC sliders on the dashboard.
- EV-stop re-optimization.
- Diagnostics snapshot card with GoodWe, controller, EMHASS and power-balance data.

### Changed

- Default periodic optimization interval changed from 15 to 60 minutes.
- Home/load diagnostics identify GoodWe register `35172` explicitly.
- Flow animation changed to continuously spaced particles.

## [0.10] - 2026-08-22

### Added

- Native EMHASS orchestrator.
- Optimize now button.
- Maximum export, Pause, Maximum charge and AUTO battery controls.
- Runtime SOC, load forecast and optional Nord Pool pricing.
- HTTP validation and fresh `P_batt` validation.

### Changed

- Optimization is independent from Automatic Control.
- EnergyPilot remains the only component writing GoodWe EMS registers.

## [0.09] - 2026-08-22

### Added

- Default EMHASS output entity IDs and optimization status.
- Recorder-based bootstrap load forecast.
- Optimization/publish validation.

## [0.08] - 2026-08-22

### Added

- Draggable dashboard layout, visibility menu and animation control.

### Changed

- Automatic Control restores its previous Home Assistant state after reload/restart.

## [0.07] - 2026-08-22

### Added

- Compact live PV / Home / Grid / Battery flow widget.

### Fixed

- Dashboard branding and Home Assistant temperature-unit handling.

## [0.06] - 2026-08-22

### Fixed

- Dashboard logo handling and frontend cache busting.

## [0.05] - 2026-08-22

### Added

- Built-in Home Assistant sidebar dashboard.

## [0.04] - 2026-08-22

### Added

- GW EnergyPilot branding and improved EMHASS setup documentation.

### Changed

- Cleaner default entity set with low-value diagnostics disabled by default.

## [0.03] - 2026-08-22

### Changed

- English setup/options UI, static-IP guidance and controller descriptions.

## [0.02] - 2026-08-22

### Added

- Native GoodWe ETA telemetry over direct Modbus TCP.

## [0.01] - 2026-08-22

### Added

- Initial HACS-compatible integration.
- EMS register control for modes 1–12.
- Manual EMS control and automatic EMHASS `P_batt` mapping.
- Optional EV coordination.
