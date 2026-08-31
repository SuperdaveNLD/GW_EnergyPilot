# EMHASS configuration synchronization

GW EnergyPilot requires EMHASS to be installed and configured separately. EnergyPilot does not install EMHASS.

## Restore recommended defaults

The EMHASS settings page exposes **Restore recommended defaults**. This only fills the GW EnergyPilot settings form with the current recommended values for review. It does not save automatically.

Canonical EnergyPilot outputs are:

- `sensor.p_batt_forecast`
- `sensor.p_grid_forecast`
- `sensor.optim_status`
- required optimization state `Optimal`

## Synchronize required config

**Synchronize required config** is an explicit administrator action. It reads the complete live EMHASS configuration, changes only mappings and runtime behavior required by EnergyPilot, writes the complete merged configuration, then reads it back for verification.

The runtime resolves the actual Home Assistant entity IDs for EnergyPilot load power, battery power and battery SOC from the entity registry. When EMHASS has PV enabled, the EnergyPilot PV total-power entity is resolved as well. Renamed entity IDs are therefore respected.

The required EMHASS runtime contract is:

- `continual_publish = false`
- `method_ts_round = first`
- `set_use_battery = true`

`continual_publish = false` establishes a single scheduler owner. EnergyPilot
performs full optimizations at fixed local wall-clock boundaries and publishes
the active saved-plan row at each inferred plan timestep. This prevents an
EMHASS background loop and an EnergyPilot timer from racing or leaving schedule
ownership ambiguous. A full optimization includes its initial publish and wins
when both operations are due at the same boundary.

## Settings-page presentation

The EMHASS settings page groups the editable EnergyPilot options into connection/planning, output mapping and price settings. A status summary at the top shows whether the live EMHASS configuration can be read, whether required values are synchronized and whether the configured output entities are complete.

The **EMHASS configuration check** is deliberately separate from the editable EnergyPilot fields. It uses the existing `managed_values` returned by `gw_energypilot/emhass_sync/get` and shows, for each EnergyPilot-owned EMHASS config value:

- a friendly setting name plus the canonical EMHASS key;
- the value EnergyPilot requires;
- the value actually read from EMHASS `config.json`;
- an explicit `In sync` or `Differs` status.

This separation is intentional. Options such as the EMHASS base URL, EnergyPilot scheduling, output entity names and runtime price integration are stored in the Home Assistant EnergyPilot config entry and do not all have a one-to-one field in EMHASS `config.json`. The UI therefore labels those values as EnergyPilot settings instead of falsely presenting them as EMHASS-stored values.

The existing **Synchronize required config** and **Restore recommended defaults** actions are reused; the presentation layer does not create a second write path or a duplicate EMHASS configuration API.

## Inverter topology is EMHASS-owned

`inverter_is_hybrid` describes the installation topology used by EMHASS and is **not** an EnergyPilot-required value. EnergyPilot preserves the configured value exactly as supplied by EMHASS.

This applies to both write paths:

- **Synchronize required config** does not list or change `inverter_is_hybrid`;
- the automatic pre-optimization policy does not overwrite `inverter_is_hybrid` before `/action/dayahead-optim`.

Changing Battery Saver mode, running **Optimize now**, or synchronizing required config therefore cannot silently switch an EMHASS installation between hybrid and non-hybrid modelling.

## PV is optional

`set_use_pv` is **not** an EnergyPilot-required value and is never forced to `true`.

- If the customer's EMHASS configuration has `set_use_pv = true`, EnergyPilot synchronizes the PV input and forecast mappings and requires a usable EnergyPilot PV entity.
- If `set_use_pv = false`, the customer's PV configuration is preserved and no PV entity is required for synchronization.

This keeps battery-only installations valid.

## Preserved configuration

Unrelated EMHASS configuration is preserved. Existing custom PV forecast entities are preserved when PV is enabled. Custom `var_model` values are preserved with a warning. Multi-battery power/SOC lists are not rewritten because EnergyPilot cannot safely infer per-battery ownership.

Battery Saver penalty fields are intentionally outside the generic required-config sync. Existing custom battery penalties remain untouched until the user explicitly selects an EnergyPilot Battery Saver mode. See `BATTERY_SAVER.md`.

## Minimum SOC ownership

The generic config-sync action does not write a GoodWe register. Minimum SOC is handled by the dedicated synchronized Minimum SOC NumberEntity under Custom and by the explicit managed-profile transaction:

- the Custom slider mirrors its verified GoodWe value into EMHASS `battery_minimum_state_of_charge`;
- a managed profile writes and verifies its GoodWe minimum first, then owns the matching EMHASS minimum and maximum;
- legacy v1.0 managed selections retain the available GoodWe floor until explicitly reselected;
- runtime `soc_final` is clamped to the effective minimum/maximum SOC range.

An explicit slider change retains the existing safety order: write and verify GoodWe first, then update EMHASS, and roll GoodWe back if the EMHASS write fails.

## Applying synchronization

The manual **Synchronize required config** action itself does not launch an optimization and does not write a GoodWe register. After changing required config manually, run a fresh EnergyPilot optimization before enabling Automatic Control.

EnergyPilot-owned optimization runs also enforce the small core runtime contract immediately before solving, so publisher ownership, battery use and timestamp rounding cannot silently drift away after a manual EMHASS edit. Installation-topology settings remain EMHASS-owned.

## Flow animation regression guard

The v0.28 consolidated frontend also makes the geometry-specific v0.13 particle keyframes authoritative by forcing `animation-direction: normal` on the flow particles. Later semantic frontend layers must not reverse those already-correct direction keyframes a second time.
