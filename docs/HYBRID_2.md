# Hybrid 2.0 Beta

Hybrid 2.0 Beta is an opt-in automatic strategy added in v1.3.0-beta.6 and
corrected in v1.3.0-beta.7. Select **Settings → GoodWe → Automatic control strategy → Hybrid
2.0 Beta**. Existing Battery, Grid and Hybrid selections keep their behavior.
The stored strategy key is `hybrid_2`; no existing config value is migrated.

## Charging rule

EMHASS selects the charging window through `P_batt`. A battery charge plan
below the Battery Hold deadband requests **mode 2, Charge PV**, at the
configured **Maximum control power**, capped at 15,000 W. `P_grid` is not a
second charging gate and is not used as the total house-import target. This is
required when EV consumption is absent from the EMHASS load forecast: the
planned grid value can remain around zero while the actual house imports for
the EV.

| Valid plan | GoodWe request |
|---|---|
| `P_batt < -battery_deadband`, any/missing `P_grid` | **2**, configured maximum control power |
| Battery inside its deadband | **8**, 0 W |
| Other non-neutral battery plan, grid inside its deadband | **1**, 0 W |
| Other non-neutral battery plan, positive grid target | **9**, bounded `abs(P_grid)` |
| Other non-neutral battery plan, negative grid target | **10**, bounded `abs(P_grid)` |

Exact deadband boundaries remain neutral. `P_batt` must be finite and the
optimizer ready. Outside a Hybrid 2.0 charge window, missing required `P_grid`
still waits without a new EMS write; an unexpired persistent plan can bridge
missing publication through the existing live-first source order. Explicit
non-ready optimizer status remains authoritative.

Mode 2 interprets register `47512` as an **upper grid-assistance allowance**
with PV priority, rather than a direct battery-power target or a PCC import
target. For example, 15 kW AC assistance plus 2 kW DC PV can contribute to
battery charging together, subject to conversion losses and the inverter's
actual operating limits. It is not a guarantee of either 15 kW import or
zero PV curtailment. Mode 4 instead prioritizes grid import; mode 11 targets
total battery charge power. See [EMS modes](EMS_MODES.md).

This strategy deliberately uses EMHASS charge timing rather than its planned
charge amplitude. Actual energy and SOC can exceed the forecast and its
planned maximum SOC before the next plan step or optimization. The EMHASS
maximum is an optimizer constraint, not a new hardware cutoff in this mode.
The inverter/BMS remains responsible for its configured limits. EnergyPilot
does not raise them or infer a per-phase connection limit from total power.
Choose existing Hybrid or Battery when following planned amplitudes is required.

## EV and ownership

EV start does not change a mode-2 charging command. EV active with a neutral
or discharge battery plan selects mode 8 Hold. For other explicit charge
plans the normal Hybrid mapping remains in effect, including PV export.
The guard uses planned battery direction; PCC/Auto modes do not guarantee
instantaneous battery direction under a different actual site balance.
EV-stop fresh-plan protection remains unchanged.

This choice does not enable, disable or reconfigure the separately opt-in EV
load balancer. It does not write charger current, add an EMS feedback timer,
or trim the setpoint against site telemetry. GoodWe performs its own local
regulation. Manual modes remain exact; Automatic Control OFF returns mode 1
at 0 W. Register definitions and `47512 → brief wait → 47511` writes are unchanged.

## Evidence and limits

The GoodWe **ARM 745 Modbus protocol**, V1.2 dated 2024-02-02, table 8-16
(pp. 164–165), describes mode 2 as grid assistance with PV priority. The
[GoodWe protocol document](https://devicelib.my-gekko.com/download_docu.php?ext=pdf&fname=GoodWe_ARM_745_Modbus_protocol_Map_ET50._ET30__ESG2_V1.2_20240202_1_.pdf&id_pk=753)
covers ET50/ET30/ESG2; that alone does not verify every ETA firmware.
The [maintained GoodWe integration](https://github.com/mletenay/home-assistant-goodwe-inverter#ems-modes)
also distinguishes the mode-2 allowance from modes 4, 9 and 11.

User-supplied GW15K-ETA-G20 dashboard observations on 2026-09-06 support the
choice of mode 2. Both snapshots used manual mode 2 and 15,000 W:

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

## Implementation

`control_decision.py` owns the single mapping used by live control and projected
execution rows. The active `controller_v033` EV path uses the same decision.
`smart_meter_api.py` persists the extra selection in existing config-entry data;
the legacy smart-meter flag stays synchronized. The existing control-command
sensor publishes `control_strategy` so the permanent Lit surface can display
the correct explanation without rebuilding its controls. Entity unique IDs,
device identity, history stores, EMHASS configuration and schedule ownership
remain unchanged.
