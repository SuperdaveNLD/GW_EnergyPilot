# Battery plan chart field validation

For the current **v1.3.0-beta.3** line, validate on a live installation:

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
19. For 15-, 30- and 60-minute plans, compare an official `SOC_opt` row with
    the chart tooltip. Confirm the Wanted SOC timestamp is exactly one inferred
    plan step after the source row, while `P_batt` and price remain at the
    source interval start. Repeat across a local DST boundary.
19. Run a fresh optimization that changes the plan but leaves the Battery · Plan · Price card already visible. Confirm the existing canonical card refreshes immediately rather than waiting for the normal five-minute cache.
20. Select **12h** and confirm the axis spans six hours before through six hours after NOW; select **24h** and confirm the fixed local day; select **36h** and confirm the fixed endpoint tomorrow 12:00.
21. Repeat the range choices on desktop, iPad and iPhone. Confirm the chosen range is restored after a dashboard structural rerender/browser reload and that no duplicate Battery · Plan · Price card appears.
22. While watching Home Assistant Recorder/history WebSocket traffic, switch repeatedly between 12h/24h/36h. Confirm the range clicks create no new Recorder/history requests; only explicit refresh, cache expiry or fresh-plan invalidation reloads the shared dataset.
23. On a Home Assistant timezone with DST, verify a spring/fall transition day remains fixed from local 00:00 to the next local 00:00 even though the elapsed duration is 23/25 hours. Confirm the 12h rolling view remains exactly twelve elapsed hours.
24. Confirm the refresh in step 19 does not create a second `.ep-v027-battery-plan-card`.
25. Confirm a newly reported `P_batt` with the **same numeric value** as the previous row is accepted as fresh after optimization (`last_reported` freshness contract).
26. Confirm the market-price series renders as interval steps and the NOW marker remains aligned with local time.
27. Confirm **Plan charge / Plan discharge** show `—` when no historical/future plan data exists instead of `0.00 kWh`.
28. Compare the GoodWe 35208/35211 headline totals with the Recorder power integral shown beneath them. A difference is allowed because these are separate measurement paths; the native GoodWe counter must remain the headline total.
29. Confirm a Home Assistant restart/integration reload restores the still-valid `gw_energypilot.plan.<entry_id>` mirror before the external plan entities recover, then refreshes it from EMHASS in the bounded startup background path.
30. Confirm missing/expired plan data degrades to an explanatory unavailable state without suppressing actual bars or prices.
31. Confirm Battery/Grid/Hybrid mode mappings, manual EMS commands and support diagnostics remain unaffected by chart reads, plan recovery and window controls.
32. In Large and expanded views, compare grid/solar charge and battery/solar export colors with simultaneous Recorder battery/PV/load/grid means. Confirm a missing or inconsistent source becomes hatched **Unknown** rather than being assigned to solar or grid.
33. Confirm Compact and Normal retain the familiar actual battery bars while only Large/expanded views replace them with source-attributed flows.
34. Confirm the dashed Wanted SOC line uses older execution snapshots for elapsed time and the current official plan for current/future time. Re-optimize and verify the historical segment does not change.
35. Confirm one `.ep-v051-history-card` shows nearest ±6-hour rows and that **Full 48h + 24h table** opens a scrollable table with one row per retained/projected event.
36. Exercise completed+verified, matching-readback skip, mismatch/unavailable, write-failure and waiting cases where safely reproducible; confirm their labels do not imply a write or verification that did not occur.
37. Change Battery/Grid/Hybrid strategy or deadband and confirm earlier table rows keep their snapshotted configuration while future projections use the current configuration and remain labelled projected.
38. Around a DST transition, confirm the full table uses Home Assistant timezone abbreviations, repeated local times remain distinct and no nonexistent spring-forward row is fabricated.
39. Confirm upgrade starts with an empty execution history, then survives integration reload/restart, prunes beyond seven days and never contains entity IDs or EMHASS credentials.

This checklist is read-only with respect to the chart. Do not change Automatic Control or EMS mode solely to manufacture visualization data. Plan-resilience testing may intentionally hide/reload publication entities, but must not invent or rewrite GoodWe register semantics.
