<p align="center">
  <img src="https://raw.githubusercontent.com/SuperdaveNLD/GW_EnergyPilot/main/custom_components/gw_energypilot/brand/logo.png" alt="GW EnergyPilot" width="180">
</p>

# GW EnergyPilot

**Turn a GoodWe ETA-G20 into a transparent, price-aware home energy system.**

GW EnergyPilot brings live inverter telemetry, safe local battery control,
EMHASS planning, dynamic prices and EV protection together in one built-in
Home Assistant dashboard. See what your home is doing now, understand what the
battery is going to do next and let one clearly owned control path execute the
plan.

[Get started](#installation--first-validation) ·
[English user guide](docs/USER_GUIDE.md) ·
[Nederlandse handleiding](docs/HANDLEIDING_NL.md) ·
[Latest beta](docs/releases/v1.3.0-beta.3.md)

> This project is independent and is not affiliated with or endorsed by GoodWe.

## One cockpit for your home energy

EnergyPilot is built for people who want more than a collection of inverter
sensors. It connects measurement, planning and execution while keeping each
system's responsibility explicit:

- **See the whole energy flow** — live PV, home, grid and battery power, SOC,
  phase currents, temperatures, daily import/export and optional external PV;
- **Plan around energy prices** — run and publish EMHASS plans on reliable
  wall-clock boundaries with optional Nord Pool/runtime pricing;
- **Control the inverter locally** — translate the active battery/grid plan to
  verified GoodWe EMS modes and setpoints over local Modbus TCP;
- **Choose how the plan is followed** — Battery, Grid or Hybrid control, from
  direct battery power to GoodWe smart-meter/PCC targets;
- **Protect the system when reality changes** — block home-battery discharge
  into a charging EV, wait for fresh plans and suspend EV coordination when
  charger state becomes stale;
- **Keep plans resilient** — bridge a temporary missing EMHASS publication
  with the last validated, still-current official plan, never an expired guess;
- **Tune battery behaviour without black boxes** — five transparent profiles,
  price-relative SOC preferences, power-stress and anti-churn costs, plus a
  fully editable Custom mode;
- **Understand every decision** — compare plan, actual battery power and price,
  inspect execution history and create a credential-free diagnostic report.

All EMS and minimum-SOC writes remain local and are read back for verification.
SEMS+ is an optional Beta telemetry source only; it never becomes a control
transport.

## How the intelligence fits together

```text
GoodWe + Home Assistant telemetry
                ↓
       EMHASS price-aware plan
                ↓
   EnergyPilot safety + strategy layer
                ↓
   verified local GoodWe EMS command
```

The dashboard's **?** button opens the user guide in English or Dutch, based on
the Home Assistant language. The guide covers first setup, daily operation,
strategies, Battery Saver, EV features, troubleshooting and safe validation.

## Status

**v1.3.0-beta.3 · Beta prerelease**

Latest production release: **v1.2.0 · Stable**

Primary reference hardware: **GoodWe GW15K-ETA-G20**.

Stable releases are the production default in HACS. Beta builds remain an
explicit per-repository opt-in for testers.

### Release channels from v1

GW EnergyPilot keeps one Home Assistant integration/domain and exposes two HACS
release channels:

- stable production releases use `v1.x.x`, are normal GitHub Releases and are
  the default for HACS users;
- opt-in test releases use `v1.x.x-beta.N` and are GitHub prereleases;
- branch pushes never publish a release; only a validated tag can do so.

`v1.2.0` is the stable production release promoted from the fully validated
beta.7 candidate. It retains the measured missing-click recovery and enlarged
Battery · Plan · Price and execution-history controls behind a new complete
frontend cache boundary. Every recovered touch still enters the existing
native click, form-submit or change route exactly once. Local Modbus remains
mandatory for every EMS and minimum-SOC write/read-back. Normal HACS users
receive this release without enabling prereleases.
See `docs/RELEASE_WORKFLOW.md` for the exact maintainer and Home Assistant steps.

Release documentation:

- `docs/USER_GUIDE.md` — English installation and daily-use guide;
- `docs/HANDLEIDING_NL.md` — Nederlandse installatie- en gebruikershandleiding;
- `docs/releases/v1.3.0-beta.3.md` — current actual-versus-expected solar-production graph beta notes;
- `docs/releases/v1.3.0-beta.2.md` — responsive Power overview and optional EV charger beta notes;
- `docs/releases/v1.3.0-beta.1.md` — compact-controls, flow-motion and built-in-help beta notes;
- `docs/RELEASE_NOTES.md` — current release index and channel scope;
- `docs/releases/v1.2.0.md` — current stable mobile-control and telemetry release notes;
- `docs/releases/v1.2.0-beta.7.md` — validated beta.6 touch-control roll-forward notes;
- `docs/releases/v1.2.0-beta.6.md` — chart/history mobile touch-target notes;
- `docs/releases/v1.2.0-beta.5.md` — Companion touch-click recovery notes;
- `docs/releases/v1.2.0-beta.4.md` — isolated iOS activation-method comparison notes;
- `docs/releases/v1.2.0-beta.3.md` — EMHASS AUTO/CUSTOM fixed load-forecast notes;
- `docs/releases/v1.2.0-beta.2.md` — SEMS SOC, Wanted-SOC timing and local Beta tests notes;
- `docs/releases/v1.2.0-beta.1.md` — mobile-control and SEMS+ combined beta notes;
- `docs/releases/v1.1.1.md` — previous stable managed-profile settings-save hotfix notes;
- `docs/releases/v1.1.0-beta.2.md` — validated prerelease hotfix notes;
- `docs/releases/v1.1.0.md` — previous stable Chargegasm, plan-range and PV-flow release notes;
- `docs/releases/v1.1.0-beta.1.md` — promoted beta-candidate notes;
- `docs/releases/v1.0.1-beta.4.md` — earlier opt-in beta release notes;
- `docs/releases/v1.0.1-beta.3.md` — previous opt-in beta release notes;
- `docs/releases/v1.0.1-beta.2.md` — earlier opt-in beta release notes;
- `docs/releases/v1.0.1-beta.1.md` — earlier opt-in beta release notes;
- `docs/releases/v1.0.0.md` — first stable v1 release notes;
- `docs/RELEASE_NOTES_V051.md` — development notes for the v0.51 feature layer promoted in v1.0.0;
- `docs/RELEASE_WORKFLOW.md` — v1 stable/beta branches, tags, gates and HACS selection;
- `docs/RELEASE_NOTES_V050.md` — v0.50 GoodWe phase-aware EV charger control and feedback;
- `docs/RELEASE_NOTES_V049.md` — v0.49 wall-clock plans, EV coordination and dashboard reliability;
- `docs/RELEASE_NOTES_V048.md` — v0.48 neutral-safe signed Hybrid PCC control;
- `docs/RELEASE_NOTES_V047.md` — v0.47 editable Custom battery costs and profile tuning;
- `docs/RELEASE_NOTES_V046.md` — v0.46 grouped external-PV controls and master switch;
- `docs/RELEASE_NOTES_V045.md` — consolidated v0.45 PV, SOC, live-flow and Optimize release;
- `docs/RELEASE_NOTES_V044.md` — v0.44 stable Optimize action and post-restart optimization recovery;
- `docs/RELEASE_NOTES_V043.md` — v0.43 reliable mobile touch-control presentation;
- `docs/RELEASE_NOTES_V042.md` — v0.42 clearer EMHASS settings overview;
- `docs/RELEASE_NOTES_V041.md` — v0.41 stable DOM, native scrolling and no-motion dashboard;
- `docs/FRONTEND_STABLE_DOM.md` — structural-render, telemetry-patch, interaction and browser-regression contract;
- `docs/FRONTEND_CONTROL_ARCHITECTURE.md` — complete control inventory and permanent declarative Lit boundary;
- `docs/FRONTEND_IPHONE_ACCEPTANCE.md` — physical Safari/Companion acceptance and passive trace protocol;
- `docs/RELEASE_NOTES_V040.md` — v0.40 stable dashboard/menu controls across full renders;
- `docs/RELEASE_NOTES_V039.md` — v0.39 stable strategy hover and complete Dutch Controller copy;
- `docs/RELEASE_NOTES_V038.md` — v0.38 rebuilt controls and canonical live-flow direction;
- `docs/FRONTEND_CONTROL_REBUILD.md` — frontend action/highlight/flow ownership;
- `docs/RELEASE_NOTES_V035.md` — v0.35 EMHASS topology-ownership fix;
- `CHANGELOG.md` — detailed technical history;
- `docs/EMHASS_CONFIG_SYNC.md` — required EMHASS synchronization and ownership boundaries;
- `docs/EMHASS_PLAN_RUNTIME.md` — persistent canonical EMHASS plan/recovery contract;
- `docs/BATTERY_SAVER.md` — Battery Saver profiles, anti-churn tuning and ownership;
- `docs/EV_ANTI_DISCHARGE.md` — EV anti-discharge control contract;
- `docs/EV_LOAD_BALANCING.md` — isolated soft EV charger load-balancing contract;
- `docs/DEBUG_LOG.md` — opt-in LOG-tab debug-session/support-report contract;
- `docs/EMS_MODES.md` — GoodWe EMS modes 1–12;
- `docs/ACCOUNTING.md` — persistent grid accounting;
- `docs/RUNTIME_STATE.md` — persistent runtime evidence;
- `docs/BATTERY_PRICE_CHART.md` — Battery & Price graph/data ownership;
- `docs/BATTERY_PLAN_CHART.md` — plan-versus-actual graph/data ownership;
- `docs/SETTINGS.md` — settings and synchronized minimum-SOC contract;
- `docs/PV_INSIGHT.md` — internal/external display-only PV source aggregation.
- `docs/SEMS_API.md` — SEMS+ Beta login, mapping and local-control boundary.

## v1.3.0-beta.3 highlights

- Adds solid actual and dashed expected solar-production lines to the Large
  and expanded Battery · Plan · Price graph.
- Uses existing combined-PV Recorder statistics for actuals and only
  non-negative `P_PV` points from the validated official EMHASS plan for the
  forecast; both remain display-only.
- Advances the complete frontend cache boundary to `1.3.0-beta.3` without
  changing GoodWe, EMS, EMHASS, Battery Saver or accounting semantics.

## v1.3.0-beta.2 highlights

- Adds `S`, `M` and `L` Power overview sizes for one column, two columns or a
  complete dashboard row, with a safe single-column mobile fallback.
- Corrects node alignment by selecting compact flow geometry from the actual
  card width instead of the browser viewport.
- Shows an EV charger branch only when a charger source is configured and
  keeps it explicitly display-only and part of total household load.
- Keeps expanded EnergyPilot disclosures above neighboring card-window
  controls and makes the non-interactive `AUTO ACTIVE` badge substantially
  smaller without changing operational touch targets.
- Advances the complete frontend cache boundary to `1.3.0-beta.2` without
  changing GoodWe, EMS, EMHASS, Battery Saver or accounting semantics.

## v1.3.0-beta.1 highlights

- Consolidates operational controls into one normal-width, fixed dashboard
  card with always-visible quick actions and compact native disclosures.
- Restores optional live-flow particle motion while retaining zero non-flow
  animations/transitions and respecting both the saved off state and reduced
  motion.
- Removes duplicate EMHASS overview SOC editors and keeps Battery Strategy →
  Custom as the single owner.
- Adds a localized **?** header link plus complete English and Dutch guides for
  setup, safe validation, daily operation and troubleshooting.
- Uses the complete `1.3.0-beta.1` frontend cache boundary. GoodWe registers,
  EMS semantics, EMHASS ownership, entity identities and persistent stores are
  unchanged.

## v1.2.0 highlights

- Promotes the exact v1.2.0-beta.7 runtime behavior to the normal HACS
  production channel without changing GoodWe, EMS, EMHASS or Battery Saver
  semantics.
- Includes the permanent mobile control surface, bounded 120 ms missing-click
  recovery and at least 44 × 44 CSS-pixel graph/history touch targets.
- Includes optional SEMS+ Beta telemetry, persistent plan resilience and the
  EMHASS AUTO/CUSTOM fixed-load forecast introduced across the beta line.
- Advances the complete frontend cache boundary to `1.2.0-stable1`.

## v1.2.0-beta.7 highlights

- Reissues the complete beta.6 mobile-control behavior as the next immutable
  prerelease after another full repository and browser validation pass.
- Retains the 120 ms missing-click recovery and the 44 CSS-pixel chart/history
  touch targets without changing GoodWe, EMS, EMHASS or Battery Saver logic.
- Advances the complete frontend cache boundary to
  `1.2.0-beta.7-chart-touch1` so Home Assistant loads one coherent module graph.

## v1.2.0-beta.6 highlights

- Expands the real coarse-pointer/narrow-display targets for `S/M/L`,
  `12h/24h/36h`, chart expand/footer actions and execution-history open/close
  controls to at least 44 × 44 CSS pixels.
- Retains the compact desktop presentation and proves the larger mobile groups
  fit without horizontal card overflow.
- Exercises the production 120 ms missing-click recovery on the real chart
  size/range and full-history controls, including late-click deduplication and
  a close button removed from the DOM by its own action.
- Advances the complete frontend cache boundary to
  `1.2.0-beta.6-chart-touch1`.

## v1.2.0-beta.5 highlights

- Applies the proven native-click plus 120 ms fallback to every enabled native
  button in the EnergyPilot panel, including operational controls, settings
  tabs/actions, layout controls, diagnostics, chart/history and modal buttons.
- Covers dashboard-menu checkbox/radio labels and native `summary`/semantic
  button controls through the same root-scoped adapter.
- Uses the existing `.click()` route only; it never calls Home Assistant,
  GoodWe or EMHASS directly and therefore retains the permanent control
  surface's pending, acknowledgement and error guards.
- Rejects movement beyond 12 px and `pointercancel`, never captures a pointer or
  cancels vertical scrolling, and suppresses one late physical click after a
  fallback so one touch cannot become two actions.
- Keeps the numbered Beta Tests controls unadapted as a raw comparison and adds
  production fallback metrics to their JSON export.
- Advances the complete frontend cache boundary to
  `1.2.0-beta.5-touch-fallback1`.

## v1.2.0-beta.4 highlights

- Adds five numbered local test methods: clean native click, direct pointerup,
  delegated pointerup, native click with a 120 ms fallback, and immediate
  pointerup with late-click deduplication.
- Buffers event and action evidence without a Lit render during the native
  pointer-to-click synthesis window; visible counters refresh after 650 ms of
  inactivity.
- Rejects pointerup activation after more than 12 px movement and retains zero
  Home Assistant, GoodWe and EMHASS calls from the diagnostic page.
- Keeps the previous eight native control comparisons available under a
  collapsed section and exports both `methods` and `controls` evidence.
- Advances the complete frontend cache boundary to
  `1.2.0-beta.4-touch-methods1`.

## v1.2.0-beta.3 highlights

- Adds **Load forecast · AUTO / CUSTOM** to Settings → EMHASS.
- Keeps the existing GoodWe/Recorder load forecast unchanged in **AUTO**, which
  remains the upgrade default for existing installations.
- Shows a fixed-watt field only in **CUSTOM** and replaces only the runtime
  `load_power_forecast` sent to `/action/dayahead-optim`.
- Derives the list length from an existing runtime `prediction_horizon` or from
  the active EMHASS `delta_forecast_daily` and `optimization_time_step`. One day
  at 15 minutes therefore sends 96 equal values; the default custom value is
  700 W.
- Advances the complete frontend cache boundary to
  `1.2.0-beta.3-load-forecast1`.

## v1.2.0-beta.2 highlights

- Includes the permanent mobile controls and selectable SEMS+ telemetry from
  beta.1 without changing GoodWe control ownership or persistent identities.
- Rejects the observed transient SEMS `soc: 0` placeholder, falls back to the
  selected inverter SOC and otherwise blocks an EnergyPilot-owned solve on an
  unavailable SOC.
- Adds credential-free raw/mapped SEMS evidence and SOC source decisions to the
  opt-in LOG debug report and Home Assistant debug logger.
- Places EMHASS Wanted SOC at the evidenced end of each 15/30/60-minute power
  interval in the chart and immutable execution evidence.
- Adds a local-only **Beta tests** page for physical Safari/Companion button,
  switch, select and slider diagnosis; it cannot send HA, GoodWe or EMHASS
  commands.
- Protects the complete `1.2.0-beta.2-soc-end-sems2-beta-tests1` frontend graph
  with desktop Chromium, iPad WebKit and iPhone WebKit regression gates.

## v1.1.1 highlights

- Fixes EP and EMHASS settings saves after a managed battery profile has been
  selected, while preserving its internal SOC-limit ownership flag.
- Includes every change from v1.0.1-beta.4, including explicit EV charging
  detection and bounded fresh-plan retries after charging stops.
- Adds **Chargegasm** between Gold Rush and Balanced as the lighter
  battery-preservation profile.
- Every managed profile owns a complete hard SOC range, matching comfort zone
  and price-relative low/high-SOC, power-stress and anti-churn costs.
- Selecting a managed profile applies the EMHASS policy and verified GoodWe
  Minimum SOC as one rollback-safe transaction; **Custom** returns both SOC
  sliders and all cost controls to the operator.
- Battery Strategy hides editable sliders for managed profiles and shows the
  active policy values instead. Settings → EMHASS contains the complete
  read-only profile comparison.
- Battery · Plan · Price remembers a 12h rolling, 24h local-day or 36h extended
  view without another Recorder query for each range click.
- The compact PV group separates internal ETA/DC PV from aggregated external
  AC/PCC PV while retaining one combined display total.
- Automatic Control collapses the connected manual mode/power controls to a
  compact ownership summary; manual ownership reveals the same controls again.
- The desktop Chromium, iPad WebKit and iPhone WebKit matrix protects the
  complete `1.1.1-stable1` frontend graph.

## v1.0.1-beta.4 highlights

- Settings → EV offers one explicit charging-detection choice: a measured
  charger-power sensor or a charging status/boolean.
- Only the selected source controls EV anti-discharge. Status detection accepts
  `on`, `true`, `charging` and `connected_charging`; charger current limits and
  allocated current remain excluded because they can stay non-zero while idle.
- Existing entries without the new choice retain the exact former
  `connected_charging`-or-power behavior until the operator saves a method.
- If the fresh-plan request after EV charging stops fails transiently, the
  battery remains safely held while EnergyPilot retries after 5, 15, 30 and 60
  seconds. Charging restarting cancels the pending retry.
- Tesla Wall Connector users can select the `Opladen` binary sensor; plug and
  connectivity entities describe connection state, not active charging.
- GoodWe registers, EMS writes, normal strategy decisions, entity identities
  and persistent Store schemas remain unchanged.

## v1.3.0-beta.1 frontend reliability work

- The former full-width control area is consolidated into one normal-width,
  fixed **EnergyPilot controls** card immediately after the four live power
  cards. Its four quick actions stay visible in a 2 × 2 grid; EMHASS, Battery
  Strategy and manual EMS use compact disclosures; and Optimize remains one
  tap away. Battery Strategy → Custom remains the single SOC editor.
- Operational dashboard controls now live in one permanent declarative Lit
  surface with native buttons/clicks and frozen control-only models.
- Service completion never selects a control optimistically: each action waits
  for matching Home Assistant or API publication, with visible pending/error
  state and duplicate-request rejection.
- The exact control nodes survive telemetry, plan refresh, Settings and real
  language/narrow/panel structural changes. The inherited renderer no longer
  assigns `shadowRoot.innerHTML`.
- A dedicated desktop Chromium, iPad WebKit and iPhone WebKit gate executes 50
  actions for every rendered control across ten critical groups (1,500 per
  profile, 4,500 total) and also covers delayed/reordered
  publication, errors, unknown state, keyboard/focus, scrolling, geometry and
  1,000 telemetry updates.
- Automated software acceptance is complete. Physical iPhone Safari and Home
  Assistant Companion acceptance remains open and must follow
  `docs/FRONTEND_IPHONE_ACCEPTANCE.md`.
- The dashboard layout menu now contains **Beta tests**, a local-only control
  laboratory with eight native button, switch, select and slider variants.
  Pointer/click/action counters help isolate a physical Safari or Companion
  failure without sending a Home Assistant service, WebSocket, GoodWe or
  EMHASS command.
- This frontend-only work does not change GoodWe registers/writes, EMS mappings,
  controller decisions, EMHASS ownership, entities, configuration or Store
  schemas.

## v1.0.1-beta.3 highlights

- Wall-clock and startup-recovery callbacks wait until Home Assistant Core is
  running, avoiding false failed EMHASS runs during an ordinary restart.
- Only an enabled historical recurring automation blocks native scheduling;
  the manual optimize-now script and a disabled automation no longer cause a
  false `legacy_yaml_detected` state (#115).
- The live EMHASS Mapping metric now shows the backend controller's canonical
  GoodWe mode and target, including Hybrid mode 1 around a zero grid target.
- The v1.0.1-beta.2 two-deadband behavior and all earlier beta fixes remain
  included; GoodWe writes and control decisions are unchanged.

## v1.0.1-beta.2 highlights

- Automatic Control now has separate thresholds for Battery Hold on `P_batt`
  and GoodWe Auto on `P_grid`, with fresh defaults of 100 W and 1000 W.
- Hybrid checks Battery Hold first, GoodWe Auto second and signed mode 9/10 PCC
  control third without subtracting either threshold from the setpoint.
- Settings → EP shows both values together with a central 0 W marker,
  charge/discharge directions and the mode 10/1/8/1/9 bar.
- Existing stored `deadband` values remain Battery Hold values; the upgrade does
  not silently retune existing installations.
- EV anti-discharge remains higher priority and uses each threshold only for
  its matching battery or grid decision.
- The v1.0.1-beta.1 interval and WebKit click fixes remain included.

## v1.0.1-beta.1 highlights

- Legacy integral optimization cadences stored as numbers such as `15.0` are
  normalized to the selector's canonical `15` form, so opening and saving the
  options flow does not reject an otherwise supported cadence (#111).
- Optimize now and EMHASS strategy buttons keep their existing text nodes when
  live telemetry does not change their label, preserving the native mobile
  click that WebKit delivers after `pointerup` (#110).
- The complete desktop Chromium, iPad WebKit and iPhone WebKit matrix now holds
  both affected controls through rapid telemetry patches and verifies one
  delivered action without a full render or replaced control.
- No GoodWe register, EMS command, Automatic Control decision, entity identity,
  persistent Store or EMHASS ownership behavior changes.

## v1.0.0 highlights

- One new **EMHASS → GOODWE** card shows the nearest decisions around ±6 hours and opens a full 48-hour history plus 24-hour conditional projection.
- Every automatic decision snapshots its EMHASS plan source, wanted SOC, strategy/config, actual SOC/power, expected GoodWe command, write result and refreshed mode/setpoint read-back.
- Execution evidence is UTC-aware, retained for seven days with a 4096-event cap and stored separately from configuration; existing installations start with an empty history without migration.
- Large/expanded Battery · Plan · Price charts estimate grid-versus-solar battery charging and battery-versus-solar export from Recorder battery/PV/load/grid actuals, preserving unknown residuals instead of inventing a source.
- The dashed wanted-SOC line remains and now uses immutable historical decision snapshots before continuing with the current official EMHASS plan.
- Verified EV anti-discharge blocking and charge-permitted intervals are shown on the same execution timeline without inventing spans across Home Assistant restarts.
- Generic Battery Strategy wording and connectivity-detail layering are corrected without changing controller behavior.
- Attribution is dashboard-only and approximate: GoodWe control, EMHASS inputs, financial accounting, registers, identities and write ordering are unchanged.
- Tag-only release automation keeps normal HACS users on stable while testers can explicitly select published prereleases.
- The complete desktop Chromium, iPad WebKit and iPhone WebKit matrix protects the stable v1 entrypoint and its `0.51-h1` feature graph.

## v0.50 highlights

- EV load balancing reads L1/L2/L3 automatically from the linked GoodWe coordinator; the manual `Measured phase current` entity is removed.
- One-phase chargers use their configured L1/L2/L3 phase, while three-phase chargers guard the highest live phase and require complete three-phase telemetry.
- The writable charger current-limit control is separated from the read-only allocated-current feedback sensor.
- Applied charger requests are verified for up to 60 seconds with a 0.25 A tolerance, so a Zaptec feedback value such as 15.984 A confirms a 16 A request.
- The EV Online binary sensor is accepted by the EV settings API, and unambiguous Zaptec control/feedback candidates can be proposed from Home Assistant device and config-entry relations.
- New or unset regulator windows default to 15 minutes; explicitly stored existing values remain unchanged.
- The complete desktop Chromium, iPad WebKit and iPhone WebKit matrix protects the `0.50-ev1` frontend graph.

## v0.49 highlights

- One serialized scheduler owns full EMHASS optimization and active saved-plan publication on local wall-clock boundaries; new choices are 15/30/60 minutes with 15 recommended.
- Optional soft EV load balancing adjusts one configured charger-current entity after sustained overload/headroom without writing GoodWe, Automatic Control or EMHASS.
- Compact connectivity status covers Modbus, charger and effective EV coordination, including a five-minute stale-charger suspension guard.
- Controller diagnostics show the active EV protection decision and persist the latest successfully completed EMS setpoint transaction.
- Plan S/M/L controls survive scoped graph refresh, SOC targets retain canonical live fallbacks, and the Hybrid explanation no longer changes height during telemetry.
- The complete desktop Chromium, iPad WebKit and iPhone WebKit matrix protects the consolidated `0.49-consolidated1` frontend graph.
- Issue #99 remains open/on hold without a speculative fix because its white-screen report could not be reproduced.

## v0.48 highlights

- A neutral Hybrid `P_batt` plan always selects mode 8 Hold, even while actual house load imports from the grid or PV exports.
- Every non-neutral Hybrid plan follows signed `P_grid`: mode 1 around zero, mode 9 for planned import and mode 10 for planned export.
- The configured per-entry deadband is applied to `P_batt` and `P_grid` in that order; exact boundaries remain neutral.
- Mode-9/10 setpoints use the complete absolute `P_grid` target, capped only by the configured maximum power.
- EV anti-discharge, Battery/Grid strategies, manual EMS ownership, registers and write ordering remain unchanged.
- The active dashboard explains the current Hybrid 8/1/9/10 behavior in English and Dutch.

## v0.47 highlights

- **Custom / Aangepast** is a first-class Battery Saver choice in both the dashboard and Settings → EMHASS.
- Administrators can edit the five supported raw EMHASS battery cost values in one validated transaction and immediately rebuild the plan; a failed write or first optimization restores the previous Battery Saver configuration.
- Gold Rush, Balanced and Battery Saver use a 6% × dynamic-price-reference anti-churn floor per direction. Mad-Steve retains its deliberately aggressive 2.25% floor.
- Gold Rush power stress is reduced to 1% × dynamic price reference after field comparison, while Balanced and Battery Saver retain 8% and 20%.
- All managed profiles can reach 100% SOC. A shared soft red zone above 95% applies profile-specific high-SOC dwell costs instead of hard-capping usable capacity.
- Battery Strategy and Battery Saver settings typography is larger across desktop and touch layouts without changing the stable-DOM/native-scroll contract.
- The complete active frontend graph uses the fresh `0.47-custom-battery1` cache key.
- No GoodWe register/write, EMS/Automatic Control decision, entity identity, Store, plan-resilience or accounting contract changes.

## v0.46 highlights

- **Include external PV** independently enables or disables external PV insight without affecting internal GoodWe PV.
- The four external entity selectors are grouped in one panel, dimmed and locked while off, and immediately active while on.
- Selected external entities are preserved while disabled and are simply excluded from the combined display total.
- Existing v0.45 installations with a configured external source remain active after upgrade; fresh installations default to external PV off.
- Static live-flow connectors use integrated arrowheads, restrained intensity and quiet idle/unavailable states without motion.
- The twelve-mode manual EMS pad collapses to a compact ownership summary while Automatic Control is on and reveals the same live controls when manual ownership becomes available (#87).
- Native mobile presses survive equivalent Home Assistant host-property updates; Battery quick actions, EMHASS strategy and manual EMS feedback remain stable through delayed publication, and an active EMHASS request rejects a duplicate tap (#84).
- The complete active frontend graph uses the fresh `0.46-external-pv1` cache key.
- No GoodWe register/write, Automatic Control decision, EMHASS objective/topology, accounting or entity-identity behavior changes.

## v0.45 highlights

- A dedicated **PV** settings page can combine canonical internal GoodWe PV with up to four external Home Assistant power entities for dashboard insight.
- The new `pv_generation_power` sensor and PV-card breakdown update from both coordinator telemetry and external entity changes, with supported power-unit normalization and invalid-source filtering.
- The combined PV value is display-only: Automatic Control, EMS, EMHASS, plans and grid accounting continue using their established canonical inputs.
- Battery Strategy SOC sliders keep the user's selected value and percentage during Chrome focus loss and telemetry, until Home Assistant confirms the saved value.
- Battery · Plan · Price overlays actual GoodWe SOC with validated
  single-battery EMHASS `SOC_opt` on a separate 0–100% axis. Because EMHASS
  computes each target after its power interval, Wanted SOC is plotted at the
  inferred 15/30/60-minute interval end rather than one slot early (#122).
- Live power connectors use static physical-direction arrows, relative low/medium/high thickness and explicit idle/unavailable states without reintroducing motion.
- **Optimize now** is one safe-area-aware floating action that remains reachable while scrolling and when the optional EMHASS card is hidden or Settings is open.
- The complete active frontend graph uses one fresh v0.45 cache key so these changes and the PV/SOC-slider work load together after upgrade.
- Issues #84 and #87 are intentionally not part of v0.45.

## v0.44 highlights

- **Optimize now** keeps `main`, the touched Optimize button, layout, Automatic Control and Battery Strategy DOM nodes connected for the complete solve/publish transaction.
- Busy/idle state, orchestrator diagnostics and the canonical Battery · Plan · Price refresh are patched in place; the inherited action-specific full dashboard render is no longer requested.
- With native orchestration enabled, EnergyPilot makes one background recovery attempt 60 seconds after restart and retries transient startup dependency failures after 15, 30 and 60 seconds.
- A successful manual, event-driven or scheduled optimization after setup cancels the remaining startup recovery sequence, preventing duplicate solves.
- No GoodWe register, Modbus, EMS mode/write order, Automatic Control decision, entity identity or persistent Store contract changes.

## v0.43 highlights

- Touch/coarse-pointer devices no longer show stale `:hover` as a second selected Optimize, EMHASS strategy, Battery Strategy, manual quick-action or layout-menu control.
- Repeated desktop Chromium, iPad WebKit and iPhone WebKit regressions verify both the visible selected state and the executed Home Assistant action.

## v0.41 highlights

- Normal GoodWe and EMHASS telemetry updates mutate the existing dashboard DOM instead of rebuilding the complete ShadowRoot, preserving button identity, focus, hover and the Home Assistant scroll container.
- Battery Strategy and Battery · Plan · Price refreshes are scoped to their own sections/cards; a fresh optimization no longer rebuilds unrelated controls.
- The active v0.41 path removes inherited pointer/render guarding and delayed mobile scroll restoration, leaving vertical pan and momentum scrolling under native browser/WebView ownership.
- v0.41 originally disabled all EnergyPilot animations, transitions, flow particles and modal backdrop filters for deterministic desktop, iPad and iPhone behavior; the current development head restores only the separately tested Flow animations preference.
- Real-browser CI covers desktop Chromium, iPad WebKit touch and iPhone WebKit touch, including telemetry during scrolling, menu/buttons, plan refresh, Dutch localization and deliberate structural rerender recovery.
- No GoodWe register, Modbus, EMS, Automatic Control or EMHASS backend semantics change.

## v0.40 highlights

- Extends render stability from Battery Strategy to the other dashboard/menu/window controls that are recreated during relevant telemetry-driven full ShadowRoot renders.
- Suppresses only interactive CSS transition restart through the rebuilt controls' first painted frame; normal hover/focus transitions resume immediately afterwards.
- Keeps live telemetry rendering, live-flow animations, v0.38 click/touch protection and v0.39 strategy-hover continuity active.
- Does not restore the old hover render-lock or stale-button-node reuse mechanisms and does not change GoodWe, EMS or EMHASS control semantics.

## v0.39 highlights

- Battery Strategy hover stays visually stable across the inherited full ShadowRoot render without blocking telemetry, capturing pointers or restoring the removed v0.35 render lock.
- Dutch Home Assistant sessions now localize the remaining inherited customer-facing Controller, manual EMS, GoodWe mode/tooltips, strategy fallback, profile-description and telemetry copy.
- `gw-energy-pilot-v039.js` is a thin release wrapper over the tested v0.38 control/localization path with a fresh browser cache key and synchronized v0.39 dashboard/footer badge.
- No GoodWe register, Modbus, EMS, Automatic Control, EMHASS backend, entity-ID or persistent-state semantics change in v0.39.

## v0.38 highlights

- Battery Strategy actions and active highlighting use stable backend keys, not translated English/Dutch button text.
- Fresh v0.38 sessions skip the v0.35 pointer/render lock and v0.36.3 old-button-node reuse that caused unusable controls on some installations.
- One delegated strategy listener handles fresh rendered controls; executable tests verify the intended mode is called exactly once and buttons re-enable after completion.
- Live-flow particles use one explicit physical mapping for PV production, grid import/export, house load and battery charge/discharge.
- Mobile native scrolling, relevant-state render filtering and existing v0.34 dashboard features are retained.
- No GoodWe register, Modbus, EMS or EMHASS backend control semantics change in v0.38.

## v0.35 highlights

- EnergyPilot no longer forces EMHASS `inverter_is_hybrid = true` through either **Synchronize required config** or the automatic pre-optimization policy.
- `inverter_is_hybrid` and `set_use_pv` are installation-specific EMHASS settings. Existing values are preserved rather than inferred from the physical GoodWe inverter model.
- Explicit `inverter_is_hybrid = false` remains false, `true` remains true, and an absent key remains absent.
- Both configuration paths now share one canonical EnergyPilot runtime contract: `continual_publish = true`, `method_ts_round = first` and `set_use_battery = true`.
- The v0.34 Battery Saver tuning, deterministic Battery Plan refresh and EV anti-discharge behavior are carried forward unchanged.
- No GoodWe register, Modbus block, EMS mapping, write ordering, entity ID, unique ID or stable device identity changes are introduced by v0.35.

## Tested hardware

| Model | Status | Notes |
|---|---|---|
| **GoodWe GW15K-ETA-G20** | Active reference hardware | Primary development and field validation inverter |

Other ETA-G20 models/firmware must be validated individually.

When reporting compatibility, include inverter model/firmware, battery model, GoodWe smart-meter presence and relevant EMS/register observations.

## Main capabilities

- direct local GoodWe Modbus TCP telemetry;
- EMS mode/setpoint control;
- manual access to all twelve EMS modes;
- three Automatic Control strategies: Battery, Grid and Hybrid;
- native EMHASS optimization/publishing;
- safe EMHASS required-config synchronization that preserves installation topology;
- persistent validated EMHASS plan continuity across temporary publication gaps;
- deterministic Battery Plan refresh after EnergyPilot optimizations;
- five EnergyPilot battery profiles with price-relative SOC/power preferences, profile-owned minimum/maximum SOC and anti-churn battery-throughput costs;
- stateful EMHASS profit/cost/self-consumption strategy;
- persistent optimization history and `last_success`;
- persistent latest successful EMS-setpoint update evidence in Controller diagnostics;
- opt-in bounded LOG-tab debug sessions and copyable support reports;
- persistent Today/Yesterday grid import/export accounting;
- optional Nord Pool/runtime prices;
- Battery plan / actual / price visualization;
- EV anti-discharge protection;
- optional soft load balancing for one three-phase EV charger without GoodWe writes;
- compact Modbus/charger reachability status with an optional five-minute EV-coordination suspension guard;
- synchronized normal on-grid minimum SOC between EMHASS and GoodWe `45356`;
- low-level Beta SOC API retained for diagnostics/backwards-compatible tooling;
- built-in EnergyPilot dashboard and support diagnostics.
- display-only aggregation of internal GoodWe PV and up to four external Home Assistant PV power entities.

## Requirements

- Home Assistant 2026.8 or newer;
- HACS;
- GoodWe ETA-G20 reachable through Modbus TCP;
- fixed inverter IP address or DHCP reservation;
- EMHASS installed/started/configured for native optimization features;
- optional runtime price source when price-aware optimization/charting is used.

Typical GoodWe ETA-G20 connection:

```text
Port:    502
Unit ID: 247
```

Use only one continuously polling/controlling direct GoodWe integration where practical.

## Installation / first validation

1. Install and start EMHASS.
2. Add this repository to HACS as an Integration.
3. Install GW EnergyPilot.
4. Restart Home Assistant.
5. Add GW EnergyPilot under Settings → Devices & services.
6. Enter inverter IP, port and Unit ID.
7. Keep Automatic Control OFF during first validation.
8. Verify PV, Home, Grid, Battery and EMS read-back values.
9. Configure EMHASS output/status entities and runtime pricing if used.
10. Optionally configure external display-only PV sources under dashboard gear → PV.
11. Verify the EMHASS topology settings (`set_use_pv`, `inverter_is_hybrid`) match the model you intentionally want EMHASS to optimize; EnergyPilot preserves these settings.
12. Press Optimize now and verify fresh numeric `P_batt`, `P_grid` and optimization status.
13. Select the intended Automatic Control strategy under dashboard gear → GOODWE.
14. Enable Automatic Control only after telemetry/control semantics are confirmed.

## EMHASS configuration ownership

EnergyPilot's automatic pre-solve preparation and **Synchronize required config** use the same small runtime contract:

```text
continual_publish = false
method_ts_round = first
set_use_battery = true
```

EnergyPilot owns both the full-optimization schedule and the active-plan-step
publication schedule, so EMHASS's independent continual publisher is disabled.
New installations can choose a 15, 30 or 60 minute wall-clock optimization
cadence; 15 minutes is recommended. Runs occur at the matching local boundary
plus 15 seconds. Plan-step publication follows the inferred persisted EMHASS
timestep, and optimization always runs first when both are due. Installation
topology is different and remains owned by EMHASS/the operator:

```text
set_use_pv
inverter_is_hybrid
```

EnergyPilot does not derive `inverter_is_hybrid` from the fact that the reference GoodWe hardware is a hybrid inverter. This allows EMHASS to represent the installation topology intentionally, including non-hybrid/external-generation models where appropriate.

See `docs/EMHASS_CONFIG_SYNC.md`.

## Automatic Control

### Battery control

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt near 0 W    -> mode 8 Battery Hold
```

This remains the backwards-compatible default when no explicit strategy exists and the legacy smart-meter flag is missing/false.

### Grid control

```text
P_grid > +deadband -> mode 9 Grid import target
P_grid < -deadband -> mode 10 Grid export target
P_grid near 0 W    -> mode 1 GoodWe Auto / self-use
```

This requires a working/validated GoodWe smart meter.

### Hybrid control

```text
P_batt near 0 W -> mode 8 Battery Hold
else P_grid near 0 W -> mode 1 GoodWe Auto / self-use
else P_grid > +deadband -> mode 9 Grid import target
else P_grid < -deadband -> mode 10 Grid export target
```

Hybrid first preserves an explicit neutral battery plan. This prevents ordinary site import or PV export from becoming an active target while EMHASS asks the battery to remain idle.

For every non-neutral battery plan, Hybrid follows the signed PCC plan. Around zero grid target, mode 1 lets GoodWe close the actual local balance for internal or AC-coupled PV. Outside the configured deadband, modes 9/10 receive the complete absolute `P_grid` magnitude, limited only by maximum power. Exact positive and negative deadband boundaries remain neutral.

### EV anti-discharge override

EV coordination is a directional anti-discharge guard, not an EV charging controller. While the configured EV source indicates active charging:

```text
P_batt > +deadband or inside deadband -> mode 8 Battery Hold
P_batt < -deadband                    -> home-battery charging remains allowed
```

For an explicit home-battery charge plan:

```text
Battery strategy -> mode 11 using abs(P_batt)
Grid strategy    -> mode 9 when P_grid > deadband, otherwise mode 11 fallback
Hybrid strategy  -> mode 9 when P_grid > deadband, otherwise mode 11 fallback
```

This prevents the home battery from feeding the EV while avoiding the previous blanket hold on legitimate charging. EV-stop stale-plan protection still waits for a fresh optimization when the native orchestrator owns optimization timing.

### EV charger load balancing

Settings → **EV** can optionally guard the house connection using the linked
GoodWe meter currents. A one-phase charger observes its configured L1, L2 or L3;
a three-phase charger guards the highest live current across all three phases.
EnergyPilot adjusts one writable charger current-limit NumberEntity and uses a
separate read-only allocated-current sensor to confirm that the requested value
was applied. The default connection is `3 × 25 A`; common Dutch connection
profiles and custom one-/three-phase profiles are available. A continuous
`1–15` minute window is used for both reducing and restoring current; `15`
minutes is recommended.

This is a soft, best-effort guard, not fuse protection. It never writes GoodWe
and does nothing when the required GoodWe phase telemetry is incomplete or
invalid. The normal maximum is `16 A`; a newly selected value above `16 A`
requires an extra warning/confirmation and is permanently recorded in the
per-entry audit Store.
See `docs/EV_LOAD_BALANCING.md`.

An optional charger-online entity can protect this feature against stale EV state. Five stable minutes unreachable temporarily suspend effective EV coordination; five stable minutes online restore it only when the user setting remained enabled. The saved setting is not overwritten. The dashboard header summarizes Modbus, charger and EV-coordination status; its Modbus state follows the configured telemetry refresh interval.

## EMS / sign conventions

Battery power:

```text
negative = charging
positive = discharging
```

GoodWe smart meter register `36008`:

```text
negative = actual import
positive = actual export
```

EMHASS `P_grid` uses the opposite grid sign:

```text
positive = planned import
negative = planned export
```

EMS contract:

```text
47511 = mode
47512 = non-negative mode-specific setpoint magnitude
```

Write ordering remains:

```text
47512 -> brief wait -> 47511
```

## Minimum SOC ownership

The normal on-grid minimum is controlled through the existing EMHASS minimum-SOC NumberEntity.

An explicit change:

```text
validate request
-> require current readable GoodWe 45356
-> write 45356
-> verify read-back
-> write same percentage to EMHASS battery_minimum_state_of_charge
-> refresh coordinator state
-> debounce one fresh optimization
```

If `45356` is unavailable, neither system is changed. If EMHASS fails after a verified GoodWe write, EnergyPilot attempts to restore the previous GoodWe value.

There is no startup/background SOC synchronization for Custom. Selecting a
managed battery profile is an explicit transaction that writes and verifies its
GoodWe minimum before applying the matching EMHASS range.

The old direct **Battery minimum SOC limits** dashboard panel is not exposed as
a normal settings path. The low-level Beta SOC API remains available for
diagnostics/backwards-compatible tooling. A managed battery profile owns both
hard SOC limits; Custom restores direct access to the existing synchronized
NumberEntities.

## Battery Saver

Battery Saver is an opt-in EnergyPilot policy layer over EMHASS. It never writes
a GoodWe EMS mode directly. The public profiles are **Mad-Steve**, **Gold
Rush**, **Chargegasm**, **Balanced** and **Battery Saver**.

Choose **Custom / Aangepast** to keep direct ownership of the active EMHASS
battery policy. The dashboard and **Settings → EMHASS → Battery Saver** expose
the same five editable raw cost values plus the existing Minimum and Maximum
SOC sliders. **Save and optimize** writes the complete intended EMHASS
configuration without replacing unrelated settings and immediately builds a
fresh plan. Custom editing currently requires one EMHASS battery model.

Managed profiles hide the SOC sliders and show their hard range, comfort zone
and preservation factors read-only. Selecting one first writes and verifies its
whole-percentage GoodWe minimum, then applies the matching EMHASS minimum,
maximum and economic profile before publishing a fresh plan. Failure restores
the previous GoodWe minimum, mode and all owned EMHASS fields.

The complete comparison and the cell-aging rationale behind lower average SOC,
power stress and throughput costs are shown in **Settings → EMHASS → Battery
Saver** and documented in `docs/BATTERY_SAVER.md`. The factors are transparent
optimizer policy, not a battery-specific lifetime promise.

See `docs/BATTERY_SAVER.md` for exact profile factors and ownership.

## Battery plan / actual / price chart

The chart is read-only.

- actual battery bars use Recorder 5-minute means from the existing GoodWe `battery_power` entity;
- charging is below zero, discharging above zero, while near-zero samples are not drawn as false directional bars;
- historical plan blocks use the configured EnergyPilot `P_batt` entity history, including the state already active at local midnight;
- future plan blocks prefer the validated persistent official EMHASS plan mirror; current Home Assistant `battery_scheduled_power` and legacy/custom `forecasts` remain compatibility fallbacks;
- the forecast interval active at NOW is clipped at NOW rather than discarded because it began a few minutes earlier;
- dashed plan overlays render above solid actual bars;
- every successful EnergyPilot-owned optimization advances `plan_revision`, allowing the frontend to force-refresh the canonical card immediately after the persistent plan refresh attempt;
- `P_batt.last_updated` remains a compatibility invalidation fallback for plans changed outside EnergyPilot;
- the market-price series comes from the same EnergyPilot runtime price source used for EMHASS and is rendered as interval steps;
- `12h` is a rolling zoom from six hours before through six hours after now, `24h` remains fixed today, and `36h` runs from today 00:00 through tomorrow 12:00 in the configured Home Assistant timezone;
- range clicks reuse one cached dataset without another Recorder query, while unavailable future plan/price coverage remains visibly unavailable rather than extrapolated;
- the card supports persistent browser-local 12h/24h/36h and S/M/L choices plus an expanded detail view;
- native GoodWe day counters `35208` / `35211` are preferred for the headline charged/discharged totals;
- Recorder-integrated battery power remains a separate visualization comparison and is not calibrated to force a match with the native inverter counter;
- if no usable plan exists, planned-energy summaries display `—` rather than a fabricated zero.

Future persistent financial accounting must consume backend grid-accounting deltas and effective prices, not reconstruct totals from chart pixels/buckets.

## Persistent state

Configuration remains in Home Assistant `ConfigEntry.data/options`, EMHASS config or GoodWe registers depending on ownership.

EnergyPilot-owned persistent runtime stores are separate:

```text
gw_energypilot.runtime.<entry_id>
gw_energypilot.control.<entry_id>
gw_energypilot.accounting.<entry_id>
gw_energypilot.optimization_log.<entry_id>
gw_energypilot.plan.<entry_id>
gw_energypilot.ev_load_balancing_audit.<entry_id>
```

The plan Store is a bounded resilience mirror of EMHASS's canonical plan, not a second optimizer or settings database. It is valid only through its inferred final plan interval. The debug session is intentionally **not** persistent and is not added to this list.

## Debug logging

Open dashboard settings → **LOG** and select **Start debug logging** only when reproducing a problem. Stop capture after reproduction, then use **Copy debug report** for support.

The debug buffer is bounded and memory-only. It observes the current EnergyPilot runtime rather than polling or controlling hardware independently. With SEMS+ selected it also records only an explicit credential-free allowlist of raw portal fields, mapped values and field-selection decisions. See `docs/DEBUG_LOG.md` for captured fields, privacy boundaries and lifecycle details.

## Safety boundary

Do not guess GoodWe register addresses, sizes, scales or signs.

`registers.py` is canonical for telemetry/register definitions. Changes to EMS mode semantics, registers `47511/47512`, sign conventions or write ordering require explicit hardware evidence.

Beta register candidates remain bounded and reversible where practical.
