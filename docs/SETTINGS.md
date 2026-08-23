# Dedicated EnergyPilot settings

GW EnergyPilot v0.16 adds a configuration area inside the built-in dashboard.

The settings gear is shown in the dashboard header for Home Assistant administrators and opens three sections:

- **EP** — EnergyPilot controller, telemetry and optional EV-coordination settings;
- **EMHASS** — EnergyPilot-owned EMHASS connection, scheduling, output mapping and Nord Pool runtime-price settings;
- **GOODWE** — local GoodWe Modbus TCP connection settings.

## One configuration source

The dashboard settings pages do **not** introduce a second configuration database.

Both the existing Home Assistant config/options flows and the dedicated dashboard pages read and update the same GW EnergyPilot `ConfigEntry`.

The backend implementation lives in:

```text
custom_components/gw_energypilot/settings_api.py
```

The frontend implementation lives in:

```text
custom_components/gw_energypilot/frontend/gw-energy-pilot-v016.js
```

This is intentional: runtime code continues to read `entry.data` and `entry.options` exactly as before, so existing installations and entity IDs remain compatible.

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

The existing live EMHASS minimum/maximum SOC sliders and cost-function buttons remain on the dashboard for v0.16. They write EMHASS `config.json` through the existing EMHASS API path and are intentionally not silently reimplemented in the config-entry settings API. They can be migrated into this page later while preserving their current backend logic.

## GOODWE page

The GOODWE section manages:

- inverter host/IP;
- Modbus TCP port;
- Modbus unit ID.

Before a connection change is stored, EnergyPilot creates a temporary `GWModbusClient` and validates that the target responds using the same setup-validation path as the normal config flow.

Only after successful validation does EnergyPilot update the config entry and reload the integration.

The Home Assistant device identity is deliberately **not** based on the mutable inverter host or Modbus unit ID anymore. v0.16 migrates the legacy `host:slave` device identifier to the stable GW EnergyPilot config-entry ID before entities are set up. This prevents an IP-address or unit-ID change from creating a second device or separating existing entities from their original device record.

Entity unique IDs remain based on the existing config-entry ID, so the settings pages do not intentionally rename existing entities or reset Recorder history/statistics.

The page also states the current primary validation target:

```text
GoodWe GW15K-ETA-G20 / ETA-G20 generation
```

The dedicated settings page does not add, infer or change any GoodWe register definition.

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
