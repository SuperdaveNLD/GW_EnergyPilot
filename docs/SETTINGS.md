# Dedicated EnergyPilot settings

GW EnergyPilot exposes administrator configuration inside the built-in dashboard. v0.27 remains **Beta** while Hybrid control, extended-meter accounting, Battery & Price visualization and synchronized minimum-SOC handling receive broader field exposure.

## Ownership

EnergyPilot does not create a parallel settings database.

- `ConfigEntry.options` owns EnergyPilot/EMHASS integration options.
- `ConfigEntry.data` owns GoodWe connection data and the Automatic Control strategy.
- EMHASS `/get-config` and `/set-config` own live EMHASS configuration such as SOC constraints and `costfun`.
- GoodWe registers own inverter-side hardware settings/state.
- Home Assistant Stores own derived runtime/accounting/log history, not user configuration.

Administrator dashboard APIs include:

```text
gw_energypilot/settings/get
gw_energypilot/settings/update
gw_energypilot/smart_meter/get
gw_energypilot/smart_meter/set
gw_energypilot/beta_soc/get
gw_energypilot/beta_soc/set
gw_energypilot/optimization_log/get
gw_energypilot/battery_price/get
```

The active v0.27 frontend is `gw-energy-pilot-v027.js`. It keeps the complete v0.26 language-aware Battery & Price/minimum-SOC presentation and corrects the Hybrid strategy explanation at the active top layer.

## EP page

The EP section owns:

- maximum controller/setpoint power;
- control deadband;
- GoodWe telemetry interval;
- EV anti-discharge protection enable/disable;
- EV mode/power observation entities and activity threshold.

EV inputs are observation-only. EnergyPilot does not start, stop or modulate the EV charger.

During active EV charging:

```text
P_batt requests discharge -> Battery Hold
P_batt is neutral         -> Battery Hold
P_batt requests charge    -> mode 11 charge allowed
```

When native orchestration is enabled, EV stop waits for a fresh optimization before normal Automatic Control resumes.

## EMHASS page

The EMHASS section owns EnergyPilot's EMHASS integration settings:

- native orchestrator enable/disable;
- EMHASS URL;
- optimization interval;
- EnergyPilot runtime final SOC target;
- fallback load;
- `P_batt` and `P_grid` output entities;
- optimization status entity/required state;
- Nord Pool/runtime-price settings.

The stateful EMHASS optimization strategy remains the active `costfun` value:

```text
profit
cost
self-consumption
```

Changing `costfun` does not change the GoodWe actuator strategy.

## Minimum and maximum SOC

### Maximum SOC

Maximum SOC remains an **EMHASS-only** optimizer constraint.

### Minimum SOC — one synchronized on-grid control

The existing EMHASS minimum-SOC NumberEntity remains the single normal on-grid operator control and keeps its existing entity/unique ID.

Field validation on the reference GW15K-ETA-G20 confirmed that GoodWe register `45356` is an independent on-grid minimum-SOC floor. A lower EMHASS minimum alone cannot override a higher inverter floor.

Therefore an explicit minimum-SOC change is transactional:

```text
1. Read/validate current EMHASS config.
2. Validate requested minimum <= EMHASS maximum.
3. Require current readable GoodWe register 45356.
4. Require a whole 0..100 percentage.
5. Write requested value to GoodWe 45356.
6. Verify immediate 45356 read-back.
7. Write the same percentage to EMHASS battery_minimum_state_of_charge.
8. Publish verified GoodWe read-back into coordinator state.
9. Schedule one fresh optimization through the existing debounce.
```

Failure behavior:

- if `45356` is unavailable, neither GoodWe nor EMHASS is changed;
- if the GoodWe write/read-back fails, EMHASS is not changed;
- if GoodWe verifies but EMHASS `/set-config` fails, EnergyPilot attempts to restore the previous `45356` value;
- if rollback also fails, that second failure is surfaced explicitly.

There is **no startup or periodic background synchronization**. Register `45356` is changed only after an explicit minimum-SOC NumberEntity write.

The previous direct on-grid `45356` dashboard card is intentionally removed to avoid two competing operator controls for the same normal minimum SOC.

## GOODWE page

The GOODWE section owns:

- inverter host/IP;
- Modbus TCP port;
- Modbus unit ID;
- Automatic Control strategy;
- independent off-grid minimum-SOC register `45358` Beta field test.

Connection changes are validated with a temporary `GWModbusClient` before the existing config entry is updated/reloaded.

### Automatic Control strategies

**Battery control**

```text
P_batt < -deadband -> mode 11 Battery charge power
P_batt > +deadband -> mode 12 Battery discharge power
P_batt near 0 W    -> mode 8 Battery Hold
```

**Grid control**

```text
P_grid > +deadband -> mode 9 Grid import target
P_grid < -deadband -> mode 10 Grid export target
P_grid near 0 W    -> mode 1 GoodWe Auto / self-use
```

**Hybrid control**

```text
P_grid > +deadband -> mode 9 Grid import target (buy/import)
else P_batt > +deadband -> mode 12 Battery discharge power (sell/discharge)
else P_batt near 0 W -> mode 8 Battery Hold
otherwise -> mode 1 GoodWe Auto / self-use
```

Hybrid therefore combines the GoodWe smart-meter/PCC loop for **buying** with direct battery-power control for **selling**. The mode-9 setpoint comes from the EMHASS `P_grid` import magnitude; the mode-12 setpoint comes from the EMHASS `P_batt` discharge magnitude.

A battery-charge request without planned grid import falls through to GoodWe mode 1/self-use. This deliberately lets GoodWe absorb locally available PV without forcing the battery to the forecast-sized `P_batt` charging setpoint. A neutral battery plan remains mode 8.

When no explicit `control_strategy` exists, backwards compatibility remains:

```text
legacy use_goodwe_smart_meter missing/false -> Battery
legacy use_goodwe_smart_meter true          -> Grid
```

Manual EMS selections are never remapped by the automatic strategy.

## Off-grid minimum-SOC field test

Register `45358` remains an independent manual Beta field-test control.

Safety rules:

- Home Assistant administrator access required;
- canonical register-key whitelist only;
- current register must already be readable;
- whole `0..100%` values only;
- frontend confirmation;
- immediate same-register read-back;
- success only when read-back matches.

The existing `beta_soc` backend API remains available for backwards-compatible diagnostics/tooling. On-grid `45356` writes through that low-level API are not the normal dashboard control path; the synchronized minimum-SOC NumberEntity is the supported operator path.

Register `47500` remains read-only because its firmware-dependent semantics are unresolved.

## Battery & Price

The Battery & Price card is read-only. It does not add user settings or a second pricing configuration source.

- Battery bars consume Recorder statistics from the existing `battery_power` entity.
- Price series come from the same EnergyPilot runtime price path used by EMHASS.
- The browser caches chart data for five minutes to avoid request churn.
- Approximate charged/discharged values are display summaries, not accounting entities.

See `docs/BATTERY_PRICE_CHART.md`.

## Persistent state is not settings

EnergyPilot currently uses per-entry Home Assistant Stores for:

```text
gw_energypilot.runtime.<entry_id>          last_success runtime evidence
gw_energypilot.accounting.<entry_id>       daily grid accounting state
gw_energypilot.optimization_log.<entry_id> newest optimization attempts
```

These stores are not editable configuration.

## Stable identity

Home Assistant device identity remains based on:

```text
(DOMAIN, config_entry_id)
```

Connection changes must not create a second EnergyPilot device. Existing entity unique IDs remain stable.

## Security and reload behavior

- Dashboard configuration write APIs require a Home Assistant administrator.
- EP/EMHASS setting changes normally reload the existing entry where the settings API requires it.
- GoodWe connection changes validate first, then reload.
- Automatic strategy changes can be applied without a full reload and re-evaluate the active plan when Automatic Control is on.
- Minimum-SOC synchronization is an explicit NumberEntity transaction and does not reload the integration.
- Persistent runtime/accounting/log Stores survive config-entry reloads and Home Assistant restarts.
