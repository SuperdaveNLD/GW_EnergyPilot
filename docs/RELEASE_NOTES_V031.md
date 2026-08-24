# GW EnergyPilot v0.31 Beta

Release date: **2026-08-24**

## Battery Saver

v0.31 adds **Battery Saver** to **Settings → EMHASS** with four EnergyPilot-owned profiles:

- **Mad-Steve** — maximum economic freedom; zero additional battery-care penalties.
- **Gold Rush** — profit first, with light high-SOC and high-power penalties.
- **Balanced** — recommended general-purpose trade-off between economics and battery care.
- **Battery Saver** — stronger soft penalties for marginal cycling, prolonged high SOC and high power.

The profile thresholds are deliberately asymmetric for the primary LFP use case. EnergyPilot does not manufacture a high low-SOC reserve: the synchronized Minimum SOC slider remains the hard lower operating limit. High-SOC dwell and unnecessary high-power cycling receive more weight in the conservative profiles.

Battery Saver costs scale against a positive price reference derived from the active import-price forecast, rather than hard-coding one EUR value. This keeps the virtual costs proportional when EMHASS operates in another currency.

Existing installations are not silently migrated. Zero-penalty EMHASS configurations are reported as Mad-Steve-like and custom non-zero penalties are preserved until the user explicitly selects a Battery Saver mode. If the first profile application or optimization fails, EnergyPilot restores the previous mode and Battery Saver-owned EMHASS fields.

See `docs/BATTERY_SAVER.md` for the complete functional and technical contract.

## Fixed: EMHASS plan now advances at every timestep

v0.30 synchronized `continual_publish = false`. That disabled EMHASS's own per-timestep publication while EnergyPilot only published after a complete optimization. The result was a stale `P_batt` / `P_grid` target until **Optimize** was pressed again.

v0.31 makes the ownership explicit:

- EnergyPilot performs full optimizations on its configured interval and event triggers;
- EMHASS uses `continual_publish = true` to advance and republish the saved plan at every `optimization_time_step`;
- a fresh published state continues through the existing EnergyPilot Automatic Control path to GoodWe.

No second EnergyPilot 15-minute publisher is introduced.

## Minimum SOC synchronization

The existing Minimum SOC NumberEntity now treats the verified GoodWe on-grid minimum SOC as the startup source of truth instead of initializing from an arbitrary EMHASS config value.

- the slider displays the GoodWe floor when telemetry is ready;
- EnergyPilot mirrors it to EMHASS `battery_minimum_state_of_charge`;
- explicit slider changes keep the existing GoodWe-write/read-back → EMHASS-write order and GoodWe rollback on failure;
- EnergyPilot-owned optimization runs reassert the available GoodWe minimum SOC;
- runtime `soc_final` is clamped to the hard EMHASS min/max range.

Existing entity IDs and unique IDs are unchanged.

## PV is optional

EnergyPilot no longer forces `set_use_pv = true` during required EMHASS synchronization.

- If EMHASS has PV enabled, EnergyPilot resolves and synchronizes the PV mappings.
- If EMHASS has PV disabled, no PV entity is required and the customer's PV configuration is left alone.

Battery-only installations therefore remain valid while `set_use_battery = true`, `inverter_is_hybrid = true`, `method_ts_round = first` and `continual_publish = true` remain part of the EnergyPilot runtime contract.

## Opt-in debug sessions in LOG

v0.31 extends the existing dashboard **LOG** tab with a temporary high-detail debug session for support and problem analysis.

The existing persistent 50-run optimization history remains unchanged. Debug capture is a separate observer-only layer and is disabled by default.

### Debug workflow

1. Open dashboard settings → **LOG**.
2. Select **Start debug logging**.
3. Reproduce the problem.
4. Select **Stop debug logging**.
5. Select **Copy debug report**.

Stopping capture retains the completed session in memory until it is cleared, the integration is reloaded or Home Assistant restarts.

### What the report captures

- complete decoded GoodWe telemetry snapshots from the existing coordinator;
- canonical register address/type/scale metadata from `registers.py`;
- Modbus/coordinator poll health and latest update exception;
- controller strategy, command, target and GoodWe mode/setpoint read-back;
- changes to configured `P_batt`, `P_grid`, optimizer-status and optional EV source entities;
- EMHASS/orchestrator status transitions and existing HTTP/error diagnostics;
- current runtime snapshot and the existing optimization history in the copied report.

The configured GoodWe host/IP and EMHASS URL are deliberately excluded from the debug report.

## Dashboard window controls

v0.31 makes the EnergyPilot/macOS-style traffic-light controls visible on all normal dashboard cards.

- **Red** hides the card through the existing Dashboard layout visibility state. Hidden cards can be restored from the Dashboard layout menu.
- **Yellow** collapses or restores the card.
- **Green** toggles the card between normal grid span and full dashboard width.

Collapse/full-width state is browser-local presentation state. The earlier Battery-only control node is removed before the v0.31 strip is attached, preventing duplicate controls.

## Remaining backlog fixes included

### Battery · Plan · Price duplicate card (#46)

The Battery · Plan · Price installer is now idempotent. Repeated render wrappers no longer append a second graph after red-close → restore. The release layer also reconciles an already-duplicated browser session back to one canonical card on the next render.

### Four-decimal price adjustments (#45)

Import price adders and export price deductions now accept `0.0001` precision in the Home Assistant options schema and dashboard input path. Values such as the existing `0.0248` default are therefore valid without rounding to `0.024` or `0.025`.

## Safety and compatibility

- No new or guessed GoodWe register definition is added.
- No GoodWe Modbus read block is changed by Battery Saver.
- Existing EMS registers and controller write ordering remain unchanged.
- Changing Battery Saver never directly writes a GoodWe EMS mode; it rebuilds the EMHASS plan and the existing controller applies published targets.
- Debug capture is administrator-only, memory-only and **OFF by default**.
- Debug logging adds no second Modbus poller and performs no GoodWe or EMHASS control write of its own.
- Battery Saver currently supports one EMHASS battery model and refuses multi-battery ownership rather than guessing mappings.
- Non-zero power-stress profiles require EMHASS 0.18.1 or newer when the EMHASS version is known.
- Existing entity IDs, unique IDs, stable device identity, accounting/runtime stores and persistent optimization-history contracts are preserved.

See `docs/DEBUG_LOG.md`, `docs/BATTERY_SAVER.md` and `docs/EMHASS_CONFIG_SYNC.md` for the detailed architecture.

## Validation status

**Beta.** The v0.31 changes have regression coverage and preserve the established controller/Modbus architecture. The new Battery Saver tuning remains a Beta policy that should be validated across more real installations and tariff profiles before stronger lifetime or savings claims are made.
