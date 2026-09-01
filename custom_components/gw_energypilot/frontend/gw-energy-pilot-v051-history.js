import {
  DATA_CACHE_MS,
  finiteNumber,
  language,
  loadChartData,
  timestampMs,
} from "./gw-energy-pilot-v027-battery-plan-data.js?v=1.2.0-beta.1-mobile-sems1";

const PANEL_NAME = "gw-energypilot-panel";
const CARD_ID = "emhass-goodwe-history";
const COMPACT_PAST_MS = 6 * 60 * 60 * 1000;
const COMPACT_FUTURE_MS = 6 * 60 * 60 * 1000;

const COPY = Object.freeze({
  en: Object.freeze({
    eyebrow: "Execution history · ±6 hours",
    title: "EMHASS → GOODWE",
    live: "Live",
    full: "Full 48h + 24h table",
    close: "Close",
    empty: "Execution history starts with the next controller decision.",
    time: "Time",
    plan: "Plan",
    strategy: "Strategy",
    automatic: "Automatic",
    manual: "Manual",
    expected: "Expected",
    actualSoc: "Actual SOC",
    goodwe: "GoodWe",
    status: "Status",
    actuals: "Actuals",
    evidence: "Evidence",
    wantedSoc: "Wanted SOC",
    projected: "Projected",
    verified: "Verified",
    mismatch: "Mismatch",
    unavailable: "Readback unavailable",
    failed: "Write failed",
    waiting: "Waiting",
    skipped: "Already applied",
    evOverride: "EV override",
    solarAssist: "Solar assist",
    gridCharge: "Grid charge",
    pvExport: "Solar export",
    batteryExport: "Battery export",
    sourceNote: "Source labels are estimates from PV, load, battery and grid actuals; unknown residuals are never forced into a source.",
    futureNote: "Future rows assume unchanged strategy and control ownership. EV overrides and GoodWe readback are not predicted.",
  }),
  nl: Object.freeze({
    eyebrow: "Uitvoeringshistorie · ±6 uur",
    title: "EMHASS → GOODWE",
    live: "Live",
    full: "Volledige tabel 48u + 24u",
    close: "Sluiten",
    empty: "De uitvoeringshistorie start bij de volgende controllerbeslissing.",
    time: "Tijd",
    plan: "Plan",
    strategy: "Strategie",
    automatic: "Automatisch",
    manual: "Handmatig",
    expected: "Verwacht",
    actualSoc: "Werkelijke SOC",
    goodwe: "GoodWe",
    status: "Status",
    actuals: "Actuals",
    evidence: "Bewijs",
    wantedSoc: "Gewenste SOC",
    projected: "Projectie",
    verified: "Geverifieerd",
    mismatch: "Afwijking",
    unavailable: "Readback ontbreekt",
    failed: "Write mislukt",
    waiting: "Wachten",
    skipped: "Al toegepast",
    evOverride: "EV-override",
    solarAssist: "Zon helpt laden",
    gridCharge: "Laden uit net",
    pvExport: "Zonexport",
    batteryExport: "Accu-export",
    sourceNote: "Bronlabels zijn schattingen uit PV-, belasting-, accu- en netactuals; onbekende residuen worden niet geforceerd toegewezen.",
    futureNote: "Toekomstregels veronderstellen een ongewijzigde strategie en control-ownership. EV-overrides en GoodWe-readback worden niet voorspeld.",
  }),
});

function copy(panel) {
  return COPY[language(panel)] || COPY.en;
}

function esc(panel, value) {
  return panel._escape(String(value ?? "—"));
}

function formatPower(value, signed = false) {
  const number = finiteNumber(value);
  if (number === null) return "—";
  const sign = signed && number > 0 ? "+" : "";
  return `${sign}${(number / 1000).toFixed(1)} kW`;
}

function formatter(panel, full = false) {
  const execution = panel.__epV027BatteryPlanData?.payload?.execution;
  const locale = panel?._hass?.locale?.language || panel?._hass?.language || undefined;
  const options = full
    ? { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", timeZoneName: "short" }
    : { hour: "2-digit", minute: "2-digit" };
  if (execution?.time_zone) options.timeZone = execution.time_zone;
  try {
    return new Intl.DateTimeFormat(locale, options);
  } catch (_err) {
    delete options.timeZone;
    return new Intl.DateTimeFormat(locale, options);
  }
}

function formatTimestamp(panel, value, full = false) {
  const timestamp = timestampMs(value);
  return timestamp === null ? "—" : formatter(panel, full).format(new Date(timestamp));
}

function modeText(panel, mode, power) {
  const number = finiteNumber(mode);
  if (number === null) return "—";
  const prefix = language(panel) === "nl" ? "Modus" : "Mode";
  const watts = finiteNumber(power);
  return watts === null || watts === 0
    ? `${prefix} ${number}`
    : `${prefix} ${number} · ${formatPower(watts)}`;
}

function planText(row) {
  const battery = row?.plan?.p_batt_w;
  const grid = row?.plan?.p_grid_w;
  if (finiteNumber(grid) === null) return `B ${formatPower(battery, true)}`;
  return `B ${formatPower(battery, true)} · G ${formatPower(grid, true)}`;
}

function ownerText(panel, row) {
  return row?.owner === "manual" ? copy(panel).manual : copy(panel).automatic;
}

function statusModel(panel, row) {
  const text = copy(panel);
  const outcome = row?.outcome || {};
  const command = String(outcome.command || "");
  if (row?.kind === "projection") return { key: "future", label: text.projected };
  if (command.startsWith("ev_")) return { key: "ev", label: text.evOverride };
  if (outcome.write_status === "failed") return { key: "bad", label: text.failed };
  if (outcome.verification_status === "mismatch") return { key: "bad", label: text.mismatch };
  if (outcome.verification_status === "unavailable") return { key: "warn", label: text.unavailable };
  if (outcome.verification_status === "verified") {
    return {
      key: "ok",
      label: outcome.write_status === "skipped_matching_readback" ? text.skipped : text.verified,
    };
  }
  return { key: "warn", label: text.waiting };
}

function sourceModel(panel, row) {
  if (row?.kind === "projection") return null;
  const text = copy(panel);
  const actual = row?.actual || {};
  const battery = finiteNumber(actual.battery_power_w);
  const pv = finiteNumber(actual.pv_power_w);
  const load = finiteNumber(actual.load_power_w);
  const grid = finiteNumber(actual.grid_power_w);
  if (battery !== null && battery < -50 && pv !== null && load !== null && pv > load + 50) {
    return { key: "solar", label: text.solarAssist };
  }
  if (battery !== null && battery < -50 && grid !== null && grid < -50) {
    return { key: "grid", label: text.gridCharge };
  }
  if (grid !== null && grid > 50 && pv !== null && load !== null && pv > load + 50) {
    return { key: "solar", label: text.pvExport };
  }
  if (grid !== null && grid > 50 && battery !== null && battery > 50) {
    return { key: "export", label: text.batteryExport };
  }
  return null;
}

export function executionRows(data) {
  const execution = data?.payload?.execution;
  return [
    ...(execution?.history || []),
    ...(execution?.future || []),
  ].filter((row) => timestampMs(row?.occurred_at) !== null)
    .sort((left, right) => timestampMs(left.occurred_at) - timestampMs(right.occurred_at));
}

export function compactExecutionRows(data) {
  const now = timestampMs(data?.payload?.execution?.now) ?? Date.now();
  const rows = executionRows(data).filter((row) => {
    const timestamp = timestampMs(row.occurred_at);
    return timestamp >= now - COMPACT_PAST_MS && timestamp <= now + COMPACT_FUTURE_MS;
  });
  const past = rows.filter((row) => timestampMs(row.occurred_at) < now).slice(-4);
  const future = rows.filter((row) => timestampMs(row.occurred_at) >= now).slice(0, 4);
  return [...past, ...future];
}

function statusPills(panel, row) {
  const status = statusModel(panel, row);
  const source = sourceModel(panel, row);
  return `<span class="ep-v051-status ${status.key}">${esc(panel, status.label)}</span>${source ? `<span class="ep-v051-status ${source.key}">${esc(panel, source.label)}</span>` : ""}`;
}

function actualsText(row) {
  const actual = row?.actual || {};
  return `B ${formatPower(actual.battery_power_w, true)} · PV ${formatPower(actual.pv_power_w)} · L ${formatPower(actual.load_power_w)} · G ${formatPower(actual.grid_power_w, true)}`;
}

function compactRow(panel, row) {
  const actual = row?.actual || {};
  const outcome = row?.outcome || {};
  const wantedSoc = finiteNumber(row?.plan?.soc_opt_pct);
  return `<tr data-kind="${esc(panel, row?.kind || "history")}">
    <td>${esc(panel, formatTimestamp(panel, row.occurred_at))}</td>
    <td title="${esc(panel, `${copy(panel).wantedSoc}: ${wantedSoc === null ? "—" : `${wantedSoc.toFixed(1)}%`}`)}">${esc(panel, planText(row))}</td>
    <td>${esc(panel, `${row?.configuration?.strategy || "—"} · ${ownerText(panel, row)}`)}</td>
    <td>${esc(panel, modeText(panel, outcome.expected_mode, outcome.expected_setpoint_w))}</td>
    <td>${esc(panel, finiteNumber(actual.battery_soc_pct) === null ? "—" : `${finiteNumber(actual.battery_soc_pct).toFixed(1)}%`)}</td>
    <td>${esc(panel, modeText(panel, outcome.readback_mode, outcome.readback_setpoint_w))}</td>
    <td><div class="ep-v051-statuses">${statusPills(panel, row)}</div></td>
  </tr>`;
}

function fullRow(panel, row) {
  const outcome = row?.outcome || {};
  const wantedSoc = finiteNumber(row?.plan?.soc_opt_pct);
  const evidence = `${outcome.write_status || "—"} · ${outcome.verification_status || "—"}`;
  return `<tr data-kind="${esc(panel, row?.kind || "history")}">
    <td>${esc(panel, formatTimestamp(panel, row.occurred_at, true))}</td>
    <td>${esc(panel, planText(row))}<small>${esc(panel, `${copy(panel).wantedSoc} ${wantedSoc === null ? "—" : `${wantedSoc.toFixed(1)}%`}`)}</small></td>
    <td>${esc(panel, row?.configuration?.strategy || "—")}<small>${esc(panel, `${ownerText(panel, row)} · Hold ${row?.configuration?.battery_hold_deadband_w ?? row?.configuration?.deadband_w ?? "—"} W · Auto ${row?.configuration?.goodwe_auto_deadband_w ?? "—"} W`)}</small></td>
    <td>${esc(panel, modeText(panel, outcome.expected_mode, outcome.expected_setpoint_w))}<small>${esc(panel, outcome.command || "—")}</small></td>
    <td>${esc(panel, modeText(panel, outcome.readback_mode, outcome.readback_setpoint_w))}</td>
    <td>${esc(panel, actualsText(row))}</td>
    <td><div class="ep-v051-statuses">${statusPills(panel, row)}</div></td>
    <td>${esc(panel, evidence)}<small>${esc(panel, outcome.error_type || "")}</small></td>
  </tr>`;
}

function compactBody(panel, data) {
  const text = copy(panel);
  const rows = compactExecutionRows(data);
  if (!rows.length) return `<div class="ep-v051-empty">${esc(panel, text.empty)}</div>`;
  return `<div class="ep-v051-table-wrap"><table><thead><tr><th>${esc(panel, text.time)}</th><th>${esc(panel, text.plan)}</th><th>${esc(panel, text.strategy)}</th><th>${esc(panel, text.expected)}</th><th>${esc(panel, text.actualSoc)}</th><th>${esc(panel, text.goodwe)}</th><th>${esc(panel, text.status)}</th></tr></thead><tbody>${rows.map((row) => compactRow(panel, row)).join("")}</tbody></table></div>`;
}

function closeModal(panel) {
  const modal = panel?.shadowRoot?.querySelector(".ep-v051-history-modal");
  if (!modal) return;
  modal.remove();
  if (panel.__epV051HistoryEscape) {
    globalThis.removeEventListener("keydown", panel.__epV051HistoryEscape);
    panel.__epV051HistoryEscape = null;
  }
}

function openModal(panel) {
  const root = panel?.shadowRoot;
  if (!root) return;
  closeModal(panel);
  const text = copy(panel);
  const data = panel.__epV027BatteryPlanData;
  const rows = executionRows(data);
  const modal = document.createElement("div");
  modal.className = "ep-v051-history-modal";
  modal.setAttribute("role", "dialog");
  modal.setAttribute("aria-modal", "true");
  modal.setAttribute("aria-label", text.title);
  modal.innerHTML = `<section><header><div><small>${esc(panel, text.eyebrow)}</small><h2>${esc(panel, text.title)}</h2></div><button type="button" data-action="close" aria-label="${esc(panel, text.close)}">×</button></header><div class="ep-v051-full-wrap"><table><thead><tr><th>${esc(panel, text.time)}</th><th>${esc(panel, text.plan)}</th><th>${esc(panel, text.strategy)}</th><th>${esc(panel, text.expected)}</th><th>${esc(panel, text.goodwe)}</th><th>${esc(panel, text.actuals)}</th><th>${esc(panel, text.status)}</th><th>${esc(panel, text.evidence)}</th></tr></thead><tbody>${rows.map((row) => fullRow(panel, row)).join("")}</tbody></table></div><footer><span>${esc(panel, text.sourceNote)}</span><span>${esc(panel, text.futureNote)}</span></footer></section>`;
  modal.querySelector('[data-action="close"]')?.addEventListener("click", () => closeModal(panel));
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeModal(panel);
  });
  panel.__epV051HistoryEscape = (event) => {
    if (event.key === "Escape") closeModal(panel);
  };
  globalThis.addEventListener("keydown", panel.__epV051HistoryEscape);
  root.appendChild(modal);
  modal.querySelector('[data-action="close"]')?.focus();
}

function ensureStyles(root) {
  if (!root || root.querySelector("#ep-v051-history-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v051-history-style";
  style.textContent = `
    .ep-v051-history-card{grid-column:1/-1!important;min-width:0;padding:17px 18px 14px;border:1px solid rgba(116,198,232,.20);border-radius:22px;background:rgba(5,18,38,.96);box-shadow:0 18px 50px rgba(0,0,0,.18),inset 0 1px 0 rgba(255,255,255,.035);overflow:hidden}
    .ep-v051-history-head{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:12px}.ep-v051-history-head small{display:block;color:#819caf;font-size:9px;letter-spacing:.04em}.ep-v051-history-head h2{margin:3px 0 0;color:#eff9fd;font-size:18px;letter-spacing:-.02em}.ep-v051-history-actions{display:flex;align-items:center;gap:9px}.ep-v051-live{padding:6px 10px;border:1px solid rgba(65,185,111,.46);border-radius:9px;background:rgba(19,83,50,.32);color:#7aeea6;font-size:9px}.ep-v051-full{min-height:32px;padding:0 12px;border:1px solid rgba(116,198,232,.22);border-radius:9px;background:rgba(9,47,74,.42);color:#c3eff8;cursor:pointer;font:700 9px -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",sans-serif}
    .ep-v051-table-wrap,.ep-v051-full-wrap{overflow:auto;overscroll-behavior:contain;-webkit-overflow-scrolling:touch}.ep-v051-history-card table,.ep-v051-history-modal table{width:100%;border-collapse:collapse;white-space:nowrap;font-size:9px}.ep-v051-history-card th,.ep-v051-history-card td,.ep-v051-history-modal th,.ep-v051-history-modal td{padding:9px 10px;border-bottom:1px solid rgba(116,198,232,.12);text-align:left;color:#cbdce7}.ep-v051-history-card th,.ep-v051-history-modal th{color:#829bac;font-size:8px;font-weight:700;letter-spacing:.04em}.ep-v051-history-card tbody tr[data-kind="projection"] td,.ep-v051-history-modal tbody tr[data-kind="projection"] td{background:rgba(196,181,253,.018)}.ep-v051-history-card tbody tr:last-child td{border-bottom:0}.ep-v051-empty{padding:22px;color:#7895aa;font-size:10px;text-align:center}.ep-v051-statuses{display:flex;align-items:center;gap:5px}.ep-v051-status{display:inline-flex;padding:4px 7px;border:1px solid rgba(124,151,170,.28);border-radius:999px;color:#a8bfcd;font-size:8px}.ep-v051-status.ok{border-color:rgba(65,185,111,.5);color:#72e89d;background:rgba(20,90,52,.22)}.ep-v051-status.bad{border-color:rgba(245,98,98,.5);color:#ff9a9a;background:rgba(118,31,31,.22)}.ep-v051-status.warn,.ep-v051-status.solar,.ep-v051-status.grid,.ep-v051-status.export{border-color:rgba(217,169,40,.5);color:#efc75a;background:rgba(94,68,13,.22)}.ep-v051-status.future,.ep-v051-status.ev{border-color:rgba(170,142,245,.48);color:#c6afff;background:rgba(67,42,118,.24)}
    .ep-v051-history-modal{position:fixed;inset:0;z-index:10001;display:grid;place-items:center;padding:20px;background:rgba(1,8,20,.82);backdrop-filter:none!important;-webkit-backdrop-filter:none!important}.ep-v051-history-modal section{width:min(1500px,96vw);max-height:92dvh;display:flex;flex-direction:column;border:1px solid rgba(116,198,232,.26);border-radius:20px;background:#071a31;box-shadow:0 24px 80px rgba(0,0,0,.5);overflow:hidden}.ep-v051-history-modal header{display:flex;align-items:center;justify-content:space-between;padding:16px 18px;border-bottom:1px solid rgba(116,198,232,.13)}.ep-v051-history-modal header small{color:#819caf;font-size:9px}.ep-v051-history-modal h2{margin:3px 0 0;color:#eff9fd;font-size:20px}.ep-v051-history-modal header button{width:34px;height:34px;border:1px solid rgba(116,198,232,.22);border-radius:10px;background:#0a2845;color:#e7f6fb;font-size:20px;cursor:pointer}.ep-v051-full-wrap{flex:1}.ep-v051-history-modal th{position:sticky;top:0;z-index:1;background:#0a223c}.ep-v051-history-modal td small{display:block;margin-top:3px;color:#668399;font-size:7px}.ep-v051-history-modal footer{display:flex;justify-content:space-between;gap:18px;padding:11px 18px;border-top:1px solid rgba(116,198,232,.13);color:#668399;font-size:8px}
    @media(max-width:720px){.ep-v051-history-card{padding:14px 13px 12px;border-radius:18px}.ep-v051-history-head{align-items:flex-start;flex-direction:column}.ep-v051-history-actions{width:100%;justify-content:space-between}.ep-v051-history-modal{padding:7px}.ep-v051-history-modal section{width:100%;max-height:96dvh;border-radius:15px}.ep-v051-history-modal footer{flex-direction:column}.ep-v051-history-card th,.ep-v051-history-card td{padding:8px}}
  `;
  root.appendChild(style);
}

function bindCard(panel, card) {
  if (!card || card.dataset.epV051Bound === "1") return;
  card.dataset.epV051Bound = "1";
  card.querySelector('[data-action="full-history"]')?.addEventListener("click", () => openModal(panel));
}

function bridgeRefresh(panel) {
  const current = panel.__epV041RefreshBatteryPlan;
  if (typeof current !== "function" || current.__epV051HistoryBridge) return;
  const bridged = () => {
    current.call(panel);
    refreshHistoryCard(panel);
  };
  bridged.__epV051HistoryBridge = true;
  panel.__epV041RefreshBatteryPlan = bridged;
}

export function refreshHistoryCard(panel) {
  const root = panel?.shadowRoot;
  const layout = root?.querySelector(".ep-dashboard-layout");
  if (!root || !layout) return;
  ensureStyles(root);
  bridgeRefresh(panel);
  const duplicates = [...root.querySelectorAll(".ep-v051-history-card")];
  const existing = duplicates[0] || null;
  for (const duplicate of duplicates.slice(1)) duplicate.remove();
  const data = panel.__epV027BatteryPlanData;
  const renderKey = String(data?.at || 0);
  if (existing?.dataset.epRenderKey === renderKey) return;
  const text = copy(panel);
  let card = existing;
  if (!card) {
    card = document.createElement("article");
    card.className = "panel-card ep-v051-history-card";
    card.dataset.epCard = CARD_ID;
    card.dataset.epSpan = "4";
    card.innerHTML = `<div class="ep-v051-history-head"><div><small>${esc(panel, text.eyebrow)}</small><h2>${esc(panel, text.title)}</h2></div><div class="ep-v051-history-actions"><span class="ep-v051-live">${esc(panel, text.live)}</span><button type="button" class="ep-v051-full" data-action="full-history">${esc(panel, text.full)}</button></div></div><div class="ep-v051-history-body"></div><div class="ep-v051-history-note"></div>`;
    const planCard = layout.querySelector(".ep-v027-battery-plan-card");
    if (planCard) planCard.insertAdjacentElement("afterend", card);
    else layout.appendChild(card);
    bindCard(panel, card);
  }
  card.dataset.epRenderKey = renderKey;
  const body = card.querySelector(".ep-v051-history-body");
  if (body) body.innerHTML = compactBody(panel, data);
  const note = card.querySelector(".ep-v051-history-note");
  if (note) {
    note.textContent = `${text.sourceNote} ${text.futureNote}`;
    note.style.cssText = "margin-top:9px;color:#668399;font-size:8px;line-height:1.45";
  }
  if (!data && !panel.__epV027BatteryPlanPromise) void loadChartData(panel);
  else if (data && Date.now() - data.at >= DATA_CACHE_MS && !panel.__epV027BatteryPlanPromise) {
    void loadChartData(panel);
  }
}

function controlSignature(panel, hass = panel?._hass) {
  const keys = ["control_command", "ems_mode", "ems_setpoint"];
  return keys.map((key) => {
    const entityId = panel?._entityId?.(key);
    const state = entityId ? hass?.states?.[entityId] : null;
    return `${entityId || ""}:${state?.last_updated || state?.last_changed || ""}:${state?.state || ""}`;
  }).join("|");
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (PanelClass && !PanelClass.prototype.__epV051HistoryInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV051HistoryRender(...args) {
    const result = previousRender.apply(this, args);
    this.__epV051ControlSignature = controlSignature(this);
    refreshHistoryCard(this);
    return result;
  };

  const descriptor = Object.getOwnPropertyDescriptor(PanelClass.prototype, "hass");
  if (descriptor?.set) {
    Object.defineProperty(PanelClass.prototype, "hass", {
      configurable: descriptor.configurable,
      enumerable: descriptor.enumerable,
      get() {
        return descriptor.get ? descriptor.get.call(this) : this._hass;
      },
      set(value) {
        const previousSignature = this.__epV051ControlSignature;
        descriptor.set.call(this, value);
        const nextSignature = controlSignature(this, value);
        this.__epV051ControlSignature = nextSignature;
        refreshHistoryCard(this);
        if (
          previousSignature && nextSignature !== previousSignature &&
          !this.__epV027BatteryPlanPromise
        ) {
          void loadChartData(this, true);
        }
      },
    });
  }

  PanelClass.prototype.__epV051HistoryInstalled = true;
}
