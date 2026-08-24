# Battery plan chart field validation

Before release consolidation, validate on a live installation:

1. Select S, M and L and confirm the selected size survives a browser refresh.
2. Confirm actual charging is below zero and actual discharging above zero.
3. Confirm the translucent historical EMHASS target follows the target that was active earlier in the day.
4. Confirm dashed future blocks match the current `P_batt` entity `forecasts` attribute.
5. Confirm the market-price line and NOW marker remain aligned with local time.
6. Compare the GoodWe 35208/35211 headline totals with the Recorder graph estimate shown beneath them.
7. Confirm a Home Assistant restart and full browser reload preserve normal dashboard/control behavior.
8. Confirm missing P_batt history or forecasts degrades to an explanatory note without suppressing actual bars or prices.

This checklist is read-only; do not change Automatic Control or EMS mode solely to manufacture chart data.
