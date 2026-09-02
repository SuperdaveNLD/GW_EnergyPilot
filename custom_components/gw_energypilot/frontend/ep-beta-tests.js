import {
  LitElement,
  html,
} from "./vendor/lit-3.3.3.js?v=1.2.0-beta.6-chart-touch1";

const METRIC_KEYS = Object.freeze([
  "pointerdown",
  "pointermove",
  "pointerup",
  "pointercancel",
  "click",
  "change",
  "input",
  "actions",
  "native_actions",
  "pointer_actions",
  "fallback_actions",
  "deduped",
]);

const METHOD_DEFINITIONS = Object.freeze([
  Object.freeze({
    key: "method-native-click",
    label: "1 · Schone native click",
    detail: "Alleen click; tellers verversen pas na de klikperiode",
  }),
  Object.freeze({
    key: "method-pointerup-direct",
    label: "2 · Directe pointerup",
    detail: "Handler op de knop; actie na maximaal 12 px beweging",
  }),
  Object.freeze({
    key: "method-pointerup-delegated",
    label: "3 · Gedelegeerde pointerup",
    detail: "Centrale capture-handler; dezelfde bewegingsdrempel",
  }),
  Object.freeze({
    key: "method-click-fallback",
    label: "4 · Click + 120 ms fallback",
    detail: "Native click wint; ontbrekende click wordt na 120 ms hersteld",
  }),
  Object.freeze({
    key: "method-pointerup-dedupe",
    label: "5 · Pointerup + dedupe",
    detail: "Pointerup activeert direct; een latere click wordt genegeerd",
  }),
]);

const CONTROL_DEFINITIONS = Object.freeze([
  Object.freeze({ key: "lit-button", label: "Lit native button", detail: "Declaratieve @click-handler" }),
  Object.freeze({ key: "listener-button", label: "DOM listener button", detail: "Eenmalige addEventListener(click)" }),
  Object.freeze({ key: "icon-button", label: "Icon button", detail: "Compacte 48 × 48 native button" }),
  Object.freeze({ key: "shadow-button", label: "Shadow DOM button", detail: "Button in een geneste custom element ShadowRoot" }),
  Object.freeze({ key: "checkbox-switch", label: "Native checkbox switch", detail: "Directe input change" }),
  Object.freeze({ key: "label-switch", label: "Label-wrapped switch", detail: "Volledige labelrij is het tikdoel" }),
  Object.freeze({ key: "native-select", label: "Native select", detail: "Keuzelijst met change-event" }),
  Object.freeze({ key: "native-range", label: "Native range", detail: "Slider met input- en change-event" }),
]);

const ALL_DEFINITIONS = Object.freeze([...METHOD_DEFINITIONS, ...CONTROL_DEFINITIONS]);
const METHOD_KEYS = new Set(METHOD_DEFINITIONS.map(({ key }) => key));
const DISPLAY_SETTLE_MS = 650;
const CLICK_FALLBACK_MS = 120;
const CLICK_DEDUPE_MS = 700;
const MOVE_THRESHOLD_PX = 12;

const BETA_TESTS_CSS = `
  ep-beta-tests, ep-beta-shadow-button { display:block; min-width:0; }
  ep-beta-tests[hidden] { display:none!important; }
  .ep-beta-tests {
    margin:14px 0 18px; padding:14px; border-radius:18px; color:#e9f8ff;
    border:1px solid rgba(104,202,239,.26);
    background:linear-gradient(145deg,rgba(5,31,56,.98),rgba(4,17,34,.99));
    touch-action:pan-y; overflow:clip;
    font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",sans-serif;
  }
  .ep-beta-tests *, .ep-beta-tests *::before, .ep-beta-tests *::after { box-sizing:border-box; }
  .ep-beta-tests *::before, .ep-beta-tests *::after { pointer-events:none; }
  .ep-beta-tests-head { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
  .ep-beta-tests-kicker { color:#67e6f7; font-size:10px; font-weight:900; letter-spacing:.13em; text-transform:uppercase; }
  .ep-beta-tests h2 { margin:4px 0 0; font-size:19px; }
  .ep-beta-tests-intro { max-width:760px; margin:9px 0 13px; color:#9eb9ca; font-size:12px; line-height:1.55; }
  .ep-beta-tests-safe { margin:0 0 14px; padding:9px 11px; border-radius:11px; color:#9de9c6; background:rgba(18,94,72,.25); border:1px solid rgba(71,222,166,.18); font-size:11px; }
  .ep-beta-tests-method-note { margin:0 0 11px; color:#cae8f2; font-size:11px; line-height:1.5; }
  .ep-beta-tests-method-note strong { color:#70ead0; }
  .ep-beta-tests-methods { margin-bottom:14px; }
  .ep-beta-tests-methods .ep-beta-test-card { border-color:rgba(72,220,184,.24); background:rgba(5,49,56,.52); }
  .ep-beta-tests-legacy { margin-top:12px; border-top:1px solid rgba(104,202,239,.16); }
  .ep-beta-tests-legacy > summary { min-height:48px; display:flex; align-items:center; color:#8eabba; cursor:pointer; touch-action:manipulation; font-size:11px; font-weight:800; }
  .ep-beta-tests-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:11px; touch-action:pan-y; }
  .ep-beta-test-card { min-width:0; padding:11px; border-radius:13px; border:1px solid rgba(84,180,220,.15); background:rgba(4,25,45,.62); }
  .ep-beta-test-card-head { display:flex; align-items:flex-start; justify-content:space-between; gap:8px; min-height:38px; }
  .ep-beta-test-card strong { display:block; color:#e9f9ff; font-size:12px; }
  .ep-beta-test-card small { display:block; margin-top:3px; color:#7894a8; font-size:9px; line-height:1.35; }
  .ep-beta-test-state { flex:0 0 auto; padding:3px 6px; border-radius:999px; color:#8fa8b8; background:rgba(255,255,255,.04); font-size:9px; font-weight:850; }
  .ep-beta-test-state.on { color:#baffdf; background:rgba(25,155,105,.25); }
  .ep-beta-test-control { margin-top:9px; min-height:52px; display:flex; align-items:center; }
  .ep-beta-tests button, ep-beta-shadow-button button {
    appearance:none; min-width:48px; min-height:48px; padding:10px 12px;
    border:1px solid rgba(79,188,226,.30); border-radius:11px;
    background:rgba(8,44,70,.86); color:#d4eff8; font-family:inherit;
    font-size:11px; font-weight:800; line-height:1.2;
    cursor:pointer; touch-action:manipulation; -webkit-tap-highlight-color:rgba(62,228,205,.22);
  }
  .ep-beta-tests button:active, ep-beta-shadow-button button:active { background:rgba(21,91,107,.96); border-color:#48e2ca; }
  .ep-beta-tests button:focus-visible, ep-beta-shadow-button button:focus-visible { outline:3px solid #72eaff; outline-offset:3px; }
  .ep-beta-test-wide { width:100%; }
  .ep-beta-test-icon { width:48px; padding:0!important; font-size:21px!important; }
  .ep-beta-tests button[aria-pressed="true"], ep-beta-shadow-button button[aria-pressed="true"] { color:#edfff7; border-color:#42dfaf; background:rgba(12,102,82,.78); }
  .ep-beta-switch-row { width:100%; min-height:48px; display:flex; align-items:center; justify-content:space-between; gap:12px; padding:5px 2px; touch-action:manipulation; cursor:pointer; }
  .ep-beta-switch-row input[type="checkbox"] { width:28px; height:28px; flex:0 0 28px; accent-color:#27dba1; touch-action:manipulation; }
  .ep-beta-test-card select { width:100%; height:48px; min-height:48px; padding:8px 10px; border:1px solid rgba(79,188,226,.30); border-radius:11px; background:#082b45; color:#e3f6fc; font-family:inherit; font-size:12px; font-weight:700; touch-action:manipulation; }
  .ep-beta-test-card input[type="range"] { width:100%; min-height:48px; accent-color:#2ddaaa; touch-action:pan-y; }
  .ep-beta-metrics { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:4px; margin-top:9px; }
  .ep-beta-metric { min-width:0; padding:5px 3px; border-radius:7px; background:rgba(255,255,255,.035); text-align:center; }
  .ep-beta-metric span { display:block; overflow:hidden; color:#708b9e; font-size:7px; text-overflow:ellipsis; white-space:nowrap; }
  .ep-beta-metric b { display:block; margin-top:2px; color:#d8eef6; font-size:11px; }
  .ep-beta-test-actions { display:flex; flex-wrap:wrap; gap:8px; margin-top:13px; }
  .ep-beta-test-actions button { min-height:44px; }
  .ep-beta-events { margin-top:13px; }
  .ep-beta-events summary { min-height:44px; display:flex; align-items:center; color:#9db8c8; cursor:pointer; touch-action:manipulation; }
  .ep-beta-events pre { max-height:220px; overflow:auto; margin:0; padding:10px; border-radius:10px; color:#a9c7d5; background:#031525; font:9px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace; white-space:pre-wrap; overflow-wrap:anywhere; }
  .ep-beta-tests-close { flex:0 0 48px; width:48px; padding:0!important; font-size:22px!important; }
  @media(max-width:720px) { .ep-beta-tests-grid { grid-template-columns:1fr; } }
  @media(max-width:420px) { .ep-beta-tests { margin:10px 0 14px; padding:10px; } .ep-beta-metrics { grid-template-columns:repeat(4,minmax(0,1fr)); } }
`;

function emptyMetric() {
  return Object.fromEntries(METRIC_KEYS.map((key) => [key, 0]));
}

function emptyMetrics() {
  return Object.fromEntries(ALL_DEFINITIONS.map(({ key }) => [key, emptyMetric()]));
}

function initialValues() {
  return {
    "method-native-click": false,
    "method-pointerup-direct": false,
    "method-pointerup-delegated": false,
    "method-click-fallback": false,
    "method-pointerup-dedupe": false,
    "lit-button": false,
    "listener-button": false,
    "icon-button": false,
    "shadow-button": false,
    "checkbox-switch": false,
    "label-switch": false,
    "native-select": "a",
    "native-range": 50,
  };
}

function eventControl(event) {
  for (const node of event.composedPath?.() || []) {
    if (node instanceof HTMLElement && node.dataset?.betaControl) {
      return node.dataset.betaControl;
    }
  }
  return null;
}

class EpBetaShadowButton extends LitElement {
  static properties = {
    active: { type: Boolean },
  };

  constructor() {
    super();
    this.active = false;
  }

  _activate() {
    this.dispatchEvent(new CustomEvent("beta-toggle", {
      bubbles: true,
      composed: true,
    }));
  }

  render() {
    return html`
      <style>
        :host { display:block; width:100%; }
        button {
          appearance:none; width:100%; min-width:48px; min-height:48px; padding:10px 12px;
          border:1px solid rgba(79,188,226,.30); border-radius:11px;
          background:rgba(8,44,70,.86); color:#d4eff8; font:800 11px/1.2 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",sans-serif;
          cursor:pointer; touch-action:manipulation; -webkit-tap-highlight-color:rgba(62,228,205,.22);
        }
        button:active { background:rgba(21,91,107,.96); border-color:#48e2ca; }
        button:focus-visible { outline:3px solid #72eaff; outline-offset:3px; }
        button[aria-pressed="true"] { color:#edfff7; border-color:#42dfaf; background:rgba(12,102,82,.78); }
      </style>
      <button type="button" data-beta-control="shadow-button"
        aria-pressed=${this.active ? "true" : "false"}
        @click=${this._activate}>
        Shadow toggle · ${this.active ? "AAN" : "UIT"}
      </button>`;
  }
}

class EpBetaTests extends LitElement {
  static properties = {
    closeAction: { attribute: false },
    values: { state: true },
    metrics: { state: true },
    recent: { state: true },
  };

  constructor() {
    super();
    this.closeAction = null;
    this.values = initialValues();
    this.metrics = emptyMetrics();
    this.recent = [];
    this._valuesBuffer = initialValues();
    this._metricsBuffer = emptyMetrics();
    this._recentBuffer = [];
    this._displayTimer = null;
    this._fallbackSequence = 0;
    this._pendingFallbacks = new Map();
    this._pointerStarts = new Map();
    this._lastMethodActions = new Map();
    this._plainListenerInstalled = false;
    this._recordEvent = (event) => this._record(event);
  }

  createRenderRoot() {
    return this;
  }

  firstUpdated() {
    for (const eventName of [
      "pointerdown",
      "pointermove",
      "pointerup",
      "pointercancel",
      "click",
      "change",
      "input",
    ]) {
      this.addEventListener(eventName, this._recordEvent, {
        capture: true,
        passive: true,
      });
    }
    this._installPlainListener();
    globalThis.__epBetaTests = {
      snapshot: () => this.snapshot(),
      json: () => JSON.stringify(this.snapshot(), null, 2),
      reset: () => this.reset(),
    };
  }

  updated() {
    this._installPlainListener();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    clearTimeout(this._displayTimer);
    for (const pending of this._pendingFallbacks.values()) clearTimeout(pending.timer);
    this._pendingFallbacks.clear();
  }

  _installPlainListener() {
    if (this._plainListenerInstalled) return;
    const button = this.querySelector('[data-beta-control="listener-button"]');
    if (!(button instanceof HTMLButtonElement)) return;
    button.addEventListener("click", () => this._toggle("listener-button"));
    this._plainListenerInstalled = true;
  }

  _bumpMetric(key, metric) {
    if (!this._metricsBuffer[key] || !METRIC_KEYS.includes(metric)) return;
    this._metricsBuffer[key][metric] += 1;
  }

  _pointerToken(key, event) {
    return `${key}:${event.pointerId}`;
  }

  _trackMethodPointer(key, event) {
    const token = this._pointerToken(key, event);
    if (event.type === "pointerdown") {
      this._pointerStarts.set(token, {
        x: Number(event.clientX) || 0,
        y: Number(event.clientY) || 0,
        moved: false,
        primary: event.isPrimary !== false,
      });
      return;
    }
    const state = this._pointerStarts.get(token);
    if (!state) return;
    if (event.type === "pointermove") {
      const distance = Math.hypot(
        (Number(event.clientX) || 0) - state.x,
        (Number(event.clientY) || 0) - state.y,
      );
      if (distance > MOVE_THRESHOLD_PX) state.moved = true;
    } else if (event.type === "pointercancel") {
      this._pointerStarts.delete(token);
    }
  }

  _pointerActivationAllowed(key, event) {
    const state = this._pointerStarts.get(this._pointerToken(key, event));
    return Boolean(state && state.primary && !state.moved);
  }

  _finishPointer(key, event) {
    this._pointerStarts.delete(this._pointerToken(key, event));
  }

  _scheduleDisplayFlush() {
    clearTimeout(this._displayTimer);
    this._displayTimer = setTimeout(() => this._flushDisplay(), DISPLAY_SETTLE_MS);
  }

  _flushDisplay() {
    this._displayTimer = null;
    this.values = { ...this._valuesBuffer };
    this.metrics = Object.fromEntries(
      Object.entries(this._metricsBuffer).map(([key, metric]) => [key, { ...metric }]),
    );
    this.recent = [...this._recentBuffer];
  }

  _recordRow(key, type, detail = "-") {
    const row = `${new Date().toISOString().slice(11, 23)} · ${key} · ${type} · ${detail} · connected=${this.isConnected}`;
    this._recentBuffer = [row, ...this._recentBuffer].slice(0, 36);
  }

  _record(event) {
    const control = eventControl(event);
    if (!control || !this._metricsBuffer[control] || !METRIC_KEYS.includes(event.type)) return;
    this._bumpMetric(control, event.type);
    if (METHOD_KEYS.has(control)) this._trackMethodPointer(control, event);
    const pointer = "pointerId" in event
      ? `${event.pointerType || "pointer"}#${event.pointerId}`
      : "-";
    const row = `${new Date().toISOString().slice(11, 23)} · ${control} · ${event.type} · ${pointer} · trusted=${event.isTrusted} · connected=${this.isConnected}`;
    this._recentBuffer = [row, ...this._recentBuffer].slice(0, 36);
    if (control === "method-pointerup-delegated" && event.type === "pointerup") {
      this._activatePointerMethod(control, event, "pointer");
    }
    if (METHOD_KEYS.has(control) && ["pointerup", "pointercancel"].includes(event.type)) {
      setTimeout(() => this._finishPointer(control, event), 0);
    }
    this._scheduleDisplayFlush();
  }

  _action(key, value, source = "native") {
    this._valuesBuffer[key] = value;
    this._bumpMetric(key, "actions");
    if (source === "native") this._bumpMetric(key, "native_actions");
    if (source === "pointer") this._bumpMetric(key, "pointer_actions");
    if (source === "fallback") this._bumpMetric(key, "fallback_actions");
    this._scheduleDisplayFlush();
  }

  _toggle(key) {
    this._action(key, !this._valuesBuffer[key]);
  }

  _setBufferedValue(key, value) {
    this._valuesBuffer[key] = value;
    this._scheduleDisplayFlush();
  }

  _commitMethodAction(key, source) {
    this._lastMethodActions.set(key, performance.now());
    this._action(key, !this._valuesBuffer[key], source);
    this._recordRow(key, "method-action", source);
  }

  _activatePointerMethod(key, event, source = "pointer") {
    if (!this._pointerActivationAllowed(key, event)) return;
    this._finishPointer(key, event);
    this._commitMethodAction(key, source);
  }

  _nativeMethodClick(key) {
    this._commitMethodAction(key, "native");
  }

  _scheduleClickFallback(key, event) {
    if (!this._pointerActivationAllowed(key, event)) return;
    this._finishPointer(key, event);
    const id = `${key}:${++this._fallbackSequence}`;
    const timer = setTimeout(() => {
      this._pendingFallbacks.delete(id);
      this._commitMethodAction(key, "fallback");
    }, CLICK_FALLBACK_MS);
    this._pendingFallbacks.set(id, { id, key, sequence: this._fallbackSequence, timer });
  }

  _latestPendingFallback(key) {
    let latest = null;
    for (const pending of this._pendingFallbacks.values()) {
      if (pending.key === key && (!latest || pending.sequence > latest.sequence)) latest = pending;
    }
    return latest;
  }

  _recentMethodAction(key) {
    const at = this._lastMethodActions.get(key);
    return Number.isFinite(at) && performance.now() - at <= CLICK_DEDUPE_MS;
  }

  _markDeduped(key, reason) {
    this._bumpMetric(key, "deduped");
    this._recordRow(key, "deduped", reason);
    this._scheduleDisplayFlush();
  }

  _clickWithFallback(key) {
    const pending = this._latestPendingFallback(key);
    if (pending) {
      clearTimeout(pending.timer);
      this._pendingFallbacks.delete(pending.id);
      this._commitMethodAction(key, "native");
    } else if (this._recentMethodAction(key)) {
      this._markDeduped(key, "late-click");
    } else {
      this._commitMethodAction(key, "native");
    }
  }

  _clickAfterPointerup(key) {
    if (this._recentMethodAction(key)) {
      this._markDeduped(key, "pointerup-click");
    } else {
      this._commitMethodAction(key, "native");
    }
  }

  reset() {
    clearTimeout(this._displayTimer);
    for (const pending of this._pendingFallbacks.values()) clearTimeout(pending.timer);
    this._pendingFallbacks.clear();
    this._pointerStarts.clear();
    this._lastMethodActions.clear();
    this._valuesBuffer = initialValues();
    this._metricsBuffer = emptyMetrics();
    this._recentBuffer = [];
    this._flushDisplay();
  }

  snapshot() {
    const collect = (definitions) => Object.fromEntries(definitions.map((definition) => {
      const node = this.querySelector(`[data-beta-control="${definition.key}"]`)
        || this.querySelector("ep-beta-shadow-button")?.shadowRoot?.querySelector("button");
      return [definition.key, {
        value: this._valuesBuffer[definition.key],
        metrics: { ...this._metricsBuffer[definition.key] },
        connected: Boolean(node?.isConnected),
      }];
    }));
    return {
      generated_at: new Date().toISOString(),
      user_agent: navigator.userAgent,
      viewport: { width: innerWidth, height: innerHeight, device_pixel_ratio: devicePixelRatio },
      no_home_assistant_calls: true,
      production_touch_fallback: globalThis.__epTouchClickFallback?.snapshot?.() || null,
      measurement: {
        display_deferred_ms: DISPLAY_SETTLE_MS,
        move_threshold_px: MOVE_THRESHOLD_PX,
        click_fallback_ms: CLICK_FALLBACK_MS,
        click_dedupe_ms: CLICK_DEDUPE_MS,
      },
      methods: collect(METHOD_DEFINITIONS),
      controls: collect(CONTROL_DEFINITIONS),
      recent: [...this._recentBuffer],
    };
  }

  _metrics(key) {
    const metric = this.metrics[key] || emptyMetric();
    return html`
      <div class="ep-beta-metrics" data-beta-metrics=${key}>
        ${METRIC_KEYS.map((name) => html`
          <div class="ep-beta-metric"><span>${name}</span><b>${metric[name]}</b></div>
        `)}
      </div>`;
  }

  _state(key) {
    const value = this.values[key];
    const on = typeof value === "boolean" ? value : true;
    return html`<span class=${`ep-beta-test-state${on ? " on" : ""}`}>${String(value).toUpperCase()}</span>`;
  }

  _card(definition, controlTemplate) {
    return html`
      <article class="ep-beta-test-card" data-beta-card=${definition.key}>
        <div class="ep-beta-test-card-head">
          <div><strong>${definition.label}</strong><small>${definition.detail}</small></div>
          ${this._state(definition.key)}
        </div>
        <div class="ep-beta-test-control">${controlTemplate}</div>
        ${this._metrics(definition.key)}
      </article>`;
  }

  render() {
    const definition = Object.fromEntries(CONTROL_DEFINITIONS.map((item) => [item.key, item]));
    return html`
      <style>${BETA_TESTS_CSS}</style>
      <section class="ep-beta-tests" data-ep-beta-tests="1" aria-label="Beta tests">
        <div class="ep-beta-tests-head">
          <div><div class="ep-beta-tests-kicker">Diagnostiek · lokaal</div><h2>Beta tests</h2></div>
          <button type="button" class="ep-beta-tests-close" aria-label="Sluit Beta tests"
            @click=${() => this.closeAction?.()}>×</button>
        </div>
        <p class="ep-beta-tests-intro">
          Tik de vijf genummerde knoppen elk vijf keer en wacht daarna één seconde. De tellers blijven
          tijdens een tik bewust stil, zodat de meting zelf geen native click kan verstoren.
        </p>
        <p class="ep-beta-tests-safe"><strong>Veilig:</strong> geen Home Assistant-service, WebSocket, GoodWe-write of EMHASS-actie.</p>
        <p class="ep-beta-tests-method-note">
          <strong>Doel:</strong> vergelijk native click, directe/gedelegeerde pointerup, een vertraagde
          click-fallback en onmiddellijke pointerup met klik-deduplicatie. Een verticale veeg mag nooit
          als actie meetellen.
        </p>
        <div class="ep-beta-tests-grid ep-beta-tests-methods">
          ${this._card(METHOD_DEFINITIONS[0], html`
            <button type="button" class="ep-beta-test-wide" data-beta-control="method-native-click"
              aria-pressed=${this.values["method-native-click"] ? "true" : "false"}
              @click=${() => this._nativeMethodClick("method-native-click")}>
              Native click · ${this.values["method-native-click"] ? "AAN" : "UIT"}
            </button>`)}
          ${this._card(METHOD_DEFINITIONS[1], html`
            <button type="button" class="ep-beta-test-wide" data-beta-control="method-pointerup-direct"
              aria-pressed=${this.values["method-pointerup-direct"] ? "true" : "false"}
              @pointerup=${(event) => this._activatePointerMethod("method-pointerup-direct", event)}>
              Direct pointerup · ${this.values["method-pointerup-direct"] ? "AAN" : "UIT"}
            </button>`)}
          ${this._card(METHOD_DEFINITIONS[2], html`
            <button type="button" class="ep-beta-test-wide" data-beta-control="method-pointerup-delegated"
              aria-pressed=${this.values["method-pointerup-delegated"] ? "true" : "false"}>
              Delegated pointerup · ${this.values["method-pointerup-delegated"] ? "AAN" : "UIT"}
            </button>`)}
          ${this._card(METHOD_DEFINITIONS[3], html`
            <button type="button" class="ep-beta-test-wide" data-beta-control="method-click-fallback"
              aria-pressed=${this.values["method-click-fallback"] ? "true" : "false"}
              @pointerup=${(event) => this._scheduleClickFallback("method-click-fallback", event)}
              @click=${() => this._clickWithFallback("method-click-fallback")}>
              Click + fallback · ${this.values["method-click-fallback"] ? "AAN" : "UIT"}
            </button>`)}
          ${this._card(METHOD_DEFINITIONS[4], html`
            <button type="button" class="ep-beta-test-wide" data-beta-control="method-pointerup-dedupe"
              aria-pressed=${this.values["method-pointerup-dedupe"] ? "true" : "false"}
              @pointerup=${(event) => this._activatePointerMethod("method-pointerup-dedupe", event)}
              @click=${() => this._clickAfterPointerup("method-pointerup-dedupe")}>
              Pointerup + dedupe · ${this.values["method-pointerup-dedupe"] ? "AAN" : "UIT"}
            </button>`)}
        </div>
        <details class="ep-beta-tests-legacy">
          <summary>Oude acht controletests tonen</summary>
          <div class="ep-beta-tests-grid">
          ${this._card(definition["lit-button"], html`
            <button type="button" class="ep-beta-test-wide" data-beta-control="lit-button"
              aria-pressed=${this.values["lit-button"] ? "true" : "false"}
              @click=${() => this._toggle("lit-button")}>
              Lit toggle · ${this.values["lit-button"] ? "AAN" : "UIT"}
            </button>`)}
          ${this._card(definition["listener-button"], html`
            <button type="button" class="ep-beta-test-wide" data-beta-control="listener-button"
              aria-pressed=${this.values["listener-button"] ? "true" : "false"}>
              Listener toggle · ${this.values["listener-button"] ? "AAN" : "UIT"}
            </button>`)}
          ${this._card(definition["icon-button"], html`
            <button type="button" class="ep-beta-test-icon" data-beta-control="icon-button"
              aria-label="Test icon toggle" aria-pressed=${this.values["icon-button"] ? "true" : "false"}
              @click=${() => this._toggle("icon-button")}>⏻</button>`)}
          ${this._card(definition["shadow-button"], html`
            <ep-beta-shadow-button .active=${this.values["shadow-button"]}
              @beta-toggle=${() => this._toggle("shadow-button")}></ep-beta-shadow-button>`)}
          ${this._card(definition["checkbox-switch"], html`
            <label class="ep-beta-switch-row"><span>Directe checkbox</span>
              <input type="checkbox" role="switch" data-beta-control="checkbox-switch"
                .checked=${this.values["checkbox-switch"]}
                @change=${(event) => this._action("checkbox-switch", event.currentTarget.checked)}>
            </label>`)}
          ${this._card(definition["label-switch"], html`
            <label class="ep-beta-switch-row" data-beta-control="label-switch"><span>Tik de hele rij</span>
              <input type="checkbox" role="switch" data-beta-control="label-switch"
                .checked=${this.values["label-switch"]}
                @change=${(event) => this._action("label-switch", event.currentTarget.checked)}>
            </label>`)}
          ${this._card(definition["native-select"], html`
            <select data-beta-control="native-select" .value=${this.values["native-select"]}
              @change=${(event) => this._action("native-select", event.currentTarget.value)}>
              <option value="a">Keuze A</option><option value="b">Keuze B</option><option value="c">Keuze C</option>
            </select>`)}
          ${this._card(definition["native-range"], html`
            <input type="range" min="0" max="100" step="1" data-beta-control="native-range"
              .value=${String(this.values["native-range"])}
              @input=${(event) => this._setBufferedValue("native-range", Number(event.currentTarget.value))}
              @change=${(event) => this._action("native-range", Number(event.currentTarget.value))}>`)}
          </div>
        </details>
        <div class="ep-beta-test-actions">
          <button type="button" @click=${() => this.reset()}>Reset tellers</button>
        </div>
        <details class="ep-beta-events">
          <summary>Laatste events en export</summary>
          <pre>${JSON.stringify(this.snapshot(), null, 2)}</pre>
        </details>
      </section>`;
  }
}

function ensureMenuStyle(root) {
  if (root.querySelector("#ep-beta-tests-menu-style")) return;
  const style = document.createElement("style");
  style.id = "ep-beta-tests-menu-style";
  style.textContent = `
    .ep-beta-tests-menu {
      width:100%; min-height:48px; margin:9px 0 2px; padding:10px 12px; text-align:left;
      border:1px solid rgba(72,220,184,.25); border-radius:11px;
      background:rgba(14,83,74,.30); color:#d8fff1; cursor:pointer; touch-action:manipulation;
    }
    .ep-beta-tests-menu strong, .ep-beta-tests-menu small { display:block; pointer-events:none; }
    .ep-beta-tests-menu small { margin-top:3px; color:#83b7a7; font-size:9px; }
    .ep-beta-tests-menu:focus-visible { outline:3px solid #72eaff; outline-offset:3px; }
  `;
  root.appendChild(style);
}

function syncBetaTestsView(panel, root) {
  const main = root.querySelector("main");
  const tests = panel.__epPermanentBetaTests;
  if (!(main instanceof HTMLElement) || !(tests instanceof HTMLElement)) return;
  const open = panel.__epBetaTestsOpen === true;
  tests.hidden = !open;
  main.toggleAttribute("data-ep-beta-tests-open", open);
  for (const child of [...main.children]) {
    if (child === tests || child.classList.contains("topbar")) continue;
    if (open) {
      if (!child.hidden) child.dataset.epBetaTestsWasVisible = "1";
      child.hidden = true;
    } else if (child.dataset.epBetaTestsWasVisible === "1") {
      delete child.dataset.epBetaTestsWasVisible;
      child.hidden = false;
    }
  }
}

function closeBetaTests(panel, root) {
  panel.__epBetaTestsOpen = false;
  syncBetaTestsView(panel, root);
}

function installBetaTestsMenuEntry(panel, root) {
  const menu = root.querySelector(".ep-layout-menu");
  if (!menu || menu.querySelector(".ep-beta-tests-menu")) return;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "ep-beta-tests-menu";
  const title = document.createElement("strong");
  title.textContent = "Beta tests";
  const detail = document.createElement("small");
  detail.textContent = "Lokale tik-, click- en switchdiagnostiek";
  button.append(title, detail);
  button.addEventListener("click", () => {
    panel.__epV008MenuOpen = false;
    panel.__epBetaTestsOpen = true;
    menu.remove();
    syncBetaTestsView(panel, root);
  });
  const reset = menu.querySelector(".ep-menu-reset");
  if (reset) reset.before(button);
  else menu.appendChild(button);
}

export function mountEnergyPilotBetaTests(panel, root = panel?.shadowRoot) {
  if (!panel || !root) return null;
  ensureMenuStyle(root);
  let tests = panel.__epPermanentBetaTests;
  if (!(tests instanceof HTMLElement)) {
    tests = document.createElement("ep-beta-tests");
    panel.__epPermanentBetaTests = tests;
  }
  tests.closeAction = () => closeBetaTests(panel, root);
  if (!tests.isConnected) {
    const main = root.querySelector("main");
    const topbar = main?.querySelector(":scope > .topbar");
    if (topbar) topbar.after(tests);
    else main?.prepend(tests);
  }
  installBetaTestsMenuEntry(panel, root);
  syncBetaTestsView(panel, root);
  return tests;
}

if (!customElements.get("ep-beta-shadow-button")) {
  customElements.define("ep-beta-shadow-button", EpBetaShadowButton);
}
if (!customElements.get("ep-beta-tests")) {
  customElements.define("ep-beta-tests", EpBetaTests);
}
