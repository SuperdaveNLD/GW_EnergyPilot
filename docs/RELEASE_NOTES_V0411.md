# GW EnergyPilot v0.41.1 Beta

v0.41.1 is a focused frontend hotfix for the **Optimize now** action introduced by the v0.41 stable-DOM release.

## Fixed

- Pressing **Optimize now** no longer ends the completed Home Assistant button service with a complete EnergyPilot dashboard render.
- The touched Optimize button remains the same DOM node for the full optimization/publish transaction.
- The Home Assistant/browser scroll container remains connected and scrollable while and after the action completes.
- Optimize busy/idle text, disabled state, `aria-busy`, orchestrator status, last-success details and errors are patched in place from current Home Assistant state.

## Root cause

The active v0.41 telemetry path correctly avoided full dashboard renders, but the Optimize button was still inherited from the historical v0.10 frontend layer. Its async click handler explicitly called `panel._queueRender()` after the button service returned. That one action-specific render detached the button during the same interaction lifecycle and could restart the Safari/WebKit blinking and scrolling failure that v0.41 otherwise removed.

v0.41.1 replaces only that inherited listener. The backend `button.gw_energypilot_optimize_now` entity and the complete existing orchestrator transaction remain unchanged.

## Validation

The browser regression presses the real dashboard Optimize control while the page is scrolled and runs it on:

| Profile | Engine | Viewport / input |
|---|---|---|
| Desktop | Chromium | 1440 × 900, mouse/keyboard |
| iPad | WebKit | 834 × 1112, mobile + touch |
| iPhone | WebKit | 390 × 844, mobile + touch |

Each profile verifies:

- exactly one Optimize service execution;
- zero complete dashboard renders;
- stable `main`, Optimize, Dashboard layout, Automatic Control and Battery Strategy DOM identities;
- no scroll-position jump;
- working scrolling after optimization;
- targeted Battery Plan refresh to the new plan revision;
- the Optimize control returns to its idle state;
- no JavaScript/page errors or unknown WebSocket calls.

The existing v0.41 full browser matrix, Python/Node Quality suite, repository validator, frontend architecture audit, HACS validation and Hassfest remain required gates. The hotfix is eligible for merge only after those gates pass on the exact release-head commit.

## Safety and compatibility

This hotfix is frontend-only. It does not change:

- GoodWe register definitions or Modbus blocks;
- EMS modes, setpoints or write ordering;
- Automatic Control decisions;
- the EMHASS solve, publish or persistent-plan transaction;
- entity IDs or unique IDs;
- configuration entries, migrations or stored runtime data.
