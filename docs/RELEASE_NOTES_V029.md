# GW EnergyPilot v0.29 Beta release notes

Release date: 2026-08-24

v0.29 is the follow-up release to v0.28. A new version number is used deliberately because v0.28 had already reached `main`; publishing the remaining work under the same manifest version could prevent existing v0.28 installations from receiving a clear HACS update.

## EMHASS configuration tools

The EMHASS settings page now adds two explicit administrator actions:

- **Restore recommended defaults** fills the GW EnergyPilot EMHASS form with the current recommended settings for review. It does not save automatically.
- **Synchronize required config** reads the complete live EMHASS configuration, changes only the mappings EnergyPilot requires, writes the complete merged configuration and then reads it back for verification.

Canonical EnergyPilot outputs are:

- `sensor.p_batt_forecast`
- `sensor.p_grid_forecast`
- `sensor.optim_status`
- required optimization state `Optimal`

The synchronization resolves the actual Home Assistant entity IDs for PV total power, GoodWe load power, battery power and battery SOC from the entity registry. Renamed entity IDs are therefore respected instead of relying on hard-coded guesses.

Unrelated EMHASS configuration is preserved. Existing custom PV forecast mappings and custom `var_model` values are preserved where safe. Multi-battery power/SOC lists are not rewritten because EnergyPilot cannot safely infer ownership for each battery.

Synchronization is administrator-triggered only, does not write GoodWe registers and does not automatically start an optimization. After changing EMHASS configuration, run a fresh optimization before enabling Automatic Control.

See `docs/EMHASS_CONFIG_SYNC.md` for the detailed ownership and safety contract.

## Flow animation regression guard

v0.29 adds a final frontend guard for the live energy-flow particles. The geometry-specific Forward/Reverse keyframes remain authoritative and later frontend layers are forced to use `animation-direction: normal`.

This prevents the previously observed double-reversal regression without changing any power sign, sensor value, GoodWe register or controller decision.

Expected visual directions remain:

- PV production: PV -> hub
- Grid import: Grid -> hub
- Grid export: hub -> Grid
- House consumption: hub -> House
- Battery charging: hub -> Battery
- Battery discharging: Battery -> hub

## v0.28 functionality carried forward

v0.29 includes the complete v0.28 release base, including:

- Hybrid Automatic Control using GoodWe mode 9 for planned import and mode 12 for planned battery discharge;
- mode 8 Battery Hold for a neutral Hybrid battery plan;
- Battery · Plan · Price chart repairs and current EMHASS `battery_scheduled_power` support;
- native GoodWe battery day counters for headline charged/discharged energy;
- Max Charge software stop at the configured EMHASS maximum battery SOC;
- Apple/macOS-style controls on the Battery/Plan card and detail window.

## Issue #22 closed

The proposed separate residual-grid-capacity allocator is not added. Field understanding is that the dynamic grid/import limit is already enforced by GoodWe itself. EnergyPilot therefore avoids implementing a second competing limiter.

## Known open investigation: issue #30

Negative raw EMHASS SOC-related values reported in issue #30 are still treated as raw/invalid diagnostics until their exact EMHASS semantics and source are established. v0.29 does not guess a percentage conversion or silently rewrite optimizer constraints.

The new restore/synchronization tools provide a controlled way to repair the EnergyPilot-required mappings, but they do not reinterpret unknown SOC semantics.

## Safety and compatibility

- No new or guessed GoodWe Modbus registers.
- No Modbus read-block changes.
- EMS control remains on registers `47511/47512` with the existing `47512 -> wait -> 47511` write order.
- Existing entity IDs and unique IDs are preserved.
- Battery control remains `P_batt -> 11/12/8`.
- Grid control remains `P_grid -> 9/10/1`.
- EV anti-discharge remains a higher-priority safety override.
- Manual EMS test-pad commands remain direct operator commands.
- EMHASS remains an external prerequisite and is not installed by GW EnergyPilot.

## Upgrade notes

After installing v0.29 through HACS:

1. Restart Home Assistant so the updated Python integration and panel module are loaded.
2. Open **GW EnergyPilot -> Settings -> EMHASS**.
3. Review **Restore recommended defaults** if the current EnergyPilot settings are uncertain.
4. Use **Synchronize required config** only when you want EnergyPilot to align its required EMHASS mappings.
5. Run a fresh optimization after EMHASS synchronization before enabling Automatic Control.

v0.29 remains **Beta** while the new EMHASS synchronization workflow and the final flow-animation guard receive live installation validation.
