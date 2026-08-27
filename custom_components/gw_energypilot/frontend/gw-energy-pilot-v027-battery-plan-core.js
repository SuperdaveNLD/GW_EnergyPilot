import "./gw-energy-pilot-v026-complete.js?v=0.26-complete1";
import {
  CARD_ID, DATA_CACHE_MS, PANEL_NAME, VERSION, chartHidden, chartSize,
  formatTime, loadChartData, saveChartSize, t,
} from "./gw-energy-pilot-v027-battery-plan-data.js?v=0.28-chart1";
import {
  cardBody, ensureStyles, sizeControlHtml,
} from "./gw-energy-pilot-v027-battery-plan-view.js?v=0.28-chart1";

function openModal(panel) {
  document.querySelector(".ep-v027-backdrop")?.remove();
  const data = panel.__epV027BatteryPlanData;
  const backdrop = document.createElement("div");
  backdrop.className = "ep-v027-backdrop";
  backdrop.innerHTML = `<style>
    .ep-v027-backdrop{position:fixed;inset:0;z-index:10090;display:grid;place-items:center;padding:18px;background:rgba(1,7,18,.72);backdrop-filter:blur(16px);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",sans-serif;color:#eef9fd}
    .ep-v027-modal{width:min(1180px,97vw);max-height:93vh;overflow:auto;padding:22px;border:1px solid rgba(119,203,235,.22);border-radius:26px;background:linear-gradient(150deg,rgba(11,35,65,.98),rgba(5,17,36,.99));box-shadow:0 38px 120px rgba(0,0,0,.62),inset 0 1px 0 rgba(255,255,255,.04)}
    .ep-v027-modal-head{display:flex;align-items:flex-start;justify-content:space-between;gap:15px;margin-bottom:8px}.ep-v027-modal-head small{display:block;color:#67e6f8;font-size:10px;letter-spacing:.15em;font-weight:850}.ep-v027-modal-head h2{margin:5px 0 0;font-size:25px;letter-spacing:-.02em}.ep-v027-modal-head p{margin:5px 0 0;color:#829caf;font-size:11px}.ep-v027-close{width:37px;height:37px;border-radius:12px;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.045);color:#e0f0f7;font-size:20px;cursor:pointer}
    .ep-v027-modal .ep-v027-chart{border-radius:17px;background:rgba(1,11,27,.31)}.ep-v027-modal .ep-v027-legend{display:flex;justify-content:center;flex-wrap:wrap;gap:12px 24px;margin:7px 0 14px;color:#91a9ba;font-size:10px}.ep-v027-modal .ep-v027-legend span{display:flex;align-items:center;gap:7px}.ep-v027-modal .ep-v027-legend i{display:inline-block}.ep-v027-modal .actual-charge,.ep-v027-modal .actual-discharge{width:10px;height:10px;border-radius:3px;background:#27dfc2}.ep-v027-modal .actual-discharge{background:#ffa52f}.ep-v027-modal .plan{width:18px;height:9px;border:1px dashed #9cbcc8;border-radius:3px}.ep-v027-modal .price{width:20px;height:2px;background:#55e8ff}.ep-v027-modal .ep-v027-summary{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px}.ep-v027-modal .ep-v027-chip{display:flex;align-items:center;gap:9px;padding:11px;border:1px solid rgba(255,255,255,.06);border-radius:14px;background:rgba(255,255,255,.025)}.ep-v027-modal .ep-v027-icon{width:30px;height:30px;display:grid;place-items:center;border-radius:50%;border:1px solid rgba(39,224,193,.6);color:#42ebce}.ep-v027-modal .discharge .ep-v027-icon{border-color:rgba(255,165,47,.65);color:#ffb34a}.ep-v027-modal .price .ep-v027-icon{border-color:rgba(85,232,255,.62);color:#64e9fb}.ep-v027-modal small{display:block;color:#849dae;font-size:8px}.ep-v027-modal strong{display:block;margin-top:2px}.ep-v027-modal em{display:block;margin-top:2px;color:#647f92;font-size:7px;font-style:normal}.ep-v027-modal .ep-v027-notes{margin-top:12px;color:#69879b;font-size:9px;line-height:1.55}
    @media(max-width:850px){.ep-v027-modal{padding:15px;border-radius:20px}.ep-v027-modal .ep-v027-summary{grid-template-columns:1fr}.ep-v027-modal-head h2{font-size:21px}}
  </style><section class="ep-v027-modal"><div class="ep-v027-modal-head"><div><small>${panel._escape(t(panel, "actual"))} + ${panel._escape(t(panel, "future"))}</small><h2>${panel._escape(t(panel, "title"))}</h2><p>${panel._escape(t(panel, "subtitle"))}</p></div><button type="button" class="ep-v027-close" aria-label="${panel._escape(t(panel, "close"))}">×</button></div>${cardBody(panel, data, "large", true)}</section>`;

  const close = () => {
    document.removeEventListener("keydown", escape);
    backdrop.remove();
  };
  const escape = (event) => { if (event.key === "Escape") close(); };
  backdrop.querySelector(".ep-v027-close")?.addEventListener("click", close);
  backdrop.addEventListener("click", (event) => { if (event.target === backdrop) close(); });
  document.addEventListener("keydown", escape);
  document.body.appendChild(backdrop);
}

function currentOptimizationPlanRevision(panel) {
  const entityId = panel._entityId?.("optimize_now");
  const state = entityId ? panel._hass?.states?.[entityId] : null;
  const raw = state?.attributes?.plan_revision;
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

function installEnhancedCard(panel, root) {
  const layout = root.querySelector(".ep-dashboard-layout");
  if (!layout) return;

  const size = chartSize();
  const data = panel.__epV027BatteryPlanData;
  const hidden = chartHidden();

  // A cache-busted frontend module can wrap _render more than once during a
  // live upgrade. Keep one canonical card, but do not let the duplicate guard
  // prevent that card from being replaced when fresh chart data arrives.
  const existingCards = [...root.querySelectorAll(".ep-v027-battery-plan-card")];
  const existingCard = existingCards[0] || null;
  for (const duplicate of existingCards.slice(1)) duplicate.remove();

  const renderKey = `${data?.at || 0}:${size}:${hidden ? 1 : 0}`;
  if (existingCard?.dataset.epRenderKey === renderKey) {
    if (data && activePlanChanged(panel, data) && !panel.__epV027BatteryPlanPromise) {
      void loadChartData(panel, true);
    } else if (data && Date.now() - data.at >= DATA_CACHE_MS && !panel.__epV027BatteryPlanPromise) {
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
  card.innerHTML = `<div class="ep-v027-head"><div><div class="ep-v027-kicker">${panel._escape(t(panel, "title"))}</div><div class="ep-v027-subtitle">${panel._escape(t(panel, "subtitle"))}</div></div><div class="ep-v027-head-actions">${sizeControlHtml(panel, size)}<button type="button" class="ep-v027-expand" title="${panel._escape(t(panel, "expand"))}" aria-label="${panel._escape(t(panel, "expand"))}">↗</button></div></div>${cardBody(panel, data, size, false)}<div class="ep-v027-footer"><div class="ep-v027-footer-actions"><button type="button" data-action="details">${panel._escape(t(panel, "details"))}</button><button type="button" data-action="refresh" title="${panel._escape(t(panel, "refresh"))}">↻</button></div><span>${panel._escape(updated)}</span></div>`;

  if (existingCard) existingCard.replaceWith(card);
  else if (oldCard) oldCard.replaceWith(card);
  else {
    const batteryCard = layout.querySelector('[data-ep-card="battery"]') || layout.querySelector(".energy-card.battery");
    if (batteryCard) batteryCard.insertAdjacentElement("afterend", card);
    else layout.appendChild(card);
  }

  card.querySelectorAll("[data-chart-size]").forEach((button) => {
    button.addEventListener("click", () => {
      saveChartSize(button.dataset.chartSize);
      panel._queueRender();
    });
  });
  card.querySelector(".ep-v027-expand")?.addEventListener("click", () => openModal(panel));
  card.querySelector('[data-action="details"]')?.addEventListener("click", () => openModal(panel));
  card.querySelector('[data-action="refresh"]')?.addEventListener("click", () => void loadChartData(panel, true));

  if (!data && !panel.__epV027BatteryPlanPromise) void loadChartData(panel);
  else if (data && activePlanChanged(panel, data) && !panel.__epV027BatteryPlanPromise) void loadChartData(panel, true);
  else if (data && Date.now() - data.at >= DATA_CACHE_MS && !panel.__epV027BatteryPlanPromise) void loadChartData(panel);
}

export function refreshBatteryPlanCard(panel) {
  const root = panel?.shadowRoot;
  if (!root) return;
  ensureStyles(root);
  installEnhancedCard(panel, root);
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;
PanelClass.prototype._render = function energyPilotV027BatteryPlanRender() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;
  this.__epV041RefreshBatteryPlan = () => refreshBatteryPlanCard(this);
  refreshBatteryPlanCard(this);
  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
};
