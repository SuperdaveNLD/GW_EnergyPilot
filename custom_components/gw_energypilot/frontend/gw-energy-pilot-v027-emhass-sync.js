import "./gw-energy-pilot-v027-battery-plan.js?v=0.27-plan1";

const VERSION = "0.27";
const PANEL_NAME = "gw-energypilot-panel";

const TEXT = {
  en: {
    defaults: "Restore recommended defaults",
    defaultsLoaded: "Recommended EMHASS defaults loaded. Review them, then save to apply.",
    title: "EMHASS configuration synchronization",
    description: "Checks EMHASS config.json against the current EnergyPilot entities and patches only the required mappings. Unrelated EMHASS settings are preserved.",
    outputs: "Recommended EnergyPilot outputs",
    pBatt: "P_batt output",
    pGrid: "P_grid output",
    statusEntity: "Optimization status",
    requiredState: "Required state",
    checking: "Checking EMHASS configuration…",
    unavailable: "Configuration check unavailable",
    synchronized: "Required configuration is synchronized",
    changes: "{count} required change(s)",
    current: "Current",
    required: "Required",
    check: "Check again",
    sync: "Synchronize required config",
    syncing: "Synchronizing…",
    noChanges: "No config changes required",
    confirm: "Write the listed required values to EMHASS config.json?\n\nThe complete current configuration is read first and unrelated settings are preserved.",
    done: "EMHASS configuration synchronized. Run a fresh optimization before enabling Automatic Control.",
    warning: "Warning",
    yes: "true",
    no: "false",
  },
  nl: {
    defaults: "Aanbevolen standaardwaarden herstellen",
    defaultsLoaded: "Aanbevolen EMHASS-standaardwaarden zijn ingevuld. Controleer ze en sla daarna op.",
    title: "EMHASS-configuratie synchroniseren",
    description: "Controleert EMHASS config.json tegen de actuele EnergyPilot-entiteiten en wijzigt alleen de noodzakelijke koppelingen. Overige EMHASS-instellingen blijven behouden.",
    outputs: "Aanbevolen EnergyPilot-uitgangen",
    pBatt: "P_batt-uitgang",
    pGrid: "P_grid-uitgang",
    statusEntity: "Optimalisatiestatus",
    requiredState: "Vereiste status",
    checking: "EMHASS-configuratie controleren…",
    unavailable: "Configuratiecontrole niet beschikbaar",
    synchronized: "Vereiste configuratie is gesynchroniseerd",
    changes: "{count} noodzakelijke wijziging(en)",
    current: "Huidig",
    required: "Vereist",
    check: "Opnieuw controleren",
    sync: "Noodzakelijke config synchroniseren",
    syncing: "Synchroniseren…",
    noChanges: "Geen configwijzigingen nodig",
    confirm: "De getoonde noodzakelijke waarden naar EMHASS config.json schrijven?\n\nEerst wordt de volledige actuele configuratie gelezen; overige instellingen blijven behouden.",
    done: "EMHASS-configuratie is gesynchroniseerd. Voer een nieuwe optimalisatie uit voordat Automatische regeling wordt ingeschakeld.",
    warning: "Waarschuwing",
    yes: "waar",
    no: "onwaar",
  },
};

const LABELS = {
  en: {
    sensor_power_photovoltaics: "PV sensor",
    sensor_power_load_no_var_loads: "House load sensor",
    sensor_power_battery: "Battery power sensor",
    sensor_battery_state_of_charge: "Battery SOC sensor",
    sensor_power_photovoltaics_forecast: "PV forecast sensor",
    sensor_replace_zero: "Zero replacement sensors",
    sensor_linear_interp: "Interpolation sensors",
    var_model: "Load model sensor",
    continual_publish: "Continual publish",
    method_ts_round: "Timestamp rounding",
    set_use_pv: "PV model enabled",
    set_use_battery: "Battery model enabled",
    inverter_is_hybrid: "Hybrid inverter",
  },
  nl: {
    sensor_power_photovoltaics: "PV-sensor",
    sensor_power_load_no_var_loads: "Huisverbruiksensor",
    sensor_power_battery: "Accuvermogensensor",
    sensor_battery_state_of_charge: "Accu-SOC-sensor",
    sensor_power_photovoltaics_forecast: "PV-prognosesensor",
    sensor_replace_zero: "Nulvervangingssensoren",
    sensor_linear_interp: "Interpolatiesensoren",
    var_model: "Verbruiksmodelsensor",
    continual_publish: "Doorlopend publiceren",
    method_ts_round: "Tijdstempelafronding",
    set_use_pv: "PV-model actief",
    set_use_battery: "Accumodel actief",
    inverter_is_hybrid: "Hybride omvormer",
  },
};

function language(panel) {
  if (typeof panel._epLanguage === "function") return panel._epLanguage();
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function t(panel, key, vars = {}) {
  let value = TEXT[language(panel)]?.[key] ?? TEXT.en[key] ?? key;
  for (const [name, replacement] of Object.entries(vars)) {
    value = value.replaceAll(`{${name}}`, String(replacement));
  }
  return value;
}

function label(panel, key) {
  return LABELS[language(panel)]?.[key] || LABELS.en[key] || key;
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v027-sync-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v027-sync-style";
  style.textContent = `
    .ep-v027-sync-card{margin:0 0 16px;padding:14px;border:1px solid rgba(67,196,224,.16);border-radius:13px;background:rgba(6,35,58,.44)}
    .ep-v027-sync-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px}.ep-v027-sync-head h4{margin:0;color:#dff7ff;font-size:13px}.ep-v027-sync-head p{max-width:760px;margin:5px 0 0;color:#7192a7;font-size:9px;line-height:1.5}
    .ep-v027-sync-status{flex:0 0 auto;padding:6px 9px;border-radius:999px;color:#8faabd;background:rgba(39,73,97,.55);font-size:8px;font-weight:850}.ep-v027-sync-status.ok{color:#d8fff1;background:rgba(27,168,126,.32)}.ep-v027-sync-status.warn{color:#ffe2b4;background:rgba(180,111,26,.32)}.ep-v027-sync-status.error{color:#ffc2bd;background:rgba(177,64,55,.28)}
    .ep-v027-sync-box{margin-top:11px;padding:10px 11px;border:1px solid rgba(79,162,211,.10);border-radius:10px;background:rgba(4,22,40,.45)}.ep-v027-sync-box-title{margin-bottom:7px;color:#8bb3c8;font-size:8px;font-weight:850;letter-spacing:.08em}
    .ep-v027-sync-output,.ep-v027-sync-values{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px 12px}.ep-v027-sync-output div{min-width:0;display:flex;justify-content:space-between;gap:8px;color:#708fa4;font-size:8px}.ep-v027-sync-output strong{color:#c7e1ec;overflow-wrap:anywhere;text-align:right}
    .ep-v027-sync-values{margin-top:11px}.ep-v027-sync-row{min-width:0;padding:9px 10px;border:1px solid rgba(79,162,211,.09);border-radius:10px;background:rgba(5,25,44,.42)}.ep-v027-sync-row.synced{border-color:rgba(44,195,144,.12)}.ep-v027-sync-label{display:flex;justify-content:space-between;gap:8px;margin-bottom:5px;color:#95b5c6;font-size:8px;font-weight:800}.ep-v027-sync-mark{color:#efb66d}.ep-v027-sync-row.synced .ep-v027-sync-mark{color:#65d5aa}.ep-v027-sync-pair{display:grid;grid-template-columns:58px minmax(0,1fr);gap:5px;color:#5f7d92;font-size:8px;line-height:1.35}.ep-v027-sync-pair strong{color:#bdd6e2;overflow-wrap:anywhere}
    .ep-v027-sync-message{margin-top:10px;padding:8px 9px;border-radius:9px;color:#e5ba7e;background:rgba(145,91,30,.17);font-size:8px;line-height:1.45}.ep-v027-sync-message.error{color:#e9aaa4;background:rgba(138,49,45,.18)}
    .ep-v027-sync-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:12px}.ep-v027-sync-action{min-height:34px;padding:7px 11px;border-radius:9px;border:1px solid rgba(77,176,229,.18);color:#b6d7e7;background:rgba(9,42,70,.48);cursor:pointer;font-size:9px;font-weight:800}.ep-v027-sync-action.primary{border-color:rgba(42,225,190,.30);color:#e5fff8;background:linear-gradient(135deg,rgba(16,112,139,.58),rgba(13,126,91,.46))}.ep-v027-sync-action:disabled{opacity:.42;cursor:wait}
    @media(max-width:760px){.ep-v027-sync-head{flex-direction:column}.ep-v027-sync-output,.ep-v027-sync-values{grid-template-columns:1fr}.ep-v027-sync-actions{flex-wrap:wrap}}
  `;
  root.appendChild(style);
}

function formatValue(panel, value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? t(panel, "yes") : t(panel, "no");
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function cache(panel) {
  if (!panel.__epV027EmhassSync) {
    panel.__epV027EmhassSync = {
      entryId: null,
      data: null,
      loading: false,
      applying: false,
      error: null,
      message: null,
    };
  }
  return panel.__epV027EmhassSync;
}

async function loadSync(panel, force = false) {
  const entryId = panel.__epV016SettingsData?.entry_id;
  const state = cache(panel);
  if (!panel._hass?.callWS || !entryId || state.loading || state.applying) return;
  if (!force && state.entryId === entryId && state.data) return;
  state.entryId = entryId;
  state.loading = true;
  state.error = null;
  panel._queueRender();
  try {
    state.data = await panel._hass.callWS({
      type: "gw_energypilot/emhass_sync/get",
      entry_id: entryId,
    });
  } catch (err) {
    console.error("GW EnergyPilot: EMHASS sync check failed", err);
    state.error = err?.message || String(err);
  } finally {
    state.loading = false;
    panel._queueRender();
  }
}

async function applySync(panel) {
  const entryId = panel.__epV016SettingsData?.entry_id;
  const state = cache(panel);
  if (!panel._hass?.callWS || !entryId || state.loading || state.applying) return;
  if (!window.confirm(t(panel, "confirm"))) return;
  state.applying = true;
  state.error = null;
  state.message = null;
  panel._queueRender();
  try {
    state.data = await panel._hass.callWS({
      type: "gw_energypilot/emhass_sync/apply",
      entry_id: entryId,
    });
    state.message = t(panel, "done");
  } catch (err) {
    console.error("GW EnergyPilot: EMHASS sync apply failed", err);
    state.error = err?.message || String(err);
  } finally {
    state.applying = false;
    panel._queueRender();
  }
}

function restoreDefaults(panel, form) {
  const defaults = cache(panel).data?.recommended_options || {};
  panel.__epV016Draft = panel.__epV016Draft || {};
  panel.__epV016Draft.emhass = panel.__epV016Draft.emhass || {};
  form.querySelectorAll("[data-setting-key]").forEach((input) => {
    const key = input.dataset.settingKey;
    if (key && Object.prototype.hasOwnProperty.call(defaults, key)) {
      panel.__epV016Draft.emhass[key] = defaults[key];
    }
  });
  panel.__epV016Message = { tone: "", text: t(panel, "defaultsLoaded") };
  panel._queueRender();
}

function installDefaultsButton(panel, root) {
  if (!panel.__epV016SettingsOpen || panel.__epV016SettingsTab !== "emhass") return;
  const form = root.querySelector('.ep-v016-form[data-section="emhass"]');
  const actions = form?.querySelector(".ep-v016-actions");
  if (!form || !actions || actions.querySelector("[data-v027-sync-defaults]")) return;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "ep-v016-action";
  button.dataset.v027SyncDefaults = "1";
  button.textContent = t(panel, "defaults");
  button.disabled = !cache(panel).data?.recommended_options;
  actions.insertBefore(button, actions.querySelector("[data-discard]") || actions.firstChild);
  button.addEventListener("click", () => restoreDefaults(panel, form));
}

function outputHtml(panel, defaults) {
  const rows = [
    [t(panel, "pBatt"), defaults?.p_batt_entity],
    [t(panel, "pGrid"), defaults?.p_grid_entity],
    [t(panel, "statusEntity"), defaults?.optim_status_entity],
    [t(panel, "requiredState"), defaults?.optim_required_state],
  ];
  return `<div class="ep-v027-sync-box"><div class="ep-v027-sync-box-title">${panel._escape(t(panel, "outputs"))}</div><div class="ep-v027-sync-output">${rows.map(([name, value]) => `<div><span>${panel._escape(name)}</span><strong>${panel._escape(formatValue(panel, value))}</strong></div>`).join("")}</div></div>`;
}

function valuesHtml(panel, values) {
  return `<div class="ep-v027-sync-values">${(values || []).map((item) => `<div class="ep-v027-sync-row ${item.synchronized ? "synced" : ""}"><div class="ep-v027-sync-label"><span>${panel._escape(label(panel, item.key))}</span><span class="ep-v027-sync-mark">${item.synchronized ? "✓" : "!"}</span></div><div class="ep-v027-sync-pair"><span>${panel._escape(t(panel, "current"))}</span><strong>${panel._escape(formatValue(panel, item.current))}</strong></div><div class="ep-v027-sync-pair"><span>${panel._escape(t(panel, "required"))}</span><strong>${panel._escape(formatValue(panel, item.required))}</strong></div></div>`).join("")}</div>`;
}

function renderSyncCard(panel, root) {
  if (!panel.__epV016SettingsOpen || panel.__epV016SettingsTab !== "emhass") return;
  const form = root.querySelector('.ep-v016-form[data-section="emhass"]');
  if (!form || root.querySelector(".ep-v027-sync-card")) return;

  const state = cache(panel);
  const entryId = panel.__epV016SettingsData?.entry_id;
  if (entryId && state.entryId !== entryId && !state.loading) {
    state.data = null;
    state.error = null;
    state.message = null;
    loadSync(panel);
  } else if (entryId && !state.data && !state.loading && !state.error) {
    loadSync(panel);
  }

  const data = state.data;
  const count = data?.changes?.length || 0;
  const error = state.error || data?.error;
  let status = t(panel, "checking");
  let tone = "";
  if (error) {
    status = t(panel, "unavailable");
    tone = "error";
  } else if (data?.synchronized) {
    status = t(panel, "synchronized");
    tone = "ok";
  } else if (data?.available) {
    status = t(panel, "changes", { count });
    tone = "warn";
  }

  const messages = [];
  if (state.message) messages.push(`<div class="ep-v027-sync-message">${panel._escape(state.message)}</div>`);
  if (error) messages.push(`<div class="ep-v027-sync-message error">${panel._escape(error)}</div>`);
  const warnings = [...new Set(data?.warnings || [])];
  if (warnings.length) messages.push(`<div class="ep-v027-sync-message"><strong>${panel._escape(t(panel, "warning"))}:</strong> ${panel._escape(warnings.join(" · "))}</div>`);

  const card = document.createElement("section");
  card.className = "ep-v027-sync-card";
  card.innerHTML = `<div class="ep-v027-sync-head"><div><h4>${panel._escape(t(panel, "title"))}</h4><p>${panel._escape(t(panel, "description"))}</p></div><div class="ep-v027-sync-status ${tone}">${panel._escape(status)}</div></div>${outputHtml(panel, data?.recommended_options)}${data?.managed_values?.length ? valuesHtml(panel, data.managed_values) : ""}${messages.join("")}<div class="ep-v027-sync-actions"><button type="button" class="ep-v027-sync-action" data-v027-sync-check ${state.loading || state.applying ? "disabled" : ""}>${panel._escape(t(panel, "check"))}</button><button type="button" class="ep-v027-sync-action primary" data-v027-sync-apply ${state.loading || state.applying || !data?.available || count === 0 ? "disabled" : ""}>${panel._escape(state.applying ? t(panel, "syncing") : count === 0 && data?.available ? t(panel, "noChanges") : t(panel, "sync"))}</button></div>`;
  form.insertAdjacentElement("beforebegin", card);
  card.querySelector("[data-v027-sync-check]")?.addEventListener("click", () => loadSync(panel, true));
  card.querySelector("[data-v027-sync-apply]")?.addEventListener("click", () => applySync(panel));
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV027SyncRender() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;
  ensureStyles(root);
  renderSyncCard(this, root);
  installDefaultsButton(this, root);
  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
};
