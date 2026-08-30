# GW EnergyPilot v0.48 Beta

v0.48 corrects Hybrid Automatic Control after live v0.47 diagnostics showed a non-neutral battery plan with `P_grid = 0 W` still selecting direct battery mode 12. Hybrid now preserves a neutral battery plan first and uses the signed EMHASS PCC plan for every non-neutral battery plan.

## Hybrid decision order

When the EV anti-discharge override is not active, Hybrid evaluates the configured per-entry deadband in this exact order:

```text
abs(P_batt) <= deadband -> mode 8 Battery Hold, setpoint 0 W
else abs(P_grid) <= deadband -> mode 1 GoodWe Auto/self-use, setpoint 0 W
else P_grid > deadband -> mode 9 grid-import target, min(abs(P_grid), max_power)
else P_grid < -deadband -> mode 10 grid-export target, min(abs(P_grid), max_power)
```

Exact positive and negative boundaries remain inside the neutral zone. The deadband only selects the branch: EnergyPilot never subtracts it from a mode-9/10 setpoint.

This handles both shared hybrid-inverter PV and external AC-coupled PV. When EMHASS has a non-neutral battery plan but targets the grid around zero, mode 1 lets the GoodWe inverter close the current local balance rather than forcing a forecast-sized battery setpoint.

## Neutral-plan safety

A neutral EMHASS `P_batt` plan remains mode 8 Hold even when the site currently imports ordinary house load or exports available PV. Current site flow therefore cannot turn an idle battery plan into active buying or selling.

## Frontend and validation

The active v0.48 dashboard replaces the inherited 9/12 Hybrid explanation with current English and Dutch 8/1/9/10 guidance. `gw-energy-pilot-v048.js` is a bounded presentation wrapper over the complete v0.47 chain and uses a fresh `0.48-hybrid-control1` cache boundary.

Regression coverage includes neutral battery plans with import/export, both battery directions around zero grid target, signed mode-9/10 selection, variable exact deadband boundaries, complete setpoint magnitude and maximum-power clamping. The release browser matrix covers desktop Chromium, iPad WebKit touch and iPhone WebKit touch.

## Safety and compatibility

EV anti-discharge still executes before the selected automatic strategy: explicit charging remains allowed according to its existing mode-9/mode-11 rules and all other EV-active plans hold the battery. Battery and Grid strategies, manual EMS commands, GoodWe registers `47511`/`47512`, non-negative setpoints, setpoint-before-mode write ordering, entity identity, persistent Store keys, EMHASS optimization policy, v0.47 Battery Saver behavior, PV insight and grid accounting are unchanged.
