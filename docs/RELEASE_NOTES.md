# GW EnergyPilot release notes

This page is the user-facing release index for GW EnergyPilot.

`CHANGELOG.md` remains the detailed technical history. This page records the validation status and operator-visible scope of each release.

## Status definitions

- **Validated** — no intentionally unconfirmed control/hardware semantics are introduced by that release and repository checks passed.
- **Beta** — functionality is intentionally available before broad field testing across installations/firmware is complete.
- **Validated + beta diagnostics** — release behavior is validated while optional diagnostics still need field correlation.
- **Historical** — older development milestone retained for release history.

## Version overview

| Version | Date | Status | Main release notes |
|---|---|---|---|
| **0.41** | 2026-08-27 | **Beta** | Replaces normal telemetry full renders with stable in-place DOM updates, targeted plan/strategy refreshes, native touch scrolling and a no-motion dashboard validated in Chromium and WebKit desktop/iPad/iPhone profiles. |

| **0.40** | 2026-08-26 | **Beta** | Stabilizes the remaining dashboard, menu and card-window controls across telemetry-driven full renders by suppressing transition restart for one painted frame without delaying telemetry or reusing stale button nodes. |
| **0.39** | 2026-08-26 | **Beta** | Stabilizes Battery Strategy hover during full renders and completes Dutch customer-facing Controller localization without changing GoodWe, EMS or EMHASS behavior. |
| **0.38** | 2026-08-26 | **Beta** | Rebuilds dashboard controls around language-independent mode keys/delegated actions and makes live-flow direction a single explicit physical mapping, replacing the v0.37 stale-button-node stabilization path. |
| **0.37** | 2026-08-26 | **Beta** | Publishes the complete current 0.36.x dashboard-stability stack as a clean numeric release, retaining mobile scroll stability and stable button DOM nodes while synchronizing HACS/HA/frontend release metadata. |
| **0.36.2** | 2026-08-26 | **Beta** | Stabilizes the mobile viewport across periodic relevant telemetry refreshes by preserving the Home Assistant scroll container through complete dashboard renders while leaving GoodWe polling and live telemetry unchanged. |
| **0.36.1** | 2026-08-26 | **Beta** | Hotfixes mobile scrolling through the Battery strategy buttons by removing touch pointer capture, deferring destructive renders through touch-scroll settle, and adding a stuck-interaction safety timeout. |
| **0.36** | 2026-08-25 | **Beta** | Adds customer-facing Mad-Steve/Gold Rush/Balanced/Battery Saver/Custom strategy controls, preserves Custom EMHASS values, fixes dashboard render storms and lost clicks, and corrects live-flow direction/mobile sizing. |
| **0.35** | 2026-08-25 | **Beta** | Preserves the user-owned EMHASS inverter topology instead of forcing `inverter_is_hybrid=true`, and centralizes the small EnergyPilot runtime contract used by config sync and pre-solve preparation. |
| **0.34** | 2026-08-25 | **Beta** | Consolidates deterministic Battery Plan refresh, Battery Saver hard maximum-SOC/anti-churn tuning, and EV anti-discharge behavior that pauses discharge while allowing strategy-aware charging through mode 9 or 11. |
| **0.33** | 2026-08-25 | **Beta** | Persists the canonical EMHASS plan across Home Assistant restart/publication gaps, fixes fresh-output and chart refresh handling, and adds shared anti-churn Battery Saver weights with Gold Rush 5–96%. |
| **0.32** | 2026-08-25 | **Beta** | Hotfixes EMHASS settings saving on current Home Assistant while preserving four-decimal tariff values such as `0.0248`. |
| **0.31** | 2026-08-24 | **Beta** | Adds an opt-in, administrator-only debug session to LOG with bounded memory-only runtime tracing, full decoded GoodWe telemetry, controller/read-back and EMHASS status correlation, plus a copyable support report. |
| **0.30** | 2026-08-24 | **Beta** | Standardizes numeric GitHub Releases for HACS/Home Assistant so updates show `0.30` instead of a shortened commit SHA, with validated release automation and a synchronized v0.30 frontend badge. |
| **0.29** | 2026-08-24 | **Beta** | Adds safe EMHASS required-config synchronization and recommended defaults, resolves current EnergyPilot entity IDs from the Home Assistant registry, and adds a final live-flow double-reversal guard. |
| **0.28** | 2026-08-24 | **Beta** | Corrects Hybrid control to mode-9 buying / mode-12 selling and repairs the Battery · Plan · Price chart: canonical EMHASS battery schedule, historical-plan continuity, visible plan overlays, active-interval clipping and stepwise market prices. |
| **0.27** | 2026-08-24 | **Beta** | Resizable Battery plan/actual/price chart, historical active `P_batt` targets plus current EMHASS future forecast, native GoodWe battery-day counters, compact support diagnostics and corrected Hybrid neutral hold behavior. |
| **0.26** | 2026-08-24 | **Beta** | Consolidated release: Home Assistant language-aware Dutch/English UI, Battery & Price chart, canonical backend price-series API/cache, and synchronized EMHASS/GoodWe on-grid minimum SOC through register 45356 with verified write/read-back and rollback protection. |
| **0.25** | 2026-08-24 | **Beta** | Three Automatic Control strategies including Hybrid, extended 15 kW+ daily grid-accounting source selection and persistent 50-run optimization history/LOG. |
| **0.24** | 2026-08-23 | **Beta** | Restores the backwards-compatible direct `P_batt` automatic-control default while preserving explicit PCC control. |
| **0.23** | 2026-08-23 | **Beta** | Persistent Today/Yesterday grid accounting, EV anti-discharge protection, persistent `last_success` and final flow-direction fix. |
| **0.22** | 2026-08-23 | **Beta** | Adds optional GoodWe smart-meter/PCC automatic control through modes 9/10/1 with direct 11/12/8 fallback. |
| **0.21** | 2026-08-23 | **Beta** | Adds the manual 12-mode EMS test pad, live mode highlight, tooltips and manual setpoint slider. |
| **0.20** | 2026-08-23 | **Beta** | Corrects SOC diagnostics and separates configured runtime final SOC from last-sent runtime evidence. |
| **0.19** | 2026-08-23 | **Beta** | Adds combined SOC/constraint diagnostics across GoodWe, EMHASS and EnergyPilot. |
| **0.18** | 2026-08-23 | **Beta** | Adds verified manual field-test writes for G20 minimum-SOC registers 45356/45358. |
| **0.17** | 2026-08-23 | **Beta** | Adds dashboard settings, stable device identity migration, stateful EMHASS strategy readback and Beta SOC diagnostics. |
| **0.16** | 2026-08-23 | **Beta** | Adds optional G20 SOC-protection and extended-meter diagnostics including UINT64 decoding. |
| **0.15** | 2026-08-23 | **Validated** | Adds stateful EMHASS profit/cost/self-consumption strategy controls. |
| **0.14** | 2026-08-23 | **Validated + beta diagnostics** | Adds optional battery SOH and charge/discharge energy diagnostics. |
| **0.13** | 2026-08-23 | **Validated** | Establishes ETA-G20 load semantics, grid energy counters, history and SOC guidance. |
| **0.12** | 2026-08-23 | **Historical** | Startup, EMHASS health and Nord Pool reliability improvements. |
| **0.11** | 2026-08-23 | **Historical** | EMHASS SOC controls, EV-stop optimization and diagnostics snapshot. |
| **0.10** | 2026-08-22 | **Historical** | Native EMHASS orchestrator, Optimize now and manual battery actions. |
| **0.09** | 2026-08-22 | **Historical** | EMHASS output defaults, Recorder load bootstrap and publish validation. |
| **0.08** | 2026-08-22 | **Historical** | Draggable dashboard, visibility/animation controls and Automatic Control restore behavior. |
| **0.07** | 2026-08-22 | **Historical** | Compact PV/Home/Grid/Battery live-flow widget. |
| **0.06** | 2026-08-22 | **Historical** | Dashboard branding and cache-busting fixes. |
| **0.05** | 2026-08-22 | **Historical** | Built-in Home Assistant sidebar dashboard. |
| **0.04** | 2026-08-22 | **Historical** | Branding and EMHASS setup documentation. |
| **0.03** | 2026-08-22 | **Historical** | English setup/options UI and static-IP guidance. |
| **0.02** | 2026-08-22 | **Historical** | Native GoodWe ETA telemetry over direct Modbus TCP. |
| **0.01** | 2026-08-22 | **Historical** | Initial HACS integration with EMS modes 1–12, manual control and EMHASS mapping. |

# v0.41 — Stable DOM and native mobile scrolling

v0.41 replaces the active dashboard's normal telemetry-driven full ShadowRoot rebuild with in-place updates of the existing DOM. Live values, status classes, labels, diagnostics and meter widths still follow current Home Assistant state, but the page, layout menu, Automatic Control button and Battery Strategy controls are not detached during an ordinary GoodWe/EMHASS refresh.

Battery Strategy feedback is updated inside the strategy section and a new EMHASS plan refresh replaces only the Battery · Plan · Price card. Genuine structure changes — first initialization, language/user/theme changes, entity-registry changes and optional-card topology changes — still use a complete render. The active v0.41 path no longer writes saved scroll positions back into the Home Assistant scroll container and does not use the inherited v0.38 pointer/render guard.

EnergyPilot motion is deliberately disabled in this release: no moving flow particles, CSS animations, CSS transitions or modal backdrop filters remain active. This is a reliability decision, not a presentation fallback.

The candidate was exercised with a deterministic Playwright matrix using desktop Chromium plus WebKit touch profiles at iPad and iPhone dimensions. The matrix verifies scroll movement, stable control identity, menu operation, Automatic Control, Battery Strategy, graph-only plan refresh, Dutch localization, deliberate structural rerender recovery, zero active motion and clean JavaScript/WebSocket diagnostics. Physical-device/firmware diversity remains Beta field scope.

No GoodWe, Modbus, EMS, Automatic Control, EMHASS backend, entity identity or persistent-state contract changes.

See `docs/RELEASE_NOTES_V041.md` and `docs/FRONTEND_STABLE_DOM.md`.

# v0.40 — Stable dashboard and menu controls across full renders

v0.40 extends the v0.39 presentation fix from Battery Strategy to the rest of the interactive dashboard. Relevant Home Assistant updates still use the established full ShadowRoot render path, but recreated controls no longer visibly replay their hover/switch transition under a stationary pointer.

The new render-settle layer disables CSS transitions only for interactive controls during the synchronous rebuild and through the first painted frame. It does not pause telemetry, capture a pointer, reuse old button nodes or restore the removed v0.35 hover/render lock. Live-flow animations remain enabled because v0.40 does not suppress CSS animations.

See `docs/RELEASE_NOTES_V040.md`.

# v0.39 — Stable strategy hover and complete Dutch Controller copy

v0.39 is a focused frontend follow-up to the rebuilt v0.38 control path. The Battery Strategy control under a stationary desktop mouse no longer visibly blinks when the inherited full ShadowRoot render briefly detaches and reinserts the already-reused strategy node. Hover continuity is presentation-only: it never delays telemetry, captures a pointer or reinstates the removed v0.35 hover/render lock.

Dutch Home Assistant sessions also receive the remaining customer-facing controller localization inherited from older frontend layers: controller headings, automatic-control copy, GoodWe EMS mode names/tooltips, manual EMS status messages, strategy fallback copy, profile descriptions and telemetry presentation. Technical identifiers such as `EMS`, `P_grid`, `P_batt` and `PCC`, plus profile names such as Mad-Steve and Gold Rush, remain intentionally stable.

The new `gw-energy-pilot-v039.js` entrypoint is release/version-only and imports the tested v0.38 behavior with a fresh cache key. No GoodWe register, Modbus, EMS mapping/write order, Automatic Control, EMHASS, entity-ID or persistent-state contract changes.

See `docs/RELEASE_NOTES_V039.md`.

# v0.38 — Rebuilt controls and canonical live-flow direction

v0.38 replaces the v0.37 dashboard-control stabilization approach instead of adding another monkey-patch layer. Fresh sessions load the new v0.38 runtime directly over the v0.34 feature base and therefore do not execute the v0.35 pointer/render lock or v0.36.3 old-button-node reuse.

Battery Strategy actions use stable backend mode keys (`mad_steve`, `gold_rush`, `balanced`, `battery_saver`, `custom`) and selected/highlight state uses `aria-pressed`. English/Dutch labels and descriptions are presentation only. A delegated ShadowRoot listener executes the existing Battery Saver API, so translated text and stale per-node listener closures cannot define control behavior.

Live-flow animation has one final physical owner: PV production flows to the hub, grid import to the hub, grid export away from the hub, house load away from the hub, battery discharge to the hub and battery charge away from the hub. Explicit geometry keyframes are selected from that mapping with normal animation direction, preventing older reversal rules from reinterpreting the final result.

Quality now executes JavaScript syntax checks plus Node regression tests for localization/profile identity, delegated clicks, control re-enable behavior and physical flow mapping, alongside the full Python unit suite and repository validator. HACS and Hassfest remain release gates.

No GoodWe register, Modbus, EMS, Automatic Control, EMHASS backend, entity-ID or persistent-state contract changes.

See `docs/RELEASE_NOTES_V038.md` and `docs/FRONTEND_CONTROL_REBUILD.md`.

# v0.37 — Clean stable-control release

v0.37 publishes the complete current dashboard-stability stack as one clean numeric HACS/Home Assistant release. It carries forward the v0.36.2 mobile scroll fix and the interim v0.36.3 stable-control layer without changing GoodWe or EMHASS control behavior.

The active frontend is now `gw-energy-pilot-v037.js`. It cache-busts and wraps the v0.36.3 stable-control module, which preserves equivalent button DOM nodes across telemetry-driven full renders so controls no longer visibly flash or lose hover/focus state. The underlying v0.36.2 layer continues to preserve Home Assistant scroll containers on narrow/mobile layouts.

The interim v0.36.3 code reached `main` but its manifest version was not added to the central changelog/release index, so the repository release validator could not publish a matching GitHub Release. v0.37 restores that release metadata contract and is intended to be the next installable update.

No GoodWe register definitions, Modbus read blocks, EMS mappings, Automatic Control behavior, EMHASS optimization/configuration ownership, entity IDs, unique IDs, config-entry data, persistent Store keys or stable device identity change.

See `docs/RELEASE_NOTES_V037.md`.

# v0.36.2 — Periodic refresh scroll stability

v0.36.2 fixes the remaining mobile viewport jump that could occur on a configured GoodWe polling cycle after the v0.36.1 touch fix. Relevant EnergyPilot state updates still have to refresh the live dashboard, and the current layered frontend still rebuilds the complete Shadow DOM for such renders. On mobile Home Assistant/WebView that structural replacement could cause the browser to choose a different scroll anchor after layout, moving the viewport even when the user was no longer touching a control.

On narrow/mobile layouts, EnergyPilot now captures the actual composed Home Assistant scroll containers before the complete render chain runs and restores their exact positions immediately after rendering and across two animation frames. The panel subtree also opts out of browser scroll anchoring with `overflow-anchor: none`. GoodWe polling cadence and live telemetry remain unchanged; this hotfix stabilizes presentation rather than suppressing refreshes.

No GoodWe register definitions, Modbus read blocks, EMS mappings, Automatic Control behavior, Battery Saver/EMHASS policy, entity IDs, unique IDs or device identity change.

See `docs/RELEASE_NOTES_V0362.md`.

# v0.36.1 — Mobile strategy scrolling hotfix

v0.36.1 fixes a mobile Home Assistant interaction regression around the large Battery strategy buttons introduced in v0.36. A vertical swipe can start on any interactive control; the v0.35 interaction guard previously captured that touch pointer immediately to protect clicks from a concurrent destructive render. On narrow phone layouts the strategy buttons occupy most of the viewport width, so normal scrolling could enter that protected-press path and interfere with native WebView panning.

Touch pointers are no longer explicitly captured. Movement of at least 8 px is treated as a scroll gesture, and full Shadow DOM rebuilds remain deferred until a short 350 ms post-gesture settle window has elapsed. A 5 second safety timeout clears interrupted pointer interactions so the dashboard cannot remain render-locked. Desktop mouse capture remains in place for click reliability, and the strategy buttons explicitly advertise `touch-action: pan-y`.

This is a frontend-only hotfix. It does not change GoodWe registers, Modbus reads/writes, EMS mappings, Automatic Control, EMHASS optimization/configuration ownership, entity IDs, unique IDs or device identity.

See `docs/RELEASE_NOTES_V0361.md`.

# v0.36 — Customer strategy controls and dashboard reliability

v0.36 makes the Controller card customer-facing while consolidating two frontend reliability fixes developed after v0.35.

The Controller card now shows the active **Battery strategy** with direct choices for **Mad-Steve**, **Gold Rush**, **Balanced**, **Battery Saver** and **Custom**. The first four reuse the existing canonical Battery Saver profiles. **Custom** releases EnergyPilot preset ownership without resetting the currently effective EMHASS battery values, and exposes the established minimum/maximum SOC NumberEntities plus read-only advanced EMHASS battery costs for transparency.

Every managed-profile or Custom transition runs the existing complete EnergyPilot optimization/publish transaction. After the persistent EMHASS plan refresh, the existing `plan_revision` contract invalidates the Battery · Plan · Price cache so the graph follows the new plan immediately. The low-level controller command such as `hybrid_battery_discharge` is removed from the normal customer Controller presentation but remains available through Diagnostics/support output.

The dashboard also fixes installation-dependent render storms. Once entity discovery is complete, unrelated Home Assistant state changes no longer rebuild the complete Shadow DOM. Relevant EnergyPilot/EMHASS changes are batched for 80 ms, and a narrow pointer/keyboard guard prevents an actual button press from being destroyed by a concurrent relevant render. Locale, user and theme changes remain render triggers.

Live-flow particles now neutralize the legacy double-reversal rule at matching CSS specificity while retaining the established geometry-specific animation keyframes. On narrow panels, node/hub/connector geometry is calculated from the measured card width and follows phone rotation/resizing through `ResizeObserver`; wide desktop geometry is unchanged.

No GoodWe register definitions, Modbus read blocks, EMS mappings, entity IDs, unique IDs or stable device identity are changed. EMS remains on `47511/47512` with the established `47512 -> wait -> 47511` write order. EMHASS remains the canonical optimizer and plan owner.

See `docs/RELEASE_NOTES_V036.md` and `docs/BATTERY_SAVER.md`.

# v0.35 — Preserve EMHASS inverter topology

v0.35 corrects an ownership mistake in the v0.34 EMHASS integration path. EnergyPilot previously had two independent paths that could force `inverter_is_hybrid = true`: **Synchronize required config** and the automatic pre-solve policy immediately before an EnergyPilot-owned optimization.

`inverter_is_hybrid` describes the optimizer's installation/model topology. It is therefore not part of the small EnergyPilot publication/runtime contract and must not be inferred from the physical GoodWe reference inverter. v0.35 preserves the existing EMHASS value exactly, including an explicit `false`, an explicit `true`, or an absent key.

Both configuration-write paths now share one canonical EnergyPilot runtime contract:

```text
continual_publish = true
method_ts_round = first
set_use_battery = true
```

`set_use_pv` and `inverter_is_hybrid` remain installation-specific EMHASS settings. The synchronization API derives its managed-value presentation from the same canonical key list, preventing the UI and backend ownership definitions from drifting apart again.

Regression coverage verifies the explicit sync path, the automatic pre-solve path and false/true/missing inverter-topology values. Battery Saver tuning, hard maximum SOC ownership, EV anti-discharge behavior, persistent-plan recovery and all GoodWe control mappings remain unchanged.

No GoodWe register definitions, Modbus read blocks, EMS mappings, entity IDs, unique IDs or stable device identity are changed. EMS remains on `47511/47512` with the established `47512 -> wait -> 47511` write order.

See `docs/RELEASE_NOTES_V035.md` and `docs/EMHASS_CONFIG_SYNC.md`.

# v0.34 — Consolidated plan refresh, Battery Saver tuning and EV anti-discharge

v0.34 consolidates all open post-v0.33 release work into one Beta candidate.

The Battery · Plan · Price card now follows an explicit optimization `plan_revision`, so every successful EnergyPilot optimization can invalidate the cached chart immediately after the persistent EMHASS plan refresh attempt. A fresh v0.34 frontend wrapper also cache-busts both the updated Battery Saver module and Battery Plan core for already-open Home Assistant sessions.

Battery Saver profiles now own their hard EMHASS maximum SOC when explicitly selected: Mad-Steve 100%, Gold Rush 96%, Balanced 95% and Battery Saver/Eco 90%. The shared charge/discharge anti-churn floor increases from 1.5% to 2.25% of the dynamic price reference per direction based on field comparison.

EV coordination remains an anti-discharge guard. While the EV is charging, battery discharge or a neutral battery plan uses mode 8 Battery Hold. An explicit home-battery charge request is no longer unnecessarily held: Battery control uses mode 11; Grid/Hybrid use mode 9 when a positive `P_grid` import target is available, with a mode-11 fallback for an explicit battery-charge request when needed.

No GoodWe register definitions, Modbus read blocks, entity IDs, unique IDs or stable device identity are changed. EMS remains on `47511/47512` with `47512 -> wait -> 47511`. The v0.33 persistent-plan fallback, optimizer readiness gates and EV-stop fresh-plan protection remain intact.

See `docs/RELEASE_NOTES_V034.md`, `docs/BATTERY_PLAN_CHART.md`, `docs/BATTERY_SAVER.md` and `docs/EV_ANTI_DISCHARGE.md`.

# v0.33 — Persistent EMHASS plan and calmer Battery Saver optimization

v0.33 consolidates the reliability fixes and Battery Saver field findings made after v0.32 into one release candidate.

## Persistent canonical EMHASS plan

EMHASS remains the canonical plan owner. Current EMHASS persists its latest optimization and exposes the versioned read-only `GET /api/v1/plan` endpoint. EnergyPilot now validates that plan and stores a per-config-entry resilience mirror in Home Assistant Store:

```text
gw_energypilot.plan.<config_entry_id>
```

The mirror contains timestamped `P_batt` and `P_grid` horizon points, generation time, schema version, inferred timestep and an explicit `valid_until` boundary.

Control source order is:

```text
1. live configured Home Assistant P_batt / P_grid
2. current point from a still-valid persistent EnergyPilot plan mirror
3. existing unavailable/waiting behavior
```

A valid mirror may bridge a temporary missing Home Assistant publication after restart/reload. An explicit live non-ready optimization status remains authoritative and is never overridden. EnergyPilot also never extrapolates the last command beyond the final inferred plan interval.

The Battery · Plan · Price future horizon now prefers the same persistent validated plan. Existing Home Assistant schedule attributes remain compatibility fallback rather than a second plan owner.

See `docs/EMHASS_PLAN_RUNTIME.md`.

## Fresh EMHASS output detection

A valid EMHASS publish can repeat exactly the same numeric `P_batt` value and attributes. Home Assistant does not necessarily advance `last_updated` for such a report. v0.33 therefore uses `State.last_reported` as the primary proof of a fresh publication, retaining `last_updated` only as compatibility fallback for older State-like test doubles.

The existing safety gates stay intact: `P_batt` must still be finite and the optimizer status must still be ready.

## Battery · Plan · Price refresh

The chart's duplicate-card protection remains, but it no longer prevents the existing canonical card from being rebuilt after fresh chart data arrives. When the configured active-plan entity has a newer timestamp than the cached payload, v0.33 forces a read-only chart refresh immediately instead of waiting up to the normal five-minute frontend cache interval.

## Battery Saver anti-churn tuning

Field comparison showed that a small linear cost on battery throughput removes low-value quarter-hour reversals much more directly than simply increasing the quadratic power-stress cost. v0.33 therefore adds the same small transaction cost to all four managed profiles:

```text
weight_battery_charge    = 1.5% × dynamic price reference
weight_battery_discharge = 1.5% × dynamic price reference
```

On the primary field test, approximately `0.005` currency/kWh per direction removed several small charge/discharge reversals while preserving high-value evening discharge up to the physical inverter/battery limits. The price-relative 1.5% factor yields approximately `0.004658` per direction at the observed price reference of `0.3105` and scales with other price/currency magnitudes.

The four public profiles remain:

- **Mad-Steve** — maximum economic freedom, zero additional SOC/power-stress costs, but now with the shared anti-churn floor so tiny price noise does not automatically justify a reversal.
- **Gold Rush** — profit first, shared anti-churn floor, light power stress and a high-SOC soft threshold changed from 98% to **96%**.
- **Balanced** — the recommended general-purpose profile with the shared anti-churn floor and the existing moderate SOC/power-stress costs.
- **Battery Saver** — the shared anti-churn floor plus the strongest existing SOC/power-stress costs.

The normal hard Minimum/Maximum SOC settings remain separate. Gold Rush 96% is a **soft threshold**, not a hard maximum.

Battery Saver ownership expands from six to eight EMHASS fields so failed first-apply transactions also restore the two charge/discharge weights. Existing unmanaged/custom EMHASS configuration remains untouched until the user explicitly selects a profile.

See `docs/BATTERY_SAVER.md`.

## Why `P_batt` may be below 15 kW

The optimizer table can show battery power below the configured 15 kW maximum for multiple valid reasons. In the hybrid inverter model, PV and battery share the same AC converter path, so the inverter can already be at 15 kW AC while `P_batt` is only 14–14.8 kW. When no physical limit binds, EMHASS can also reserve energy for a later higher-price interval or reduce instantaneous power because `battery_stress_cost` is a quadratic/PWL power penalty.

This release documents that distinction; it does not add another power limiter or rewrite EMHASS's optimizer.

## Safety and compatibility

- No new or guessed GoodWe register definitions or Modbus read blocks.
- EMS remains `47511` / `47512` with the established `47512 -> wait -> 47511` write order.
- Battery/Grid/Hybrid control mappings are unchanged.
- Live configured EMHASS states remain first priority over the persistent plan mirror.
- Explicit live non-ready optimization status is not bypassed.
- Expired plan data is not repeated indefinitely.
- Existing entity IDs, unique IDs and stable device identity are preserved.
- EMHASS remains an external prerequisite and EnergyPilot does not install or replace it.

v0.33 remains **Beta** while plan recovery across live restart/reload scenarios and the revised Battery Saver tuning receive broader installation validation.

# v0.32 — Home Assistant price-selector hotfix

v0.32 is a focused compatibility hotfix for the EMHASS settings form introduced immediately after v0.31.

Home Assistant currently validates `NumberSelector` configuration with a minimum numeric `step` of `0.001`. v0.31 configured the import/export price selectors with `step=0.0001`, which caused settings validation to fail before the values could be saved:

```text
not a valid value for dictionary value @ data['step']
```

v0.32 restores the Home Assistant selector configuration to `step=0.001`. This does **not** reduce the stored precision: in BOX mode Home Assistant does not round typed input to the configured step. Values such as `0.0248` therefore remain valid and are stored unchanged.

The EnergyPilot dashboard still exposes a browser input increment of `0.0001`, retaining convenient fine-grained tariff entry while respecting the Home Assistant backend selector contract.

No GoodWe register, Modbus block, controller mapping, EMHASS optimization model, Battery Saver tuning, entity ID or unique ID changes in this hotfix.

See `docs/RELEASE_NOTES_V032.md`.

# v0.31 — Opt-in debug sessions for problem analysis

v0.31 extends the existing dashboard **LOG** tab with a temporary high-detail debug session. The existing persistent 50-run optimization history remains unchanged and continues below the new debug controls.

Debug capture is administrator-only and **off by default**. Starting it opens a fresh memory-only session with a complete baseline. While active, EnergyPilot observes its existing coordinator, controller and orchestrator signals and records:

- all decoded GoodWe telemetry values plus canonical `registers.py` address/type/scale metadata;
- coordinator poll success/failure, latest update exception and current Modbus connection state;
- controller strategy, command, target and GoodWe EMS mode/setpoint read-back;
- configured `P_batt`, `P_grid`, optimization-status and optional EV source changes;
- EMHASS/orchestrator status transitions and the HTTP/error diagnostics already exposed by the orchestrator.

The session is bounded to the newest 1200 events. Stopping capture preserves the session in memory for copying; clearing, integration reload/unload or Home Assistant restart discards it. Debug events are not written to Home Assistant Store, Recorder or config-entry data.

**Copy debug report** combines the current debug session/runtime snapshot with the existing persistent optimization history. The configured GoodWe host/IP and EMHASS base URL are intentionally excluded; configured entity IDs and diagnostic values remain because they are needed to diagnose mapping and stale/unavailable-input problems.

Debug capture is observer-only: it does not add a second Modbus poller, change a register/read block, write an EMS command, alter EMHASS configuration, trigger an optimization or introduce new entities/unique IDs.

See `docs/DEBUG_LOG.md` and `docs/RELEASE_NOTES_V031.md`.

# v0.30 — Versioned HACS/Home Assistant releases

v0.30 standardizes the release path so HACS/Home Assistant can present a normal GW EnergyPilot version instead of a shortened Git commit SHA.

The release contract is now:

```text
manifest version: 0.30
GitHub release:   0.30
HACS / HA:        0.30
```

The release workflow verifies that the numeric version matches `manifest.json`, then runs Python compilation, unit tests, repository invariants, HACS validation and Hassfest before creating the GitHub Release. A new manifest version reaching `main` can create the matching release/tag automatically; manually pushed numeric tags are still accepted when they exactly match the manifest version.

GW EnergyPilot does not create a competing Home Assistant `update` entity. HACS remains responsible for update discovery and installation.

The active frontend wrapper is `gw-energy-pilot-v030.js` and reports `v0.30 BETA` while retaining the complete v0.29 dashboard/control implementation underneath.

No GoodWe register, Modbus read block, EMS mapping, entity unique ID, EMHASS objective or persistent runtime/accounting contract changes in this release.

See `docs/RELEASE_NOTES_V030.md` and `docs/RELEASE_WORKFLOW.md` for the release-specific and publishing details.

# v0.29 — EMHASS configuration sync and frontend stabilization

v0.29 is deliberately published as a new version because v0.28 had already reached `main`. Keeping the remaining changes under the same manifest version could prevent an installation already on v0.28 from receiving a clear HACS update.

## EMHASS configuration tools

The EMHASS settings page adds two explicit administrator actions:

- **Restore recommended defaults** fills the GW EnergyPilot EMHASS form with the current canonical defaults for review. It does not save automatically.
- **Synchronize required config** reads the complete live EMHASS configuration, changes only the mappings required by EnergyPilot, writes the complete merged configuration and reads it back again for verification.

Canonical EnergyPilot outputs remain:

```text
sensor.p_batt_forecast
sensor.p_grid_forecast
sensor.optim_status
required state: Optimal
```

The synchronization resolves the actual Home Assistant entity IDs for EnergyPilot PV total power, GoodWe load power, battery power and battery SOC from the entity registry. Renamed entity IDs are therefore used instead of hard-coded guesses.

Unrelated EMHASS configuration is preserved. Existing custom PV forecast mappings and compatible custom `var_model` values are preserved. Multi-battery power/SOC lists are not rewritten because EnergyPilot cannot safely infer per-battery ownership.

Synchronization is administrator-triggered only, does not write GoodWe registers and does not automatically run an optimization. Run a fresh optimization after changing EMHASS configuration before enabling Automatic Control.

See `docs/EMHASS_CONFIG_SYNC.md` and the detailed `docs/RELEASE_NOTES_V029.md`.

## Flow animation regression guard

The v0.29 frontend adds a final guard for the live-flow particles: the geometry-specific Forward/Reverse keyframes remain authoritative and later frontend layers are forced to use `animation-direction: normal`.

This prevents the previously observed layered double reversal without changing power signs, Home Assistant entity values, GoodWe register semantics or controller behavior.

Expected directions remain PV → hub, Grid import → hub, hub → Grid export, hub → Battery charge, Battery discharge → hub, and hub → House.

## Release-base functionality retained

v0.29 includes the complete v0.28 base: Hybrid mode-9 import / mode-12 discharge control, neutral mode-8 hold, Battery · Plan · Price repairs, current EMHASS `battery_scheduled_power` support, Max Charge maximum-SOC guard and Apple/macOS-style Battery/Plan window controls.

Issue #22 is closed without a second residual-grid-capacity allocator because GoodWe itself already enforces the dynamic grid/import power limit.

Issue #30 remains open. Negative raw EMHASS SOC-related values continue to be shown as invalid/raw diagnostics and are not guessed into percentages or silently rewritten until their exact semantics/source is established.

## Safety and compatibility

- No new or guessed GoodWe register definitions or Modbus read blocks.
- EMS registers remain `47511` / `47512` with the established `47512 -> wait -> 47511` write order.
- Existing entity IDs, unique IDs and stable device identity are preserved.
- Battery strategy remains `P_batt -> 11/12/8`.
- Grid strategy remains `P_grid -> 9/10/1`.
- EV anti-discharge remains a higher-priority directional override.
- Manual EMS commands remain direct operator commands.
- EMHASS remains an external prerequisite and is not installed by GW EnergyPilot.

v0.29 remains **Beta** while the EMHASS synchronization workflow and final flow-animation guard receive live installation validation.

# v0.28 — Corrected Hybrid control and Battery chart repair

v0.28 combines the corrected meaning of the **Hybrid** Automatic Control strategy with fixes found during live v0.27 Battery · Plan · Price validation.

## Corrected Hybrid buy/sell control

The previous Hybrid implementation combined direct battery charging through mode 11 with PCC export control through mode 10. The intended strategy is asymmetric in the other direction:

```text
buy/import      -> GoodWe mode 9  -> target from EMHASS P_grid
sell/discharge  -> GoodWe mode 12 -> target from EMHASS P_batt
```

The complete decision order is:

```text
P_grid > +deadband -> mode 9 Grid import target
else P_batt > +deadband -> mode 12 Battery discharge power
else P_batt inside deadband -> mode 8 Battery Hold
otherwise -> mode 1 GoodWe Auto / self-use
```

The import branch is evaluated first because an explicit positive `P_grid` is the Hybrid buying signal. Mode 9 lets GoodWe regulate the PCC import target using the planned grid-import magnitude while local PV can be added by the inverter.

Selling is deliberately direct battery control. A positive `P_batt` request uses mode 12 at the planned battery-discharge magnitude instead of forcing a PCC export target through mode 10.

A Hybrid battery-charge request with no planned grid import falls through to mode 1/self-use. This allows available local PV surplus to charge the battery according to GoodWe's own fast control rather than limiting charging to the forecast-sized `P_batt` value. A neutral battery plan remains mode 8 Battery Hold.

## Battery · Plan · Price fixes

Live v0.27 validation showed that the chart's future-plan parser did not match current EMHASS output. Current EMHASS publishes the `P_batt` horizon through the **`battery_scheduled_power`** attribute. v0.28 uses that as the canonical schedule and keeps `forecasts` only as a conservative compatibility fallback for older/custom publishers.

The chart also corrects several timeline and presentation details:

- Home Assistant's start-time history state is retained at local 00:00 when the active `P_batt` state originated before midnight.
- A current EMHASS schedule interval that started just before NOW remains visible and is clipped at NOW instead of being discarded.
- Solid actual bars render below the dashed historical/future plan overlay so planned versus actual remains visible when values overlap.
- Near-zero actual samples are not rendered as false charge/discharge bars or zero-power discharge tooltips.
- Missing historical/future plan data displays `—` for planned energy instead of a fabricated `0.00 kWh`.
- Timestamped market prices are rendered as a step series because they represent intervals, not continuously interpolated measurements.
- The read-only chart payload is versioned as schema `3` and reports which schedule attribute was detected.
- The complete nested ES-module import chain uses v0.28 cache keys so a browser cannot keep a stale v0.27 data/view module underneath a new panel wrapper.

## Battery daily totals

The headline charged/discharged values continue to prefer the native GoodWe day counters:

```text
35208 = battery_charge_energy_today
35211 = battery_discharge_energy_today
```

The secondary graph figure remains a numerical integration of Recorder 5-minute mean samples from instantaneous battery power register `35182`.

Those values can differ because they are separate measurement paths. v0.28 clarifies that distinction and does **not** scale or calibrate the Recorder integral to force a match with the inverter's own day counter. The GoodWe counter remains the headline value.

## Safety and compatibility

- Battery strategy remains `P_batt -> 11/12/8`.
- Grid strategy remains `P_grid -> 9/10/1`.
- EV anti-discharge remains a higher-priority directional override.
- Manual EMS commands remain direct operator commands.
- No new or guessed GoodWe register definitions or Modbus read blocks.
- EMS registers remain `47511` / `47512` with the existing `47512 -> wait -> 47511` write order.
- Chart/API reads remain read-only and do not trigger optimization or write inverter state.
- No entity ID, unique ID, stable device identity, EMHASS optimization objective or persistent accounting/runtime/log store changes.

v0.28 remains **Beta** while the Hybrid 9/12 mapping and corrected real-world plan/actual chart receive live installation validation.

# v0.27 — Battery plan versus actual and dashboard refinement

v0.27 turns the v0.26 Battery & Price visualization into a planning and verification view while preserving the existing GoodWe/EMHASS ownership boundaries.

## Battery plan versus actual

- The card can be switched between **S**, **M** and **L** layouts with an Apple-style segmented control; the browser remembers the selected size.
- Solid bars remain actual GoodWe `battery_power` history from Home Assistant Recorder.
- Historical plan blocks use the configured EnergyPilot `P_batt` entity history, so the graph shows the target that was actually active at each time rather than rewriting the past with the newest optimization.
- Future plan blocks were introduced from the current EMHASS battery forecast payload; v0.28 later corrects the attribute contract to current `battery_scheduled_power`.
- EMHASS and GoodWe battery signs remain aligned: negative = charge, positive = discharge.
- The market-price line and NOW marker stay on the same local-day timeline.

The read-only `gw_energypilot/battery_price/get` response is extended with a versioned chart payload, native battery-day energy values and normalized battery-plan points. Dashboard reads never run an optimization or write a GoodWe register.

## Battery energy totals

The headline **charged today** and **discharged today** values now prefer the already-decoded GoodWe day counters `35208` and `35211`. The Recorder integration remains visible as a graph-derived comparison and clips the still-active final five-minute bucket at the current time.

No new GoodWe register or Modbus block is introduced.

## Hybrid neutral hold

Hybrid Automatic Control now treats a neutral `P_batt` plan as an explicit battery hold when there is no stronger export request:

```text
P_batt < -deadband  -> mode 11 battery charge
else P_grid < -deadband -> mode 10 grid export
else P_batt inside deadband -> mode 8 Battery Hold
otherwise -> mode 1 GoodWe Auto / self-use
```

The export branch remains higher priority so a planned export can still use mode 10 while `P_batt` is neutral. Battery and Grid strategies are unchanged.

## Support and SOC presentation

The legacy direct minimum-SOC field-test panel is removed from the normal dashboard. The synchronized on-grid minimum-SOC NumberEntity remains the supported operator path; the low-level Beta SOC API remains available for diagnostics/backwards-compatible tooling.

The Support card becomes a compact operational summary with GoodWe telemetry, control ownership, optimizer state and EMHASS/GoodWe minimum-SOC synchronization at a glance. Deep raw-register and lifetime diagnostics remain available through the support-report copy action.

## Safety and compatibility

- No guessed or new GoodWe register definitions.
- No Modbus read-block changes.
- EMS registers remain `47511` / `47512` with the existing write order.
- No entity ID, unique ID, device identity or persistent accounting-store change.
- No EMHASS optimization objective change.
- The new chart is read-only; financial accounting must continue to use backend accounting deltas rather than reconstructing money from frontend graph samples.

v0.27 remains **Beta** while the S/M/L layouts and plan-versus-actual overlays receive live installation exposure.

# v0.26 — Language, Battery & Price and synchronized minimum SOC

v0.26 consolidates the release-ready work after v0.25 into one Beta release. It does not change GoodWe EMS register addresses, the EMS write order, or the established Automatic Control strategy mappings.

## Home Assistant language-aware dashboard

The dashboard follows Home Assistant language through `hass.locale.language` / `hass.language`.

- Dutch and English are supported.
- English is the fallback.
- Dashboard, settings, optimization-log, strategy confirmations and the new chart use the same language selection.
- Existing entity IDs, unique IDs and configuration keys are unchanged.

## Battery & Price chart

The new full-width card compares actual battery operation with market price for the current local Home Assistant day.

- GoodWe battery charging (`battery_power < 0`) is shown below zero.
- Battery discharging (`battery_power > 0`) is shown above zero.
- Market price is a separate line with a currency/kWh axis.
- A NOW marker separates observed battery operation from later available price slots.
- Approximate charged/discharged summaries integrate the displayed Recorder 5-minute mean buckets; they are visualization aids, not accounting entities.
- The graph has an expandable read-only detail view and uses a five-minute frontend cache.

Battery history comes from the existing `battery_power` Home Assistant entity/Recorder statistics. No duplicate Modbus or battery entity path is introduced.

The read-only `gw_energypilot/battery_price/get` WebSocket API serves timestamped market, effective buy and effective sell series from the same EnergyPilot price path used for EMHASS. Dashboard reads do not start an optimization.

See `docs/BATTERY_PRICE_CHART.md`.

## Synchronized on-grid minimum SOC

Field validation confirmed that the GoodWe inverter-side on-grid minimum in register `45356` can remain more restrictive than EMHASS `battery_minimum_state_of_charge`. Lowering only the EMHASS value therefore does not necessarily allow discharge to the requested minimum.

The existing EMHASS minimum-SOC NumberEntity remains the single normal on-grid operator control. An explicit change now performs:

```text
validate requested minimum against EMHASS maximum
require current readable GoodWe 45356
write requested whole percentage to GoodWe 45356
verify same-register read-back
write the same percentage to EMHASS battery_minimum_state_of_charge
publish verified GoodWe value into coordinator state
schedule the existing debounced fresh optimization
```

If `45356` is unavailable, neither layer is changed. If the GoodWe write verifies but the following EMHASS write fails, EnergyPilot attempts to restore the previous `45356` value. A failed rollback is surfaced instead of hidden.

There is no startup/background synchronization. The cross-system write happens only after an explicit minimum-SOC NumberEntity change.

The direct on-grid `45356` dashboard field-test card is removed to avoid two competing controls. Off-grid register `45358` remains an independent manual Beta field test. Maximum SOC remains EMHASS-only. The existing `beta_soc` backend API remains available for diagnostics/backwards-compatible tooling.

## Safety and compatibility

- No new or guessed GoodWe register definitions.
- No Modbus read-block changes.
- EMS registers remain `47511` / `47512` with `47512 -> wait -> 47511` ordering.
- Battery/Grid/Hybrid Automatic Control mappings are unchanged.
- No EMHASS objective/cost-function change.
- No existing entity unique ID or stable device-identity change.
- Persistent grid-accounting, runtime `last_success` and optimization-log stores are unchanged.
- The Battery & Price graph is read-only and must not become the source for future persistent financial accounting.

v0.26 remains **Beta** because the Battery & Price visualization and synchronized cross-system SOC transaction still need broader multi-installation field exposure.
