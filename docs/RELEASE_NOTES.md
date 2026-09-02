# GW EnergyPilot release notes

This page is the user-facing release index for GW EnergyPilot.

`CHANGELOG.md` remains the detailed technical history. This page records the validation status and operator-visible scope of each release.

## Status definitions

- **Stable** — production release selected by HACS unless a user explicitly
  opts in to prereleases.
- **Validated** — no intentionally unconfirmed control/hardware semantics are introduced by that release and repository checks passed.
- **Beta** — functionality is intentionally available before broad field testing across installations/firmware is complete.
- **Validated + beta diagnostics** — release behavior is validated while optional diagnostics still need field correlation.
- **Historical** — older development milestone retained for release history.

Starting with v1, `v1.x.x-beta.N` is published as a GitHub prerelease from the
`beta` line and `v1.x.x` as a normal release from `main`. Existing `0.x`
history is retained unchanged. See `docs/RELEASE_WORKFLOW.md`.

# v1.2.0-beta.7 — Validated mobile-control roll-forward

This prerelease republishes beta.6's complete mobile-control behavior on a new
immutable version and frontend cache boundary. The bounded 120 ms missing-click
recovery, 44 CSS-pixel chart/history touch targets and existing permanent Lit
control surface are unchanged.

The complete Quality, HACS, hassfest and desktop Chromium/iPad WebKit/iPhone
WebKit matrix is repeated for the beta.7 commit. GoodWe, EMS, EMHASS, Battery
Saver, entity identity and persistent-state semantics are unchanged. See
`docs/releases/v1.2.0-beta.7.md`.

# v1.2.0-beta.6 — Larger chart and history touch targets

The remaining compact Battery · Plan · Price controls now expose real minimum
44 × 44 CSS-pixel targets on coarse-pointer or narrow displays. This covers
`S/M/L`, `12h/24h/36h`, chart expand/footer actions and execution-history
open/close controls while retaining the compact desktop presentation.

The browser matrix now removes native click from the real chart-size,
chart-range and full-history buttons and proves exactly one fallback action,
late-click deduplication, modal close after its node is removed, no horizontal
card overflow and no JavaScript/page errors. Beta.5's bounded 120 ms adapter
and all GoodWe/EMS/EMHASS semantics are unchanged. See
`docs/releases/v1.2.0-beta.6.md`.

# v1.2.0-beta.5 — Companion touch-click recovery

The 120 ms method that completed every valid beta.4 Companion pointer sequence
is now applied once at the EnergyPilot panel boundary. Buttons in the permanent
EMS surface, Settings, dashboard layout, diagnostics, graphs, history and
modals all retain their original click handlers. Dashboard-menu checkbox/radio
controls use that same bounded recovery.

A native click arriving in time proceeds normally. If it is absent after a
primary touch that moved no more than 12 px, EnergyPilot calls only the same
element's existing `.click()` route. One later physical click is deduplicated.
Movement, pointer cancellation, disabled/disconnected targets, mouse/pen and
keyboard use do not enter this fallback path. Pointer listeners remain passive;
the adapter never captures a pointer, cancels scrolling or directly calls Home
Assistant, GoodWe or EMHASS.

The five numbered Beta Tests methods remain raw and excluded from production
adaptation. Their JSON export now also includes production fallback counters.
See `docs/releases/v1.2.0-beta.5.md` and
`docs/FRONTEND_IPHONE_ACCEPTANCE.md`.

# v1.2.0-beta.4 — Isolated iOS activation-method tests

**Beta tests** now starts with five numbered local buttons that compare a clean
native click, direct pointerup, delegated pointerup, native click with a 120 ms
fallback and immediate pointerup with late-click deduplication. Test evidence is
buffered during the complete pointer-to-click window and appears after 650 ms
of inactivity, preventing the diagnostic's own Lit render from influencing the
native click under investigation.

Pointerup-based methods require the primary pointer to remain within 12 px and
never capture the pointer, cancel a gesture or synthesize a click. The original
eight native control variants remain available in a collapsed comparison. The
page stays strictly local and cannot call Home Assistant, GoodWe or EMHASS.
See `docs/releases/v1.2.0-beta.4.md` and
`docs/FRONTEND_IPHONE_ACCEPTANCE.md`.

# v1.2.0-beta.3 — Selectable EMHASS load forecast

Settings → EMHASS now offers **Load forecast · AUTO / CUSTOM**. AUTO remains
the default and preserves the existing GoodWe/Recorder forecast. CUSTOM reveals
a fixed-watt field, initially 700 W, and applies that value to every step of an
EnergyPilot-owned day-ahead solve.

The runtime list follows an existing `prediction_horizon` when present.
Otherwise EnergyPilot derives its length from the active EMHASS
`delta_forecast_daily` and `optimization_time_step`; one day at 15 minutes is
therefore 96 equal values. The final request-body boundary replaces only
`load_power_forecast`, preserving SOC, prices, battery limits and unrelated
runtime values. Switching back to AUTO is the rollback and retains the saved
CUSTOM wattage. See `docs/releases/v1.2.0-beta.3.md`.

# v1.2.0-beta.2 — SEMS SOC safety, plan timing and local touch diagnostics

SEMS telemetry now rejects the observed transient `soc: 0` portal placeholder.
EnergyPilot first tries the selected inverter's positive SOC and otherwise
makes the battery SOC unavailable, which blocks an EnergyPilot-owned EMHASS
solve instead of initializing it at a false 0%. The opt-in LOG debug report and
Home Assistant debug logger contain only an explicit credential-free allowlist
of raw SEMS values, mapped output and SOC source/rejection decisions.

Battery · Plan · Price now places Wanted SOC at the end of the associated
EMHASS power interval (#122). A 50% `SOC_opt` row starting at 19:00 in a
15-minute plan is therefore shown at 19:15. The same contract is derived from
15-, 30- or 60-minute plans and retained in new historical execution evidence;
battery-power and price timestamps are unchanged.

The dashboard layout menu additionally offers **Beta tests**, a harmless local
control laboratory for physical Safari and Home Assistant Companion diagnosis.
Eight native button, switch, select and slider variants expose separate
pointer, click, change/input and completed-action counters. The page sends no
Home Assistant service, WebSocket, GoodWe or EMHASS command; see
`docs/FRONTEND_IPHONE_ACCEPTANCE.md` for the short field protocol.

Local Modbus remains the only transport for EMS and verified minimum-SOC
writes/read-back. Entity IDs, device identity, config entries and persistent
Store keys are unchanged. See `docs/releases/v1.2.0-beta.2.md`.

# v1.2.0-beta.1 — Mobile control modernization and SEMS+ telemetry

The operational dashboard controls now live in one permanent declarative Lit
tree. Battery actions, Automatic Control, EMHASS/Battery Strategy, Optimize,
Custom SOC and manual EMS remain connected through telemetry and structural
updates. Selected state follows confirmed backend publication, with one shared
pending/acknowledged/error contract and duplicate-request protection.

Configuration additionally offers **Local Modbus TCP** or **SEMS+ API · Beta**
as telemetry source. SEMS credentials are write-only in the dashboard; station
and inverter identity must be explicit when discovery is ambiguous. Regional
authentication, one token renewal, bounded rate-limit back-off and strict
freshness/shape/sentinel validation protect the cloud path.

Only an evidence-backed PV/load/grid/inverter/battery subset is mapped. Cloud
lifetime counters and missing meter phase currents never impersonate canonical
local registers. Local Modbus remains mandatory and solely owns every EMS and
minimum-SOC write/read-back; its health remains independent from SEMS health.
Existing entries default to Local Modbus. See
`docs/releases/v1.2.0-beta.1.md`, `docs/SEMS_API.md` and
`docs/FRONTEND_CONTROL_ARCHITECTURE.md`.

# v1.1.1 — Managed-profile settings-save hotfix

This stable patch fixes EP and EMHASS settings saves after a managed Battery
Strategy profile has been selected. The dedicated
`battery_saver_soc_limits_managed` ownership flag is now removed before the
generic dashboard schema validates the remaining options and restored
unchanged afterward. The prior `extra keys not allowed` error no longer blocks
unrelated configuration changes.

The fix does not change the selected profile, GoodWe minimum SOC, EMHASS
policy, automatic control, entities or persistent Stores. It was published and
validated first as v1.1.0-beta.2. See `docs/releases/v1.1.1.md`.

# v1.1.0-beta.2 — Managed-profile settings-save hotfix candidate

This prerelease contains the same bounded settings-save fix promoted in
v1.1.1. See `docs/releases/v1.1.0-beta.2.md`.

# v1.1.0 — Chargegasm, chart ranges and clearer PV flow

This stable release promotes the validated v1.1.0-beta.1 candidate. It includes
every v1.0.1-beta.1 through beta.4 change and adds the new
Battery Saver policy layer. Battery Strategy now offers **Mad-Steve**, **Gold
Rush**, **Chargegasm**, **Balanced**, **Battery Saver** and **Custom**. The five
managed modes have explicit hard minimum/maximum SOC ranges, comfort zones,
low/high-SOC costs, power-stress costs and anti-churn factors. The full
comparison is visible in **Settings → EMHASS → Battery Saver** and summarized
on the Controller card.

Battery · Plan · Price now remembers 12h, 24h and 36h views using backend
Home Assistant-timezone/DST windows while reusing one cached Recorder dataset.
The live PV group keeps one combined total and separates the internal ETA/DC
route from the aggregated external AC/PCC route. Automatic ownership collapses
the existing manual inverter controls to a compact summary and reveals the same
connected controls again when manual ownership returns.

Selecting a managed profile writes and verifies its whole-percentage GoodWe
on-grid minimum before applying the matching EMHASS range and building a fresh
plan. A failure restores the previous GoodWe minimum, mode and all ten owned
EMHASS fields. Direct SOC slider/service writes are rejected while a managed
profile is active; **Custom** preserves current values and restores the two
sliders. Existing v1.0 managed selections require explicit reselection, so
installing the release alone does not change the inverter minimum.

The documentation explains the lower-average-SOC, SOC-window, power and
throughput rationale and its limits. The profile factors are transparent
price-relative optimizer policy, not a battery-specific lifetime guarantee.
See `docs/releases/v1.1.0.md` and `docs/BATTERY_SAVER.md`.
# v1.0.1-beta.4 — Explicit charging detection and safe EV-stop recovery

Settings → EV now asks the operator to choose one charging signal: measured
charger power or a charging status/boolean. Only the selected source can
activate EV anti-discharge. Status mode accepts `on`, `true`, `charging` and
`connected_charging`, covering a Tesla Wall Connector `Opladen` binary sensor
and a Zaptec charging-mode sensor without treating plug/connectivity state as
active charging. Allocated or maximum current remains excluded because it can
stay non-zero while the EV is idle.

Existing entries without the method key keep their exact previous
`connected_charging`-or-power behavior until an explicit choice is saved. When
EV charging stops, a transient failure or overlap in the required fresh
optimization now keeps the battery safely held and retries after 5, 15, 30 and
60 seconds; renewed charging cancels that sequence. GoodWe registers, EMS
writes and all non-EV controller decisions are unchanged. See
`docs/releases/v1.0.1-beta.4.md`.

# v1.0.1-beta.3 — Restart-safe scheduling and canonical EMS feedback

Wall-clock boundaries and bounded startup recovery now wait until Home
Assistant Core is running before entering the optimization/logging chain. An
ordinary restart no longer creates a misleading failed EMHASS run while the
delayed recovery is still waiting to build the fresh plan.

Only an enabled historical recurring automation is treated as a competing
scheduler. Its manual optimize-now helper and a disabled automation no longer
block EnergyPilot's native schedule (#115). The live EMHASS Mapping value now
uses the backend controller's canonical expected GoodWe mode and setpoint, so
Hybrid mode 1 around a zero grid target is presented correctly. See
`docs/releases/v1.0.1-beta.3.md`.

# v1.0.1-beta.2 — Separate Battery Hold and GoodWe Auto deadbands

Automatic Control now has two explicit neutral boundaries. Battery Hold uses
`P_batt` with a 100 W fresh default; GoodWe Auto uses `P_grid` with a separate
1000 W default. Hybrid evaluates them in that order before selecting signed
mode 9/10 PCC control, and exact boundaries remain neutral.

Settings → EP presents both values with a central 0 W marker, charging and
discharging directions and the mode 10/1/8/1/9 bar. Existing stored `deadband`
values remain Battery Hold values and are not silently retuned. EV
anti-discharge remains higher priority. See
`docs/releases/v1.0.1-beta.2.md`.

# v1.0.1-beta.1 — Mobile click and legacy interval compatibility

The options flow now accepts supported wall-clock cadences that older stored
configuration represented as integral floats, such as `15.0`, and presents
them in the selector's canonical string form. Fractional or unsupported values
remain invalid.

Optimize now and EMHASS cost-function telemetry patches no longer rewrite an
unchanged button text node while WebKit is holding a native press. The browser
matrix verifies the complete press and exactly one service action on desktop
Chromium, iPad WebKit and iPhone WebKit. Controller, GoodWe and EMHASS command
semantics are unchanged. See `docs/releases/v1.0.1-beta.1.md`.

# v1.0.0 — First stable production release

The dashboard now links each EnergyPilot controller decision to its plan,
strategy, wanted and actual SOC, expected GoodWe command, write result and
refreshed GoodWe mode/setpoint read-back. The compact card covers the nearest
±6 hours; its full table presents 48 hours of retained evidence and a
conditional 24-hour projection.

Large and expanded Battery · Plan · Price views estimate which actual charge
came from the grid or solar and which grid export came from battery or solar.
Unknown residuals remain visible and the normal/compact graph keeps its
familiar charge/discharge bars. The dashed wanted-SOC line now preserves its
historical snapshots instead of rewriting elapsed time with a newer plan.

History is stored per config entry for seven days with a 4096-event cap. It
starts empty after upgrade, stores UTC instants without entity IDs or EMHASS
credentials, and never owns controller success. Source labels are estimates,
not settlement-grade accounting. Verified EV anti-discharge blocking and
charge-permitted intervals share this evidence and are runtime-session bounded.
The release also corrects generic Battery Strategy copy and connectivity-detail
layering. See `docs/releases/v1.0.0.md`, `docs/RELEASE_NOTES_V051.md` and
`docs/CHANGELOG_V051.md`.

# v0.50 — GoodWe phase-aware EV charger control and feedback

EV load balancing now reads L1/L2/L3 directly from the linked GoodWe coordinator. One-phase chargers use their configured phase; three-phase chargers guard the highest live phase and fail without a write when complete phase telemetry is unavailable.

The writable charger current-limit NumberEntity and read-only allocated-current sensor are separate fields. EnergyPilot verifies each request for up to 60 seconds with a 0.25 A tolerance, accepts the EV Online binary sensor, and proposes unambiguous Zaptec control/feedback pairs from Home Assistant registry relations. New or unset condition windows default to 15 minutes while explicitly stored existing values remain unchanged.

The regulator still never writes GoodWe or invokes Automatic Control/EMHASS. See `docs/RELEASE_NOTES_V050.md` and `docs/CHANGELOG_V050.md`.

# v0.49 — Wall-clock plans, EV coordination and stable operator feedback

EnergyPilot now owns one serialized wall-clock schedule for full EMHASS optimization and due active-plan publication. New installations select 15, 30 or 60 minutes, with 15 recommended; due plan rows are published only after fresh finite outputs are proven. Nord Pool unavailable-state classification is also corrected.

Optional soft EV load balancing adjusts one configured charger limit after sustained current conditions without writing GoodWe or invoking Automatic Control/EMHASS. A compact reachability control, stale-charger coordination guard and explicit EV anti-discharge feedback make the active safety state visible.

Controller diagnostics persist the latest successful EMS setpoint transaction. Plan S/M/L controls, live SOC target fallbacks and the Hybrid explanation now remain stable through their respective refresh paths. Issue #99 remains open/on hold without a speculative fix because the white-screen report could not be reproduced.

See `docs/RELEASE_NOTES_V049.md` and `docs/CHANGELOG_V049.md`.

# v0.48 — Neutral-safe signed Hybrid PCC control

Hybrid Automatic Control now preserves a neutral `P_batt` plan through mode 8 before considering grid flow. For every non-neutral battery plan, signed `P_grid` selects mode 1 around zero, mode 9 for planned import and mode 10 for planned export. Exact configured deadband boundaries remain neutral, and mode-9/10 setpoints keep the complete absolute grid target without deadband subtraction.

The correction follows live v0.47 diagnostics where `P_batt = +1.223 kW` and `P_grid = 0 W` still selected the inherited direct-discharge mode 12. The same plan now selects mode 1 so GoodWe can close the actual local balance. The dashboard provides matching English and Dutch Hybrid guidance.

EV anti-discharge remains higher priority. Battery/Grid strategies, manual EMS control, GoodWe registers/write order, v0.47 Battery Saver policy, EMHASS ownership and persistent state are unchanged.

See `docs/RELEASE_NOTES_V048.md` and `docs/CHANGELOG_V048.md`.

# v0.47 — Editable Custom battery costs and profile tuning

The dashboard and **Settings → EMHASS → Battery Saver** now both include **Custom / Aangepast** as a visible choice. When active, the five displayed EMHASS battery cost values are editable and saved together before EnergyPilot immediately rebuilds the plan. Invalid or negative costs are rejected, unrelated EMHASS settings are preserved and a failed save/optimization restores the previous Battery Saver transaction. The Battery Strategy and settings typography is also larger for improved readability on desktop and touch layouts.

Minimum and Maximum SOC keep using the existing synchronized Home Assistant number entities. Custom cost editing is limited to one EMHASS battery model; multi-battery installations can still select Custom to release managed-profile ownership without rewriting their values.

The preserved standard Gold Rush field plan still contained marginal one-slot charge/discharge reversals. A first 3.5% comparison was insufficient; the validated follow-up therefore sets charge and discharge anti-churn to **6% × dynamic price reference per direction**, while reducing Gold Rush battery power stress from 3% to **1% × dynamic price reference**. At the captured `0.1215` reference, the resulting `0.007290` weights removed the low-value 765 W, 857 W and 426 W reversals while preserving full 15 kW evening dispatch.

Balanced and Battery Saver adopt the same 6% transaction floor so the preservation-oriented profiles cannot accept cycling rejected by Gold Rush; their existing low-SOC and 8%/20% power-stress values remain unchanged. Mad-Steve retains 2.25% for its deliberately aggressive character.

All four managed profiles can now reach 100% SOC. The former profile-specific hard ceilings become one shared soft red zone above 95%. EMHASS applies an hourly cost to every kWh in that zone: 5% / 10% / 25% / 50% × dynamic price reference for Mad-Steve / Gold Rush / Balanced / Battery Saver. A sufficiently valuable opportunity can therefore use the last 5%, while the accumulating dwell cost discourages charging there too early or remaining full unnecessarily. Battery charge/discharge efficiency, inverter topology and all unrelated EMHASS configuration remain unchanged.

## Version overview

| Version | Date | Status | Main release notes |
|---|---|---|---|
| **1.2.0-beta.7** | 2026-09-02 | **Beta** | Republishes the fully validated beta.6 mobile-control behavior behind a new complete frontend cache boundary. |
| **1.2.0-beta.6** | 2026-09-02 | **Beta** | Enlarges the remaining chart/history touch targets and adds real missing-click coverage for S/M/L, 12h/24h/36h and full history. |
| **1.2.0-beta.5** | 2026-09-02 | **Beta** | Applies the measured 120 ms missing-click recovery to all EnergyPilot buttons and dashboard-menu switches with scroll rejection and late-click deduplication. |
| **1.2.0-beta.4** | 2026-09-02 | **Beta** | Adds observer-neutral native-click and guarded pointerup/fallback/deduplication comparisons for the Companion iOS defect. |
| **1.2.0-beta.3** | 2026-09-02 | **Beta** | Adds AUTO/CUSTOM EMHASS load forecasting with a horizon-aware fixed-watt runtime request. |
| **1.2.0-beta.2** | 2026-09-01 | **Beta** | Rejects false SEMS 0% SOC, corrects Wanted-SOC interval timing and adds an isolated local mobile-control diagnostic page. |
| **1.2.0-beta.1** | 2026-09-01 | **Beta** | Combines permanent mobile controls with guarded SEMS+ Beta telemetry while retaining local-only EMS/minimum-SOC writes. |
| **1.1.1** | 2026-08-31 | **Stable** | Fixes EP/EMHASS settings saves for managed battery profiles while preserving SOC-limit ownership. |
| **1.1.0-beta.2** | 2026-08-31 | **Beta** | Validates the managed-profile settings-save hotfix before stable promotion. |
| **1.1.0** | 2026-08-31 | **Stable** | Promotes v1.1.0-beta.1 with Chargegasm, complete managed SOC ranges, 12h/24h/36h plan views, compact manual ownership and separate internal/external PV routes. |
| **1.1.0-beta.1** | 2026-08-31 | **Beta** | Includes v1.0.1-beta.4 and adds Chargegasm, complete managed SOC ranges, 12h/24h/36h plan views, compact manual ownership and separate internal/external PV routes. |
| **1.0.1-beta.4** | 2026-08-31 | **Beta** | Adds an exclusive power-or-status EV charging detector and bounded fresh-plan retries after charging stops. |
| **1.0.1-beta.3** | 2026-08-31 | **Beta** | Makes scheduling restart-safe, fixes false legacy-scheduler detection and displays the backend controller's canonical GoodWe mapping. |
| **1.0.1-beta.2** | 2026-08-30 | **Beta** | Separates Battery Hold on `P_batt` from GoodWe Auto on `P_grid` and adds the centered decision-zone settings panel. |
| **1.0.1-beta.1** | 2026-08-30 | **Beta** | Normalizes integral legacy optimization intervals and keeps native mobile clicks connected while unchanged Optimize/strategy copy is patched. |
| **1.0.0** | 2026-08-30 | **Stable** | First stable v1: execution/read-back history, EV protection underlays, source-attribution estimates, historical wanted SOC, presentation fixes and safe tag-only stable/beta channels. |
| **0.50** | 2026-08-30 | **Beta** | Reads GoodWe L1/L2/L3 automatically for one-/three-phase EV guarding, separates writable current-limit control from allocated-current feedback, verifies applied requests and fixes Zaptec/online entity pairing. |
| **0.49** | 2026-08-30 | **Beta** | Consolidates wall-clock EMHASS plan execution, isolated soft EV load balancing, connectivity/EV safety visibility, persisted EMS evidence and stable graph/SOC/Hybrid presentation fixes. |
| **0.48** | 2026-08-30 | **Beta** | Makes Hybrid neutral-safe and signed-PCC based: mode 8 for a neutral battery plan, mode 1 around zero grid target, and complete mode-9/10 import/export targets outside the configured variable deadband. |
| **0.47** | 2026-08-29 | **Beta** | Adds administrator-editable Custom EMHASS battery costs, field-tuned anti-churn/power-stress policy and a shared soft 95–100% high-SOC red zone while preserving installation-owned settings and all GoodWe control semantics. |
| **0.46** | 2026-08-29 | **Beta** | Adds an independent external-PV master switch and groups the four entity selectors in one enabled/disabled panel while preserving existing v0.45 configurations. |
| **0.45** | 2026-08-29 | **Beta** | Consolidates PV insight and SOC-slider stability with #83 floating Optimize, #85 actual/forecast SOC and #86 static accessible live flow under one active frontend cache graph; #84 and #87 are excluded. |
| **0.44** | 2026-08-28 | **Beta** | Keeps Optimize now and the surrounding dashboard DOM stable for the complete solve/publish transaction, and adds one non-blocking post-restart optimization recovery sequence with bounded 15/30/60-second retry back-off. |
| **0.43** | 2026-08-28 | **Beta** | Fixes sticky touch-hover presentation across Optimize now, EMHASS and Battery Strategy selectors, quick actions/max export and the layout menu, with repeated iPhone/iPad WebKit tap regressions that verify both visible selection and executed actions. |
| **0.42** | 2026-08-28 | **Beta** | Reorganizes EMHASS settings into a clearer overview with explicit EnergyPilot-versus-EMHASS ownership and current/required synchronization values, without changing backend configuration semantics. |
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

# v0.46 — Grouped external-PV controls

v0.46 adds a separate **Include external PV** switch. The four external entity selectors now share one visual panel and are disabled/dimmed while the switch is off. Enabling the switch activates all fields immediately; disabling it preserves their values but excludes the sources from the read-only PV total.

Fresh installations default to external PV off. Existing v0.45 configurations with an external entity remain enabled on upgrade until the new switch is explicitly saved.

See `docs/RELEASE_NOTES_V046.md`, `docs/CHANGELOG_V046.md` and `docs/PV_INSIGHT.md`.

# v0.45 — Consolidated PV, SOC, live-flow and Optimize release

v0.45 adds a dedicated PV settings page and the `pv_generation_power` sensor. The sensor combines the canonical internal GoodWe PV total with up to four configured Home Assistant power entities, normalizes supported power units, filters invalid sources and exposes a per-source breakdown. The dashboard uses it for PV presentation and live-flow display only; controller, EMS, EMHASS, plan and accounting inputs are unchanged.

Battery Strategy minimum/maximum SOC sliders now retain an explicit local draft. Normal telemetry patches and Chrome focus loss cannot replace the range position or percentage label with stale Home Assistant state. The draft remains visible until matching backend acknowledgement and is released on failure.

Issue #85 adds actual Recorder-backed GoodWe SOC plus exact, validated single-battery EMHASS `SOC_opt` forecast to Battery · Plan · Price. Issue #86 replaces ambiguous/no-motion flow connectors with static directional arrows, relative intensity and explicit idle/unavailable states. Issue #83 keeps the single Optimize action fixed inside safe-area and viewport bounds, independent of the optional EMHASS card.

The v0.45 wrapper preserves the complete v0.44 Optimize/restart behavior and refreshes every import in the active frontend graph with one integrated release cache key. The release matrix covers all included work alongside the inherited Chromium/WebKit stable-DOM, touch, plan and scrolling contracts. Issues #84 and #87 are intentionally excluded.

See `docs/RELEASE_NOTES_V045.md`, `docs/CHANGELOG_V045.md`, `docs/PV_INSIGHT.md` and `docs/FRONTEND_STABLE_DOM.md`.

# v0.44 — Stable Optimize action and restart recovery

v0.44 removes the last action-specific complete dashboard render from **Optimize now**. The active wrapper replaces only the inherited listener, calls the existing Home Assistant button entity once and updates busy/idle presentation plus orchestrator diagnostics in place. A successful optimization still advances `plan_revision` and refreshes only the canonical Battery · Plan · Price card.

When native orchestration is enabled, EnergyPilot now schedules one background plan-recovery attempt 60 seconds after setup. Home Assistant-running state, GoodWe telemetry, EMHASS health and output-validity gates remain authoritative. Transient failures retry after 15, 30 and 60 seconds, while any newer successful optimization cancels the remaining sequence. Config-entry setup never waits for these attempts.

The release matrix covers desktop Chromium, iPad WebKit touch and iPhone WebKit touch and requires one Optimize action, zero complete renders, stable persistent controls, native scroll anchoring and working scroll after the targeted plan refresh.

See `docs/RELEASE_NOTES_V044.md`, `docs/CHANGELOG_V044.md` and `docs/FRONTEND_STABLE_DOM.md`.

# v0.43 — Reliable touch-control selection

v0.43 prevents iPhone/iPad sticky `:hover` from visually impersonating a second active selection. On touch/coarse-pointer devices, inactive Optimize now, EMHASS strategy, Battery Strategy, manual battery quick-action/max-export and layout-menu controls retain their base presentation after a tap. Actual selection remains owned by `.active` and `aria-pressed="true"` application state.

The change is a top-level frontend presentation layer over the unchanged v0.42 runtime. It does not intercept pointer events or change service/WebSocket actions. The release matrix repeatedly taps every affected control group on iPhone and iPad WebKit profiles, verifies exactly one visible selected state and confirms that each corresponding action is recorded, including across telemetry and a deliberate structural render.

See `docs/RELEASE_NOTES_V043.md`, `docs/CHANGELOG_V043.md` and `docs/FRONTEND_STABLE_DOM.md`.

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
