# GW EnergyPilot v0.35 Beta

v0.35 corrects EMHASS configuration ownership: GW EnergyPilot no longer forces `inverter_is_hybrid = true` during configuration synchronization or immediately before an EnergyPilot-owned optimization.

## Why this changes

EMHASS uses `inverter_is_hybrid` to describe the installation/model topology used by the optimizer. That is structurally different from EnergyPilot's small runtime publication contract. Although the primary GoodWe reference inverter is physically hybrid, the active EMHASS model can intentionally represent a different topology, for example when external/AC-coupled production is part of the installation.

v0.34 had two independent write paths that could overwrite that user choice:

- **Synchronize required config**;
- the automatic pre-solve policy executed before `/action/dayahead-optim`.

Both paths are corrected in v0.35.

## Canonical runtime contract

EnergyPilot now has one shared runtime-contract helper used by both configuration sync and the pre-solve path. It owns only:

```text
continual_publish = true
method_ts_round = first
set_use_battery = true
```

The following remain installation-specific EMHASS settings and are preserved exactly rather than synthesized or forced:

```text
set_use_pv
inverter_is_hybrid
```

The Settings → EMHASS synchronization API also derives its managed-value list from the same canonical key definition, preventing the UI and backend ownership lists from drifting apart.

## Regression coverage

Tests cover all three inverter-topology states:

- `inverter_is_hybrid = false` remains false;
- `inverter_is_hybrid = true` remains true;
- a missing `inverter_is_hybrid` key remains missing.

Additional wiring tests verify that the automatic optimization path uses the canonical runtime helper and that the synchronization API does not re-add topology ownership.

## Compatibility and safety

- No GoodWe register definitions or Modbus read blocks change.
- No EMS mode mapping or `47512 -> wait -> 47511` write order changes.
- No Automatic Control strategy changes.
- No entity ID, unique ID, device identity or Store-key changes.
- Battery Saver v0.34 profile tuning and maximum-SOC ownership remain unchanged.
- EMHASS remains the canonical optimizer and plan owner.
- Existing EMHASS `inverter_is_hybrid` values are preserved; v0.35 does not attempt to guess the correct topology for the user.
