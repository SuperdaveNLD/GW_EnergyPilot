# GW EnergyPilot v0.38 frontend ownership

v0.38 replaces the active dashboard-control stabilization approach used by v0.37. This document records the frontend ownership rules so the fix does not exist only in issue/chat history.

## Active module chain

The v0.38 panel entrypoint is:

```text
gw-energy-pilot-v038.js
    -> gw-energy-pilot-v034.js
        -> existing pre-v0.35 dashboard chain
```

The following historical modules remain in the repository for release history, but are deliberately **not imported by a fresh v0.38 session**:

```text
gw-energy-pilot-v035.js
gw-energy-pilot-v036-customer-controller.js
gw-energy-pilot-v0362-scroll-stability.js
gw-energy-pilot-v0363-control-stability.js
gw-energy-pilot-v037.js
```

This is intentional. v0.38 consolidates only the post-v0.34 behavior that is still required instead of stacking another behavioral monkey patch over v0.37.

## Button/control identity

Interactive behavior must never depend on visible or translated text.

Battery Strategy buttons use the backend mode key as their identity:

```text
mad_steve
gold_rush
balanced
battery_saver
custom
```

The DOM contract is:

```text
data-ep-v038-profile="<mode_key>"
aria-pressed="true|false"
```

- action dispatch uses `data-ep-v038-profile`;
- selected/highlight state uses `aria-pressed`;
- English/Dutch labels and descriptions are presentation only;
- button order, label length and translated text have no control meaning.

v0.37's `buttonIdentity()` / `normalizedText()` comparison and old-button-node reinsertion are not used by a fresh v0.38 frontend. A compatibility sentinel prevents the historical v0.36.3 wrapper from restoring stale button nodes if v0.38 is loaded into an already-open browser JavaScript realm where v0.37 had previously executed.

## Event handling and render safety

v0.38 does not capture pointers and does not suppress the browser click path.

It explicitly avoids:

```text
setPointerCapture
preventDefault on button presses
stopPropagation on button presses
pointer-active _render blocking
stable old-button-node reinsertion
```

Battery Strategy and Custom SOC actions are delegated from the persistent `shadowRoot`. A rendered button may therefore be replaced by a later legitimate dashboard render without carrying stale per-node listener closures forward.

Relevant Home Assistant state filtering remains: the latest `hass` object is always retained, but unrelated entity changes do not rebuild the complete dashboard. Relevant bursts are batched for 80 ms.

A press sets a short 300 ms **render quiet window** for HASS-triggered renders. This delays only a scheduled telemetry rebuild; it does not block the pointer/click event, service call or explicit action render.

The v0.36.2 mobile scroll-position preservation behavior is consolidated into v0.38 so dropping the old active wrapper chain does not reintroduce phone viewport jumps.

## Canonical live-flow direction

v0.38 gives flow animation one final semantic owner. Each connector receives:

```text
data-ep-v038-flow="to-hub"
data-ep-v038-flow="from-hub"
```

The mapping uses the already-confirmed GW EnergyPilot sign conventions:

| Connector | Runtime condition | Visual direction |
|---|---|---|
| PV | production > 50 W | PV -> hub |
| Grid | GoodWe meter < -50 W (import) | Grid -> hub |
| Grid | GoodWe meter > +50 W (export) | Hub -> Grid |
| House | non-idle load | Hub -> House |
| Battery | power > +50 W (discharge) | Battery -> hub |
| Battery | power < -50 W (charge) | Hub -> Battery |

The v0.38 CSS selects explicit geometry-specific Forward/Reverse keyframes from this semantic attribute and forces `animation-direction: normal`. Older `inbound/outbound`, v0.22 semantic classes and inherited animation-direction rules can no longer reverse the final v0.38 result.

## Scope boundary

v0.38 is a frontend correction only. It does not change:

- GoodWe register definitions or Modbus read blocks;
- EMS mode definitions, setpoint semantics or `47512 -> wait -> 47511` ordering;
- Automatic Control decisions;
- EMHASS optimization, Battery Saver backend policy or config ownership;
- entity IDs, unique IDs, config-entry data or persistent Store keys.
