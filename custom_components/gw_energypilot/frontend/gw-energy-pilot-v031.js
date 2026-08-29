import "./gw-energy-pilot-v030.js?v=0.46-external-pv1";

const VERSION = "0.31";
const PANEL_NAME = "gw-energypilot-panel";
const AUTO_REFRESH_MS = 3000;
const VISIBLE_EVENTS = 80;

const TEXT = {
  en: {
    title: "Debug session",
    description: "Temporary high-detail capture for problem analysis. Records GoodWe telemetry/poll health, controller decisions and read-back, configured source changes and EMHASS/orchestrator state. Debug data is memory-only and disappears on integration reload or Home Assistant restart.",
    active: "DEBUG ACTIVE",
    off: "DEBUG OFF",
    start: "Start debug logging",
    stop: "Stop debug logging",
    refresh: "Refresh",
    refreshing: "Refreshing…",
    copy: "Copy debug report",
    copied: "Copied",
    clear: "Clear captured data",
    admin: "Administrator access is required for debug logging.",
    unavailable: "Debug session unavailable",
    events: "events",
    dropped: "dropped",
    started: "Started",
    stopped: "Stopped",
    retained: "Stopping capture keeps the session available here until it is cleared, reloaded or Home Assistant restarts.",
    privacy: "The report intentionally excludes the configured GoodWe host and EMHASS URL. Entity IDs and diagnostic values are included because they are needed for support analysis.",
    empty: "No debug events captured. Start debug logging, reproduce the problem, then stop and copy the report.",
    latest: "Latest debug events",
  },
  nl: {
    title: "Debugsessie",
    description: "Tijdelijke detailregistratie voor probleemanalyse. Registreert GoodWe-telemetrie/pollstatus, controllerbeslissingen en teruglezing, wijzigingen van ingestelde bronnen en EMHASS/orchestrator-status. Debugdata staat alleen in geheugen en verdwijnt bij een integratie-reload of Home Assistant-herstart.",
    active: "DEBUG ACTIEF",
    off: "DEBUG UIT",
    start: "Debug logging starten",
    stop: "Debug logging stoppen",
    refresh: "Vernieuwen",
    refreshing: "Vernieuwen…",
    copy: "Debugrapport kopiëren",
    copied: "Gekopieerd",
    clear: "Vastgelegde data wissen",
    admin: "Beheerdersrechten zijn vereist voor debug logging.",
    unavailable: "Debugsessie niet beschikbaar",
    events: "events",
    dropped: "vervallen",
    started: "Gestart",
    stopped: "Gestopt",
    retained: "Na stoppen blijft de sessie hier beschikbaar totdat je wist, de integratie herlaadt of Home Assistant herstart.",
    privacy: "Het rapport bevat bewust niet de ingestelde GoodWe-host of EMHASS-URL. Entity-ID's en diagnostische waarden worden wel opgenomen omdat die nodig zijn voor supportanalyse.",
    empty: "Nog geen debug-events vastgelegd. Start debug logging, reproduceer het probleem, stop daarna en kopieer het rapport.",
    latest: "Laatste debug-events",
  },
};

function language(panel) {
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function text(panel) {
  return TEXT[language(panel)] || TEXT.en;
}

function entryId(panel) {
  return panel.__epV016SettingsData?.entry_id || null;
}

function formatTimestamp(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v031-debug-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v031-debug-style";
  style.textContent = `
    .ep-v031-debug {
      margin:0 0 16px; padding:13px; border:1px solid rgba(63,197,222,.16);
      border-radius:13px; background:linear-gradient(145deg,rgba(6,35,57,.62),rgba(5,25,44,.72));
    }
    .ep-v031-debug.active { border-color:rgba(44,229,176,.36); box-shadow:inset 0 0 22px rgba(35,221,172,.04); }
    .ep-v031-debug-head { display:flex; align-items:flex-start; justify-content:space-between; gap:14px; }
    .ep-v031-debug-title { color:#e5f5fb; font-size:12px; font-weight:850; }
    .ep-v031-debug-description { max-width:860px; margin-top:4px; color:#7698ac; font-size:8px; line-height:1.5; }
    .ep-v031-debug-badge {
      flex:0 0 auto; padding:5px 8px; border:1px solid rgba(116,146,164,.18); border-radius:999px;
      color:#819bad; background:rgba(55,69,80,.18); font-size:7px; font-weight:900; letter-spacing:.09em;
    }
    .ep-v031-debug-badge.active { color:#93f4d0; border-color:rgba(42,230,172,.40); background:rgba(17,105,82,.28); }
    .ep-v031-debug-meta { display:flex; flex-wrap:wrap; gap:6px 14px; margin:11px 0 0; color:#7797a9; font-size:8px; }
    .ep-v031-debug-meta strong { color:#c3dce7; font-weight:760; }
    .ep-v031-debug-actions { display:flex; flex-wrap:wrap; gap:7px; margin-top:11px; }
    .ep-v031-debug-button {
      min-height:33px; padding:7px 10px; border:1px solid rgba(74,176,220,.18); border-radius:9px;
      color:#afd5e3; background:rgba(8,42,68,.52); cursor:pointer; font-size:8px; font-weight:820;
    }
    .ep-v031-debug-button.primary { color:#dffdf3; border-color:rgba(44,225,174,.38); background:rgba(12,91,75,.42); }
    .ep-v031-debug-button.stop { color:#ffd5cd; border-color:rgba(238,139,125,.30); background:rgba(103,45,42,.30); }
    .ep-v031-debug-button:disabled { opacity:.40; cursor:wait; }
    .ep-v031-debug-note { margin-top:10px; color:#607f93; font-size:8px; line-height:1.5; }
    .ep-v031-debug-note + .ep-v031-debug-note { margin-top:3px; }
    .ep-v031-debug-error { margin-top:10px; color:#efa6a0; font-size:8px; line-height:1.45; }
    .ep-v031-event-title { margin:13px 0 7px; color:#86bfd0; font-size:8px; font-weight:850; letter-spacing:.08em; text-transform:uppercase; }
    .ep-v031-events { display:grid; gap:5px; max-height:340px; overflow:auto; padding-right:2px; }
    .ep-v031-event {
      display:grid; grid-template-columns:145px 90px 135px minmax(0,1fr); gap:8px; align-items:start;
      padding:7px 8px; border:1px solid rgba(76,151,191,.08); border-radius:8px; background:rgba(5,25,43,.42);
      color:#7594a6; font-size:7px; line-height:1.4;
    }
    .ep-v031-event-time { color:#a9c3d0; }
    .ep-v031-event-category { color:#67d6e9; font-weight:820; text-transform:uppercase; }
    .ep-v031-event-name { color:#b8d3de; font-weight:760; word-break:break-word; }
    .ep-v031-event-data { color:#7898aa; white-space:pre-wrap; word-break:break-word; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
    .ep-v031-debug-empty { margin-top:11px; padding:13px; border:1px dashed rgba(82,157,194,.12); border-radius:9px; color:#6f8fa2; font-size:8px; }
    @media (max-width:760px) {
      .ep-v031-debug-head { flex-direction:column; }
      .ep-v031-event { grid-template-columns:1fr 1fr; }
      .ep-v031-event-data { grid-column:1/-1; }
    }
    @media (max-width:520px) {
      .ep-v031-event { grid-template-columns:1fr; }
      .ep-v031-event-data { grid-column:1; }
    }
  `;
  root.appendChild(style);
}

async function loadDebug(panel, force = false) {
  const id = entryId(panel);
  if (!panel._hass?.callWS || !id || panel.__epV031DebugLoading) return;
  const now = Date.now();
  if (!force && panel.__epV031DebugData && (!panel.__epV031DebugData.enabled || now - (panel.__epV031DebugLoadedAt || 0) < AUTO_REFRESH_MS)) return;

  panel.__epV031DebugLoading = true;
  panel.__epV031DebugError = null;
  panel._queueRender();
  try {
    panel.__epV031DebugData = await panel._hass.callWS({
      type: "gw_energypilot/debug_log/get",
      entry_id: id,
    });
    panel.__epV031DebugLoadedAt = Date.now();
  } catch (err) {
    panel.__epV031DebugError = err?.message || String(err);
  } finally {
    panel.__epV031DebugLoading = false;
    panel._queueRender();
  }
}

async function setDebugEnabled(panel, enabled) {
  const id = entryId(panel);
  if (!panel._hass?.callWS || !id || panel.__epV031DebugBusy) return;
  panel.__epV031DebugBusy = true;
  panel.__epV031DebugError = null;
  panel._queueRender();
  try {
    panel.__epV031DebugData = await panel._hass.callWS({
      type: "gw_energypilot/debug_log/set_enabled",
      entry_id: id,
      enabled,
    });
    panel.__epV031DebugLoadedAt = Date.now();
  } catch (err) {
    panel.__epV031DebugError = err?.message || String(err);
  } finally {
    panel.__epV031DebugBusy = false;
    panel._queueRender();
  }
}

async function clearDebug(panel) {
  const id = entryId(panel);
  if (!panel._hass?.callWS || !id || panel.__epV031DebugBusy) return;
  panel.__epV031DebugBusy = true;
  panel.__epV031DebugError = null;
  panel._queueRender();
  try {
    panel.__epV031DebugData = await panel._hass.callWS({
      type: "gw_energypilot/debug_log/clear",
      entry_id: id,
    });
    panel.__epV031DebugLoadedAt = Date.now();
  } catch (err) {
    panel.__epV031DebugError = err?.message || String(err);
  } finally {
    panel.__epV031DebugBusy = false;
    panel._queueRender();
  }
}

async function copyReport(panel, button) {
  const copy = text(panel);
  await loadDebug(panel, true);
  const report = {
    product: "GW EnergyPilot",
    version: VERSION,
    generated_at: new Date().toISOString(),
    debug_session: panel.__epV031DebugData || null,
    optimization_history: panel.__epV025LogData?.history || [],
  };
  const value = JSON.stringify(report, null, 2);
  try {
    await navigator.clipboard.writeText(value);
    if (button) {
      button.textContent = copy.copied;
      setTimeout(() => { button.textContent = copy.copy; }, 1200);
    }
  } catch (_err) {
    window.prompt(copy.copy, value);
  }
}

function renderEvents(panel, data, copy) {
  const events = [...(data?.events || [])].reverse().slice(0, VISIBLE_EVENTS);
  if (!events.length) return `<div class="ep-v031-debug-empty">${panel._escape(copy.empty)}</div>`;
  return `
    <div class="ep-v031-event-title">${panel._escape(copy.latest)} · ${events.length}/${data.event_count || events.length}</div>
    <div class="ep-v031-events">
      ${events.map((item) => `
        <div class="ep-v031-event">
          <div class="ep-v031-event-time">${panel._escape(formatTimestamp(item.timestamp))}</div>
          <div class="ep-v031-event-category">${panel._escape(item.category || "—")}</div>
          <div class="ep-v031-event-name">${panel._escape(item.event || "—")}</div>
          <div class="ep-v031-event-data">${panel._escape(JSON.stringify(item.data || {}))}</div>
        </div>`).join("")}
    </div>`;
}

function renderDebug(panel, root) {
  if (!panel.__epV025LogOpen) return;
  const content = root.querySelector(".ep-v016-settings-content");
  if (!content || content.querySelector(".ep-v031-debug")) return;
  const copy = text(panel);
  const admin = panel._hass?.user?.is_admin === true;
  const data = panel.__epV031DebugData;
  const busy = Boolean(panel.__epV031DebugBusy || panel.__epV031DebugLoading);

  if (admin && entryId(panel) && (!data || (data.enabled && Date.now() - (panel.__epV031DebugLoadedAt || 0) >= AUTO_REFRESH_MS))) {
    queueMicrotask(() => loadDebug(panel));
  }

  const wrap = document.createElement("div");
  wrap.className = `ep-v031-debug${data?.enabled ? " active" : ""}`;
  const status = data?.enabled ? copy.active : copy.off;
  const error = panel.__epV031DebugError
    ? `<div class="ep-v031-debug-error">${panel._escape(`${copy.unavailable}: ${panel.__epV031DebugError}`)}</div>`
    : "";
  const adminNote = admin ? "" : `<div class="ep-v031-debug-error">${panel._escape(copy.admin)}</div>`;
  const eventCount = data?.event_count ?? 0;
  const dropped = data?.dropped_events ?? 0;

  wrap.innerHTML = `
    <div class="ep-v031-debug-head">
      <div>
        <div class="ep-v031-debug-title">${panel._escape(copy.title)}</div>
        <div class="ep-v031-debug-description">${panel._escape(copy.description)}</div>
      </div>
      <span class="ep-v031-debug-badge ${data?.enabled ? "active" : ""}">${panel._escape(status)}</span>
    </div>
    <div class="ep-v031-debug-meta">
      <span><strong>${eventCount}</strong> ${panel._escape(copy.events)}</span>
      <span><strong>${dropped}</strong> ${panel._escape(copy.dropped)}</span>
      <span>${panel._escape(copy.started)} · <strong>${panel._escape(formatTimestamp(data?.started_at))}</strong></span>
      ${data?.stopped_at ? `<span>${panel._escape(copy.stopped)} · <strong>${panel._escape(formatTimestamp(data.stopped_at))}</strong></span>` : ""}
    </div>
    <div class="ep-v031-debug-actions">
      <button type="button" class="ep-v031-debug-button ${data?.enabled ? "stop" : "primary"}" data-debug-action="toggle" ${!admin || busy ? "disabled" : ""}>${panel._escape(data?.enabled ? copy.stop : copy.start)}</button>
      <button type="button" class="ep-v031-debug-button" data-debug-action="refresh" ${!admin || busy ? "disabled" : ""}>${panel._escape(panel.__epV031DebugLoading ? copy.refreshing : copy.refresh)}</button>
      <button type="button" class="ep-v031-debug-button" data-debug-action="copy" ${!admin || busy || !data ? "disabled" : ""}>${panel._escape(copy.copy)}</button>
      <button type="button" class="ep-v031-debug-button" data-debug-action="clear" ${!admin || busy || !data ? "disabled" : ""}>${panel._escape(copy.clear)}</button>
    </div>
    <div class="ep-v031-debug-note">${panel._escape(copy.retained)}</div>
    <div class="ep-v031-debug-note">${panel._escape(copy.privacy)}</div>
    ${adminNote}
    ${error}
    ${renderEvents(panel, data, copy)}`;

  const sectionHead = content.querySelector(".ep-v016-section-head");
  if (sectionHead) sectionHead.insertAdjacentElement("afterend", wrap);
  else content.prepend(wrap);

  wrap.querySelector('[data-debug-action="toggle"]')?.addEventListener("click", () => {
    setDebugEnabled(panel, !Boolean(panel.__epV031DebugData?.enabled));
  });
  wrap.querySelector('[data-debug-action="refresh"]')?.addEventListener("click", () => loadDebug(panel, true));
  wrap.querySelector('[data-debug-action="clear"]')?.addEventListener("click", () => clearDebug(panel));
  wrap.querySelector('[data-debug-action="copy"]')?.addEventListener("click", (event) => copyReport(panel, event.currentTarget));
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV031Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  ensureStyles(root);
  renderDebug(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
};
