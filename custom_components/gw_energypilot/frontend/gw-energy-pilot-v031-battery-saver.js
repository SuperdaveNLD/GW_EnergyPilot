import "./gw-energy-pilot-v031-window-controls.js?v=0.50-ev1";

const PANEL_NAME = "gw-energypilot-panel";
const CUSTOM_MODE = "custom";

const TEXT = {
  en: {
    title: "Battery Saver",
    description: "Choose how strongly EnergyPilot values battery preservation inside EMHASS optimization. A managed profile sets the EMHASS Maximum SOC; the GoodWe-synchronized Minimum SOC remains the hard lower operating limit.",
    unmanaged: "Existing EMHASS behavior is not managed by EnergyPilot yet.",
    legacyMadSteve: "Legacy zero-cost EMHASS behavior is more aggressive than current Mad-Steve. Select a mode to add the shared anti-churn trading cost.",
    custom: "Custom EMHASS battery costs are active. Edit and save them below, or choose a managed EnergyPilot profile.",
    customLabel: "Custom",
    customDescription: "Keep direct control of the five EMHASS battery cost values.",
    customTitle: "Custom battery costs",
    deficit: "Low-SOC cost",
    surplus: "High-SOC cost",
    stress: "Power stress",
    chargeWeight: "Charge cost",
    dischargeWeight: "Discharge cost",
    saveCustom: "Save and optimize",
    savingCustom: "Saving custom values and rebuilding the plan…",
    savedCustom: "Custom values saved and a new EMHASS plan was published.",
    customError: "Custom values could not be saved",
    singleBatteryOnly: "Custom value editing is available for one EMHASS battery.",
    applying: "Applying mode and rebuilding the plan…",
    applied: "Battery Saver mode applied and a new EMHASS plan was published.",
    hardRange: "Hard SOC range",
    low: "Low-SOC soft threshold",
    high: "High-SOC soft threshold",
    maximum: "Hard maximum",
    effective: "Effective profile",
    priceRef: "price reference",
    recommended: "RECOMMENDED",
    version: "EMHASS",
    unavailable: "Battery Saver status unavailable",
  },
  nl: {
    title: "Battery Saver",
    description: "Kies hoe zwaar EnergyPilot batterijbehoud meeweegt in de EMHASS-optimalisatie. Een beheerd profiel stelt de EMHASS Maximum SOC in; de met GoodWe gesynchroniseerde Minimum SOC blijft de harde ondergrens.",
    unmanaged: "Het bestaande EMHASS-gedrag wordt nog niet door EnergyPilot beheerd.",
    legacyMadSteve: "Het oude EMHASS-gedrag zonder kosten is agressiever dan de huidige Mad-Steve. Kies een modus om de gedeelde anti-churn handelskosten toe te passen.",
    custom: "Aangepaste EMHASS-batterijkosten zijn actief. Bewerk en bewaar ze hieronder, of kies een beheerd EnergyPilot-profiel.",
    customLabel: "Aangepast",
    customDescription: "Beheer de vijf EMHASS-batterijkosten rechtstreeks.",
    customTitle: "Aangepaste batterijkosten",
    deficit: "Kosten lage SOC",
    surplus: "Kosten hoge SOC",
    stress: "Vermogensstress",
    chargeWeight: "Laadkosten",
    dischargeWeight: "Ontlaadkosten",
    saveCustom: "Opslaan en optimaliseren",
    savingCustom: "Aangepaste waarden opslaan en nieuw plan maken…",
    savedCustom: "Aangepaste waarden opgeslagen en een nieuw EMHASS-plan gepubliceerd.",
    customError: "Aangepaste waarden konden niet worden opgeslagen",
    singleBatteryOnly: "Aangepaste waarden kunnen voor één EMHASS-batterij worden bewerkt.",
    applying: "Modus toepassen en nieuw plan maken…",
    applied: "Battery Saver-modus toegepast en een nieuw EMHASS-plan gepubliceerd.",
    hardRange: "Harde SOC-range",
    low: "Zachte low-SOC-drempel",
    high: "Zachte high-SOC-drempel",
    maximum: "Harde maximum-SOC",
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

function shareBatterySaverData(panel, data) {
  panel.__epV031BSData = data;
  if (panel.__epV038BatterySaver) panel.__epV038BatterySaver.data = data;
  return data;
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
    .ep-v031-bs-title { color:#edfaff; font-size:16px; font-weight:880; }
    .ep-v031-bs-description { max-width:920px; margin-top:5px; color:#819fb1; font-size:11px; line-height:1.55; }
    .ep-v031-bs-version { flex:0 0 auto; color:#7797aa; font-size:10px; font-weight:760; }
    .ep-v031-bs-status { margin-top:11px; padding:9px 10px; border:1px solid rgba(79,167,205,.10); border-radius:9px; color:#88a7b8; background:rgba(4,24,42,.35); font-size:10px; line-height:1.5; }
    .ep-v031-bs-status.ok { color:#83dcb9; border-color:rgba(49,211,157,.16); }
    .ep-v031-bs-status.error { color:#f1aaa3; border-color:rgba(238,139,125,.20); }
    .ep-v031-bs-modes { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; margin-top:13px; }
    .ep-v031-bs-mode {
      position:relative; min-height:112px; padding:12px; border:1px solid rgba(77,164,207,.11); border-radius:11px;
      color:#abc6d4; background:rgba(5,27,47,.50); cursor:pointer; text-align:left;
    }
    .ep-v031-bs-mode:hover { border-color:rgba(54,207,226,.30); background:rgba(7,42,66,.62); }
    .ep-v031-bs-mode.active { border-color:rgba(42,224,183,.38); background:linear-gradient(145deg,rgba(10,81,91,.48),rgba(8,66,52,.45)); box-shadow:inset 0 0 20px rgba(38,220,174,.04); }
    .ep-v031-bs-mode:disabled { opacity:.48; cursor:wait; }
    .ep-v031-bs-mode strong { display:block; padding-right:28px; color:#e5f5fb; font-size:12px; font-weight:880; }
    .ep-v031-bs-mode p { margin:7px 0 0; color:#7899ab; font-size:10px; line-height:1.45; }
    .ep-v031-bs-mode.active p { color:#88afaf; }
    .ep-v031-bs-rec { position:absolute; top:8px; right:8px; color:#66dfbc; font-size:8px; font-weight:900; letter-spacing:.08em; }
    .ep-v031-bs-thresholds { margin-top:8px; color:#698a9e; font-size:9px; }
    .ep-v031-bs-meta { display:flex; flex-wrap:wrap; gap:7px 14px; margin-top:12px; color:#7798aa; font-size:10px; }
    .ep-v031-bs-meta strong { color:#c5dce7; font-weight:780; }
    .ep-v031-bs-profile { margin-top:7px; color:#6f90a2; font-size:9px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; word-break:break-word; }
    .ep-v031-bs-custom { margin-top:12px; padding:11px; border:1px solid rgba(70,181,211,.13); border-radius:10px; background:rgba(4,24,42,.38); }
    .ep-v031-bs-custom-title { color:#dceff6; font-size:12px; font-weight:850; }
    .ep-v031-bs-custom-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; margin-top:9px; }
    .ep-v031-bs-custom-field { display:block; min-width:0; color:#7899aa; font-size:9px; }
    .ep-v031-bs-custom-field input {
      box-sizing:border-box; width:100%; min-width:0; min-height:36px; margin-top:5px; padding:7px 8px;
      border:1px solid rgba(80,178,215,.22); border-radius:7px; outline:none;
      color:#d9edf5; background:rgba(3,20,36,.72); font:750 11px ui-monospace,SFMono-Regular,Menlo,monospace;
    }
    .ep-v031-bs-custom-field input:focus { border-color:rgba(43,221,185,.62); box-shadow:0 0 0 2px rgba(43,221,185,.10); }
    .ep-v031-bs-custom-field input:disabled { opacity:.55; }
    .ep-v031-bs-custom-actions { display:flex; justify-content:flex-end; margin-top:10px; }
    .ep-v031-bs-custom-save {
      min-height:37px; padding:8px 13px; border:1px solid rgba(42,224,183,.42); border-radius:8px;
      color:#defcf2; background:rgba(10,88,72,.58); cursor:pointer; font-size:10px; font-weight:850;
    }
    .ep-v031-bs-custom-save:disabled { opacity:.5; cursor:wait; }
    .ep-v031-bs-custom-note { margin-top:8px; color:#7899aa; font-size:9px; line-height:1.5; }
    @media (max-width:1100px) { .ep-v031-bs-modes,.ep-v031-bs-custom-grid { grid-template-columns:repeat(3,minmax(0,1fr)); } }
    @media (max-width:900px) { .ep-v031-bs-modes,.ep-v031-bs-custom-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
    @media (max-width:520px) { .ep-v031-bs-head { flex-direction:column; } .ep-v031-bs-modes,.ep-v031-bs-custom-grid { grid-template-columns:1fr; } }
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
    shareBatterySaverData(panel, await panel._hass.callWS({
      type: "gw_energypilot/battery_saver/get",
      entry_id: id,
    }));
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
    shareBatterySaverData(panel, await panel._hass.callWS({
      type: "gw_energypilot/battery_saver/set",
      entry_id: id,
      mode,
    }));
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
  if (value === null || value === undefined || value === "") return "—";
  return Number.isFinite(Number(value)) ? `${Number(value).toFixed(0)}%` : "—";
}

function firstWeight(value) {
  if (Array.isArray(value)) return value.length ? value[0] : null;
  return value ?? null;
}

function inputValue(value) {
  const raw = firstWeight(value);
  if (raw === null || raw === undefined || raw === "") return "";
  const number = Number(raw);
  return Number.isFinite(number) && number >= 0
    ? String(Math.round(number * 1000000) / 1000000)
    : "";
}

function customEditorHtml(panel, t, data, busy) {
  const values = data?.current_emhass_values || {};
  const fields = [
    ["battery_soc_deficit_cost", t.deficit],
    ["battery_soc_surplus_cost", t.surplus],
    ["battery_stress_cost", t.stress],
    ["weight_battery_charge", t.chargeWeight],
    ["weight_battery_discharge", t.dischargeWeight],
  ];
  const editable = data?.battery_count === 1;
  return `
    <form class="ep-v031-bs-custom" data-bs-custom-form>
      <div class="ep-v031-bs-custom-title">${panel._escape(t.customTitle)}</div>
      <div class="ep-v031-bs-custom-grid">
        ${fields.map(([key, label]) => `
          <label class="ep-v031-bs-custom-field">
            <span>${panel._escape(label)}</span>
            <input type="number" inputmode="decimal" min="0" step="0.000001" required
              data-bs-custom-value="${panel._escape(key)}"
              value="${panel._escape(inputValue(values[key]))}"
              ${busy || !editable ? "disabled" : ""}>
          </label>`).join("")}
      </div>
      <div class="ep-v031-bs-custom-actions">
        <button type="submit" class="ep-v031-bs-custom-save" ${busy || !editable ? "disabled" : ""}>${panel._escape(busy ? t.savingCustom : t.saveCustom)}</button>
      </div>
      ${!editable ? `<div class="ep-v031-bs-custom-note">${panel._escape(t.singleBatteryOnly)}</div>` : ""}
    </form>`;
}

async function saveCustomValues(panel, form) {
  const id = entryId(panel);
  if (!panel._hass?.callWS || !id || panel.__epV031BSBusy || !form) return;
  const values = {};
  for (const input of form.querySelectorAll("[data-bs-custom-value]")) {
    const value = Number(input.value);
    if (!Number.isFinite(value) || value < 0) {
      input.reportValidity?.();
      return;
    }
    values[input.dataset.bsCustomValue] = value;
  }

  const t = copy(panel);
  panel.__epV031BSBusy = true;
  panel.__epV031BSError = null;
  panel.__epV031BSMessage = t.savingCustom;
  panel._queueRender();
  try {
    shareBatterySaverData(panel, await panel._hass.callWS({
      type: "gw_energypilot/battery_saver/custom_set",
      entry_id: id,
      values,
    }));
    panel.__epV031BSMessage = t.savedCustom;
  } catch (err) {
    panel.__epV031BSError = `${t.customError}: ${err?.message || String(err)}`;
    panel.__epV031BSMessage = null;
  } finally {
    panel.__epV031BSBusy = false;
    panel._queueRender();
  }
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

  const availableModes = [
    ...(data?.modes || []),
    { key: CUSTOM_MODE, label: t.customLabel, description: t.customDescription },
  ];
  const activeMode = data?.managed ? data.mode : CUSTOM_MODE;
  const modes = availableModes.map((mode) => `
    <button type="button" class="ep-v031-bs-mode ${activeMode === mode.key ? "active" : ""}" data-bs-mode="${panel._escape(mode.key)}" ${busy ? "disabled" : ""}>
      ${mode.recommended ? `<span class="ep-v031-bs-rec">${panel._escape(t.recommended)}</span>` : ""}
      <strong>${panel._escape(mode.label)}</strong>
      <p>${panel._escape(mode.description)}</p>
      ${mode.key === CUSTOM_MODE ? "" : `<div class="ep-v031-bs-thresholds">${panel._escape(t.low)} ${mode.deficit_threshold_pct}% · ${panel._escape(t.high)} ${mode.surplus_threshold_pct}% · ${panel._escape(t.maximum)} ${mode.maximum_soc_pct}%</div>`}
    </button>`).join("");

  const profile = data?.effective_profile;
  const profileMax = profile?.battery_maximum_state_of_charge;
  const profileMaxText = Number.isFinite(Number(profileMax))
    ? `${Math.round(Number(profileMax) * 100)}%`
    : "—";
  const profileText = profile
    ? `${t.effective}: max SOC ${profileMaxText} · cycle charge ${firstWeight(profile.weight_battery_charge)} · cycle discharge ${firstWeight(profile.weight_battery_discharge)} · deficit ${profile.battery_soc_deficit_cost} · surplus ${profile.battery_soc_surplus_cost} · stress ${profile.battery_stress_cost} · ${t.priceRef} ${profile.price_reference}`
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
    ${activeMode === CUSTOM_MODE ? customEditorHtml(panel, t, data, busy) : ""}
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
  wrap.querySelector("[data-bs-custom-form]")?.addEventListener("submit", (event) => {
    event.preventDefault();
    void saveCustomValues(panel, event.currentTarget);
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
