# Dedicated EnergyPilot settings

GW EnergyPilot exposes administrator-only configuration inside the built-in dashboard.

v0.25 remains **Beta** while Hybrid control, extended-meter accounting selection, persistent optimization history and synchronized G20 minimum-SOC handling receive wider field exposure.

## Configuration ownership

EnergyPilot does not create a parallel settings database.

- `ConfigEntry.options` owns EP/EMHASS integration options.
- `ConfigEntry.data` owns GoodWe connection data and the automatic-control strategy.
- EMHASS `/get-config` and `/set-config` own live EMHASS configuration such as SOC bounds and `costfun`.
- The **EMHASS minimum SOC slider** is the single operator control for the normal on-grid minimum: an explicit change writes the same whole-percent value to EMHASS `battery_minimum_state_of_charge` and GoodWe register `45356`.
- GoodWe register `45358` remains an independent off-grid inverter setting and manual Beta field test.
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

The `beta_soc` API remains available for backwards-compatible diagnostics/tooling. The active dashboard no longer exposes a separate direct on-grid `45356` control because that would create two competing operator controls for the same minimum SOC.

The active v0.25 frontend layers the LOG view and current SOC-control alignment over the complete v0.24 Hybrid-control frontend.

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

### Minimum and maximum SOC sliders

The maximum-SOC slider remains an EMHASS-only optimizer constraint.

The minimum-SOC slider has a stricter contract on the validated ETA-G20 path. Field testing established that lowering only EMHASS `battery_minimum_state_of_charge` is insufficient when the inverter-side on-grid floor in register `45356` is higher. The inverter stops discharge at its own floor even if EMHASS planned a lower SOC.

Therefore one explicit minimum-SOC slider change now performs this transaction:

```text
validate minimum <= EMHASS maximum
read current GoodWe 45356 from coordinator telemetry
write requested whole-percent minimum to GoodWe 45356
verify 45356 read-back
write the same percentage to EMHASS battery_minimum_state_of_charge
publish the verified GoodWe value into coordinator state
schedule one fresh optimization after the existing debounce
```

If `45356` is unavailable, EnergyPilot does **not** change the EMHASS minimum. If the verified GoodWe write succeeds but the subsequent EMHASS `/set-config` call fails, EnergyPilot attempts to restore the previous `45356` value. A failed rollback is surfaced as an error rather than hidden.

This synchronization occurs only after an explicit user/service change of the minimum-SOC number entity. It is configuration synchronization, not an Automatic Control EMS target and not a periodic background write.

## GOODWE page

The GOODWE section manages:

- inverter host/IP;
- Modbus TCP port;
- Modbus unit ID;
- **Automatic control strategy**;
- the independent off-grid minimum-SOC `45358` field test.

Connection changes are validated against a temporary `GWModbusClient` before the existing config entry is updated/reloaded.

The former direct **On-grid minimum SOC / register 45356** card is intentionally removed from this page. On-grid minimum SOC is controlled from the EMHASS minimum-SOC slider so the optimizer and inverter floor cannot be changed independently through two dashboard controls.

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

## G20 minimum-SOC register ownership

Current ETA-G20 handling is:

```text
45356  On-grid minimum SOC -> synchronized from EMHASS minimum-SOC slider
45358  Off-grid minimum SOC -> independent manual Beta field test
```

For `45356`:

- whole `0..100%` values only;
- the current register must already be readable before a minimum-SOC change is accepted;
- canonical address lookup remains in `registers.py` through the existing client helper;
- every actual write is followed by immediate same-register read-back;
- EMHASS is changed only after the GoodWe write verifies;
- a later EMHASS write failure triggers an attempted GoodWe rollback;
- there is no second dashboard control under GOODWE.

For `45358`, the existing manual field-test safety remains:

- Home Assistant administrator required;
- only the canonical register-key whitelist is accepted;
- register must already be readable;
- whole `0..100%` values only;
- frontend confirmation;
- immediate same-register read-back;
- success only when read-back matches.

`47500` remains read-only because its firmware-dependent semantics are unresolved.

## Stable Home Assistant identity

Device identity remains based on the stable config-entry ID rather than mutable host/unit-ID values. Existing entity unique IDs must not change as part of settings or connection updates.

The existing `number.<...>_emhass_minimum_soc` entity and its unique ID remain unchanged. Only its write semantics are extended to synchronize the inverter-side floor.

## Security and reload behavior

Dashboard write APIs require a Home Assistant administrator. Backend authorization is the security boundary; hiding controls in the frontend is not sufficient.

- EP/EMHASS changes normally reload the existing config entry.
- GoodWe connection changes validate first, then reload.
- Automatic strategy changes are stored in the selected config entry and may re-evaluate immediately without a full reload.
- Minimum-SOC slider changes update EMHASS and verified GoodWe `45356` without reloading the integration, then debounce one fresh optimization.
- Manual `45358` field-test writes do not reload the integration.
- accounting/runtime/optimization-history Stores survive normal config-entry reloads and Home Assistant restarts.
- all state and settings remain scoped per EnergyPilot config entry.
