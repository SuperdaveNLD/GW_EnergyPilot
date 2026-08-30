# GW EnergyPilot v0.51 Beta

> Development feature-layer notes. This candidate was promoted into the first
> public stable v1 release; see `docs/releases/v1.0.0.md`.

v0.51 adds an auditable EMHASS-to-GoodWe execution history and extends the
Battery · Plan · Price chart with estimated solar/grid flow attribution. It is
the release implementation of issue #108.

## EMHASS → GoodWe history

The dashboard has one new full-width **EMHASS → GOODWE** card. Its compact
view shows the nearest recorded and projected decisions around a ±6-hour
window. **Full 48h + 24h table** opens the complete view:

- 48 hours of immutable controller evidence, when already retained;
- 24 hours of conditional plan projection;
- the EMHASS `P_batt`, `P_grid` and wanted SOC values available to the
  decision;
- the Battery, Grid or Hybrid strategy and configured deadband;
- the expected GoodWe mode/setpoint;
- actual SOC, battery/PV/load/grid power and GoodWe mode/setpoint read-back;
- explicit write, verification, mismatch, unavailable and waiting states.

The projection runs saved plan rows through the same pure strategy mapping as
Automatic Control. It assumes that strategy, deadband, maximum power and
current control ownership do not change. It deliberately does not predict an EV
override, ownership transition, manual command, failed write or GoodWe read-back.

## Source-of-truth and persistence

EMHASS remains the canonical plan owner. The existing validated plan mirror
remains the current/future resilience source. v0.51 adds a separate per-entry
Home Assistant Store:

```text
gw_energypilot.execution.<config_entry_id>
```

The execution Store is the source of truth for what EnergyPilot decided and
what it could verify at that instant. Each record snapshots the plan source,
strategy/config values, live actuals, expected command, write result and
post-refresh read-back. A later optimization or configuration change never
rewrites an older record.

Records are UTC timestamped, ordered with a sequence and retained for seven
days with a hard limit of 4096 events. The table requests only the latest 48
hours. Existing installations require no migration: the new Store starts
empty and fills from the first controller decision after upgrade. Store
failure is diagnostic only and can never block or alter an EMS command.

The history contains no configured entity IDs, EMHASS URL, token or arbitrary
Home Assistant state attributes. It does contain local operating evidence
such as power, SOC, strategy and mode, so an exported Home Assistant backup
or support bundle should still be treated as private installation data.

## Verified command evidence

v0.51 distinguishes these outcomes:

- **already applied** — the current GoodWe mode/setpoint already matched, so
  no Modbus write was needed and the live read-back verified it;
- **completed + verified** — the established setpoint-then-mode transaction
  completed, the coordinator refreshed and both values matched;
- **completed + mismatch/unavailable** — the transaction completed but the
  refreshed read-back differed or could not be proven;
- **write failed** — the transaction raised an error; only its exception type
  is stored;
- **waiting** — a required finite plan/status value was unavailable and no
  write was attempted.

This supplements rather than changes the existing “last successful EMS
setpoint update” evidence. GoodWe registers `47512` and `47511`, their write
order and all controller safety gates remain unchanged.

## Solar/grid source estimates

The chart now requests Recorder 5-minute mean statistics for the existing
battery, combined PV, house-load and fast grid-power entities in one bounded
request. In **Large** and expanded chart views, actual flow is split into:

- green — estimated grid → battery;
- ochre — estimated solar → battery;
- orange — estimated battery → grid;
- yellow/ochre — estimated solar → grid;
- hatched grey — residual that cannot be assigned safely.

The normal and compact chart retain the familiar actual battery
charge/discharge bars. Attribution is a load-first instantaneous estimate,
not a financial or revenue-grade energy allocation. Missing or inconsistent
samples remain explicitly unknown. It does not alter persistent grid
accounting, EMHASS inputs or Automatic Control.

## Wanted SOC history

The dashed **Wanted SOC** line remains visible. For elapsed time it now uses
the wanted `SOC_opt` snapshot stored with each historical controller decision;
for current/future time it uses the latest validated official plan. A later
optimization therefore no longer redraws yesterday's wanted SOC. Before the
new Store has history, the previous current-plan fallback remains available.

## Timezone and DST

Persistence and API boundaries use timezone-aware UTC instants. The browser
renders them in Home Assistant's configured timezone. The full table includes
the timezone abbreviation so both occurrences of a repeated fall-back hour
remain distinguishable; a spring-forward gap is not fabricated. The 48-hour
and 24-hour windows are elapsed-time windows, not a fixed number of local
calendar rows.

## Compatibility and validation

The plan Store version remains unchanged because optional official-plan
`P_PV` and `P_Load` points are additive and dashboard-only. Older snapshots
without those arrays continue to restore. No entity or device identity,
register definition, accounting source, Battery Saver ownership or EMHASS
runtime policy changes.

The v1.0.0 dashboard loads `gw-energy-pilot-v051.js` as its feature layer over
the complete v0.50 chain. Every inner feature import uses the fresh `0.51-h1`
cache boundary. The release
is covered by unit tests and the desktop Chromium, iPad WebKit and iPhone
WebKit stable-DOM/touch matrix.
