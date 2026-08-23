# Changelog

All notable changes to GW EnergyPilot are documented here.

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
- Modes `1`, `6`, `7` and `8` continue to force a `0 W` setpoint. Mode `7` adds a dedicated confirmation before forced off-grid operation.
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