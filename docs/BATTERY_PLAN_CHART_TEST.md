# Battery plan chart field validation

For the current **v0.49** line, validate on a live installation:

1. Select S, M and L and confirm the selected size survives a browser refresh.
2. Confirm the red Battery · Plan · Price window control hides the card immediately and that the card can be restored from Dashboard layout / visibility.
3. Confirm the yellow window control switches the card to Compact size and that the compact preference survives a browser refresh.
4. Confirm the green window control opens the detailed graph. In the detail window, confirm red closes, yellow returns to the compact dashboard card, and green toggles the detail window size. Escape and backdrop-click must still close the detail window.
5. Confirm actual charging is below zero and actual discharging above zero.
6. Confirm near-zero battery-power samples do not render as false charge/discharge bars or tooltips.
7. Confirm the dashed historical EMHASS target follows the `P_batt` target that was active earlier in the day and remains visible on top of the actual bars.
8. Confirm a `P_batt` state already active before local midnight is represented from 00:00 until the next state change.
9. After a successful optimization, confirm the future horizon reports the persistent official EMHASS-plan source when `GET /api/v1/plan` is available. Confirm the displayed points match the EMHASS plan timestamps/values.
10. Temporarily reproduce a Home Assistant `P_batt`/`P_grid` publication gap while the mirrored plan is still valid. Confirm the future plan remains available and Automatic Control can resolve the current plan point without creating replacement Home Assistant entities.
11. Confirm an explicit live non-ready optimizer status is **not** bypassed by the persistent mirror.
12. Confirm the final mirrored plan point is not extrapolated after its inferred `valid_until` interval; expired plan data must not remain a current control target.
13. If the official EMHASS plan endpoint is unavailable, confirm current `battery_scheduled_power` remains a compatibility fallback. If a custom/older publisher only supplies `forecasts`, confirm that fallback still works.
14. Confirm actual SOC follows Recorder 5-minute means from the registry-resolved EnergyPilot `battery_soc` entity without multiplying values at or below `1%`.
15. Confirm forecast SOC follows only official `SOC_opt` points and displays the known `0..1` plan fraction as `0..100%`. Values below 0, above 1, non-finite values and similarly named columns must not render.
16. Remove Recorder SOC statistics and confirm only the actual SOC line/message becomes unavailable; battery power, plan and price remain visible. Remove `SOC_opt` and confirm only forecast SOC becomes unavailable.
17. With an EMHASS multi-battery plan containing only `SOC_opt_0`/`SOC_opt_1`, confirm no aggregate forecast SOC is drawn.
18. Run the chart regressions on desktop Chromium, iPad WebKit touch and iPhone WebKit touch. Confirm telemetry preserves `main`, controls and scroll position, while a plan refresh replaces only the one canonical graph card and both SOC series remain present.
19. Run a fresh optimization that changes the plan but leaves the Battery · Plan · Price card already visible. Confirm the existing canonical card refreshes immediately rather than waiting for the normal five-minute cache.
20. Confirm the refresh in step 19 does not create a second `.ep-v027-battery-plan-card`.
21. Confirm a newly reported `P_batt` with the **same numeric value** as the previous row is accepted as fresh after optimization (`last_reported` freshness contract).
22. Confirm the market-price series renders as interval steps and the NOW marker remains aligned with local time.
23. Confirm **Plan charge / Plan discharge** show `—` when no historical/future plan data exists instead of `0.00 kWh`.
24. Compare the GoodWe 35208/35211 headline totals with the Recorder power integral shown beneath them. A difference is allowed because these are separate measurement paths; the native GoodWe counter must remain the headline total.
25. Confirm a Home Assistant restart/integration reload restores the still-valid `gw_energypilot.plan.<entry_id>` mirror before the external plan entities recover, then refreshes it from EMHASS in the bounded startup background path.
26. Confirm missing/expired plan data degrades to an explanatory unavailable state without suppressing actual bars or prices.
27. Confirm Battery/Grid/Hybrid mode mappings, manual EMS commands and support diagnostics remain unaffected by chart reads, plan recovery and window controls.

This checklist is read-only with respect to the chart. Do not change Automatic Control or EMS mode solely to manufacture visualization data. Plan-resilience testing may intentionally hide/reload publication entities, but must not invent or rewrite GoodWe register semantics.
