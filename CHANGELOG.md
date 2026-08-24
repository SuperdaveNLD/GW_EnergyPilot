# Changelog

All notable changes to GW EnergyPilot are documented here.

## [0.27] - 2026-08-24

### Added

- Added **S / M / L** sizing for the Battery & Price dashboard card using an Apple-style segmented control stored in the existing browser-local dashboard preferences.
- Added historical active-plan visualization from the configured EnergyPilot `P_batt` entity history, showing the target that was actually published at each point in the day.
- Added future battery-plan visualization from the current EMHASS battery forecast `forecasts` attribute.
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
- The active frontend is `gw-energy-pilot-v027-battery-plan.js`, which layers the v0.26 support cleanup underneath the v0.27 plan-versus-actual chart.

### Safety / compatibility

- No new or guessed GoodWe register definition or Modbus read block is introduced.
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
- EMS registers remain `47511`/`47512`; write order remains `47512 -> wait -> 47511`.
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
- Expected visual directions are PV → hub, Grid import → hub, hub → Grid export, hub → Battery charge, Battery discharge → hub, and hub → House load.

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
- The EMHASS setting label is clarified as **EnergyPilot runtime final SOC target** and explicitly notes that externally orchestrated/manual-only EMHASS may use a different runtime target.
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
- Admin-only WebSocket settings commands for reading and updating the existing configuration.
- GoodWe connection validation before host, Modbus TCP port or unit-ID changes are saved.
- Multi-entry selection for installations with more than one GW EnergyPilot config entry.
- Enabled-by-default Home Assistant Diagnostic sensors for the Beta SOC candidates `45356`, `45358` and `47500`.
- A device-registry migration from the legacy mutable `host:slave` identifier to the stable config-entry ID.
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
- Every candidate remains optional and read-only; unsupported firmware cannot make normal required telemetry unavailable.
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
