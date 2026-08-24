# Battery plan chart field validation

Before promoting v0.30, validate on a live installation:

1. Confirm the Battery · Plan · Price card shows EnergyPilot chrome: red `×`, cyan `−`, mint `↗`; the old S/M/L selector is no longer visible.
2. Click cyan `−` repeatedly and confirm the card cycles Compact → Normal → Large → Compact and the selected size survives a browser refresh.
3. Confirm red `×` hides the Battery · Plan · Price card immediately and the card can be restored from Dashboard layout / visibility.
4. Confirm every other visible dashboard card has a small red close control and every closed card can be restored through the existing layout/visibility menu.
5. Confirm mint `↗` opens the detailed graph and the detailed window still closes through its red control, Escape and backdrop click.
6. Confirm actual charging is below zero and actual discharging above zero.
7. Confirm near-zero battery-power samples do not render as false charge/discharge bars or tooltips.
8. Confirm the dashed historical EMHASS target follows the `P_batt` target that was active earlier in the day and remains visible on top of the actual bars.
9. Confirm a `P_batt` state already active before local midnight is represented from 00:00 until the next state change.
10. Confirm dashed forecast blocks continue to the right of NOW using the latest EMHASS `/api/v1/plan` `P_batt` horizon.
11. If `/api/v1/plan` is unavailable, confirm the chart degrades to the HA-entity `battery_scheduled_power` / `forecasts` fallback without suppressing actual battery bars or prices.
12. Confirm the market-price series renders as interval steps and the NOW marker remains aligned with local time.
13. Confirm **Plan charge / Plan discharge** show `—` when no historical/future plan data exists instead of `0.00 kWh`.
14. Compare the GoodWe 35208/35211 headline totals with the Recorder power integral shown beneath them. A difference is allowed because these are separate measurement paths; the native GoodWe counter must remain the headline total.
15. Confirm a Home Assistant restart and full browser reload load the v0.30 panel wrapper.
16. Confirm Battery/Grid/Hybrid control behavior, manual EMS commands and support diagnostics remain unaffected by chart/API reads and card controls.

This checklist is read-only; do not change Automatic Control or EMS mode solely to manufacture chart data.
