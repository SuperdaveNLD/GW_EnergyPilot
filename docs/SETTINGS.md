# Dedicated EnergyPilot settings

GW EnergyPilot v0.17 adds a configuration area inside the built-in dashboard.

The settings gear is shown in the dashboard header for Home Assistant administrators and opens three sections:

- **EP** — EnergyPilot controller, telemetry and optional EV-coordination settings;
- **EMHASS** — EnergyPilot-owned EMHASS connection, scheduling, output mapping and Nord Pool runtime-price settings;
- **GOODWE** — local GoodWe Modbus TCP connection settings.

v0.17 remains a **Beta** release. In this project Beta means the feature is available to the active tester group but has not yet been extensively field-tested.

## One configuration source

The dashboard settings pages do **not** introduce a second configuration database.

Both the existing Home Assistant config/options flows and the dedicated dashboard pages read and update the same GW EnergyPilot `ConfigEntry`.

Backend:

```text
custom_components/gw_energypilot/settings_api.py
```

Frontend:

```text
custom_components/gw_energypilot/frontend/gw-energy-pilot-settings-v016.js
custom_components/gw_energypilot/frontend/gw-energy-pilot-v017.js
```

The v0.17 entry point layers the settings UI on top of the existing v0.16 Beta diagnostics and stateful EMHASS strategy layer, so the G20 field-validation tools remain available.

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

The GOODWE section manages:

- inverter host/IP;
- Modbus TCP port;
- Modbus unit ID.

Before a connection change is stored, EnergyPilot creates a temporary `GWModbusClient` and validates that the target responds using the same setup-validation path as the normal config flow.

Only after successful validation does EnergyPilot update the config entry and reload the integration.

## Stable Home Assistant device identity

Older EnergyPilot versions identified the Home Assistant device by mutable `host:slave` data. Changing the inverter IP or unit ID could therefore create a second device record.

v0.17 migrates the existing device identifier to the stable GW EnergyPilot config-entry ID before platform entities are set up:

```text
legacy:  gw_energypilot + host:slave
current: gw_energypilot + config_entry_id
```

The migration is scoped to the owning config entry and uses Home Assistant's device registry update path. Existing entity unique IDs already use the config-entry ID, so this change is intended to preserve entity identity and Recorder history while making GoodWe connection changes safe.

## Beta diagnostics

The v0.16/v0.17 G20 field-validation values remain read-only:

```text
45356  Beta on-grid discharge depth
45358  Beta off-grid discharge depth
47500  Beta battery SOC protection
36104  Beta extended lifetime grid export
36120  Beta extended lifetime grid import
```

The three SOC candidates are also exposed as enabled Home Assistant Diagnostic sensors in v0.17. None of these Beta values is used by controller logic or written back to the inverter.

## Security

Configuration reads and writes use dedicated Home Assistant WebSocket commands:

```text
gw_energypilot/settings/get
gw_energypilot/settings/update
```

Both commands require a Home Assistant administrator account. The dashboard gear is hidden for known non-admin users, but backend authorization remains the security boundary.

## Reload behaviour

Saving a section updates the existing config entry and requests an integration reload so coordinator, controller and orchestrator instances are recreated from the new settings.

If Home Assistant cannot reload the entry immediately, the settings API reports that a Home Assistant restart is required.

## Multiple EnergyPilot entries

The settings model contains all GW EnergyPilot config entries. When more than one is configured, the dashboard shows an entry selector and saves only to the selected entry.
