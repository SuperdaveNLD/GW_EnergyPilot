# Dedicated EnergyPilot settings

GW EnergyPilot v0.17 added a configuration area inside the built-in dashboard. v0.18 extends the **GOODWE** page with a deliberately separate G20 field-test block for the verified-readback minimum-SOC registers `45356` and `45358`.

The settings gear is shown in the dashboard header for Home Assistant administrators and opens three sections:

- **EP** — EnergyPilot controller, telemetry and optional EV-coordination settings;
- **EMHASS** — EnergyPilot-owned EMHASS connection, scheduling, output mapping and Nord Pool runtime-price settings;
- **GOODWE** — local GoodWe Modbus TCP connection settings plus the manual G20 minimum-SOC field test.

v0.18 remains a **Beta** release. In this project Beta means the feature is available to the active tester group but has not yet been extensively field-tested.

## Configuration ownership

The dashboard settings pages do **not** introduce a second configuration database.

EP options, EMHASS integration options and the GoodWe host/port/unit-ID continue to use the existing GW EnergyPilot `ConfigEntry` as their single Home Assistant configuration source.

The v0.18 G20 SOC-floor controls are different by design: `45356` and `45358` are settings stored by the **GoodWe inverter itself**. They are therefore read from and written to the inverter and are not copied into the Home Assistant `ConfigEntry`.

Backend:

```text
custom_components/gw_energypilot/settings_api.py
custom_components/gw_energypilot/beta_soc_api.py
```

Frontend:

```text
custom_components/gw_energypilot/frontend/gw-energy-pilot-settings-v016.js
custom_components/gw_energypilot/frontend/gw-energy-pilot-v017.js
custom_components/gw_energypilot/frontend/gw-energy-pilot-v018.js
```

The v0.18 entry point layers the minimum-SOC field-test controls on top of the complete v0.17 settings, stateful EMHASS strategy and Beta diagnostics implementation.

## EP page

The EP section currently manages:

- maximum controller power;
- `P_batt` deadband;
- GoodWe telemetry refresh interval;
- EV coordination enable/disable;
- EV mode entity;
- EV power entity;
- EV activity/deadband threshold.

Saving uses the same validation/conversion path as the Home Assistant options flow and reloads the config entry.

## EMHASS page

The EMHASS section currently manages EnergyPilot's integration with EMHASS:

- native orchestrator enable/disable;
- EMHASS URL;
- periodic optimization interval;
- final SOC target;
- fallback load;
- `P_batt` output entity;
- optimization status entity and required state;
- Nord Pool runtime-price enable/disable;
- optimization trigger when tomorrow prices arrive;
- Nord Pool area and currency;
- import price adder;
- export price deduction.

The live EMHASS minimum/maximum SOC sliders and **EMHASS optimization strategy** are deliberately separate from these ConfigEntry options because they write the active EMHASS `config.json` through the existing `/get-config` → `/set-config` path.

The optimization strategy is exposed as one stateful Home Assistant select backed by EMHASS `costfun`. The dashboard highlights its current Profit / Cost / Self-consumption value. The three older v0.15 strategy buttons remain as backward-compatible configuration actions for existing automations.

These live EMHASS controls are intentionally not duplicated inside the ConfigEntry settings WebSocket API.

## GOODWE page

The normal GOODWE connection section manages:

- inverter host/IP;
- Modbus TCP port;
- Modbus unit ID.

Before a connection change is stored, EnergyPilot creates a temporary `GWModbusClient` and validates that the target responds using the same setup-validation path as the normal config flow.

Only after successful validation does EnergyPilot update the config entry and reload the integration.

### G20 Beta minimum-SOC field test

v0.18 adds a separate block below the connection settings for:

```text
45356  On-grid minimum SOC
45358  Off-grid minimum SOC
```

The controls show the raw register percentages already collected by the coordinator. On the reference GW15K-ETA-G20 both registers were observed at `10%` while discharge stopped around `10%` SOC.

For `45356`, current upstream GoodWe handling defines the user-facing on-grid depth of discharge as:

```text
DoD = 100 - raw register 45356
```

Therefore a raw `45356` value of `10` is presented by EnergyPilot as a **10% on-grid minimum SOC floor**, equivalent to 90% DoD. `45358` is treated as the corresponding off-grid minimum-SOC floor for this Beta validation.

The field-test path is intentionally narrower than the normal settings API:

- Home Assistant administrator access is required;
- only the two canonical keys already defined in `registers.py` can be written;
- the register must already be readable on the current inverter;
- only whole percentages from `0` through `100` are accepted;
- each action changes exactly one register;
- the dashboard asks for confirmation before the write;
- EnergyPilot immediately reads the same register back;
- success is reported only when read-back equals the requested value;
- a verified value is pushed into the coordinator snapshot immediately so the existing Diagnostic entity updates without waiting for the next scheduled poll.

The Beta SOC write path does **not** update or reload the Home Assistant config entry. The setting lives in the inverter.

The recommended validation sequence is to change one register at a time, record the old value, requested value and verified read-back, then observe the actual battery behavior before making another change.

`47500` remains read-only. Its G20 semantics are unresolved and the reference inverter has returned `65535`, so EnergyPilot does not interpret it as a writable percentage.

## Stable Home Assistant device identity

Older EnergyPilot versions identified the Home Assistant device by mutable `host:slave` data. Changing the inverter IP or unit ID could therefore create a second device record.

v0.17 migrates the existing device identifier to the stable GW EnergyPilot config-entry ID before platform entities are set up:

```text
legacy:  gw_energypilot + host:slave
current: gw_energypilot + config_entry_id
```

The migration is scoped to the owning config entry and uses Home Assistant's device registry update path. Existing entity unique IDs already use the config-entry ID, so this change is intended to preserve entity identity and Recorder history while making GoodWe connection changes safe.

## Beta diagnostics and control boundary

The G20 field-validation values continue to be collected through optional telemetry:

```text
45356  Beta on-grid minimum SOC floor
45358  Beta off-grid minimum SOC floor
47500  Beta battery SOC protection/status
36104  Beta extended lifetime grid export
36120  Beta extended lifetime grid import
```

The three SOC candidates are exposed as enabled Home Assistant Diagnostic sensors. `36104/36120` remain diagnostic-only lifetime-counter candidates and do not replace `36015/36017` for canonical Recorder-facing grid energy.

v0.18 creates one explicit exception to the former read-only Beta policy: **only `45356` and `45358` may be written, only through the dedicated manual field-test API described above**. They are still not inputs or outputs of the EnergyPilot automatic controller, EMHASS optimizer, event triggers or scheduled jobs.

No generic arbitrary-register writer is exposed.

## Security

Configuration reads and writes use dedicated Home Assistant WebSocket commands:

```text
gw_energypilot/settings/get
gw_energypilot/settings/update
gw_energypilot/beta_soc/get
gw_energypilot/beta_soc/set
```

All four commands require a Home Assistant administrator account. The dashboard gear is hidden for known non-admin users, but backend authorization remains the security boundary.

The Beta SOC API accepts only the fixed `45356/45358` key whitelist and percentage range; callers cannot supply an arbitrary Modbus address.

## Reload behaviour

Saving an EP, EMHASS or GoodWe connection section updates the existing config entry and requests an integration reload so coordinator, controller and orchestrator instances are recreated from the new settings.

If Home Assistant cannot reload the entry immediately, the settings API reports that a Home Assistant restart is required.

A manual `45356/45358` field-test write does **not** reload the integration. After verified read-back, the coordinator snapshot is updated and the normal polling cycle subsequently confirms the inverter value again.

## Multiple EnergyPilot entries

The settings model contains all GW EnergyPilot config entries. When more than one is configured, the dashboard shows an entry selector and saves only to the selected entry.

The Beta minimum-SOC controls use the same selected entry and therefore write only to that entry's configured GoodWe client.
