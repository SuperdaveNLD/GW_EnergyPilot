import "./gw-energy-pilot-v034.js?v=0.38-base1";

const VERSION = "0.38";
const PANEL_NAME = "gw-energypilot-panel";
const CUSTOM_MODE = "custom";
const HASS_RENDER_BATCH_MS = 80;
const PRESS_RENDER_QUIET_MS = 300;
const MOBILE_SCROLL_BREAKPOINT_PX = 720;
const INTERACTIVE_SELECTOR =
  'button, input, select, textarea, a[href], [role="button"], [tabindex]';
const LEGACY_EXTERNAL_ENTITIES = [
  "sensor.p_batt_forecast",
  "sensor.optim_status",
  "sensor.soc_batt_forecast",
  "sensor.p_load_forecast",
  "sensor.p_pv_forecast",
];
const LEGACY_EXTERNAL_SUFFIXES = [
  ".p_batt_forecast",
  "_p_batt_forecast",
  ".optim_status",
  "_optim_status",
  ".soc_batt_forecast",
  "_soc_batt_forecast",
  ".p_load_forecast",
  "_p_load_forecast",
  ".p_pv_forecast",
  "_p_pv_forecast",
];

const TEXT = {
  en: {
    kicker: "CHARGING STRATEGY",
    title: "Battery strategy",
    description:
      "Choose how EnergyPilot should value battery use. A profile change updates EMHASS and immediately builds a fresh plan.",
    custom: "Custom",
    customDescription:
      "Keep the current EMHASS battery values and tune the main limits manually.",
    active: "ACTIVE",
    applying: "Applying profile and optimizing…",
    applied: "Profile applied · fresh plan published.",
    customTitle: "Custom battery settings",
    customNote:
      "SOC sliders use the existing Home Assistant entities. Minimum SOC remains synchronized with the GoodWe on-grid battery floor; each completed change triggers a fresh optimization. Advanced EMHASS battery penalties are shown below for transparency and remain managed in EMHASS.",
    minimum: "Minimum SOC",
    maximum: "Maximum SOC",
    deficit: "Low-SOC cost",
    surplus: "High-SOC cost",
    stress: "Power stress",
    chargeWeight: "Charge cost",
    dischargeWeight: "Discharge cost",
    diagnostics: "Low-level controller command is available in Diagnostics.",
    socUpdateFailed: "Battery SOC update failed",
    profiles: {
      mad_steve: {
        label: "Mad-Steve",
        description:
          "Maximum economic freedom up to 100% SOC with anti-churn protection and no extra SOC or power-stress penalty.",
      },
      gold_rush: {
        label: "Gold Rush",
        description:
          "Profit first with a 96% hard maximum, anti-churn protection and light power stress.",
      },
      balanced: {
        label: "Balanced",
        description:
          "Balances trading value and battery preservation with a 95% hard maximum and moderate power stress.",
      },
      battery_saver: {
        label: "Battery Saver",
        description:
          "Uses a 90% hard maximum and the strongest low-SOC and high-power preservation penalties.",
      },
    },
  },
  nl: {
    kicker: "LAADSTRATEGIE",
    title: "Batterijstrategie",
    description:
      "Kies hoe EnergyPilot batterijgebruik moet waarderen. Een profielwijziging past EMHASS aan en bouwt direct een nieuw plan.",
    custom: "Custom",
    customDescription:
      "Behoud de huidige EMHASS-batterijwaarden en stel de belangrijkste limieten handmatig af.",
    active: "ACTIEF",
    applying: "Profiel toepassen en optimaliseren…",
    applied: "Profiel toegepast · nieuw plan gepubliceerd.",
    customTitle: "Custom batterijinstellingen",
    customNote:
      "De SOC-sliders gebruiken de bestaande Home Assistant-entiteiten. Minimum SOC blijft gekoppeld aan de GoodWe on-grid ondergrens; iedere afgeronde wijziging start een nieuwe optimalisatie. De overige EMHASS-batterijkosten staan hieronder ter controle en blijven in EMHASS beheerd.",
    minimum: "Minimum SOC",
    maximum: "Maximum SOC",
    deficit: "Kosten lage SOC",
    surplus: "Kosten hoge SOC",
    stress: "Vermogensstress",
    chargeWeight: "Laadkosten",
    dischargeWeight: "Ontlaadkosten",
    diagnostics: "Het technische controllercommando staat in Diagnostiek.",
    socUpdateFailed: "Bijwerken van batterij-SOC mislukt",
    profiles: {
      mad_steve: {
        label: "Mad-Steve",
        description:
          "Maximale economische vrijheid tot 100% SOC, met anti-churn bescherming en zonder extra SOC- of vermogensstraf.",
      },
      gold_rush: {
        label: "Gold Rush",
        description:
          "Winst eerst, met 96% harde bovengrens, anti-churn bescherming en lichte vermogensstress.",
      },
      balanced: {
        label: "Balanced",
        description:
          "Balanceert handelswaarde en batterijbehoud met 95% harde bovengrens en gematigde vermogensstress.",
      },
      battery_saver: {
        label: "Battery Saver",
        description:
          "Gebruikt een 90% harde bovengrens en de sterkste bescherming tegen lage SOC en hoog batterijvermogen.",
      },
    },
  },
};

function language(panel) {
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function copy(panel) {
  return TEXT[language(panel)];
}

function eventElement(event, selector) {
  for (const node of event.composedPath?.() || []) {
    if (node instanceof Element && node.matches(selector)) return node;
  }
  return null;
}

function finiteNumber(value, fallback = null) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v038-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v038-style";
  style.textContent = `
    .ep-v038-strategy { margin-top:15px; padding-top:14px; border-top:1px solid rgba(81,168,211,.10); }
    .ep-v038-head { display:flex; align-items:flex-start; justify-content:space-between; gap:14px; }
    .ep-v038-kicker { color:#62e5f7; font-size:8px; font-weight:900; letter-spacing:.15em; }
    .ep-v038-title { margin-top:3px; color:#e8f7fc; font-size:14px; font-weight:860; }
    .ep-v038-description { max-width:720px; margin-top:5px; color:#7696aa; font-size:9px; line-height:1.5; }
    .ep-v038-profile-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; margin-top:12px; }
    .ep-v038-profile {
      position:relative;
      min-height:78px;
      padding:10px;
      border:1px solid rgba(75,164,209,.12);
      border-radius:11px;
      color:#a7c3d1;
      background:rgba(5,27,47,.48);
      cursor:pointer;
      text-align:left;
      touch-action:pan-y;
      transition:border-color .12s linear, background-color .12s linear, box-shadow .12s linear;
    }
    .ep-v038-profile:hover:not(:disabled),
    .ep-v038-profile:focus-visible:not(:disabled) {
      border-color:rgba(55,213,231,.36);
      background:rgba(7,43,66,.68);
      outline:none;
    }
    .ep-v038-profile[aria-pressed="true"] {
      border-color:rgba(41,226,181,.56);
      color:#eafff8;
      background:linear-gradient(145deg,rgba(10,82,91,.58),rgba(8,67,52,.52));
      box-shadow:inset 0 0 18px rgba(37,220,174,.07), 0 0 12px rgba(37,220,174,.06);
    }
    .ep-v038-profile:disabled { opacity:.52; cursor:wait; }
    .ep-v038-profile strong { display:block; color:#e7f7fc; font-size:10px; font-weight:850; }
    .ep-v038-profile small { display:block; margin-top:6px; color:#64869a; font-size:7px; line-height:1.4; }
    .ep-v038-profile[aria-pressed="true"] small { color:#87acab; }
    .ep-v038-badge { position:absolute; top:7px; right:7px; color:#64dfbb; font-size:6px; font-weight:900; letter-spacing:.08em; }
    .ep-v038-message { margin-top:9px; min-height:14px; color:#6f91a4; font-size:8px; }
    .ep-v038-message.ok { color:#72dbb3; }
    .ep-v038-message.error { color:#ef9f98; }
    .ep-v038-custom { margin-top:11px; padding:11px; border:1px solid rgba(67,188,215,.12); border-radius:11px; background:rgba(5,24,42,.38); }
    .ep-v038-custom-head { color:#d8edf5; font-size:10px; font-weight:820; }
    .ep-v038-custom-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin-top:9px; }
    .ep-v038-soc { padding:9px 10px; border:1px solid rgba(76,157,202,.10); border-radius:9px; background:rgba(7,29,50,.43); }
    .ep-v038-soc-label { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:6px; color:#8fa9ba; font-size:8px; }
    .ep-v038-soc-label strong { color:#e5f4fa; font-size:10px; }
    .ep-v038-soc input { width:100%; accent-color:#25ddb6; touch-action:pan-y; }
    .ep-v038-custom-values { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:7px; margin-top:9px; }
    .ep-v038-custom-value { padding:8px; border:1px solid rgba(76,157,202,.08); border-radius:8px; background:rgba(7,29,50,.32); min-width:0; }
    .ep-v038-custom-value span { display:block; color:#66879a; font-size:7px; }
    .ep-v038-custom-value strong { display:block; margin-top:3px; color:#bfd6e1; font-size:8px; overflow-wrap:anywhere; }
    .ep-v038-custom-note { margin-top:8px; color:#5f7e91; font-size:7px; line-height:1.45; }
    .ep-v038-diagnostic-note { margin-top:10px; color:#58788d; font-size:8px; }

    /* v0.38 owns flow direction at one final layer. The data attribute expresses
       semantic energy direction; the selector chooses geometry. No inherited
       animation-direction reversal is allowed to reinterpret it. */
    .ep-flow-link[data-ep-v038-flow] .ep-v011-particles span {
      animation-direction:normal !important;
    }
    .ep-link-pv[data-ep-v038-flow="to-hub"] .ep-v011-particles span,
    .ep-link-grid[data-ep-v038-flow="from-hub"] .ep-v011-particles span {
      animation-name:epV038HForward !important;
    }
    .ep-link-pv[data-ep-v038-flow="from-hub"] .ep-v011-particles span,
    .ep-link-grid[data-ep-v038-flow="to-hub"] .ep-v011-particles span {
      animation-name:epV038HReverse !important;
    }
    .ep-link-house[data-ep-v038-flow="to-hub"] .ep-v011-particles span,
    .ep-link-battery[data-ep-v038-flow="from-hub"] .ep-v011-particles span {
      animation-name:epV038VForward !important;
    }
    .ep-link-house[data-ep-v038-flow="from-hub"] .ep-v011-particles span,
    .ep-link-battery[data-ep-v038-flow="to-hub"] .ep-v011-particles span {
      animation-name:epV038VReverse !important;
    }
    @keyframes epV038HForward {
      from { translate:-9px 0; }
      to { translate:var(--ep-track-distance, 80px) 0; }
    }
    @keyframes epV038HReverse {
      from { translate:var(--ep-track-distance, 80px) 0; }
      to { translate:-9px 0; }
    }
    @keyframes epV038VForward {
      from { translate:0 -9px; }
      to { translate:0 var(--ep-track-distance, 80px); }
    }
    @keyframes epV038VReverse {
      from { translate:0 var(--ep-track-distance, 80px); }
      to { translate:0 -9px; }
    }

    @media (max-width:1000px) {
      .ep-v038-profile-grid { grid-template-columns:repeat(3,minmax(0,1fr)); }
      .ep-v038-custom-values { grid-template-columns:repeat(3,minmax(0,1fr)); }
    }
    @media (max-width:650px) {
      .ep-v038-profile-grid { grid-template-columns:1fr 1fr; }
      .ep-v038-custom-grid, .ep-v038-custom-values { grid-template-columns:1fr; }
    }
    @media (max-width:430px) { .ep-v038-profile-grid { grid-template-columns:1fr; } }
  `;
  root.appendChild(style);
}

function refreshLegacyExternalEntityIds(panel, hass, force = false) {
  const states = hass?.states || {};
  const stateCount = Object.keys(states).length;
  if (
    !force &&
    panel.__epV038LegacyExternalEntityIds &&
    panel.__epV038ObservedStateCount === stateCount
  ) {
    return panel.__epV038LegacyExternalEntityIds;
  }

  const ids = new Set(LEGACY_EXTERNAL_ENTITIES);
  for (const entityId of Object.keys(states)) {
    if (LEGACY_EXTERNAL_SUFFIXES.some((suffix) => entityId.endsWith(suffix))) {
      ids.add(entityId);
    }
  }
  panel.__epV038LegacyExternalEntityIds = [...ids];
  panel.__epV038ObservedStateCount = stateCount;
  return panel.__epV038LegacyExternalEntityIds;
}

function configuredExternalEntityIds(panel, hass) {
  const ids = new Set();
  const optimizeId = panel._entityId?.("optimize_now");
  const optimizeState = optimizeId ? hass?.states?.[optimizeId] : null;
  const attrs = optimizeState?.attributes || {};
  for (const key of ["p_batt_entity", "p_grid_entity", "optim_status_entity"]) {
    const entityId = attrs[key];
    if (typeof entityId === "string" && entityId.includes(".")) ids.add(entityId);
  }

  const planEntity = panel.__epV027BatteryPlanData?.payload?.battery_plan?.entity_id;
  if (typeof planEntity === "string" && planEntity.includes(".")) ids.add(planEntity);
  return ids;
}

function relevantEntityIds(panel, previousHass, nextHass) {
  const ids = new Set(Object.values(panel._entityMap || {}).filter(Boolean));
  const previousCount = Object.keys(previousHass?.states || {}).length;
  const nextCount = Object.keys(nextHass?.states || {}).length;
  const legacy = refreshLegacyExternalEntityIds(
    panel,
    nextHass,
    previousCount !== nextCount
  );
  for (const entityId of legacy) ids.add(entityId);
  for (const entityId of configuredExternalEntityIds(panel, previousHass)) ids.add(entityId);
  for (const entityId of configuredExternalEntityIds(panel, nextHass)) ids.add(entityId);
  return ids;
}

function hassContextChanged(previousHass, nextHass) {
  if (!previousHass || !nextHass) return true;
  return (
    previousHass.locale !== nextHass.locale ||
    previousHass.language !== nextHass.language ||
    previousHass.user !== nextHass.user ||
    previousHass.themes !== nextHass.themes
  );
}

function relevantHassStateChanged(panel, previousHass, nextHass) {
  if (!previousHass?.states || !nextHass?.states) return true;
  for (const entityId of relevantEntityIds(panel, previousHass, nextHass)) {
    if (previousHass.states[entityId] !== nextHass.states[entityId]) return true;
  }
  return false;
}

function renderQuietDelay(panel) {
  return Math.max(0, Number(panel.__epV038RenderQuietUntil || 0) - Date.now());
}

function scheduleHassRender(panel) {
  if (panel.__epV038HassRenderTimer) return;

  const run = () => {
    panel.__epV038HassRenderTimer = null;
    const quietDelay = renderQuietDelay(panel);
    if (quietDelay > 0) {
      panel.__epV038HassRenderTimer = globalThis.setTimeout(run, quietDelay);
      return;
    }
    panel._queueRender();
  };

  panel.__epV038HassRenderTimer = globalThis.setTimeout(run, HASS_RENDER_BATCH_MS);
}

function installHassRenderGuard(PanelClass) {
  if (PanelClass.prototype.__epV038HassRenderGuardInstalled) return;
  const descriptor = Object.getOwnPropertyDescriptor(PanelClass.prototype, "hass");
  if (!descriptor?.set) return;

  Object.defineProperty(PanelClass.prototype, "hass", {
    configurable: descriptor.configurable,
    enumerable: descriptor.enumerable,
    get() {
      return descriptor.get ? descriptor.get.call(this) : this._hass;
    },
    set(value) {
      const previousHass = this._hass;
      if (!previousHass || !this._registryLoaded) {
        descriptor.set.call(this, value);
        return;
      }

      this._hass = value;
      if (this.__epV016SettingsOpen) return;

      if (
        hassContextChanged(previousHass, value) ||
        relevantHassStateChanged(this, previousHass, value)
      ) {
        scheduleHassRender(this);
      }
    },
  });
  PanelClass.prototype.__epV038HassRenderGuardInstalled = true;
}

function neutralizeLegacyInteractionState(panel) {
  for (const key of ["__epV035PointerFinishTimer", "__epV035PointerSafetyTimer"]) {
    if (panel[key]) globalThis.clearTimeout(panel[key]);
    panel[key] = null;
  }
  panel.__epV035PointerActive = false;
  panel.__epV035KeyboardActive = false;
  panel.__epV035PointerId = null;
  panel.__epV035PointerType = null;
  panel.__epV035TouchMoved = false;
  panel.__epV035RenderDeferred = false;
}

function installPressQuietWindow(panel, root) {
  if (panel.__epV038PressQuietInstalled) return;
  panel.__epV038PressQuietInstalled = true;

  const mark = () => {
    neutralizeLegacyInteractionState(panel);
    panel.__epV038RenderQuietUntil = Date.now() + PRESS_RENDER_QUIET_MS;
  };

  root.addEventListener(
    "pointerdown",
    (event) => {
      const target = eventElement(event, INTERACTIVE_SELECTOR);
      if (!target || (typeof event.button === "number" && event.button !== 0)) return;
      mark();
    },
    true
  );
  root.addEventListener(
    "keydown",
    (event) => {
      if ((event.key === "Enter" || event.key === " ") && eventElement(event, INTERACTIVE_SELECTOR)) {
        mark();
      }
    },
    true
  );
}

function armLegacyStableButtonBypass(panel, PanelClass) {
  const root = panel?.shadowRoot;
  if (!root || !PanelClass.prototype.__epV0363ControlStabilityInstalled) return;
  root.querySelectorAll("[data-ep-v038-render-sentinel]").forEach((node) => node.remove());
  if (!root.querySelector("button")) return;

  // v0.36.3 decides whether to reinsert stale button nodes by comparing button
  // counts/identities around the inherited render. One hidden sentinel makes
  // that comparison intentionally fail when an already-open browser still has
  // the old wrapper in memory, so the fresh render and fresh listeners win.
  const sentinel = document.createElement("button");
  sentinel.type = "button";
  sentinel.hidden = true;
  sentinel.tabIndex = -1;
  sentinel.dataset.epV038RenderSentinel = "1";
  root.appendChild(sentinel);
}

function composedParent(node) {
  if (node?.parentElement) return node.parentElement;
  const root = node?.getRootNode?.();
  const host = root?.host;
  return host instanceof Element ? host : null;
}

function shouldPreserveScroll(panel) {
  return Boolean(
    panel?.narrow === true ||
    panel?._narrow === true ||
    globalThis.matchMedia?.(`(max-width: ${MOBILE_SCROLL_BREAKPOINT_PX}px)`)?.matches === true
  );
}

function scrollSnapshot(element) {
  if (!(element instanceof Element)) return null;
  const scrollTop = Number(element.scrollTop || 0);
  const scrollLeft = Number(element.scrollLeft || 0);
  const scrollRange = Number(element.scrollHeight || 0) - Number(element.clientHeight || 0);
  if (scrollRange <= 1 && scrollTop <= 0) return null;

  const overflowY = globalThis.getComputedStyle?.(element)?.overflowY || "";
  if (scrollTop <= 0 && !/(auto|scroll|overlay)/.test(overflowY)) return null;
  return { element, scrollTop, scrollLeft };
}

function captureScrollPositions(panel) {
  const snapshots = [];
  const seen = new Set();
  let node = panel;
  while (node) {
    const snapshot = scrollSnapshot(node);
    if (snapshot && !seen.has(snapshot.element)) {
      snapshots.push(snapshot);
      seen.add(snapshot.element);
    }
    node = composedParent(node);
  }

  const documentScroller = globalThis.document?.scrollingElement;
  const documentSnapshot = scrollSnapshot(documentScroller);
  if (documentSnapshot && !seen.has(documentSnapshot.element)) snapshots.push(documentSnapshot);
  return snapshots;
}

function restoreScrollPositions(snapshots) {
  for (const snapshot of snapshots) {
    const element = snapshot.element;
    if (!element?.isConnected) continue;
    const maxTop = Math.max(0, Number(element.scrollHeight || 0) - Number(element.clientHeight || 0));
    const maxLeft = Math.max(0, Number(element.scrollWidth || 0) - Number(element.clientWidth || 0));
    element.scrollTop = Math.min(snapshot.scrollTop, maxTop);
    element.scrollLeft = Math.min(snapshot.scrollLeft, maxLeft);
  }
}

function stabilizeScrollAfterRender(snapshots) {
  if (!snapshots.length) return;
  restoreScrollPositions(snapshots);
  globalThis.requestAnimationFrame?.(() => {
    restoreScrollPositions(snapshots);
    globalThis.requestAnimationFrame?.(() => restoreScrollPositions(snapshots));
  });
}

function batterySaverCache(panel) {
  panel.__epV038BatterySaver = panel.__epV038BatterySaver || {};
  return panel.__epV038BatterySaver;
}

async function loadBatterySaver(panel, force = false) {
  const cache = batterySaverCache(panel);
  if (!panel._hass?.callWS || cache.loading) return;
  if (!force && cache.data) return;
  cache.loading = true;
  try {
    cache.data = await panel._hass.callWS({ type: "gw_energypilot/battery_saver/get" });
    cache.error = null;
  } catch (err) {
    cache.error = err?.message || String(err);
  } finally {
    cache.loading = false;
    panel._queueRender();
  }
}

async function selectProfile(panel, mode) {
  const cache = batterySaverCache(panel);
  if (!panel._hass?.callWS || cache.busy) return;
  if (!cache.data?.entry_id) await loadBatterySaver(panel, true);
  const entryId = cache.data?.entry_id;
  if (!entryId) return;

  const t = copy(panel);
  cache.busy = true;
  cache.message = t.applying;
  cache.tone = "";
  panel._queueRender();
  try {
    cache.data = await panel._hass.callWS({
      type: "gw_energypilot/battery_saver/set",
      entry_id: entryId,
      mode,
    });
    cache.message = t.applied;
    cache.tone = "ok";
    cache.error = null;
  } catch (err) {
    cache.message = err?.message || String(err);
    cache.tone = "error";
  } finally {
    cache.busy = false;
    panel._queueRender();
  }
}

function numberModel(panel, key, fallback) {
  const entityId = panel._entityId?.(key);
  const state = entityId ? panel._state?.(entityId) : null;
  const value = Number(state?.state);
  return { entityId, value: Number.isFinite(value) ? value : fallback };
}

function displayConfigValue(value) {
  if (Array.isArray(value)) return value.map((item) => displayConfigValue(item)).join(", ");
  const number = Number(value);
  return Number.isFinite(number) ? String(Math.round(number * 1000000) / 1000000) : "—";
}

function customSocHtml(panel, t, data) {
  const min = numberModel(panel, "emhass_minimum_soc", 0);
  const max = numberModel(panel, "emhass_maximum_soc", 100);
  const values = data?.current_emhass_values || {};
  const fields = [
    [t.deficit, values.battery_soc_deficit_cost],
    [t.surplus, values.battery_soc_surplus_cost],
    [t.stress, values.battery_stress_cost],
    [t.chargeWeight, values.weight_battery_charge],
    [t.dischargeWeight, values.weight_battery_discharge],
  ];
  return `
    <div class="ep-v038-custom">
      <div class="ep-v038-custom-head">${panel._escape(t.customTitle)}</div>
      <div class="ep-v038-custom-grid">
        <div class="ep-v038-soc">
          <div class="ep-v038-soc-label"><span>${panel._escape(t.minimum)}</span><strong data-ep-v038-soc-value="min">${Math.round(min.value)}%</strong></div>
          <input data-ep-v038-soc="min" type="range" min="0" max="100" step="1" value="${min.value}" ${min.entityId ? "" : "disabled"}>
        </div>
        <div class="ep-v038-soc">
          <div class="ep-v038-soc-label"><span>${panel._escape(t.maximum)}</span><strong data-ep-v038-soc-value="max">${Math.round(max.value)}%</strong></div>
          <input data-ep-v038-soc="max" type="range" min="0" max="100" step="1" value="${max.value}" ${max.entityId ? "" : "disabled"}>
        </div>
      </div>
      <div class="ep-v038-custom-values">
        ${fields.map(([label, value]) => `<div class="ep-v038-custom-value"><span>${panel._escape(label)}</span><strong>${panel._escape(displayConfigValue(value))}</strong></div>`).join("")}
      </div>
      <div class="ep-v038-custom-note">${panel._escape(t.customNote)}</div>
    </div>`;
}

function profilePresentation(t, mode) {
  if (mode.key === CUSTOM_MODE) {
    return { label: t.custom, description: t.customDescription };
  }
  return t.profiles?.[mode.key] || {
    label: mode.label || mode.key,
    description: mode.description || "",
  };
}

function removeLowLevelCommand(card) {
  for (const metric of card.querySelectorAll(".metric")) {
    const label = metric.querySelector(".metric-label")?.textContent?.trim().toLowerCase();
    if (label === "command" || label === "commando") metric.remove();
  }
}

function installCustomerStrategy(panel, root) {
  const card = root.querySelector(".panel-card.controller");
  if (!card) return;
  removeLowLevelCommand(card);
  root.querySelectorAll(".ep-v036-strategy").forEach((node) => node.remove());
  if (card.querySelector(".ep-v038-strategy")) return;

  const cache = batterySaverCache(panel);
  if (!cache.data && !cache.loading && !cache.error) queueMicrotask(() => loadBatterySaver(panel));
  const data = cache.data;
  const t = copy(panel);
  const activeMode = data?.managed ? data.mode : CUSTOM_MODE;
  const modes = [
    ...(data?.modes || []),
    { key: CUSTOM_MODE, label: t.custom, description: t.customDescription, recommended: false },
  ];

  const wrap = document.createElement("section");
  wrap.className = "ep-v038-strategy";
  wrap.dataset.epV038Strategy = "1";
  wrap.innerHTML = `
    <div class="ep-v038-head">
      <div>
        <div class="ep-v038-kicker">${panel._escape(t.kicker)}</div>
        <div class="ep-v038-title">${panel._escape(t.title)}</div>
        <div class="ep-v038-description">${panel._escape(t.description)}</div>
      </div>
    </div>
    <div class="ep-v038-profile-grid">
      ${modes.map((mode) => {
        const view = profilePresentation(t, mode);
        const selected = activeMode === mode.key;
        return `
          <button type="button"
            class="ep-v038-profile"
            data-ep-v038-profile="${panel._escape(mode.key)}"
            aria-pressed="${selected ? "true" : "false"}"
            ${cache.busy || cache.loading ? "disabled" : ""}>
            ${selected ? `<span class="ep-v038-badge">${panel._escape(t.active)}</span>` : ""}
            <strong>${panel._escape(view.label)}</strong>
            <small>${panel._escape(view.description)}</small>
          </button>`;
      }).join("")}
    </div>
    ${activeMode === CUSTOM_MODE ? customSocHtml(panel, t, data) : ""}
    <div class="ep-v038-message ${cache.tone || ""}">${panel._escape(cache.error || cache.message || "")}</div>
    <div class="ep-v038-diagnostic-note">${panel._escape(t.diagnostics)}</div>`;

  const manualPad = card.querySelector(".ep-v021-manual-pad");
  if (manualPad) card.insertBefore(wrap, manualPad);
  else card.appendChild(wrap);
}

function installCustomerEvents(panel, root) {
  if (panel.__epV038CustomerEventsInstalled) return;
  panel.__epV038CustomerEventsInstalled = true;

  root.addEventListener("click", (event) => {
    const button = eventElement(event, "button[data-ep-v038-profile]");
    if (!button || button.disabled) return;
    const mode = button.dataset.epV038Profile;
    if (mode) selectProfile(panel, mode);
  });

  root.addEventListener("input", (event) => {
    const slider = eventElement(event, "input[data-ep-v038-soc]");
    if (!slider) return;
    const kind = slider.dataset.epV038Soc;
    const label = root.querySelector(`[data-ep-v038-soc-value="${kind}"]`);
    if (label) label.textContent = `${slider.value}%`;
  });

  root.addEventListener("change", async (event) => {
    const slider = eventElement(event, "input[data-ep-v038-soc]");
    if (!slider || slider.disabled) return;
    const kind = slider.dataset.epV038Soc;
    const ref = kind === "min"
      ? numberModel(panel, "emhass_minimum_soc", 0)
      : numberModel(panel, "emhass_maximum_soc", 100);
    if (!ref.entityId) return;

    slider.disabled = true;
    try {
      await panel._hass.callService("number", "set_value", {
        entity_id: ref.entityId,
        value: Number(slider.value),
      });
    } catch (err) {
      window.alert(`${copy(panel).socUpdateFailed}: ${err?.message || err}`);
    } finally {
      slider.disabled = false;
      panel._queueRender();
    }
  });
}

function setCanonicalFlow(link, direction) {
  if (!link) return;
  if (!direction || link.classList.contains("idle")) {
    delete link.dataset.epV038Flow;
    return;
  }
  link.dataset.epV038Flow = direction;
}

function enforceCanonicalFlowDirections(panel, root) {
  const pv = finiteNumber(panel._stateByKey?.("pv_total_power")?.state);
  const grid = finiteNumber(panel._stateByKey?.("meter_total_power_fast")?.state);
  const battery = finiteNumber(panel._stateByKey?.("battery_power")?.state);

  setCanonicalFlow(
    root.querySelector(".ep-link-pv"),
    Number.isFinite(pv) && pv > 50 ? "to-hub" : null
  );
  setCanonicalFlow(
    root.querySelector(".ep-link-grid"),
    !Number.isFinite(grid) || Math.abs(grid) < 50
      ? null
      : grid > 0
        ? "from-hub"
        : "to-hub"
  );
  const houseLink = root.querySelector(".ep-link-house");
  setCanonicalFlow(houseLink, houseLink?.classList.contains("idle") ? null : "from-hub");
  setCanonicalFlow(
    root.querySelector(".ep-link-battery"),
    !Number.isFinite(battery) || Math.abs(battery) < 50
      ? null
      : battery > 0
        ? "to-hub"
        : "from-hub"
  );
}

function updateVersion(root) {
  const versionBadge = root?.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root?.querySelectorAll("footer span") || [];
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
installHassRenderGuard(PanelClass);

if (!PanelClass.prototype.__epV038ReleaseInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV038Render() {
    const preserveScroll = shouldPreserveScroll(this);
    const snapshots = preserveScroll ? captureScrollPositions(this) : [];
    if (preserveScroll) this.style.setProperty("overflow-anchor", "none");
    else this.style.removeProperty("overflow-anchor");

    neutralizeLegacyInteractionState(this);
    armLegacyStableButtonBypass(this, PanelClass);
    if (this.__epV038HassRenderTimer) {
      globalThis.clearTimeout(this.__epV038HassRenderTimer);
      this.__epV038HassRenderTimer = null;
    }

    previousRender.call(this);
    const root = this.shadowRoot;
    if (!root) return;

    root.querySelectorAll("[data-ep-v038-render-sentinel]").forEach((node) => node.remove());
    neutralizeLegacyInteractionState(this);
    installPressQuietWindow(this, root);
    ensureStyles(root);
    installCustomerEvents(this, root);
    installCustomerStrategy(this, root);
    enforceCanonicalFlowDirections(this, root);
    updateVersion(root);
    stabilizeScrollAfterRender(snapshots);
  };
  PanelClass.prototype.__epV038ReleaseInstalled = true;
}
