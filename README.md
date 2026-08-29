<p align="center">
  <img src="https://raw.githubusercontent.com/SuperdaveNLD/GW_EnergyPilot/main/custom_components/gw_energypilot/brand/logo.png" alt="GW EnergyPilot" width="180">
</p>

# GW EnergyPilot

GW EnergyPilot is an unofficial Home Assistant integration for local GoodWe ETA-G20 telemetry, GoodWe EMS control and EMHASS optimization.

> This project is independent and is not affiliated with or endorsed by GoodWe.

## Status

**v0.45 · Beta**

Primary reference hardware: **GoodWe GW15K-ETA-G20**.

In this project, **Beta** means functionality is intentionally available before broad field testing across installations and firmware versions is complete.

Release documentation:

- `docs/RELEASE_NOTES.md` — current release index and Beta scope;
- `docs/RELEASE_NOTES_V045.md` — consolidated v0.45 PV, SOC, live-flow and Optimize release;
- `docs/RELEASE_NOTES_V044.md` — v0.44 stable Optimize action and post-restart optimization recovery;
- `docs/RELEASE_NOTES_V043.md` — v0.43 reliable mobile touch-control presentation;
- `docs/RELEASE_NOTES_V042.md` — v0.42 clearer EMHASS settings overview;
- `docs/RELEASE_NOTES_V041.md` — v0.41 stable DOM, native scrolling and no-motion dashboard;
- `docs/FRONTEND_STABLE_DOM.md` — structural-render, telemetry-patch, interaction and browser-regression contract;
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
- `docs/DEBUG_LOG.md` — opt-in LOG-tab debug-session/support-report contract;
- `docs/EMS_MODES.md` — GoodWe EMS modes 1–12;
- `docs/ACCOUNTING.md` — persistent grid accounting;
- `docs/RUNTIME_STATE.md` — persistent runtime evidence;
- `docs/BATTERY_PRICE_CHART.md` — Battery & Price graph/data ownership;
- `docs/BATTERY_PLAN_CHART.md` — plan-versus-actual graph/data ownership;
- `docs/SETTINGS.md` — settings and synchronized minimum-SOC contract;
- `docs/PV_INSIGHT.md` — internal/external display-only PV source aggregation.

## v0.45 highlights

- A dedicated **PV** settings page can combine canonical internal GoodWe PV with up to four external Home Assistant power entities for dashboard insight.
- The new `pv_generation_power` sensor and PV-card breakdown update from both coordinator telemetry and external entity changes, with supported power-unit normalization and invalid-source filtering.
- The combined PV value is display-only: Automatic Control, EMS, EMHASS, plans and grid accounting continue using their established canonical inputs.
- Battery Strategy SOC sliders keep the user's selected value and percentage during Chrome focus loss and telemetry, until Home Assistant confirms the saved value.
- Battery · Plan · Price now overlays actual GoodWe SOC with validated single-battery EMHASS `SOC_opt` forecast on a separate 0–100% axis.
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
- All EnergyPilot animations, transitions, flow particles and modal backdrop filters are intentionally disabled for deterministic desktop, iPad and iPhone behavior.
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
- four EnergyPilot Battery Saver profiles with price-relative SOC/power preferences, profile-owned maximum SOC and anti-churn battery-throughput costs;
- stateful EMHASS profit/cost/self-consumption strategy;
- persistent optimization history and `last_success`;
- opt-in bounded LOG-tab debug sessions and copyable support reports;
- persistent Today/Yesterday grid import/export accounting;
- optional Nord Pool/runtime prices;
- Battery plan / actual / price visualization;
- EV anti-discharge protection;
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
continual_publish = true
method_ts_round = first
set_use_battery = true
```

Those values are required for the EnergyPilot orchestration/publication path. Installation topology is different and remains owned by EMHASS/the operator:

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
P_grid > +deadband -> mode 9 Grid import target (buy/import)
else P_batt > +deadband -> mode 12 Battery discharge power (sell/discharge)
else P_batt near 0 W -> mode 8 Battery Hold
otherwise -> mode 1 GoodWe Auto / self-use
```

Hybrid is deliberately asymmetric. Buying is controlled at the PCC through mode 9 and the EMHASS `P_grid` magnitude. Selling is controlled through direct battery discharge mode 12 and the EMHASS `P_batt` magnitude.

A Hybrid charging plan with no planned grid import normally falls back to GoodWe self-use. That lets locally available PV flow to the battery according to the inverter's own fast control instead of forcing the battery to the forecast-sized EMHASS charging value. A neutral EMHASS battery plan remains neutral through mode 8.

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

There is no startup/background SOC synchronization.

The old direct **Battery minimum SOC limits** dashboard panel is not exposed as a normal settings path. The low-level Beta SOC API remains available for diagnostics/backwards-compatible tooling. Maximum SOC remains an EMHASS hard limit; when a Battery Saver profile is managed, EnergyPilot owns that EMHASS maximum as part of the selected profile.

## Battery Saver

Battery Saver is an opt-in EnergyPilot policy layer over EMHASS. It never writes a GoodWe mode directly. The public profiles are **Mad-Steve**, **Gold Rush**, **Balanced** and **Battery Saver**.

Managed profiles use a common price-relative charge/discharge anti-churn cost and profile-specific hard maximum SOC/power-stress behavior. Current hard maxima are **100% / 96% / 95% / 90%** for Mad-Steve / Gold Rush / Balanced / Battery Saver respectively. Minimum SOC remains the GoodWe-synchronized hard floor.

The common anti-churn factor is **2.25% × price reference per direction**. At the field-test price reference around `0.31`, that is approximately `0.007` per charged or discharged kWh.

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
- the card supports S/M/L layouts and an expanded detail view;
- native GoodWe day counters `35208` / `35211` are preferred for the headline charged/discharged totals;
- Recorder-integrated battery power remains a separate visualization comparison and is not calibrated to force a match with the native inverter counter;
- if no usable plan exists, planned-energy summaries display `—` rather than a fabricated zero.

Future persistent financial accounting must consume backend grid-accounting deltas and effective prices, not reconstruct totals from chart pixels/buckets.

## Persistent state

Configuration remains in Home Assistant `ConfigEntry.data/options`, EMHASS config or GoodWe registers depending on ownership.

EnergyPilot-owned persistent runtime stores are separate:

```text
gw_energypilot.runtime.<entry_id>
gw_energypilot.accounting.<entry_id>
gw_energypilot.optimization_log.<entry_id>
gw_energypilot.plan.<entry_id>
```

The plan Store is a bounded resilience mirror of EMHASS's canonical plan, not a second optimizer or settings database. It is valid only through its inferred final plan interval. The debug session is intentionally **not** persistent and is not added to this list.

## Debug logging

Open dashboard settings → **LOG** and select **Start debug logging** only when reproducing a problem. Stop capture after reproduction, then use **Copy debug report** for support.

The debug buffer is bounded and memory-only. It observes the current EnergyPilot runtime rather than polling or controlling hardware independently. See `docs/DEBUG_LOG.md` for captured fields, privacy boundaries and lifecycle details.

## Safety boundary

Do not guess GoodWe register addresses, sizes, scales or signs.

`registers.py` is canonical for telemetry/register definitions. Changes to EMS mode semantics, registers `47511/47512`, sign conventions or write ordering require explicit hardware evidence.

Beta register candidates remain bounded and reversible where practical.
