# Hybrid 2.0 Beta

Hybrid 2.0 Beta is an opt-in automatic strategy added in v1.3.0-beta.6 and
corrected in the v1.3.0-beta.8 candidate. Select **Settings → GoodWe → Automatic control strategy → Hybrid
2.0 Beta**. Existing Battery, Grid and Hybrid selections keep their behavior.
The stored strategy key is `hybrid_2`; no existing config value is migrated.

## Plan and EV rules

EMHASS owns the grid-charging window and its battery-power target. Charging
below the Battery Hold deadband with import above the GoodWe Auto deadband
requests **mode 11 at `abs(P_batt)`**, capped by Maximum control power and
15,000 W. Mode 2 remains available manually: its grid-assistance allowance
can add to DC PV and therefore does not mean the same battery watts.

During EV charging, self-use remains available for the ordinary house.
EnergyPilot asks for **mode 9 with net import equal to measured EV power**.
GoodWe balances the remaining house and PV locally. Positive `P_batt` with a
neutral grid plan is self-use, not explicit scheduled battery export. PV-only
charging, including charging alongside planned PV export, uses this same EV
reference. This is a user-selected change from the blanket anti-discharge rule.

| Valid plan | Without EV | EV charging |
|---|---|---|
| `P_batt < -battery_deadband` and `P_grid > grid_deadband` | **11**, bounded `abs(P_batt)` | **11**, same target |
| Battery inside its deadband | **8**, 0 W | **8**, 0 W |
| Non-neutral battery plan, grid inside its deadband (either battery sign) | **1**, 0 W | **9**, measured EV power |
| Battery charging, negative grid target | **10**, bounded `abs(P_grid)` | **9**, measured EV power |
| Discharge plan, positive grid target | **9**, bounded `abs(P_grid)` | **8**, 0 W |
| Discharge plan, negative grid target | **10**, bounded `abs(P_grid)` | **8**, 0 W |

Exact deadband boundaries remain neutral. Example, neglecting losses: total
load 11.6 kW minus EV 11 kW leaves 0.6 kW ordinary house load. Mode 9 at 11 kW
allows about 0.2 kW battery discharge with 0.4 kW PV, or about 1.4 kW battery
charging with 2 kW PV. House/PV readings are not added to the EV reference;
this avoids double counting external AC PV and the EV.

Self-use follows actual site balance, so it can differ from planned battery
power and SOC. Net charging follows the planned battery watts instead of
unconditionally requesting the maximum. BMS/inverter limits remain
authoritative. Neither exact transient isolation of EV demand nor absence of
PV curtailment at hardware/SOC limits is guaranteed. EMHASS's maximum SOC is
an optimizer constraint, not a new hardware cutoff. See [EMS modes](EMS_MODES.md).

## Measurement, cadence and failure handling

- The existing controller rechecks the EV reference every **15 seconds**. EV
  power events may trigger evaluation, but successive self-use commands are
  limited to that cadence. Pause, explicit discharge, net-charge changes,
  invalid inputs and confirmed EV stop bypass that throttle.
- Use the configured measured EV power sensor, even with charging-status
  detection. Allocated charger current and the EMHASS load forecast are not
  substitutes. The measurement requires explicit W/kW/MW/mW units, finite
  non-negative power and an aware report timestamp no older than **30 seconds**.
  `last_reported` is primary, `last_updated` is the compatibility fallback.
  Future timestamps are rejected.
- A missing, stale, zero or invalid EV reference in a self-use branch selects
  mode 8 Hold. A reference above Maximum control power or 15,000 W is held,
  never silently clamped, since too little PCC import could feed the EV.
- An unavailable selected activity source during an active session is not a
  confirmed stop. Preserve the guard until valid stop evidence arrives.
- During EV charging, missing required plan inputs, non-ready optimization or
  a suspended native plan publication select Hold. A still-valid persistent
  plan may supply missing live publication; explicit non-ready status wins.
  Without EV, missing plan inputs retain the existing waiting behavior.
- A confirmed EV stop with native orchestration immediately requests Hold and
  retains the existing fresh-optimization/retry gate. The periodic callback
  cannot resume a stale plan. Manual ownership and unload stop periodic work.

## EV and ownership

This choice does not enable, disable or reconfigure the separately opt-in EV
load balancer or write charger current. The 15-second callback belongs to the
existing controller and uses its same control lock and write/readback path;
there is no second EMS controller or error-integrating power loop. GoodWe
performs local regulation. Manual modes remain exact; Automatic Control OFF returns mode 1
at 0 W. Register definitions and `47512 → brief wait → 47511` writes are unchanged.

The controller banner distinguishes house self-consumption, explicit battery
charging, planned-discharge Hold and invalid-input Hold. Execution history
records the fresh EV reference. House self-consumption is not drawn as a
guaranteed charging or discharge-blocked interval; it allows both directions.

## Evidence and limits

The user's beta.6 EV-active snapshot at about 15:37 had `P_batt = -1.33 kW`,
`P_grid = -29 W`, mode 1 and about 7.94 kW actual battery discharge. The
corrected result for that plan is mode 1 without EV and mode 9 at measured EV
power during EV charging.
The later planned charging window (`P_batt = -4.3 kW`, `P_grid = +3.6 kW`)
selects mode 11 at 4.3 kW with or without EV. This distinguishes an omitted EV load from
EMHASS permission to buy battery energy.

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

## Implementation

`control_decision.py` owns the single mapping used by live control and projected
execution rows. The active `controller_v033` EV path uses the same decision.
`smart_meter_api.py` persists the extra selection in existing config-entry data;
the legacy smart-meter flag stays synchronized. The existing control-command
sensor publishes `control_strategy` so the permanent Lit surface can display
the correct explanation without rebuilding its controls. Entity unique IDs,
device identity, history stores, EMHASS configuration and schedule ownership
remain unchanged.
