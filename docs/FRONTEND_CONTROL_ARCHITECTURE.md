# Frontend control architecture

This document records the control inventory found on the canonical
`v1.0.1-beta.4` base (`f7b3d38348cc70fbe521553091564ca2157b1c68`) and the
implemented migration contract for issue #84. It is deliberately about browser
ownership and presentation state. GoodWe modes, setpoints, Home Assistant
entity IDs and backend service/WebSocket contracts remain unchanged.

## Pre-migration inventory

The active entry point is `gw-energy-pilot-v101.js`. It reaches the original
`GWEnergyPilotPanel extends HTMLElement` implementation through the historical
release/import chain documented in `DEVELOPMENT.md`. Normal telemetry is
intercepted by `gw-energy-pilot-v041.js`, but control creation and listeners are
still distributed across older modules.

| Control | Creator / listener owner | Backend route | Confirmed visual state | Pending / error before migration | Replacement and stale-state risk |
| --- | --- | --- | --- | --- | --- |
| Battery Max export, Pause, Max charge, AUTO | `v010` creates each button and installs one captured click closure; `v041` patches selection | `button.press` on `max_export`, `battery_pause`, `max_charge`, `resume_auto` | `automatic_control` plus `control_command` | Disabled text only on the touched DOM node; alert on error | Structural render recreates all four. The closure captures the entity ID. Intermediate split HA publications can temporarily expose ambiguous ownership. |
| Automatic Control | Base `gw-energy-pilot.js` creates `#auto-toggle` and installs the listener | `switch.turn_on` / `switch.turn_off` | `automatic_control` | No authoritative pending state and no visible inline error | Every base structural render replaces the button. The original listener has no duplicate-call guard. |
| Optimize now | `v010` creates it; `v044` clones and replaces that button and installs a second-generation listener | `button.press` on `optimize_now` | Orchestrator attributes and `plan_revision` | `__epV044OptimizePending`; alert on error | `v044` intentionally replaces the inherited node once per structural render. Completion patches the clone, not a component state machine. |
| EMHASS optimization strategy | `v016` creates three buttons and listeners; `v041` patches them | `select.select_option`, legacy `button.press` fallback | `emhass_cost_function` state/attributes | `__epV016CostfunBusy`; alert on error | Structural render recreates the group. The listener captures a strategy definition; availability and confirmed state are read separately. |
| Battery Strategy profiles | `v038-strategy` renders the group and uses one delegated ShadowRoot click listener | `gw_energypilot/battery_saver/set` | Battery Saver API payload | Shared cache with `busy`, `pendingMode`, message and error | Any signature change assigns `wrap.innerHTML`, replacing every profile button. `pendingMode` is also treated as active before backend confirmation. |
| Custom Battery Strategy values | `v038-strategy` delegated submit handler | `gw_energypilot/battery_saver/custom_set` | Battery Saver API payload | Shared profile busy/error state | Form is conditional and replaced by `innerHTML`; draft and backend state are not separate component properties. |
| Minimum/maximum SOC sliders | `v038-strategy` delegated input/change handlers; older equivalents exist in `v011` | `number.set_value` | `emhass_minimum_soc`, `emhass_maximum_soc` | Draft stored on the input dataset; alert on error | Custom form replacement discards node identity and can discard a draft on a signature change. |
| Manual EMS modes 1–12 | `v021` creates buttons and captured listeners; `v041` patches live read-back | optional `number.set_value`, then `select.select_option` on `manual_mode` | `ems_mode` and `automatic_control` | `__epV021ManualBusy` and a panel message | Structural render recreates the pad. The slider listeners capture the max/step model from creation time. Manual read-back remains visibly active while Automatic Control owns the inverter. |
| Manual power slider | `v021` input/change listeners | `number.set_value` on `manual_power` | `manual_power` | Panel draft flags plus manual group busy state | Structural render recreates the slider. Telemetry protection is an imperative focus/dirty check. |
| Automatic strategy selector | `v024` creates a select | `gw_energypilot/smart_meter/set` | API payload plus `control_strategy` | Select-local disabled/message state | Recreated by structural renders; it configures controller policy and is not a second EMS actuator. |
| Settings | `settings-v016` creates the header button, tabs, fields and form listeners | `gw_energypilot/settings/get` and `/update` | Settings API payload | Panel loading/saving/draft/message fields | Opening, tab changes, discard and save request complete structural renders. Normal telemetry is deferred while the page is open. |
| Dashboard layout/menu | `v008`, stabilized drag handlers in `v012-stable` | `localStorage` | Stored layout preferences | No asynchronous state | Menu open/close and preference changes request structural renders and recreate the layout button/menu controls. |
| Card close/minimize/maximize | `v031-window-controls` | `localStorage` | Stored card window state | None | Buttons are recreated with cards. The window bar has an active `pointerdown` propagation handler. |
| Connectivity popover | `v041` | No write; telemetry entity only | `connectivity_status` | Checking presentation | Stable for normal telemetry; a genuine structural render recreates it. |
| Grid, Battery/Price, Plan and History modal controls | `v013`, `v026-battery-price`, `v027-battery-plan-core`, `v051-history` | Recorder and EnergyPilot read APIs where applicable | Local modal/view state plus fetched data | Module-specific loading/error fields | Modal controls exist only while their modal exists. Their owning card can be replaced on a deliberate plan/card refresh. |
| Diagnostics, debug and copy/refresh controls | `v011-support`, `v018`, `v025`, `v031`, `v041` | Diagnostics/debug/optimization-log WebSocket APIs and Clipboard | API payload or local completion text | Module-specific busy/error fields | Recreated with diagnostics/settings structure. They do not write EMS control state. |

## Pre-migration event route

The pre-migration operational route was:

```text
native event
  -> listener installed by the historical creator (or delegated ShadowRoot listener)
  -> Home Assistant callService/callWS
  -> local panel field or direct DOM mutation
  -> Home Assistant state/API payload
  -> v0.41 imperative live patch, targeted strategy innerHTML, or structural render
```

Normal v0.41 telemetry usually preserves nodes, but this is not an ownership
boundary: the controls are still children of dashboard cards, different modules
can mutate the same nodes, and genuine host/context renders reconstruct them.
That leaves no single state machine capable of proving one activation, one
request and one confirmed visual result.

## Implemented boundary

The migration introduces one permanent Lit-owned boundary inside `main` and
outside the set of legacy children that structural rendering may replace:

```text
gw-energypilot-panel
├── ep-control-surface
│   ├── ep-battery-actions
│   ├── ep-automatic-control
│   ├── ep-emhass-strategy
│   ├── ep-battery-strategy
│   ├── ep-optimize-action
│   └── ep-manual-ems-controls
└── legacy dashboard content (incrementally migrated)
```

The panel passes only immutable control models and a narrow action gateway to
the control surface; it does not pass the complete `hass` object. Each child
derives `disabled`, `aria-busy`, `aria-pressed`, copy and visible selection from
the same local state machine plus confirmed backend model. The fixed transition
contract is `idle -> pending -> acknowledged | error`.

The permanent surface is outside replaceable dashboard content. Structural
dashboard reconstruction must retain the exact surface node, while telemetry,
plan/history refresh, host state publication and real `narrow` changes update
properties only. Historical creators must not install parallel controls or
listeners once the boundary is active.

The implemented event route is:

```text
native button click or native input change
  -> one Lit child state machine enters pending
  -> narrow ControlGateway invokes the existing HA service/WebSocket route once
  -> service result and confirmed HA/API model may arrive in either order
  -> both observed: acknowledged; either failure/timeout: visible error
  -> confirmed model alone owns aria-pressed/selected presentation
```

A manual mode activation now invokes only the existing `manual_mode`
`select.select_option` route. The backend select entity already reads the
stored `manual_power` value and applies the established controller command; the
manual power slider remains its own `number.set_value` action. This removes a
frontend-generated two-service activation without changing EMS semantics or
write ownership.

## Hardware evidence boundary

Automated Chromium and Playwright WebKit tests are release gates, not proof of
branded iPhone Safari or the Home Assistant Companion WebView. The control
surface therefore includes a passive ring-buffer trace for pointer/click order,
node identity, connection state, backend-call start/end, HA model publication
and structural renders. `docs/FRONTEND_IPHONE_ACCEPTANCE.md` defines the physical
acceptance run. Until that run passes, status is **software ready, hardware
acceptance open**.
