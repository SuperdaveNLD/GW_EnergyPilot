# Dedicated EnergyPilot settings

GW EnergyPilot exposes administrator-only configuration inside the built-in dashboard.

v0.25 remains **Beta** while Hybrid control, extended-meter accounting selection and persistent optimization history receive wider field exposure.

## Configuration ownership

EnergyPilot does not create a parallel settings database.

- `ConfigEntry.options` owns EP/EMHASS integration options.
- `ConfigEntry.data` owns GoodWe connection data and the automatic-control strategy.
- EMHASS `/get-config` and `/set-config` own live EMHASS configuration such as SOC bounds and `costfun`.
- GoodWe registers such as `45356/45358` own inverter-stored settings.
- Home Assistant Stores own derived accounting/runtime history only; they are not editable user configuration.

Backend dashboard APIs include:

```text
gw_energypilot/settings/get
gw_energypilot/settings/update
gw_energypilot/smart_meter/get
gw_energypilot/smart_meter/set
gw_energypilot/beta_soc/get
gw_energypilot/beta_soc/set
gw_energypilot/optimization_log/get
```

The active v0.25 frontend layers the LOG view over the complete v0.24 Hybrid-control frontend.

## EP page

The EP section manages:

- maximum controller/setpoint power;
- control deadband;
- GoodWe telemetry refresh interval;
- EV anti-discharge protection enable/disable;
- EV mode entity;
- EV power entity;
- EV activity threshold.

Maximum power caps the requested **mode-specific** setpoint. A mode-9/10 value is a PCC grid target; a mode-11/12 value is a direct battery target.

### EV anti-discharge protection

For backwards compatibility the stored option remains:

```text
enable_ev_coordination
```

The EV entities are observation inputs only. EnergyPilot does not start, stop or modulate the charger.

While EV charging is active:

```text
P_batt > +deadband -> mode 8 Battery Hold
P_batt near 0 W    -> mode 8 Battery Hold
P_batt < -deadband -> mode 11 Battery charge allowed
```

This override is evaluated before the normal Battery/Grid/Hybrid strategy. After EV charging stops, native orchestration waits for a fresh optimization before normal automatic execution resumes.

## EMHASS page

The EMHASS section manages EnergyPilot's integration with EMHASS, including URL, scheduler, runtime final SOC, fallback load, `P_batt`, `P_grid`, optimizer status and optional Nord Pool runtime-price settings.

The stateful EMHASS objective remains one `costfun` value:

```text
profit
cost
self-consumption
```

Changing `costfun` does not silently change the GoodWe Automatic Control strategy.

## GOODWE page

The GOODWE section manages:

- inverter host/IP;
- Modbus TCP port;
- Modbus unit ID;
- **Automatic control strategy**;
- manual G20 minimum-SOC field tests.

Connection changes are validated against a temporary `GWModbusClient` before the existing config entry is updated/reloaded.

## Automatic control strategy

v0.25 exposes three explicit choices.

### Battery control

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt near 0 W    -> mode 8 Battery Hold
```

This is the backwards-compatible behavior when no explicit `control_strategy` exists and the legacy `use_goodwe_smart_meter` value is absent/false.

### Grid control

```text
P_grid > +deadband -> mode 9 Grid import target
P_grid < -deadband -> mode 10 Grid export target
P_grid near 0 W    -> mode 1 GoodWe Auto / self-use
```

Use this only with a valid/validated GoodWe smart meter. GoodWe performs the fast PCC control loop internally.

### Hybrid control

```text
P_batt < -deadband      -> mode 11 Battery charge target
else P_grid < -deadband -> mode 10 Grid export target
otherwise               -> mode 1 GoodWe Auto / self-use
```

Hybrid uses direct battery power for charging, PCC power for export and GoodWe self-use for other situations. It deliberately does not force a normal discharge request through mode 12.

The old `use_goodwe_smart_meter` boolean remains synchronized for compatibility with older frontend/support layers. Existing installations without an explicit `control_strategy` retain the old mapping: false/missing = Battery, true = Grid.

Changing the strategy while Automatic Control is ON requires frontend confirmation because the current plan is re-evaluated immediately.

Manual mode 9/10/11/12 commands are never remapped by this setting.

## LOG page

v0.25 adds an administrator-only, read-only optimization history view.

It loads the latest 50 EnergyPilot-owned optimization attempts from:

```text
gw_energypilot.optimization_log.<config_entry_id>
```

The viewer shows newest first and supports manual refresh. It does not edit or replay runs.

Typical stored diagnostics include run timestamps/duration, trigger reason, success/failure, SOC inputs, current load, price source/points, load-forecast point count, `P_batt`, EMHASS HTTP statuses and error text.

The log Store is separate from `gw_energypilot.runtime.<config_entry_id>` so a failed run can be retained as diagnostic evidence without changing `last_success`.

## Persistent accounting is not settings

Derived Today/Yesterday grid accounting is stored per config entry. v0.25 may select:

```text
extended: 36104 export / 36120 import
legacy:   36015 export / 36017 import
```

The populated extended pair is preferred when coherent; an empty `0/0` optional extended pair does not replace usable legacy totals. The selected source is persisted and any source change re-baselines before new deltas are accumulated.

This affects only the derived accounting source. Established physical lifetime Home Assistant entities retain their existing unique IDs/state classes.

See `docs/ACCOUNTING.md`.

## G20 Beta minimum-SOC field test

The GOODWE page retains manual field-test controls for:

```text
45356  On-grid minimum SOC
45358  Off-grid minimum SOC
```

Rules:

- Home Assistant administrator required;
- only the canonical register-key whitelist is accepted;
- register must already be readable;
- whole `0..100%` values only;
- one register per action;
- frontend confirmation;
- immediate same-register read-back;
- success only when read-back matches.

`47500` remains read-only because its firmware-dependent semantics are unresolved.

## Stable Home Assistant identity

Device identity remains based on the stable config-entry ID rather than mutable host/unit-ID values. Existing entity unique IDs must not change as part of settings or connection updates.

## Security and reload behavior

Dashboard write APIs require a Home Assistant administrator. Backend authorization is the security boundary; hiding controls in the frontend is not sufficient.

- EP/EMHASS changes normally reload the existing config entry.
- GoodWe connection changes validate first, then reload.
- Automatic strategy changes are stored in the selected config entry and may re-evaluate immediately without a full reload.
- Manual `45356/45358` field-test writes do not reload the integration.
- accounting/runtime/optimization-history Stores survive normal config-entry reloads and Home Assistant restarts.
- all state and settings remain scoped per EnergyPilot config entry.
