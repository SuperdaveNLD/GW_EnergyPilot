# Dedicated EnergyPilot settings

GW EnergyPilot exposes administrator-only configuration inside the built-in dashboard.

The settings gear opens three sections:

- **EP** — EnergyPilot controller, telemetry and optional EV-coordination settings;
- **EMHASS** — EnergyPilot-owned EMHASS connection, scheduling, output mapping and Nord Pool runtime-price settings;
- **GOODWE** — local GoodWe connection, automatic actuator strategy and manual G20 field-test controls.

v0.22 remains **Beta** because the new automatic mode-9/mode-10 strategy still has limited multi-installation field exposure.

## Configuration ownership

The dashboard does not create a parallel settings database.

- EP/EMHASS options use the existing GW EnergyPilot `ConfigEntry.options`.
- GoodWe host/port/unit-ID and the v0.22 smart-meter actuator choice use the existing `ConfigEntry.data`.
- EMHASS live configuration such as SOC bounds and `costfun` remains in EMHASS `config.json` and is changed through `/get-config` → `/set-config`.
- Beta SOC-floor registers `45356/45358` live in the GoodWe inverter itself.

Backend configuration APIs:

```text
custom_components/gw_energypilot/settings_api.py
custom_components/gw_energypilot/smart_meter_api.py
custom_components/gw_energypilot/beta_soc_api.py
```

The active frontend is layered; v0.22 adds its controls on top of the existing settings implementation rather than creating a second settings page.

## EP page

The EP section manages:

- maximum controller/setpoint power;
- control deadband;
- GoodWe telemetry refresh interval;
- EV coordination enable/disable;
- EV mode entity;
- EV power entity;
- EV activity threshold.

The configured maximum power caps the requested **mode-specific setpoint**. With mode 9/10 PCC control, this is the requested grid import/export target. It is not necessarily the final battery power because local PV or house load can add/subtract energy behind the meter.

## EMHASS page

The EMHASS section manages EnergyPilot's integration with EMHASS:

- native orchestrator enable/disable;
- EMHASS URL;
- periodic optimization interval;
- runtime final SOC target;
- fallback load;
- `P_batt` output entity;
- `P_grid` output entity;
- optimization status entity and required state;
- Nord Pool runtime-price settings.

The live EMHASS minimum/maximum SOC sliders and **EMHASS optimization strategy** remain separate because they modify the active EMHASS configuration itself.

The strategy is one stateful `costfun` value:

```text
profit
cost
self-consumption
```

Changing `costfun` never silently changes the GoodWe actuator strategy.

## GOODWE page

The GOODWE section manages:

- inverter host/IP;
- Modbus TCP port;
- Modbus unit ID;
- **GoodWe smart meter active** automatic-control strategy;
- manual G20 minimum-SOC field tests.

### Connection settings

Before host/port/unit-ID changes are stored, EnergyPilot validates the target with a temporary `GWModbusClient` using the same setup-validation path as the normal config flow.

Only after successful validation does EnergyPilot update/reload the existing config entry.

## GoodWe smart meter active

v0.22 adds a dedicated strategy switch to the GOODWE page.

This value belongs to the GoodWe/config-entry layer, not to EMHASS `config.json`.

### ON — PCC/grid target control

This is the v0.22 default.

Automatic Control uses EMHASS `P_grid`:

```text
P_grid > +deadband  -> mode 9  Grid import target
P_grid < -deadband  -> mode 10 Grid export target
P_grid near 0 W     -> mode 1  GoodWe Auto / AI
```

GoodWe performs the fast control loop against its own smart meter/PCC.

The dashboard shows whether live `meter_total_power_fast` telemetry is currently available. Do not rely on PCC control when the GoodWe meter is absent or invalid.

If the setting is changed while Automatic Control is ON, the dashboard requires confirmation because the current EMHASS plan is immediately re-evaluated with the newly selected actuator strategy.

### OFF — direct battery fallback

Automatic Control uses EMHASS `P_batt`:

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt near 0 W    -> mode 8  Battery Hold
```

This fallback does not require `P_grid` to be valid.

Use it for installations without a usable GoodWe smart meter or while validating a different ETA-G20/firmware combination.

The strategy switch affects **Automatic Control only**. Manual mode 9/10/11/12 selections always execute exactly the selected mode.

## G20 Beta minimum-SOC field test

The GOODWE page also contains a separate field-test block for:

```text
45356  On-grid minimum SOC
45358  Off-grid minimum SOC
```

These values are stored by the inverter, not Home Assistant.

Current reference interpretation:

```text
raw 45356 = on-grid minimum SOC floor
DoD        = 100 - raw 45356

raw 45358 = off-grid minimum SOC floor candidate
```

The field-test path is deliberately narrow:

- Home Assistant administrator access is required;
- only the canonical `45356/45358` keys can be written;
- the register must already be readable;
- only whole `0..100%` values are accepted;
- each action writes exactly one register;
- the UI asks for confirmation;
- EnergyPilot reads the same register back immediately;
- success is reported only when read-back matches;
- verified read-back is pushed into the coordinator snapshot.

`47500` remains read-only because its firmware-dependent semantics are unresolved.

## Stable Home Assistant device identity

EnergyPilot identifies the Home Assistant device using the stable config-entry ID:

```text
current: gw_energypilot + config_entry_id
legacy:  gw_energypilot + host:slave
```

The v0.17 migration moves legacy devices to the stable identifier before entity platform setup. Do not change device identity back to mutable connection information.

## Beta diagnostics and control boundary

Optional field-validation values include:

```text
45356  Beta on-grid minimum SOC floor
45358  Beta off-grid minimum SOC floor
47500  Beta battery SOC protection/status
36104  Beta extended lifetime grid export
36120  Beta extended lifetime grid import
```

Except for the dedicated manual `45356/45358` write path, Beta register candidates do not feed automatic EMS control.

The v0.22 mode-9/mode-10 strategy is different: it uses already-established EMS registers `47511/47512` and the GoodWe smart meter. Its **automatic use** is still labelled Beta because the strategy has limited field exposure, not because new register addresses are being guessed.

## Security

Dashboard configuration commands require a Home Assistant administrator account.

Relevant WebSocket commands include:

```text
gw_energypilot/settings/get
gw_energypilot/settings/update
gw_energypilot/smart_meter/get
gw_energypilot/smart_meter/set
gw_energypilot/beta_soc/get
gw_energypilot/beta_soc/set
```

Backend authorization is the security boundary; hiding controls in the frontend alone is not sufficient.

The Beta SOC API accepts only the fixed register-key whitelist and percentage range. No generic arbitrary-register writer is exposed.

## Reload and runtime behavior

- EP/EMHASS settings updates normally reload the existing config entry.
- GoodWe connection changes validate first, then reload the existing entry.
- The GoodWe smart-meter strategy can be changed without a full reload because the controller reads the config-entry data dynamically; when Automatic Control is active the current plan is re-evaluated immediately after the change.
- Manual `45356/45358` field-test writes do not reload the integration.

## Multiple EnergyPilot entries

The main settings model supports multiple GW EnergyPilot config entries and saves only to the selected entry.

The smart-meter strategy and Beta SOC controls also operate on the selected entry, so one inverter can use PCC modes 9/10 while another remains on direct modes 11/12.
