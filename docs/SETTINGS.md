# Dedicated EnergyPilot settings

GW EnergyPilot exposes administrator configuration inside the built-in dashboard. The active v0.49 settings chain keeps EnergyPilot, EV, EMHASS, PV and GoodWe ownership separated.

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

The active frontend chain is documented in `docs/FRONTEND_STABLE_DOM.md`. The settings shell remains owned by `gw-energy-pilot-settings-v016.js`; later release layers extend presentation without creating a second configuration database.

## EP page

The EP section owns:

- maximum controller/setpoint power;
- control deadband;
- GoodWe telemetry interval;

## EV page

The EV section owns two independent feature groups:

- the existing observation-based battery anti-discharge coordination;
- opt-in soft house-connection load balancing through one charger NumberEntity.

Load balancing configures the house-connection profile, a one-phase current
sensor, the three-phase charger current control, the shared `1–15` minute
condition window, and charger minimum/maximum boundaries. `3 × 25 A`, `5 min`,
`6 A` minimum and `16 A` maximum are the defaults. Custom one-phase and
three-phase connection profiles accept a per-phase current value.

The load balancer never calls the GoodWe client or EMS controller. A new charger
maximum above `16 A` requires explicit frontend and backend confirmation and
appends a durable operational acknowledgement to
`gw_energypilot.ev_load_balancing_audit.<entry_id>`. See
`docs/EV_LOAD_BALANCING.md`.

The anti-discharge EV mode/power inputs remain observation-only.

During active EV charging:

```text
P_batt requests discharge -> Battery Hold
P_batt is neutral         -> Battery Hold
P_batt requests charge    -> mode 11 charge allowed
```

When native orchestration is enabled, EV stop waits for a fresh optimization before normal Automatic Control resumes.

When an online entity is configured, missing, `unknown` and `unavailable` mean unreachable. A `binary_sensor` uses `on`/`off` explicitly; another available entity state means the charger integration is reporting. If the charger remains unreachable for five minutes, EnergyPilot temporarily suspends effective EV coordination without changing the saved user setting. Five stable online minutes resume it only when the setting is still enabled. Both transitions and connectivity changes are written to the Home Assistant log and the opt-in debug session.

## EMHASS page

The EMHASS section owns EnergyPilot's EMHASS integration settings:

- native orchestrator enable/disable;
- EMHASS URL;
- wall-clock optimization interval: 15, 30 or 60 minutes, with 15 minutes recommended;
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

Scheduled optimization is anchored to local clock boundaries at second 15.
Active plan-step publication follows the inferred EMHASS plan timestep. When
both are due, the full optimization and its initial publish complete before
Automatic Control is explicitly evaluated.

## PV page

The PV section owns display-only PV source selection:

- include/exclude the existing canonical internal GoodWe `pv_total_power` value;
- independently enable/disable all external PV insight;
- select up to four external Home Assistant instantaneous power entities;
- normalize supported `W`, `kW`, `MW` and `mW` readings to watts;
- expose one combined PV power sensor and dashboard source breakdown.

Internal GoodWe PV remains enabled by default for backwards-compatible dashboard behavior. The four external selectors share one panel and are editable only while **Include external PV** is on. Turning it off preserves their values but removes them from the live total. External values must be non-negative generation values.

These settings do not change EMHASS input, optimizer topology, Automatic Control, GoodWe EMS writes or grid accounting. See `docs/PV_INSIGHT.md`.

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

The previous direct minimum-SOC field-test panel is intentionally not shown in the dashboard. This avoids a second operator path alongside the synchronized minimum-SOC control.

## GOODWE page

The GOODWE section owns:

- inverter host/IP;
- Modbus TCP port;
- Modbus unit ID;
- Automatic Control strategy.

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
P_batt near 0 W -> mode 8 Battery Hold
else P_grid near 0 W -> mode 1 GoodWe Auto / self-use
else P_grid > +deadband -> mode 9 Grid import target
else P_grid < -deadband -> mode 10 Grid export target
```

Hybrid evaluates the configured deadband against `P_batt` first, so a neutral battery plan always remains mode 8. Every non-neutral plan then follows signed `P_grid`: mode 1 around zero lets GoodWe close the current local balance, while modes 9/10 receive the complete absolute planned import/export magnitude. Exact deadband boundaries remain neutral and the deadband is never subtracted from the setpoint.

When no explicit `control_strategy` exists, backwards compatibility remains:

```text
legacy use_goodwe_smart_meter missing/false -> Battery
legacy use_goodwe_smart_meter true          -> Grid
```

Manual EMS selections are never remapped by the automatic strategy.

## Low-level Beta SOC API

The old **Battery minimum SOC limits** field-test panel is no longer exposed in the GOODWE dashboard.

The existing `gw_energypilot/beta_soc/get` and `gw_energypilot/beta_soc/set` backend API remains available for backwards-compatible diagnostics and controlled field tooling. It is not a second normal operator settings path.

Safety rules for that low-level API remain unchanged:

- Home Assistant administrator access required;
- canonical register-key whitelist only;
- current register must already be readable;
- whole `0..100%` values only;
- immediate same-register read-back;
- success only when read-back matches.

Normal on-grid minimum SOC must use the synchronized NumberEntity path described above. Register `45358` remains a Beta register and is not exposed as a normal dashboard setting. Register `47500` remains read-only because its firmware-dependent semantics are unresolved.

## Battery plan / actual / price

The Battery plan / actual / price card is read-only. It does not add user settings or a second pricing configuration source.

- Actual battery bars consume Recorder statistics from the existing `battery_power` entity.
- Historical plan blocks consume Home Assistant history for the configured `P_batt` output entity.
- Future plan blocks consume the current EMHASS `forecasts` attribute from that battery forecast entity.
- Price series come from the same EnergyPilot runtime price path used by EMHASS.
- The browser caches chart data for five minutes to avoid request churn.
- The S/M/L card size is a browser-local dashboard preference, not an integration setting.
- Headline charged/discharged values prefer the existing GoodWe day counters `35208` / `35211`; graph integration remains a visualization comparison.

See `docs/BATTERY_PRICE_CHART.md` and `docs/BATTERY_PLAN_CHART.md`.

## Support diagnostics

The visible **Support** card is intentionally an operational summary instead of a full raw-register dump.

It shows four immediate health indicators:

```text
GoodWe live telemetry
Automatic/manual control ownership
Optimizer status
EMHASS / GoodWe minimum-SOC synchronization
```

The visible detail is grouped into:

- **GOODWE / LIVE** — actual EMS mode/setpoint, signed grid and battery direction, house load and battery SOC/SOH;
- **CONTROL / EMHASS** — current command/target, expected mode, both `P_batt` and `P_grid`, optimization/orchestrator state and last trigger/error;
- **SOC / LIMITS** — current SOC, synchronized EMHASS/GoodWe minimum, maximum SOC and the latest optimization SOC path.

Raw inverter mode registers, Beta candidates, lifetime energy counters and legacy/invalid EMHASS constraint values are deliberately not shown in the normal dashboard overview. They remain available through the single **Copy support report** action so issue reports retain deep diagnostic evidence without making the everyday UI unreadable.

This is presentation-only cleanup. Existing diagnostic entity attributes, register reads, `beta_soc` API behavior, controller logic and EMHASS behavior are unchanged apart from the explicitly documented v0.28 Hybrid strategy correction.

## Persistent state is not settings

EnergyPilot currently uses per-entry Home Assistant Stores for:

```text
gw_energypilot.runtime.<entry_id>          last_success runtime evidence
gw_energypilot.accounting.<entry_id>       daily grid accounting state
gw_energypilot.optimization_log.<entry_id> newest optimization attempts
gw_energypilot.plan.<entry_id>             validated EMHASS plan mirror
gw_energypilot.ev_load_balancing_audit.<entry_id> confirmed limits above 16 A
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
- EP/EV/EMHASS/PV setting changes normally reload the existing entry where the settings API requires it.
- GoodWe connection changes validate first, then reload.
- Automatic strategy changes can be applied without a full reload and re-evaluate the active plan when Automatic Control is on.
- Minimum-SOC synchronization is an explicit NumberEntity transaction and does not reload the integration.
- Persistent runtime/accounting/log Stores survive config-entry reloads and Home Assistant restarts.
