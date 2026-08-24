import "./gw-energy-pilot-v031-window-controls.js?v=0.31-window2";

const PANEL_NAME = "gw-energypilot-panel";

const TEXT = {
  en: {
    title: "Battery Saver",
    description: "Choose how strongly EnergyPilot values battery preservation inside EMHASS optimization. These are soft economic preferences; the Minimum SOC and Maximum SOC sliders remain the hard operating limits.",
    unmanaged: "Existing EMHASS behavior is not managed by EnergyPilot yet.",
    legacyMadSteve: "The current zero-penalty EMHASS behavior matches Mad-Steve. Select a mode to let EnergyPilot own these settings.",
    custom: "Custom EMHASS battery penalties are active. They are preserved until you explicitly select an EnergyPilot mode.",
    applying: "Applying mode and rebuilding the plan…",
    applied: "Battery Saver mode applied and a new EMHASS plan was published.",
    hardRange: "Hard SOC range",
    low: "Low-SOC soft threshold",
    high: "High-SOC soft threshold",
    effective: "Effective profile",
    priceRef: "price reference",
    recommended: "RECOMMENDED",
    version: "EMHASS",
    unavailable: "Battery Saver status unavailable",
  },
  nl: {
    title: "Battery Saver",
    description: "Kies hoe zwaar EnergyPilot batterijbehoud meeweegt in de EMHASS-optimalisatie. Dit zijn zachte economische voorkeuren; de sliders Minimum SOC en Maximum SOC blijven de harde bedrijfsgrenzen.",
    unmanaged: "Het bestaande EMHASS-gedrag wordt nog niet door EnergyPilot beheerd.",
    legacyMadSteve: "Het huidige EMHASS-gedrag met nul penalties komt overeen met Mad-Steve. Kies een modus om EnergyPilot deze instellingen te laten beheren.",
    custom: "Er zijn custom EMHASS-batterijpenalties actief. Die blijven behouden totdat je expliciet een EnergyPilot-modus kiest.",
    applying: "Modus toepassen en nieuw plan maken…",
    applied: "Battery Saver-modus toegepast en een nieuw EMHASS-plan gepubliceerd.",
    hardRange: "Harde SOC-range",
    low: "Zachte low-SOC-drempel",
    high: "Zachte high-SOC-drempel",
    effective: "Effectief profiel",
    priceRef: "prijsreferentie",
    recommended: "AANBEVOLEN",
    version: "EMHASS",
    unavailable: "Battery Saver-status niet beschikbaar",
  },
};

function language(panel) {
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function copy(panel) {
  return TEXT[language(panel)] || TEXT.en;
}

function entryId(panel) {
  return panel.__epV016SettingsData?.entry_id || null;
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v031-battery-saver-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v031-battery-saver-style";
  style.textContent = `
    .ep-v031-battery-saver {
      margin:0 0 18px; padding:15px; border:1px solid rgba(64,202,221,.17);
      border-radius:14px; background:linear-gradient(145deg,rgba(7,39,61,.58),rgba(5,24,43,.68));
    }
    .ep-v031-bs-head { display:flex; align-items:flex-start; justify-content:space-between; gap:14px; }
    .ep-v031-bs-title { color:#edfaff; font-size:13px; font-weight:880; }
    .ep-v031-bs-description { max-width:820px; margin-top:5px; color:#7596aa; font-size:9px; line-height:1.55; }
    .ep-v031-bs-version { flex:0 0 auto; color:#62869b; font-size:8px; font-weight:760; }
    .ep-v031-bs-status { margin-top:11px; padding:9px 10px; border:1px solid rgba(79,167,205,.10); border-radius:9px; color:#7799ad; background:rgba(4,24,42,.35); font-size:8px; line-height:1.5; }
    .ep-v031-bs-status.ok { color:#83dcb9; border-color:rgba(49,211,157,.16); }
    .ep-v031-bs-status.error { color:#f1aaa3; border-color:rgba(238,139,125,.20); }
    .ep-v031-bs-modes { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:8px; margin-top:13px; }
    .ep-v031-bs-mode {
      position:relative; min-height:112px; padding:12px; border:1px solid rgba(77,164,207,.11); border-radius:11px;
      color:#abc6d4; background:rgba(5,27,47,.50); cursor:pointer; text-align:left;
    }
    .ep-v031-bs-mode:hover { border-color:rgba(54,207,226,.30); background:rgba(7,42,66,.62); }
    .ep-v031-bs-mode.active { border-color:rgba(42,224,183,.38); background:linear-gradient(145deg,rgba(10,81,91,.48),rgba(8,66,52,.45)); box-shadow:inset 0 0 20px rgba(38,220,174,.04); }
    .ep-v031-bs-mode:disabled { opacity:.48; cursor:wait; }
    .ep-v031-bs-mode strong { display:block; color:#e5f5fb; font-size:10px; font-weight:880; }
    .ep-v031-bs-mode p { margin:7px 0 0; color:#688ba0; font-size:8px; line-height:1.45; }
    .ep-v031-bs-mode.active p { color:#88afaf; }
    .ep-v031-bs-rec { position:absolute; top:8px; right:8px; color:#66dfbc; font-size:6px; font-weight:900; letter-spacing:.08em; }
    .ep-v031-bs-thresholds { margin-top:8px; color:#55788d; font-size:7px; }
    .ep-v031-bs-meta { display:flex; flex-wrap:wrap; gap:7px 14px; margin-top:12px; color:#66899e; font-size:8px; }
    .ep-v031-bs-meta strong { color:#c5dce7; font-weight:780; }
    .ep-v031-bs-profile { margin-top:7px; color:#5d7e92; font-size:7px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; word-break:break-word; }
    @media (max-width:900px) { .ep-v031-bs-modes { grid-template-columns:repeat(2,minmax(0,1fr)); } }
    @media (max-width:520px) { .ep-v031-bs-head { flex-direction:column; } .ep-v031-bs-modes { grid-template-columns:1fr; } }
  `;
  root.appendChild(style);
}

async function loadBatterySaver(panel, force = false) {
  const id = entryId(panel);
  if (!panel._hass?.callWS || !id || panel.__epV031BSLoading) return;
  if (!force && panel.__epV031BSData?.entry_id === id) return;
  panel.__epV031BSLoading = true;
  panel.__epV031BSError = null;
  panel._queueRender();
  try {
    panel.__epV031BSData = await panel._hass.callWS({
      type: "gw_energypilot/battery_saver/get",
      entry_id: id,
    });
  } catch (err) {
    panel.__epV031BSError = err?.message || String(err);
  } finally {
    panel.__epV031BSLoading = false;
    panel._queueRender();
  }
}

async function setBatterySaverMode(panel, mode) {
  const id = entryId(panel);
  if (!panel._hass?.callWS || !id || panel.__epV031BSBusy) return;
  const t = copy(panel);
  panel.__epV031BSBusy = true;
  panel.__epV031BSError = null;
  panel.__epV031BSMessage = t.applying;
  panel._queueRender();
  try {
    panel.__epV031BSData = await panel._hass.callWS({
      type: "gw_energypilot/battery_saver/set",
      entry_id: id,
      mode,
    });
    panel.__epV031BSMessage = t.applied;
  } catch (err) {
    panel.__epV031BSError = err?.message || String(err);
    panel.__epV031BSMessage = null;
  } finally {
    panel.__epV031BSBusy = false;
    panel._queueRender();
  }
}

function pct(value) {
  return Number.isFinite(Number(value)) ? `${Number(value).toFixed(0)}%` : "—";
}

function renderBatterySaver(panel, root) {
  if (!panel.__epV016SettingsOpen || panel.__epV016SettingsTab !== "emhass") return;
  const content = root.querySelector(".ep-v016-settings-content");
  if (!content || content.querySelector(".ep-v031-battery-saver")) return;
  const id = entryId(panel);
  if (!id) return;
  const t = copy(panel);
  const data = panel.__epV031BSData?.entry_id === id ? panel.__epV031BSData : null;
  const busy = Boolean(panel.__epV031BSBusy || panel.__epV031BSLoading);

  if (!data && !panel.__epV031BSLoading && !panel.__epV031BSError) {
    queueMicrotask(() => loadBatterySaver(panel));
  }

  const wrap = document.createElement("section");
  wrap.className = "ep-v031-battery-saver";

  let statusText = "";
  let statusTone = "";
  if (panel.__epV031BSError) {
    statusText = `${t.unavailable}: ${panel.__epV031BSError}`;
    statusTone = "error";
  } else if (panel.__epV031BSMessage) {
    statusText = panel.__epV031BSMessage;
    statusTone = "ok";
  } else if (data && !data.managed) {
    statusText = data.legacy_behavior === "mad_steve" ? t.legacyMadSteve : t.custom;
  }

  const modes = (data?.modes || []).map((mode) => `
    <button type="button" class="ep-v031-bs-mode ${data?.mode === mode.key ? "active" : ""}" data-bs-mode="${panel._escape(mode.key)}" ${busy ? "disabled" : ""}>
      ${mode.recommended ? `<span class="ep-v031-bs-rec">${panel._escape(t.recommended)}</span>` : ""}
      <strong>${panel._escape(mode.label)}</strong>
      <p>${panel._escape(mode.description)}</p>
      <div class="ep-v031-bs-thresholds">${panel._escape(t.low)} ${mode.deficit_threshold_pct}% · ${panel._escape(t.high)} ${mode.surplus_threshold_pct}%</div>
    </button>`).join("");

  const profile = data?.effective_profile;
  const profileText = profile
    ? `${t.effective}: deficit ${profile.battery_soc_deficit_cost} · surplus ${profile.battery_soc_surplus_cost} · stress ${profile.battery_stress_cost} · ${t.priceRef} ${profile.price_reference}`
    : "";

  wrap.innerHTML = `
    <div class="ep-v031-bs-head">
      <div>
        <div class="ep-v031-bs-title">${panel._escape(t.title)}</div>
        <div class="ep-v031-bs-description">${panel._escape(t.description)}</div>
      </div>
      <div class="ep-v031-bs-version">${panel._escape(t.version)} ${panel._escape(data?.emhass_version || "—")}</div>
    </div>
    ${statusText ? `<div class="ep-v031-bs-status ${statusTone}">${panel._escape(statusText)}</div>` : ""}
    ${modes ? `<div class="ep-v031-bs-modes">${modes}</div>` : ""}
    <div class="ep-v031-bs-meta">
      <span>${panel._escape(t.hardRange)} · <strong>${pct(data?.hard_minimum_soc_pct)} – ${pct(data?.hard_maximum_soc_pct)}</strong></span>
      ${data?.battery_count ? `<span>EMHASS batteries · <strong>${panel._escape(data.battery_count)}</strong></span>` : ""}
    </div>
    ${profileText ? `<div class="ep-v031-bs-profile">${panel._escape(profileText)}</div>` : ""}`;

  const note = content.querySelector(".ep-v016-emhass-note");
  if (note) note.insertAdjacentElement("afterend", wrap);
  else content.prepend(wrap);

  wrap.querySelectorAll("[data-bs-mode]").forEach((button) => {
    button.addEventListener("click", () => setBatterySaverMode(panel, button.dataset.bsMode));
  });
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV031BatterySaverRender() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;
  ensureStyles(root);
  renderBatterySaver(this, root);
};
