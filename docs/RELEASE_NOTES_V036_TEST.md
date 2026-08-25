# GW EnergyPilot v0.36 field-test checklist

This checklist complements the automated regression suite for the v0.36 Beta candidate. It is intentionally focused on operator-visible behavior that benefits from live Home Assistant browser validation.

## Preconditions

- GW EnergyPilot is loaded with an existing working GoodWe ETA configuration.
- EMHASS is installed/configured externally and a normal EnergyPilot-owned optimization succeeds.
- Automatic Control behavior has already been validated for the installation before changing Battery strategy.
- Browser cache is refreshed after installing the v0.36 candidate.

## Battery strategy controls

1. Open the normal **Controller** card.
2. Confirm **Battery strategy** shows Mad-Steve, Gold Rush, Balanced, Battery Saver and Custom.
3. Confirm exactly one strategy is marked active.
4. Confirm the low-level command such as `hybrid_battery_discharge` is not presented as a normal customer metric.
5. Open Diagnostics/support output and confirm the controller command remains available there.

## Managed profile transition

1. Record the current Battery · Plan · Price plan.
2. Select a different managed strategy.
3. Confirm the UI reports that the profile is being applied/optimized.
4. Confirm EMHASS completes a fresh optimization and publish cycle.
5. Confirm the newly selected strategy becomes active.
6. Confirm Battery · Plan · Price reloads the fresh plan without waiting for the normal frontend cache interval.
7. Confirm normal Automatic Control continues to use the existing strategy-specific GoodWe EMS mapping; the Battery strategy selector itself must not write a GoodWe EMS mode directly.

## Custom transition

1. Note the active managed profile values in EMHASS.
2. Select **Custom**.
3. Confirm the current EMHASS battery values are retained rather than reset to defaults.
4. Confirm minimum/maximum SOC controls become visible.
5. Confirm low-SOC cost, high-SOC cost, power-stress cost and charge/discharge weights are shown read-only.
6. Change one SOC slider and allow the existing debounce/optimization path to complete.
7. Confirm the graph refreshes after the resulting successful optimization.
8. For minimum SOC, confirm the existing GoodWe on-grid minimum-SOC synchronization/read-back behavior remains intact.

## High-update dashboard interaction

1. Use the dashboard while GoodWe telemetry and unrelated Home Assistant entities are updating rapidly.
2. Confirm buttons/sliders do not flicker because of unrelated HA state changes.
3. Press several dashboard buttons while telemetry is changing.
4. Confirm a pointer/keyboard press completes and is not lost due to a destructive rerender.
5. Confirm telemetry continues to refresh normally when merely hovering over controls.

## Live-flow direction

Validate the visible particle direction under states that are available on the installation:

- PV production: PV → hub.
- Grid import: Grid → hub.
- Grid export: hub → Grid.
- Battery charging: hub → Battery.
- Battery discharging: Battery → hub.
- House consumption: hub → House.

Do not infer control or register-sign behavior from the animation alone; compare against the existing telemetry labels/read-back when field-validating direction.

## Phone / narrow panel

1. Open EnergyPilot on a phone-width Home Assistant panel.
2. Confirm the live-flow card fits without desktop-sized clipping/overflow.
3. Rotate portrait ↔ landscape or resize the panel.
4. Confirm node/hub/connector geometry updates without reloading the page.
5. Confirm particles travel the complete resized connector length.
6. Confirm the normal desktop layout is unchanged on a wide browser.

## Failure/rollback spot check

Where a safe test environment permits temporarily causing an EMHASS apply/optimization failure:

1. Attempt a managed profile transition.
2. Confirm the previous EnergyPilot Battery Saver mode remains/restores after failure.
3. Confirm Battery Saver-owned EMHASS values are restored rather than leaving a half-applied profile.
4. Confirm no new GoodWe register-writing path is involved in the profile transaction itself.

## Automated validation expected before merge

The final v0.36 branch must pass:

- Python compile step;
- full unit-test discovery;
- repository invariants;
- HACS validation;
- Hassfest validation.

The automated test suite also covers the Custom ownership contract, failed transition rollback, plan-revision chart invalidation, live-flow direction specificity, responsive resize installation and render-storm/active-press guards.
