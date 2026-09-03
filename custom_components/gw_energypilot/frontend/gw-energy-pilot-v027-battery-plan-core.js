import "./gw-energy-pilot-v026-complete.js?v=1.2.0-stable1";
import {
  CARD_ID, DATA_CACHE_MS, PANEL_NAME, VERSION, chartHidden, chartRange,
  chartSize, chartSubtitle, chartWindowData, formatTime, loadChartData,
  saveChartRange, saveChartSize, t,
} from "./gw-energy-pilot-v027-battery-plan-data.js?v=1.2.0-stable1";
import {
  cardBody, ensureStyles, rangeControlHtml, sizeControlHtml,
} from "./gw-energy-pilot-v027-battery-plan-view.js?v=1.2.0-stable1";

const V041_PANEL_STYLE_ID = "ep-v041-scoped-no-motion";
const V041_GLOBAL_STYLE_ID = "ep-v041-scoped-global-no-motion";
const V041_STATIC_ATTRIBUTE = "data-ep-v041-static";
const V041_STATIC_SELECTOR = `[${V041_STATIC_ATTRIBUTE}][${V041_STATIC_ATTRIBUTE}][${V041_STATIC_ATTRIBUTE}][${V041_STATIC_ATTRIBUTE}][${V041_STATIC_ATTRIBUTE}][${V041_STATIC_ATTRIBUTE}][${V041_STATIC_ATTRIBUTE}][${V041_STATIC_ATTRIBUTE}]`;
const BOUND_CARD_CONTROLS = new WeakSet();

function freezeV041Element(element) {
  if (!(element instanceof Element)) return;
  element.setAttribute(V041_STATIC_ATTRIBUTE, "");
  element.style.setProperty("animation", "none", "important");
  element.style.setProperty("animation-name", "none", "important");
  element.style.setProperty("animation-duration", "0s", "important");
  element.style.setProperty("transition", "none", "important");
  element.style.setProperty("transition-property", "none", "important");
  element.style.setProperty("transition-duration", "0s", "important");
  element.style.setProperty("scroll-behavior", "auto", "important");
}

function freezeV041GlobalMotion() {
  if (!globalThis.document) return;
  document.body?.setAttribute("data-ep-v041-no-motion", "");
  if (!document.getElementById(V041_GLOBAL_STYLE_ID)) {
    const style = document.createElement("style");
    style.id = V041_GLOBAL_STYLE_ID;
    style.textContent = `
      body[data-ep-v041-no-motion] .ep-v027-backdrop,
      body[data-ep-v041-no-motion] .ep-v027-backdrop *,
      body[data-ep-v041-no-motion] .ep-v027-backdrop *::before,
      body[data-ep-v041-no-motion] .ep-v027-backdrop *::after,
      body[data-ep-v041-no-motion] .ep-v026-bp-backdrop,
      body[data-ep-v041-no-motion] .ep-v026-bp-backdrop *,
      body[data-ep-v041-no-motion] .ep-v026-bp-backdrop *::before,
      body[data-ep-v041-no-motion] .ep-v026-bp-backdrop *::after,
      body[data-ep-v041-no-motion] .ep13-backdrop,
      body[data-ep-v041-no-motion] .ep13-backdrop *,
      body[data-ep-v041-no-motion] .ep13-backdrop *::before,
      body[data-ep-v041-no-motion] .ep13-backdrop *::after {
        animation: none !important;
        transition: none !important;
        scroll-behavior: auto !important;
      }
      body[data-ep-v041-no-motion] .ep-v027-backdrop,
      body[data-ep-v041-no-motion] .ep-v026-bp-backdrop,
      body[data-ep-v041-no-motion] .ep13-backdrop {
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
      }
    `;
    document.head.appendChild(style);
  }
  for (const element of document.querySelectorAll(
    ".ep-v027-backdrop, .ep-v027-backdrop *, .ep-v026-bp-backdrop, .ep-v026-bp-backdrop *, .ep13-backdrop, .ep13-backdrop *"
  )) {
    freezeV041Element(element);
  }
}

export function freezeV041Motion(panel) {
  if (!panel?.__epV041StableRuntime) return;
  const root = panel.shadowRoot;
  if (!root) return;
  panel.setAttribute("data-ep-v041-no-motion", "");
  if (!root.querySelector(`#${V041_PANEL_STYLE_ID}`)) {
    const style = document.createElement("style");
    style.id = V041_PANEL_STYLE_ID;
    style.textContent = `
      :host([data-ep-v041-no-motion]) ${V041_STATIC_SELECTOR}::before,
      :host([data-ep-v041-no-motion]) ${V041_STATIC_SELECTOR}::after {
        animation: none !important;
        animation-name: none !important;
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        animation-iteration-count: 1 !important;
        transition: none !important;
        transition-property: none !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
      }
    `;
    root.appendChild(style);
  }
  for (const element of root.querySelectorAll("*")) freezeV041Element(element);
  for (const element of root.querySelectorAll(
    ".ep-flow-arrows, .ep-flow-live span, .ep-v011-particles, .ep-v011-particles span"
  )) {
    element.style.setProperty("display", "none", "important");
  }
  freezeV041GlobalMotion();
}

function openModal(panel) {
  document.querySelector(".ep-v027-backdrop")?.remove();
  const range = chartRange();
  const data = chartWindowData(panel.__epV027BatteryPlanData, range);
  const backdrop = document.createElement("div");
  backdrop.className = "ep-v027-backdrop";
  backdrop.innerHTML = `<style>
    .ep-v027-backdrop{position:fixed;inset:0;z-index:10090;display:grid;place-items:center;padding:18px;background:rgba(1,7,18,.72);backdrop-filter:blur(16px);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif;color:#eef9fd}
    .ep-v027-modal{width:min(1180px,97vw);max-height:93vh;overflow:auto;padding:22px;border:1px solid rgba(119,203,235,.22);border-radius:26px;background:linear-gradient(150deg,rgba(11,35,65,.98),rgba(5,17,36,.99));box-shadow:0 38px 120px rgba(0,0,0,.62),inset 0 1px 0 rgba(255,255,255,.04)}
    .ep-v027-modal-head{display:flex;align-items:flex-start;justify-content:space-between;gap:15px;margin-bottom:8px}.ep-v027-modal-head small{display:block;color:#67e6f8;font-size:10px;letter-spacing:.15em;font-weight:850}.ep-v027-modal-head h2{margin:5px 0 0;font-size:25px;letter-spacing:-.02em}.ep-v027-modal-head p{margin:5px 0 0;color:#829caf;font-size:11px}.ep-v027-close{width:37px;height:37px;border-radius:12px;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.045);color:#e0f0f7;font-size:20px;cursor:pointer}
    .ep-v027-modal .ep-v027-chart{border-radius:17px;background:rgba(1,11,27,.31)}.ep-v027-modal .ep-v027-legend{display:flex;justify-content:center;flex-wrap:wrap;gap:12px 24px;margin:7px 0 14px;color:#91a9ba;font-size:10px}.ep-v027-modal .ep-v027-legend span{display:flex;align-items:center;gap:7px}.ep-v027-modal .ep-v027-legend i{display:inline-block}.ep-v027-modal .actual-charge,.ep-v027-modal .actual-discharge{width:10px;height:10px;border-radius:3px;background:#27dfc2}.ep-v027-modal .actual-discharge{background:#ffa52f}.ep-v027-modal .plan{width:18px;height:9px;border:1px dashed #9cbcc8;border-radius:3px}.ep-v027-modal .ev-charge-allowed,.ep-v027-modal .ev-discharge-blocked{width:16px;height:9px;border:1px solid rgba(140,242,155,.46);border-radius:2px}.ep-v027-modal .ev-charge-allowed{background:repeating-linear-gradient(135deg,rgba(162,242,173,.42) 0 2px,rgba(121,230,140,.06) 2px 6px)}.ep-v027-modal .ev-discharge-blocked{background:rgba(121,230,140,.32)}.ep-v027-modal .actual-soc{width:18px;height:2px;background:#f472b6}.ep-v027-modal .forecast-soc{width:18px;height:0;border-top:2px dashed #c4b5fd}.ep-v027-modal .price{width:20px;height:2px;background:#55e8ff}.ep-v027-modal .ep-v027-summary{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px}.ep-v027-modal .ep-v027-chip{display:flex;align-items:center;gap:9px;padding:11px;border:1px solid rgba(255,255,255,.06);border-radius:14px;background:rgba(255,255,255,.025)}.ep-v027-modal .ep-v027-icon{width:30px;height:30px;display:grid;place-items:center;border-radius:50%;border:1px solid rgba(39,224,193,.6);color:#42ebce}.ep-v027-modal .discharge .ep-v027-icon{border-color:rgba(255,165,47,.65);color:#ffb34a}.ep-v027-modal .price .ep-v027-icon{border-color:rgba(85,232,255,.62);color:#64e9fb}.ep-v027-modal small{display:block;color:#849dae;font-size:8px}.ep-v027-modal strong{display:block;margin-top:2px}.ep-v027-modal em{display:block;margin-top:2px;color:#647f92;font-size:7px;font-style:normal}.ep-v027-modal .ep-v027-notes{margin-top:12px;color:#69879b;font-size:9px;line-height:1.55}
    @media(max-width:850px){.ep-v027-modal{padding:15px;border-radius:20px}.ep-v027-modal .ep-v027-summary{grid-template-columns:1fr}.ep-v027-modal-head h2{font-size:21px}}
  </style><section class="ep-v027-modal"><div class="ep-v027-modal-head"><div><small>${panel._escape(t(panel, "actual"))} + ${panel._escape(t(panel, "future"))}</small><h2>${panel._escape(t(panel, "title"))}</h2><p>${panel._escape(chartSubtitle(panel, range))}</p></div><button type="button" class="ep-v027-close" aria-label="${panel._escape(t(panel, "close"))}">×</button></div>${cardBody(panel, data, "large", true)}</section>`;

  const close = () => {
    document.removeEventListener("keydown", escape);
    backdrop.remove();
  };
  const escape = (event) => { if (event.key === "Escape") close(); };
  backdrop.querySelector(".ep-v027-close")?.addEventListener("click", close);
  backdrop.addEventListener("click", (event) => { if (event.target === backdrop) close(); });
  document.addEventListener("keydown", escape);
  document.body.appendChild(backdrop);
  freezeV041Motion(panel);
}

function currentOptimizationPlanRevision(panel) {
  const entityId = panel._entityId?.("optimize_now");
  const state = entityId ? panel._hass?.states?.[entityId] : null;
  const raw = state?.attributes?.plan_revision;
  if (raw === null || raw === undefined || raw === "") return null;
  const revision = Number(raw);
  return Number.isFinite(revision) ? revision : null;
}

function currentExecutionHistoryRevision(panel) {
  const entityId = panel._entityId?.("control_command");
  const state = entityId ? panel._hass?.states?.[entityId] : null;
  const raw = state?.attributes?.execution_history_revision;
  if (raw === null || raw === undefined || raw === "") return null;
  const revision = Number(raw);
  return Number.isFinite(revision) ? revision : null;
}

function activePlanChanged(panel, data) {
  const currentRevision = currentOptimizationPlanRevision(panel);
  const cachedRaw = data?.payload?.plan_revision;
  const cachedRevision = cachedRaw === null || cachedRaw === undefined || cachedRaw === ""
    ? null
    : Number(cachedRaw);
  if (
    currentRevision !== null &&
    (!Number.isFinite(cachedRevision) || currentRevision !== cachedRevision)
  ) {
    return true;
  }

  // Preserve the external-EMHASS fallback: a plan published outside an
  // EnergyPilot optimization still invalidates the chart when P_batt changes.
  const plan = data?.payload?.battery_plan;
  const entityId = plan?.entity_id;
  if (!entityId) return false;
  const state = panel._hass?.states?.[entityId];
  if (!state?.last_updated || !plan?.last_updated) return false;
  return state.last_updated !== plan.last_updated;
}

function activeExecutionHistoryChanged(panel, data) {
  const currentRevision = currentExecutionHistoryRevision(panel);
  const cachedRaw = data?.payload?.execution?.revision;
  const cachedRevision = cachedRaw === null || cachedRaw === undefined || cachedRaw === ""
    ? null
    : Number(cachedRaw);
  return currentRevision !== null && (
    !Number.isFinite(cachedRevision) || currentRevision !== cachedRevision
  );
}

function chartRefreshIdle(panel) {
  return Boolean(
    !panel.__epV027BatteryPlanLoading &&
    !panel.__epV027BatteryPlanPromise
  );
}

function bindClickOnce(element, listener) {
  if (!element || BOUND_CARD_CONTROLS.has(element)) return;
  element.addEventListener("click", listener);
  BOUND_CARD_CONTROLS.add(element);
}

function bindCardControls(panel, card) {
  card.querySelectorAll("[data-chart-range]").forEach((button) => {
    bindClickOnce(button, () => {
      saveChartRange(button.dataset.chartRange);
      if (panel.__epV041StableRuntime) refreshBatteryPlanCard(panel);
      else panel._queueRender();
    });
  });
  card.querySelectorAll("[data-chart-size]").forEach((button) => {
    bindClickOnce(button, () => {
      saveChartSize(button.dataset.chartSize);
      if (panel.__epV041StableRuntime) refreshBatteryPlanCard(panel);
      else panel._queueRender();
    });
  });
  bindClickOnce(card.querySelector(".ep-v027-expand"), () => openModal(panel));
  bindClickOnce(card.querySelector('[data-action="details"]'), () => openModal(panel));
  bindClickOnce(
    card.querySelector('[data-action="refresh"]'),
    () => void loadChartData(panel, true)
  );
}

function preserveInteractiveShell(existingCard, card) {
  const existingHead = existingCard.querySelector(":scope > .ep-v027-head");
  const nextHead = card.querySelector(":scope > .ep-v027-head");
  const existingButtons = [...(existingHead?.querySelectorAll("[data-chart-size]") || [])];
  const nextButtons = [...(nextHead?.querySelectorAll("[data-chart-size]") || [])];
  const existingRanges = [...(existingHead?.querySelectorAll("[data-chart-range]") || [])];
  const nextRanges = [...(nextHead?.querySelectorAll("[data-chart-range]") || [])];
  if (
    !existingHead || !nextHead || existingButtons.length !== nextButtons.length ||
    existingRanges.length !== nextRanges.length
  ) {
    return false;
  }

  const nextBySize = new Map(
    nextButtons.map((button) => [button.dataset.chartSize, button])
  );
  for (const button of existingButtons) {
    const nextButton = nextBySize.get(button.dataset.chartSize);
    if (!nextButton) return false;
    button.className = nextButton.className;
    button.title = nextButton.title;
    button.setAttribute("aria-pressed", nextButton.getAttribute("aria-pressed") || "false");
  }
  const nextByRange = new Map(
    nextRanges.map((button) => [button.dataset.chartRange, button])
  );
  for (const button of existingRanges) {
    const nextButton = nextByRange.get(button.dataset.chartRange);
    if (!nextButton) return false;
    button.className = nextButton.className;
    button.title = nextButton.title;
    button.setAttribute("aria-pressed", nextButton.getAttribute("aria-pressed") || "false");
  }

  for (const selector of [".ep-v027-kicker", ".ep-v027-subtitle"]) {
    const existingText = existingHead.querySelector(selector);
    const nextText = nextHead.querySelector(selector);
    if (existingText && nextText) existingText.textContent = nextText.textContent;
  }
  const existingExpand = existingHead.querySelector(".ep-v027-expand");
  const nextExpand = nextHead.querySelector(".ep-v027-expand");
  if (existingExpand && nextExpand) {
    existingExpand.title = nextExpand.title;
    existingExpand.setAttribute(
      "aria-label",
      nextExpand.getAttribute("aria-label") || nextExpand.title
    );
  }

  const windowBar = existingCard.querySelector(":scope > .ep-v031-card-windowbar");
  const preservedClasses = [...existingCard.classList].filter(
    (className) => className.startsWith("ep-v031-card-")
  );
  existingCard.className = card.className;
  for (const className of preservedClasses) existingCard.classList.add(className);
  existingCard.dataset.epCard = card.dataset.epCard;
  existingCard.dataset.epSpan = card.dataset.epSpan;
  existingCard.dataset.epRenderKey = card.dataset.epRenderKey;
  existingCard.hidden = card.hidden;

  // Keep the live card and header in the same connected parent throughout a
  // scoped refresh. Rebuild only the graph body/footer so a native press that
  // started on S/M/L can still produce its click after the refresh completes.
  for (const child of [...existingCard.children]) {
    if (child !== windowBar && child !== existingHead) child.remove();
  }
  for (const child of [...card.children]) {
    if (child !== nextHead) existingCard.appendChild(child);
  }
  return true;
}

function installEnhancedCard(panel, root) {
  const layout = root.querySelector(".ep-dashboard-layout");
  if (!layout) return;

  const size = chartSize();
  const range = chartRange();
  const data = panel.__epV027BatteryPlanData;
  const viewData = chartWindowData(data, range);
  const hidden = chartHidden();

  // A cache-busted frontend module can wrap _render more than once during a
  // live upgrade. Keep one canonical card, but do not let the duplicate guard
  // prevent that card from being refreshed when fresh chart data arrives.
  const existingCards = [...root.querySelectorAll(".ep-v027-battery-plan-card")];
  const existingCard = existingCards[0] || null;
  for (const duplicate of existingCards.slice(1)) duplicate.remove();

  const renderKey = `${data?.at || 0}:${size}:${range}:${hidden ? 1 : 0}`;
  if (existingCard?.dataset.epRenderKey === renderKey) {
    if (data && activePlanChanged(panel, data) && chartRefreshIdle(panel)) {
      void loadChartData(panel, true);
    } else if (data && activeExecutionHistoryChanged(panel, data) && chartRefreshIdle(panel)) {
      void loadChartData(panel, true, false);
    } else if (data && Date.now() - data.at >= DATA_CACHE_MS && chartRefreshIdle(panel)) {
      void loadChartData(panel);
    }
    return;
  }

  const oldCard = root.querySelector(".ep-v026-battery-price-card");
  const card = document.createElement("article");
  card.className = `panel-card ep-v027-battery-plan-card size-${size}`;
  card.dataset.epCard = CARD_ID;
  card.dataset.epSpan = size === "compact" ? "2" : "4";
  card.dataset.epRenderKey = renderKey;
  card.hidden = hidden;
  const updated = data?.at ? t(panel, "updated", { time: formatTime(data.at) }) : t(panel, "waiting");
  card.innerHTML = `<div class="ep-v027-head"><div><div class="ep-v027-kicker">${panel._escape(t(panel, "title"))}</div><div class="ep-v027-subtitle">${panel._escape(chartSubtitle(panel, range))}</div></div><div class="ep-v027-head-actions">${rangeControlHtml(panel, range)}${sizeControlHtml(panel, size)}<button type="button" class="ep-v027-expand" title="${panel._escape(t(panel, "expand"))}" aria-label="${panel._escape(t(panel, "expand"))}">↗</button></div></div>${cardBody(panel, viewData, size, false)}<div class="ep-v027-footer"><div class="ep-v027-footer-actions"><button type="button" data-action="details">${panel._escape(t(panel, "details"))}</button><button type="button" data-action="refresh" title="${panel._escape(t(panel, "refresh"))}">↻</button></div><span>${panel._escape(updated)}</span></div>`;

  let installedCard = card;
  if (existingCard) {
    if (preserveInteractiveShell(existingCard, card)) installedCard = existingCard;
    else existingCard.replaceWith(card);
  } else if (oldCard) oldCard.replaceWith(card);
  else {
    const batteryCard = layout.querySelector('[data-ep-card="battery"]') || layout.querySelector(".energy-card.battery");
    if (batteryCard) batteryCard.insertAdjacentElement("afterend", card);
    else layout.appendChild(card);
  }

  bindCardControls(panel, installedCard);

  if (!data && chartRefreshIdle(panel)) void loadChartData(panel);
  else if (data && activePlanChanged(panel, data) && chartRefreshIdle(panel)) void loadChartData(panel, true);
  else if (data && activeExecutionHistoryChanged(panel, data) && chartRefreshIdle(panel)) void loadChartData(panel, true, false);
  else if (data && Date.now() - data.at >= DATA_CACHE_MS && chartRefreshIdle(panel)) void loadChartData(panel);
}

export function refreshBatteryPlanCard(panel) {
  const root = panel?.shadowRoot;
  if (!root) return;
  ensureStyles(root);
  installEnhancedCard(panel, root);
  freezeV041Motion(panel);
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;
PanelClass.prototype._render = function energyPilotV027BatteryPlanRender() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;
  if (this.__epV041StableRuntime) {
    this.__epV041FreezeMotion = () => freezeV041Motion(this);
    queueMicrotask(() => freezeV041Motion(this));
  }
  this.__epV041RefreshBatteryPlan = () => refreshBatteryPlanCard(this);
  refreshBatteryPlanCard(this);
  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
};
