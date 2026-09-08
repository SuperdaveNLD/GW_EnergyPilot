# Hybrid 2.0 Beta — grid-first test mapping

This is the **v1.3.0-beta.10 opt-in test mapping**, based on beta.9's
grid-first model with the owner's 2026-09-08 change from charging mode 11 to
mode 2. Published beta.9 still used mode 11; beta.8 used a different mode-9
EV reference. Their release notes remain historical. Select **Settings → GoodWe → Automatic
control strategy → Hybrid 2.0 Beta** after installing this change. The stored
key remains `hybrid_2`. Battery, Grid and original Hybrid behavior is unchanged.

## Decision order

Manual ownership, explicit Pause and the existing readiness/EV-stop gates keep
priority. A numeric `P_batt = 0` is not an explicit Pause. Valid plan inputs use
EMHASS signs: battery negative = charging; grid positive = import.

| Valid plan | Without EV | EV charging |
|---|---|---|
| Grid inside its deadband, including exact boundaries and any battery sign/zero | **1**, 0 W | **5**, bounded actual load minus EV |
| Grid outside deadband, battery below its negative deadband | **2**, bounded `abs(P_batt)` grid assistance | **2**, same allowance |
| Grid outside deadband, battery above its positive deadband | **3**, bounded `P_batt` | **8**, 0 W |
| Grid outside deadband, battery inside its deadband | **9** import / **10** export, bounded `abs(P_grid)` | **8**, unresolved net-only EV case |
| Explicit manual Pause | **8**, 0 W | **8**, 0 W |

Exact battery boundaries are neutral too. Deadbands choose the branch and are
never subtracted from its watts. Directed commands are capped by Maximum
control power and 15,000 W. A zero dispatch limit uses Hold for directed
battery commands; mode 3 / 0 W is not substituted for an explicit Pause.

Examples: load 1,000 W minus PV 500 W minus battery 500 W gives grid 0 W → Auto.
A plan of battery 300 W and grid 400 W gives Auto with a 1,000 W grid deadband,
but mode 3 at **300 W**, not 400 W, with a 300 W grid deadband. Battery 0 W and
grid 700 W also gives Auto with the default 1,000 W band.

Outside the grid band, planned charging uses mode 2 with the existing
bounded `abs(P_batt)` watt calculation, even alongside planned export.
The setpoint is now a PV-priority grid-assistance allowance, not a fixed
battery-power target. Available GoodWe-visible PV can contribute on top;
actual battery charging and SOC may therefore exceed the EMHASS forecast.
Do not add measured PV to the setpoint or substitute maximum control power
for the planned magnitude. Inverter/BMS limits remain authoritative, and
synchronized automatic mode-2/PV/EV validation remains required. Mode 2 can
buy grid energy when actual PV falls; no extra tariff gate is inferred.
A net-only mode 9/10 target can
move the battery in either direction; it does not enforce neutral battery
power. The unresolved EV variant therefore uses protective Hold, not a mode-9
EV import reference. This fallback is labelled house-control Hold, not an
explicit pause in the optimizer plan.

## EV house reference and ownership

The new test reference is:

```text
house_reference = max(0, fresh local GoodWe load 35172 - fresh measured EV watts)
mode 5 setpoint = min(house_reference, Maximum control power, 15000 W)
```

Mode 5 targets inverter AC output. Internal PV and battery are not added to or
subtracted from this AC target. External AC PV is **not subtracted again**.
This assumes 35172 includes EV and already reflects external AC PV. That exact
meter boundary is still unverified. Mode 5 PV-surplus behavior is also open;
this is not a guarantee of preserved PV or battery charging from surplus PV.

For example 12.5 kW load minus 11 kW EV requests 1.5 kW inverter output. This
is not a request for 1.5 kW battery discharge: PV can contribute to the output.
An EV above 15 kW is allowed as an input; only the resulting inverter allowance
is capped. A negative calculated reference is clamped to zero, whose hardware
behavior remains part of the mode-5 test.

The existing controller updates the reference every **15 seconds**, using its
same control lock and write/readback path. Meter error is never integrated and
there is no second controller or charger write. Safety/plan branch changes
bypass the self-use update throttle. Manual ownership stops automatic work;
Automatic Control OFF still returns mode 1 / 0 W. Manual modes remain exact.

## Freshness and failure handling

- Require finite EV power with explicit W/kW/MW/mW units. Use `last_reported`,
  with `last_updated` only as compatibility fallback. Age must be 0–30 seconds;
  future, naive or missing timestamps are rejected. Active self-use requires
  EV power above zero.
- Require finite local Modbus 35172 from a successful complete telemetry read
  no older than 30 seconds. Full Modbus reads now timestamp `source_updated_at`.
  Failed/stale reads, cloud values and control-only readback cannot substitute
  for fresh local load. The EMHASS load forecast is never used as actual load.
- Missing self-use measurements select mode 8. Missing/non-ready/suspended
  plans during EV charging select mode 8 too. Without EV, missing plan inputs
  retain the existing wait behavior. A valid persistent plan may bridge
  missing publication; explicit non-ready optimizer status still wins.
- Unavailable EV activity after an active session preserves the guard.
  Confirmed EV stop retains the native fresh-optimization/retry gate and Hold.
- EMHASS topology, SOC profiles, power limits and schedule are not rewritten.
  Inverter/BMS limits remain authoritative; this test does not create a
  certified phase-current limit or eliminate inter-sample EV transients.

## Measured hardware evidence

Owner-provided GW15K-ETA-G20 dashboard snapshots, 2026-09-06; firmware unknown.
Positive battery watts below mean discharge; import/export is explicit.
EV was 0 W in all these evening snapshots. Separate inverter-AC readback was
not included. These are point observations, not synchronized time series.

| About | Mode / setpoint | DC PV | External AC PV | Battery | Meter | 35172 | SOC |
|---|---|---:|---:|---:|---|---:|---:|
| 19:46 | 3 / 15,000 W | 162 W | 64 W | 15,000 W | export 14,200 W | 820 W | 60% |
| 19:48 | 3 / 1,000 W | 164 W | 64 W | 1,430 W* | export 199 W | 729 W | 59% |
| 19:48 | 5 / 1,000 W | 172 W | 64 W | 1,080 W | export 244 W | 761 W | 59% |
| 19:49 | 10 / 1,000 W | 165 W | 64 W | 1,630 W | export 998 W | 767 W | 59% |
| 19:52 | 3 / 5,000 W | 157 W | 61 W | 5,030 W | export 4,190 W | 772 W | 57% |
| 19:54 | 3 / 0 W | 149 W | 61 W | 285 W | import 644 W | 793 W | 57% |
| 19:56 | 8 / 0 W | 140 W | 57 W | 88 W | import 831 W | 840 W | 57% |
| 19:57 | 8 / 0 W | 131 W | 55 W | 16 W | import 853 W | 847 W | 57% |

* At mode 3 / 1,000 W, 758 V × 1.30 A ≈ 985 W disagreed with the 1,430 W
power card; a mode switch followed after 25 seconds. At 5,000 W, 758 V × 6.60 A
≈ 5,003 W corroborated the 5,030 W card. Several earlier diagnostic sections
stayed at 14.2 kW export / 64% SOC while live cards changed. Mode 8 settled
from 88 W to 16 W with 0.00 A displayed, supporting practical Pause under
these conditions; it does not establish a universal meter offset.

Mode 5's 761 W + 244 W ≈ 1,005 W supports an inverter-output target, whereas
mode 10 reached 998 W net export. At this low PV neither PV-first operation
near the AC limit nor surplus charging is proven. The owner reports PV stops
in mode 12; it is excluded from this Hybrid 2.0 mapping. See [Modbus evidence](MODBUS.md).

Remaining tests: mode 3 near the AC limit with high PV; mode 5 with surplus PV
and battery charge headroom; 35172 with EV and external PV independently and
together; then EV start/stop and house-load changes with this test strategy.

## Read-only inspection and offline replay

The existing control-command sensor adds `mapping_preview`: proposed mode,
watts, branch reason, input availability, current command comparison and
`validation_required`. Its `preview_only: true` describes this diagnostic
calculation; it does not mean a selected Hybrid 2.0 controller is disabled.
An unresolved EV net-only case shows no candidate, while live control holds.
No new entity IDs, statistics, Store keys or versions are introduced.

The offline script uses the same pure model and never connects to HA/GoodWe:

```sh
python3 scripts/preview_ems_mapping.py --p-batt 300 --p-grid 400 --grid-deadband 300
python3 scripts/preview_ems_mapping.py --p-batt 700 --p-grid 0 --ev-active --load-power 12500 --ev-power 11000
python3 scripts/preview_ems_mapping.py --plan /path/to/emhass-results.txt
```

CSV, TSV and pasted EMHASS result tables retain **every row**. An EV scenario
for an entire plan is explicitly hypothetical. Forecast `P_Load` is never
silently used as measured load. `preview_hybrid_mapping` in `control_decision.py`
is shared by preview and the opt-in resolver; the preview itself cannot write.
Execution history adds the fresh local load alongside the measured EV input.

## Earlier charging evidence and documentation

The GoodWe **ARM 745 Modbus protocol**, V1.2 dated 2024-02-02, table 8-16
(pp. 164–165), describes mode 2 as grid assistance with PV priority. The
[GoodWe protocol document](https://devicelib.my-gekko.com/download_docu.php?ext=pdf&fname=GoodWe_ARM_745_Modbus_protocol_Map_ET50._ET30__ESG2_V1.2_20240202_1_.pdf&id_pk=753)
covers ET50/ET30/ESG2; that alone does not verify every ETA firmware.
The [maintained GoodWe integration](https://github.com/mletenay/home-assistant-goodwe-inverter#ems-modes)
also distinguishes the mode-2 allowance from modes 4, 9 and 11.

Earlier GW15K-ETA-G20 observations on 2026-09-06 informed beta.6's mode-2
experiment. Both snapshots used manual mode 2 and 15,000 W:

| Observation | EV | Inverter AC import | Internal DC PV | Battery evidence |
|---|---:|---:|---:|---|
| About 14:05 | 11.0 kW | 6.38 kW | 2.80 kW | 8.96 kW charging; 785 V × 11.4 A ≈ 8.95 kW |
| About 14:07, EV stopped | 0 W | 15.0 kW | 2.97 kW | 816 V × 21.5 A ≈ 17.54 kW; dashboard power disagreed at 14.6 kW |

The earlier snapshot included a transitional mode-4 history row; both showed
unavailable diagnostics and some inconsistent/asynchronous load or battery
readings. The first also showed about 25.4–25.5 A per phase. These observations
support AC assistance plus PV and local adaptation to EV load, but do not
prove a strict 25 A cap, synchronized energy balance, or uncurtailed PV.
Firmware identity and synchronized readback of the new automatic strategy
remain field-validation work; unit/browser tests cannot supply that evidence.

Further user snapshots at about 16:15 used manual modes 2, 4, 9 and 11, each
at 15,000 W, with EV load 11.1 kW and battery SOC 95%:

| Mode readback | House grid import card | Internal PV | Battery charging |
|---|---:|---:|---:|
| 2 | 12.9 kW | 4 W | 2.96 kW |
| 4 | 13.8 kW | 2.45 kW | 2.92 kW |
| 9 | 14.5 kW | 2 W | 2.93 kW |
| 11 | 12.8 kW | 4 W | 2.94 kW |

These are short sequential snapshots, not settled measurements under identical
conditions. Diagnostics remained at 14 W grid and an older battery/grid plan
while the main cards changed. The samples record accepted manual modes and
similar battery charging at high SOC; they cannot attribute PV curtailment or
the charging limit to a particular mode. Manual ownership also means they do
not validate automatic Hybrid 2.0 or its EV override.
