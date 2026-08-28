# GW EnergyPilot v0.44 Beta

v0.44 combines two bounded reliability improvements: **Optimize now** no longer rebuilds the dashboard after completion, and native EMHASS orchestration can recover the first plan after a Home Assistant restart while dependencies are still settling.

## Stable Optimize now

The inherited Optimize action already called the correct Home Assistant `button.press` entity, but its asynchronous helper requested a complete dashboard render in `finally`. That detached the touched control when the solve/publish transaction completed and could reintroduce blinking or broken native scrolling on WebKit.

The v0.44 release wrapper replaces only that listener. It:

- executes the existing Optimize entity exactly once;
- patches busy/idle text, disabled state and `aria-busy` in place;
- patches orchestrator status, last success and error details in place;
- preserves `main`, Optimize now, layout, Automatic Control and Battery Strategy nodes;
- retains the established `plan_revision`-driven refresh of only the Battery · Plan · Price card.

## Post-restart optimization recovery

With native orchestration enabled, EnergyPilot schedules one background optimization 60 seconds after setup. If Home Assistant, GoodWe telemetry or EMHASS is temporarily unavailable, the attempt retries after 15, 30 and 60 seconds.

The sequence is deliberately bounded. Any successful manual, scheduled or event-driven EnergyPilot optimization after setup cancels the remaining attempts. If all recovery attempts fail, the ordinary periodic schedule remains active. Home Assistant config-entry setup never waits for EMHASS or Modbus I/O.

Every successful attempt still uses the established EMHASS runtime contract, fresh finite-output checks, persistent optimization log, official-plan mirror refresh and `plan_revision` publication.

## Validation scope

- Python compile and complete unit suite;
- repository invariant validation;
- HACS and Hassfest validation on the exact release head;
- frontend architecture audit;
- desktop Chromium at 1440 × 900;
- iPad WebKit touch at 834 × 1112;
- iPhone WebKit touch at 390 × 844;
- exact Optimize action count, zero complete renders, stable persistent-control identity, native scroll anchoring and working post-optimization scrolling;
- startup scheduling, restored-runtime baseline, successful skip, disabled/manual-only skip and bounded retry exhaustion.

## Safety and compatibility

v0.44 does not change GoodWe registers, Modbus blocks or writes, EMS mappings or write order, Automatic Control decisions, Battery Saver policy, EMHASS objective/configuration ownership, entity IDs, unique IDs, config-entry data, persistent Store keys or stable device identity.

EMHASS remains an external prerequisite and is not installed or replaced by EnergyPilot.
