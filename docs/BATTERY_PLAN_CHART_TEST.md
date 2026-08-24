# Battery plan chart field validation

Before promoting v0.28, validate on a live installation:

1. Select S, M and L and confirm the selected size survives a browser refresh.
2. Confirm actual charging is below zero and actual discharging above zero.
3. Confirm near-zero battery-power samples do not render as false charge/discharge bars or tooltips.
4. Confirm the dashed historical EMHASS target follows the `P_batt` target that was active earlier in the day and remains visible on top of the actual bars.
5. Confirm a `P_batt` state already active before local midnight is represented from 00:00 until the next state change.
6. Confirm dashed future blocks match the configured `P_batt` entity `battery_scheduled_power` attribute. If a custom/older publisher only supplies `forecasts`, confirm the compatibility fallback still works.
7. Confirm the market-price series renders as interval steps and the NOW marker remains aligned with local time.
8. Confirm **Plan charge / Plan discharge** show `—` when no historical/future plan data exists instead of `0.00 kWh`.
9. Compare the GoodWe 35208/35211 headline totals with the Recorder power integral shown beneath them. A difference is allowed because these are separate measurement paths; the native GoodWe counter must remain the headline total.
10. Confirm a Home Assistant restart and full browser reload load the v0.28 chart modules rather than cached v0.27 nested modules.
11. Confirm missing P_batt history/schedule degrades to an explanatory note without suppressing actual bars or prices.
12. Confirm Battery/Grid/Hybrid control behavior, manual EMS commands and support diagnostics remain unaffected by chart reads.

This checklist is read-only; do not change Automatic Control or EMS mode solely to manufacture chart data.
