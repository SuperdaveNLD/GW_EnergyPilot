import "./gw-energy-pilot-v012-stable.js?v=0.12-stable2";

const VERSION = "0.13";
const PANEL_NAME = "gw-energypilot-panel";
const DAILY_CACHE_MS = 5 * 60 * 1000;
const PARTICLE_SECONDS = 4.6;

function optimizeAttrs(panel) {
  const entityId = panel._entityId("optimize_now");
  return (entityId ? panel._state(entityId)?.attributes : null) || {};
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v013-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v013-style";
  style.textContent = `
    .ep-v013-refresh {
      position: absolute;
      right: 11px;
      bottom: 9px;
      z-index: 8;
      color: rgba(150, 184, 210, .68);
      font-size: 8px;
      letter-spacing: .06em;
      pointer-events: none;
    }
    .ep-flow-overview .ep-v013-refresh {
      right: 13px;
      bottom: 8px;
    }
    .energy-card.grid {
      cursor: pointer;
      transition: border-color .14s linear, background-color .14s linear !important;
    }
    .energy-card.grid:hover {
      transform: none !important;
      border-color: rgba(42, 218, 255, .34) !important;
    }
    .ep-v013-grid-hint {
      margin-top: 11px;
      color: #6fa3bd;
      font-size: 9px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .ep-v013-grid-daily {
      margin-top: 8px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
    }
    .ep-v013-grid-day {
      border: 1px solid rgba(255,255,255,.045);
      background: rgba(255,255,255,.018);
      border-radius: 9px;
      padding: 6px 7px;
      color: #8ca4b9;
      font-size: 8px;
      line-height: 1.35;
    }
    .ep-v013-grid-day strong { color: #dff7ff; font-size: 9px; }

    .ep-v013-soc-info {
      appearance: none;
      border: 1px solid rgba(89, 221, 255, .25);
      background: rgba(18, 105, 145, .13);
      color: #7de7ff;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      display: inline-grid;
      place-items: center;
      padding: 0;
      margin-left: 5px;
      font-size: 10px;
      font-weight: 800;
      cursor: pointer;
      vertical-align: middle;
    }
    .ep-v013-soc-info:hover { background: rgba(18, 149, 184, .22); }

    /* v0.12-stable animated transform, but v0.12 also contained a static
       transform:none!important. Individual CSS translate is independent from
       transform, so it stays compositor-friendly and actually moves. */
    .ep-v011-particles { z-index: 20 !important; }
    .ep-v011-particles span {
      width: 8px !important;
      height: 8px !important;
      border-radius: 50% !important;
      opacity: 1 !important;
      background: #ecffff !important;
      box-shadow:
        0 0 5px 2px rgba(231,255,255,.95),
        0 0 13px 5px rgba(35,224,255,.72),
        0 0 24px 8px rgba(29,241,176,.25) !important;
      animation-duration: ${PARTICLE_SECONDS}s !important;
      animation-timing-function: linear !important;
      animation-iteration-count: infinite !important;
      will-change: translate !important;
    }
    .ep-link-pv .ep-v011-particles span,
    .ep-link-battery .ep-v011-particles span {
      background: #eafff7 !important;
      box-shadow:
        0 0 5px 2px rgba(234,255,247,.98),
        0 0 14px 5px rgba(34,245,156,.78),
        0 0 25px 8px rgba(34,245,156,.28) !important;
    }
    .ep-link-pv.inbound .ep-v011-particles span,
    .ep-link-grid.outbound .ep-v011-particles span {
      animation-name: epV013HForward !important;
    }
    .ep-link-pv.outbound .ep-v011-particles span,
    .ep-link-grid.inbound .ep-v011-particles span {
      animation-name: epV013HReverse !important;
    }
    .ep-link-house.outbound .ep-v011-particles span,
    .ep-link-battery.inbound .ep-v011-particles span {
      animation-name: epV013VReverse !important;
    }
    .ep-link-house.inbound .ep-v011-particles span,
    .ep-link-battery.outbound .ep-v011-particles span {
      animation-name: epV013VForward !important;
    }
    @keyframes epV013HForward {
      from { translate: -9px 0; }
      to { translate: var(--ep-track-distance, 80px) 0; }
    }
    @keyframes epV013HReverse {
      from { translate: var(--ep-track-distance, 80px) 0; }
      to { translate: -9px 0; }
    }
    @keyframes epV013VForward {
      from { translate: 0 -9px; }
      to { translate: 0 var(--ep-track-distance, 80px); }
    }
    @keyframes epV013VReverse {
      from { translate: 0 var(--ep-track-distance, 80px); }
      to { translate: 0 -9px; }
    }
  `;
  root.appendChild(style);
}

function setParticlePhases(root) {
  const phase = (Date.now() / 1000) % PARTICLE_SECONDS;
  for (const link of root.querySelectorAll(".ep-flow-link")) {
    const holder = link.querySelector(".ep-v011-particles");
    if (!holder) continue;
    while (holder.children.length < 5) holder.appendChild(document.createElement("span"));
    [...holder.querySelectorAll("span")].forEach((particle, index) => {
      const stagger = (index * PARTICLE_SECONDS) / 5;
      particle.style.animationDelay = `${-((phase + stagger) % PARTICLE_SECONDS)}s`;
    });
  }
}

function formatEnergy(value) {
  return Number.isFinite(value) ? `${value.toFixed(value >= 10 ? 1 : 2)} kWh` : "—";
}

function localDayBounds(offsetDays = 0) {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offsetDays);
  const end = offsetDays === 0
    ? now
    : new Date(now.getFullYear(), now.getMonth(), now.getDate() + offsetDays + 1);
  return { start, end };
}

async function statisticChange(panel, entityId, start, end) {
  if (!entityId || !panel._hass?.callWS) return null;
  try {
    const result = await panel._hass.callWS({
      type: "recorder/statistic_during_period",
      statistic_id: entityId,
      fixed_period: {
        start_time: start.toISOString(),
        end_time: end.toISOString(),
      },
      types: ["change"],
    });
    const value = Number(result?.change);
    return Number.isFinite(value) ? Math.max(0, value) : null;
  } catch (err) {
    console.debug("GW EnergyPilot: daily grid statistic unavailable", err);
    return null;
  }
}

async function loadDailyGridTotals(panel, force = false) {
  const now = Date.now();
  if (!force && panel.__epV013GridDaily && now - panel.__epV013GridDaily.at < DAILY_CACHE_MS) {
    return panel.__epV013GridDaily;
  }
  if (panel.__epV013GridDailyPromise) return panel.__epV013GridDailyPromise;

  const importId = panel._entityId("meter_total_energy_import");
  const exportId = panel._entityId("meter_total_energy_export");
  if (!importId || !exportId) return null;

  const today = localDayBounds(0);
  const yesterday = localDayBounds(-1);
  panel.__epV013GridDailyPromise = Promise.all([
    statisticChange(panel, importId, today.start, today.end),
    statisticChange(panel, exportId, today.start, today.end),
    statisticChange(panel, importId, yesterday.start, yesterday.end),
    statisticChange(panel, exportId, yesterday.start, yesterday.end),
  ]).then(([todayImport, todayExport, yesterdayImport, yesterdayExport]) => {
    panel.__epV013GridDaily = {
      at: Date.now(),
      todayImport,
      todayExport,
      yesterdayImport,
      yesterdayExport,
    };
    return panel.__epV013GridDaily;
  }).finally(() => {
    panel.__epV013GridDailyPromise = null;
  });
  return panel.__epV013GridDailyPromise;
}

function dailySummaryHtml(totals) {
  if (!totals) return "";
  return `
    <div class="ep-v013-grid-daily">
      <div class="ep-v013-grid-day"><strong>Today</strong><br>↓ ${formatEnergy(totals.todayImport)} · ↑ ${formatEnergy(totals.todayExport)}</div>
      <div class="ep-v013-grid-day"><strong>Yesterday</strong><br>↓ ${formatEnergy(totals.yesterdayImport)} · ↑ ${formatEnergy(totals.yesterdayExport)}</div>
    </div>`;
}

function refreshBadges(panel, root) {
  const attrs = optimizeAttrs(panel);
  const scan = Number(attrs.telemetry_refresh_seconds) || 10;
  const optim = Number(attrs.optimization_interval_minutes) || 60;
  const targets = [
    [".ep-flow-overview", `telemetry ${scan}s`],
    [".energy-card.solar", `refresh ${scan}s`],
    [".energy-card.home", `refresh ${scan}s`],
    [".energy-card.grid", `refresh ${scan}s`],
    [".energy-card.battery", `refresh ${scan}s`],
    [".panel-card.controller", `telemetry ${scan}s`],
    [".panel-card.thermal", `refresh ${scan}s`],
    [".panel-card.emhass", `${optim}m + events`],
    [".panel-card.diagnostics", `telemetry ${scan}s`],
  ];
  for (const [selector, text] of targets) {
    const card = root.querySelector(selector);
    if (!card || card.querySelector(".ep-v013-refresh")) continue;
    const badge = document.createElement("span");
    badge.className = "ep-v013-refresh";
    badge.textContent = text;
    card.appendChild(badge);
  }
}

function correctPowerSemantics(panel, root) {
  const rawLoad = panel._numberByKey("total_load_power");
  const grid = panel._numberByKey("meter_total_power_fast");
  const attrs = optimizeAttrs(panel);
  const phaseSum = Number(attrs.house_load_phase_sum);
  const systemBalance = Number(
    attrs.system_balance_power ?? attrs.house_load_power_balance
  );

  const homeCard = root.querySelector(".energy-card.home");
  if (homeCard && Number.isFinite(rawLoad)) {
    homeCard.querySelector(".hero-value").textContent = panel._formatPower(rawLoad);
    homeCard.querySelector(".hero-sub").textContent = "GoodWe load · register 35172";
    const rows = homeCard.querySelectorAll(".balance-row");
    if (rows[0]) {
      rows[0].querySelector("span").textContent = "Load phase sum";
      rows[0].querySelector("strong").textContent = panel._formatPower(phaseSum);
    }
    if (rows[1]) {
      rows[1].querySelector("span").textContent = "System power balance";
      rows[1].querySelector("strong").textContent = panel._formatPower(systemBalance);
    }
  }

  const flowHouseValue = root.querySelector(".ep-flow-house .ep-flow-node-value");
  const flowHouseSub = root.querySelector(".ep-flow-house .ep-flow-node-sub");
  if (flowHouseValue && Number.isFinite(rawLoad)) flowHouseValue.textContent = panel._formatPower(rawLoad);
  if (flowHouseSub) flowHouseSub.textContent = "GoodWe load 35172";

  // Keep the signed raw grid value in diagnostics/history, but make the primary
  // card easier to read: direction is already communicated by the Importing/
  // Exporting pill.
  const gridCard = root.querySelector(".energy-card.grid");
  if (gridCard && Number.isFinite(grid)) {
    const hero = gridCard.querySelector(".hero-value");
    const sub = gridCard.querySelector(".hero-sub");
    if (hero) hero.textContent = panel._formatPower(Math.abs(grid));
    if (sub) sub.textContent = grid < -50 ? "Import from grid · GoodWe smart meter" : grid > 50 ? "Export to grid · GoodWe smart meter" : "Grid balanced · GoodWe smart meter";
  }
  const flowGridValue = root.querySelector(".ep-flow-grid .ep-flow-node-value");
  if (flowGridValue && Number.isFinite(grid)) flowGridValue.textContent = panel._formatPower(Math.abs(grid));
}

function installSocInfo(panel, root) {
  for (const wrap of root.querySelectorAll(".ep-v011-soc-wrap")) {
    const label = wrap.querySelector(".ep-v011-soc-label span:first-child");
    if (!label || label.querySelector(".ep-v013-soc-info")) continue;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "ep-v013-soc-info";
    button.textContent = "i";
    button.title = "SOC guidance";
    label.appendChild(button);
    button.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      openInfoModal(
        "Battery SOC limits",
        `<p><strong>EnergyPilot recommendation for normal grid-connected cycling:</strong> use roughly <strong>5% minimum</strong> and <strong>95% maximum</strong> unless your battery/inverter requirements say otherwise.</p>
         <p>The EMHASS sliders are optimizer constraints only. GoodWe/SEMS+ and the battery BMS keep their own protection limits and always win. For example, if the GoodWe on-grid minimum SOC is 10%, a mode 12 discharge request can stop at about 10% even when EMHASS requests a lower target.</p>
         <p>Off-grid reserve is a separate safety setting and can require a substantially higher minimum.</p>`
      );
    });
  }
}

function modalStyles() {
  return `
    <style>
      .ep13-backdrop{position:fixed;inset:0;z-index:10050;background:rgba(1,8,20,.72);backdrop-filter:blur(5px);display:grid;place-items:center;padding:20px;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#edf8ff}
      .ep13-modal{width:min(920px,96vw);max-height:88vh;overflow:auto;border-radius:20px;border:1px solid rgba(77,185,255,.25);background:linear-gradient(150deg,#0a1b37,#071328);box-shadow:0 28px 90px rgba(0,0,0,.55);padding:20px}
      .ep13-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-bottom:16px}.ep13-kicker{font-size:10px;letter-spacing:.16em;color:#65e5f9;font-weight:800}.ep13-title{font-size:24px;font-weight:780;margin-top:2px}.ep13-close{appearance:none;width:34px;height:34px;border-radius:10px;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.04);color:#d9ecf8;font-size:20px;cursor:pointer}.ep13-close:hover{background:rgba(255,255,255,.09)}
      .ep13-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.ep13-stat{border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:11px;background:rgba(255,255,255,.025)}.ep13-stat span{display:block;color:#89a4ba;font-size:10px}.ep13-stat strong{display:block;margin-top:4px;font-size:18px}.ep13-chart{margin-top:14px;border:1px solid rgba(255,255,255,.06);border-radius:14px;padding:12px;background:rgba(1,12,29,.38)}.ep13-note{color:#7f9bb2;font-size:10px;line-height:1.5;margin-top:10px}.ep13-loading{padding:60px 10px;text-align:center;color:#8ca9bf}.ep13-info p{color:#b9ccda;line-height:1.55;font-size:13px}.ep13-info p+p{margin-top:12px}.ep13-info strong{color:#f0fbff}
      @media(max-width:620px){.ep13-grid{grid-template-columns:1fr}.ep13-modal{padding:15px}.ep13-title{font-size:20px}}
    </style>`;
}

function createModal(title, kicker = "GW ENERGYPILOT") {
  document.querySelector(".ep13-backdrop")?.remove();
  const backdrop = document.createElement("div");
  backdrop.className = "ep13-backdrop";
  backdrop.innerHTML = `${modalStyles()}<div class="ep13-modal"><div class="ep13-head"><div><div class="ep13-kicker">${kicker}</div><div class="ep13-title">${title}</div></div><button class="ep13-close" aria-label="Close">×</button></div><div class="ep13-body"></div></div>`;
  const close = () => backdrop.remove();
  backdrop.querySelector(".ep13-close")?.addEventListener("click", close);
  backdrop.addEventListener("click", (event) => { if (event.target === backdrop) close(); });
  const esc = (event) => {
    if (event.key === "Escape") {
      document.removeEventListener("keydown", esc);
      close();
    }
  };
  document.addEventListener("keydown", esc);
  document.body.appendChild(backdrop);
  return backdrop.querySelector(".ep13-body");
}

function openInfoModal(title, html) {
  const body = createModal(title, "BATTERY GUIDANCE");
  body.className = "ep13-body ep13-info";
  body.innerHTML = html;
}

function graphSvg(rows) {
  const points = (rows || []).map((row) => ({
    t: typeof row.start === "number" ? row.start : Date.parse(row.start),
    v: Number(row.mean),
  })).filter((point) => Number.isFinite(point.t) && Number.isFinite(point.v));

  if (points.length < 2) return `<div class="ep13-loading">Recorder has not collected enough 5-minute grid statistics yet.</div>`;

  const width = 860;
  const height = 300;
  const left = 52;
  const right = 16;
  const top = 18;
  const bottom = 34;
  const plotW = width - left - right;
  const plotH = height - top - bottom;
  const tMin = points[0].t;
  const tMax = points[points.length - 1].t;
  const peak = Math.max(500, ...points.map((point) => Math.abs(point.v)));
  const yMin = -peak;
  const yMax = peak;
  const x = (t) => left + ((t - tMin) / Math.max(1, tMax - tMin)) * plotW;
  const y = (v) => top + ((yMax - v) / (yMax - yMin)) * plotH;
  const path = points.map((point, index) => `${index ? "L" : "M"}${x(point.t).toFixed(1)},${y(point.v).toFixed(1)}`).join(" ");
  const zeroY = y(0).toFixed(1);
  const lines = [0, .25, .5, .75, 1].map((fraction) => {
    const xx = left + fraction * plotW;
    const timestamp = new Date(tMin + fraction * (tMax - tMin));
    const label = timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    return `<line x1="${xx}" y1="${top}" x2="${xx}" y2="${height-bottom}" stroke="rgba(123,174,207,.08)"/><text x="${xx}" y="${height-10}" text-anchor="middle" fill="#7894aa" font-size="10">${label}</text>`;
  }).join("");
  const peakLabel = peak >= 1000 ? `${(peak/1000).toFixed(1)} kW` : `${Math.round(peak)} W`;

  return `<svg viewBox="0 0 ${width} ${height}" width="100%" role="img" aria-label="Grid power last 24 hours">
    ${lines}
    <line x1="${left}" y1="${zeroY}" x2="${width-right}" y2="${zeroY}" stroke="rgba(190,230,250,.30)" stroke-width="1"/>
    <text x="8" y="${top+8}" fill="#68eab1" font-size="10">Export</text>
    <text x="8" y="${height-bottom-4}" fill="#6edcff" font-size="10">Import</text>
    <text x="${left}" y="${top+8}" fill="#7894aa" font-size="9">±${peakLabel}</text>
    <path d="${path}" fill="none" stroke="#39e4ff" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/>
  </svg>`;
}

async function openGridModal(panel) {
  const body = createModal("Grid · last 24 hours", "GRID DETAIL");
  body.innerHTML = `<div class="ep13-loading">Loading Recorder statistics…</div>`;

  const gridId = panel._entityId("meter_total_power_fast");
  const importId = panel._entityId("meter_total_energy_import");
  const exportId = panel._entityId("meter_total_energy_export");
  const now = new Date();
  const start = new Date(now.getTime() - 24 * 60 * 60 * 1000);

  try {
    const [history, totals] = await Promise.all([
      panel._hass.callWS({
        type: "recorder/statistics_during_period",
        start_time: start.toISOString(),
        end_time: now.toISOString(),
        statistic_ids: [gridId],
        period: "5minute",
        types: ["mean"],
      }),
      loadDailyGridTotals(panel, true),
    ]);
    const rows = history?.[gridId] || [];
    const importTotal = panel._numberByKey("meter_total_energy_import");
    const exportTotal = panel._numberByKey("meter_total_energy_export");
    body.innerHTML = `
      <div class="ep13-grid">
        <div class="ep13-stat"><span>Today imported</span><strong>${formatEnergy(totals?.todayImport)}</strong></div>
        <div class="ep13-stat"><span>Today exported</span><strong>${formatEnergy(totals?.todayExport)}</strong></div>
        <div class="ep13-stat"><span>Yesterday imported</span><strong>${formatEnergy(totals?.yesterdayImport)}</strong></div>
        <div class="ep13-stat"><span>Yesterday exported</span><strong>${formatEnergy(totals?.yesterdayExport)}</strong></div>
      </div>
      <div class="ep13-chart">${graphSvg(rows)}</div>
      <div class="ep13-note">Signed graph: export is above zero, import below zero. Native GoodWe meter counters: import ${formatEnergy(importTotal)}, export ${formatEnergy(exportTotal)}. Daily values are calculated from Home Assistant Recorder changes, so the first complete yesterday value is available after EnergyPilot has recorded across midnight.</div>`;
  } catch (err) {
    console.error("GW EnergyPilot: unable to load grid detail", err);
    body.innerHTML = `<div class="ep13-loading">Unable to load Recorder grid statistics. The live Grid card remains available.</div>`;
  }
}

function installGridInteraction(panel, root) {
  const card = root.querySelector(".energy-card.grid");
  if (!card) return;
  card.setAttribute("role", "button");
  card.setAttribute("tabindex", "0");
  card.setAttribute("aria-label", "Open grid history and daily totals");
  card.addEventListener("click", () => openGridModal(panel));
  card.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openGridModal(panel);
    }
  });

  if (!card.querySelector(".ep-v013-grid-hint")) {
    const hint = document.createElement("div");
    hint.className = "ep-v013-grid-hint";
    hint.innerHTML = `<span>Click for 24h graph</span><span>daily import / export ›</span>`;
    card.appendChild(hint);
  }
  if (panel.__epV013GridDaily && !card.querySelector(".ep-v013-grid-daily")) {
    card.querySelector(".ep-v013-grid-hint")?.insertAdjacentHTML("beforebegin", dailySummaryHtml(panel.__epV013GridDaily));
  }

  if (!panel.__epV013GridDaily && !panel.__epV013GridDailyPromise) {
    loadDailyGridTotals(panel).then((totals) => {
      if (!totals || !panel.shadowRoot) return;
      const currentCard = panel.shadowRoot.querySelector(".energy-card.grid");
      if (currentCard && !currentCard.querySelector(".ep-v013-grid-daily")) {
        currentCard.querySelector(".ep-v013-grid-hint")?.insertAdjacentHTML("beforebegin", dailySummaryHtml(totals));
      }
    });
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV013Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  ensureStyles(root);
  setParticlePhases(root);
  correctPowerSemantics(this, root);
  refreshBadges(this, root);
  installSocInfo(this, root);
  installGridInteraction(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION}`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION}`;
};
