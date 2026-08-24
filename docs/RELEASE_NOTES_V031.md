# GW EnergyPilot v0.31 Beta

Release date: **2026-08-24**

## Main change: opt-in debug sessions in LOG

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

v0.31 also makes the macOS-style traffic-light controls visible on **all normal dashboard cards**, rather than only wiring the earlier implementation to the Battery · Plan · Price card.

- **Red** hides the card through the existing Dashboard layout visibility state. Hidden cards can be restored from the Dashboard layout menu.
- **Yellow** collapses or restores the card to a compact title/window bar.
- **Green** toggles the card between its normal grid span and full dashboard width.

Collapse/full-width state is browser-local presentation state. It does not create Home Assistant entities or modify the integration config entry. The existing Battery-only traffic-light controls are removed from the card before the v0.31 controls are attached, preventing duplicate buttons.

## Storage and safety

- Debug capture is administrator-only and **OFF by default**.
- Debug events are stored in memory only; no new persistent database or Home Assistant entity is introduced.
- The buffer keeps at most 1200 newest events and reports how many older events were dropped.
- No extra Modbus polling is performed.
- No GoodWe register definitions or read blocks change.
- No EMS write behavior changes.
- No EMHASS configuration or optimization is changed or triggered by debug logging.
- Dashboard window controls only alter browser-local presentation/visibility state.
- Existing entity IDs, unique IDs, config entries, runtime/accounting stores and the persistent optimization history are preserved.

See `docs/DEBUG_LOG.md` for the full support/debug architecture.

## Validation status

**Beta.** The debug subsystem is designed as an observer-only support feature, and the dashboard window controls reuse existing local layout state, but the new dashboard workflow and collected field data still require broader real-installation validation.
