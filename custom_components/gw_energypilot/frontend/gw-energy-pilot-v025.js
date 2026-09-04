import "./gw-energy-pilot-v024.js?v=1.3.0-beta.1";

const VERSION = "0.25";
const PANEL_NAME = "gw-energypilot-panel";

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

function ensureLogStyles(root) {
  if (root.querySelector("#ep-v025-log-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v025-log-style";
  style.textContent = `
    .ep-v025-log-toolbar {
      display:flex; align-items:center; justify-content:space-between; gap:12px;
      margin:0 0 14px; padding:10px 12px; border:1px solid rgba(67,196,224,.13);
      border-radius:11px; color:#83a9bd; background:rgba(8,43,66,.30);
      font-size:9px; line-height:1.5;
    }
    .ep-v025-log-refresh {
      min-height:34px; padding:7px 11px; border-radius:9px;
      border:1px solid rgba(77,176,229,.18); color:#b6d7e7;
      background:rgba(9,42,70,.48); cursor:pointer; font-size:9px; font-weight:800;
    }
    .ep-v025-log-refresh:disabled { opacity:.45; cursor:wait; }
    .ep-v025-log-list { display:grid; gap:9px; }
    .ep-v025-log-row {
      display:grid; grid-template-columns:150px 110px 80px minmax(0,1fr); gap:12px;
      align-items:start; padding:12px 13px; border:1px solid rgba(79,162,211,.10);
      border-radius:12px; background:rgba(7,29,51,.38); color:#8ca8ba;
      font-size:9px;
    }
    .ep-v025-log-time { color:#c8dde9; font-weight:760; }
    .ep-v025-log-reason { color:#9edff4; font-weight:760; word-break:break-word; }
    .ep-v025-log-status { font-weight:850; }
    .ep-v025-log-status.ok { color:#68ddb0; }
    .ep-v025-log-status.error { color:#f0a29c; }
    .ep-v025-log-details { display:flex; flex-wrap:wrap; gap:5px 12px; line-height:1.45; }
    .ep-v025-log-details span strong { color:#bdd8e5; font-weight:700; }
    .ep-v025-log-error {
      grid-column:1/-1; padding-top:8px; border-top:1px solid rgba(240,162,156,.10);
      color:#e9aaa4; line-height:1.45; word-break:break-word;
    }
    .ep-v025-log-empty {
      padding:55px 20px; text-align:center; color:#7597ad; font-size:11px;
      border:1px dashed rgba(79,162,211,.13); border-radius:12px;
    }
    @media (max-width:900px) {
      .ep-v025-log-row { grid-template-columns:1fr 1fr; }
      .ep-v025-log-details { grid-column:1/-1; }
    }
    @media (max-width:600px) {
      .ep-v025-log-row { grid-template-columns:1fr; }
      .ep-v025-log-details, .ep-v025-log-error { grid-column:1; }
      .ep-v025-log-toolbar { align-items:flex-start; flex-direction:column; }
    }
  `;
  root.appendChild(style);
}

function formatTimestamp(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function formatNumber(value, suffix = "") {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  return Number.isFinite(number) ? `${number}${suffix}` : String(value);
}

async function loadOptimizationLog(panel, force = false) {
  const entryId = panel.__epV016SettingsData?.entry_id;
  if (!panel._hass?.callWS || !entryId || panel.__epV025LogLoading) return;
  if (!force && panel.__epV025LogData?.entry_id === entryId) return;

  panel.__epV025LogLoading = true;
  panel.__epV025LogError = null;
  panel._queueRender();
  try {
    panel.__epV025LogData = await panel._hass.callWS({
      type: "gw_energypilot/optimization_log/get",
      entry_id: entryId,
    });
  } catch (err) {
    console.error("GW EnergyPilot: optimization log load failed", err);
    panel.__epV025LogError = err?.message || String(err);
  } finally {
    panel.__epV025LogLoading = false;
    panel._queueRender();
  }
}

function renderOptimizationLog(panel, root) {
  const shell = root.querySelector(".ep-v016-settings");
  if (!shell) return;

  const nav = shell.querySelector(".ep-v016-settings-nav");
  const content = shell.querySelector(".ep-v016-settings-content");
  if (!nav || !content) return;

  let logTab = nav.querySelector("[data-v025-log-tab]");
  if (!logTab) {
    logTab = document.createElement("button");
    logTab.type = "button";
    logTab.className = "ep-v016-tab";
    logTab.dataset.v025LogTab = "1";
    logTab.innerHTML = "<span>LOG</span><small>›</small>";
    nav.appendChild(logTab);
    logTab.addEventListener("click", () => {
      panel.__epV025LogOpen = true;
      panel.__epV016Message = null;
      panel._queueRender();
      loadOptimizationLog(panel);
    });
  }

  shell.querySelectorAll("[data-settings-tab]").forEach((button) => {
    if (button.__epV025LogBound) return;
    button.__epV025LogBound = true;
    button.addEventListener("click", () => {
      panel.__epV025LogOpen = false;
    });
  });

  if (!panel.__epV025LogOpen) {
    logTab.classList.remove("active");
    return;
  }

  shell.querySelectorAll(".ep-v016-tab").forEach((button) => button.classList.remove("active"));
  logTab.classList.add("active");

  const entryId = panel.__epV016SettingsData?.entry_id;
  if (entryId && panel.__epV025LogData?.entry_id !== entryId && !panel.__epV025LogLoading) {
    loadOptimizationLog(panel);
  }

  const history = [...(panel.__epV025LogData?.history || [])].reverse();
  let body;
  if (panel.__epV025LogLoading && !panel.__epV025LogData) {
    body = `<div class="ep-v025-log-empty">Loading optimization history…</div>`;
  } else if (panel.__epV025LogError) {
    body = `<div class="ep-v025-log-empty">Unable to load optimization history: ${panel._escape(panel.__epV025LogError)}</div>`;
  } else if (history.length === 0) {
    body = `<div class="ep-v025-log-empty">No EnergyPilot-owned optimization attempts have been recorded yet.</div>`;
  } else {
    body = `<div class="ep-v025-log-list">${history.map((record) => {
      const statusClass = record.success ? "ok" : "error";
      const statusText = record.success ? "SUCCESS" : "FAILED";
      const error = record.error
        ? `<div class="ep-v025-log-error"><strong>Error:</strong> ${panel._escape(record.error)}</div>`
        : "";
      return `
        <div class="ep-v025-log-row">
          <div class="ep-v025-log-time">${panel._escape(formatTimestamp(record.started_at))}</div>
          <div class="ep-v025-log-reason">${panel._escape(record.reason || "unknown")}</div>
          <div class="ep-v025-log-status ${statusClass}">${statusText}</div>
          <div class="ep-v025-log-details">
            <span><strong>SOC</strong> ${panel._escape(formatNumber(record.soc_init))} → ${panel._escape(formatNumber(record.soc_final))}</span>
            <span><strong>Load</strong> ${panel._escape(formatNumber(record.current_load, " W"))}</span>
            <span><strong>Prices</strong> ${panel._escape(record.price_source || "—")} · ${panel._escape(formatNumber(record.price_points))} pts</span>
            <span><strong>Forecast</strong> ${panel._escape(formatNumber(record.load_forecast_points))} pts</span>
            <span><strong>P_batt</strong> ${panel._escape(formatNumber(record.p_batt, " W"))}</span>
            <span><strong>HTTP</strong> ${panel._escape(formatNumber(record.optimize_http_status))}/${panel._escape(formatNumber(record.publish_http_status))}</span>
            <span><strong>Duration</strong> ${panel._escape(formatNumber(record.duration_seconds, " s"))}</span>
          </div>
          ${error}
        </div>`;
    }).join("")}</div>`;
  }

  content.innerHTML = `
    <div class="ep-v016-section-head">
      <h3>Optimization log</h3>
      <p>Persistent diagnostics for the latest 50 EnergyPilot-owned optimization attempts. Manual, scheduled and event-triggered runs use the same log.</p>
    </div>
    <div class="ep-v025-log-toolbar">
      <span>Newest run first · read-only · stored per GW EnergyPilot config entry.</span>
      <button type="button" class="ep-v025-log-refresh" ${panel.__epV025LogLoading ? "disabled" : ""}>${panel.__epV025LogLoading ? "Refreshing…" : "Refresh"}</button>
    </div>
    ${body}`;

  content.querySelector(".ep-v025-log-refresh")?.addEventListener("click", () => {
    loadOptimizationLog(panel, true);
  });
}

PanelClass.prototype._render = function energyPilotV025Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  ensureLogStyles(root);
  renderOptimizationLog(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
};
