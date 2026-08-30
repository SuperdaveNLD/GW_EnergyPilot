import "./gw-energy-pilot-v041.js?v=1.0.1-beta2";

const PANEL_NAME = "gw-energypilot-panel";
const STYLE_ID = "ep-v041-emhass-settings-style";

const GROUPS = Object.freeze([
  Object.freeze({
    key: "connection",
    keys: [
      "enable_emhass_orchestrator",
      "emhass_url",
      "emhass_optimization_interval",
      "emhass_soc_final_pct",
      "emhass_fallback_load",
    ],
  }),
  Object.freeze({
    key: "outputs",
    keys: [
      "p_batt_entity",
      "p_grid_entity",
      "optim_status_entity",
      "optim_required_state",
    ],
  }),
  Object.freeze({
    key: "prices",
    keys: [
      "use_nordpool_prices",
      "optimize_on_tomorrow_prices",
      "nordpool_area",
      "nordpool_currency",
      "buy_price_adder",
      "sell_price_deduction",
    ],
  }),
]);

const SYNC_LABELS = Object.freeze({
  sensor_power_photovoltaics: ["PV power sensor", "PV-vermogenssensor"],
  sensor_power_load_no_var_loads: ["Load power sensor", "Belastingssensor"],
  sensor_power_battery: ["Battery power sensor", "Batterijvermogenssensor"],
  sensor_battery_state_of_charge: ["Battery SOC sensor", "Batterij-SOC-sensor"],
  sensor_power_photovoltaics_forecast: ["PV forecast sensor", "PV-voorspellingssensor"],
  sensor_replace_zero: ["Replace-zero sensors", "Nulwaarden vervangen"],
  sensor_linear_interp: ["Interpolation sensors", "Interpolatiesensoren"],
  var_model: ["Load model input", "Invoer belastingsmodel"],
  continual_publish: ["Continual publish", "Continu publiceren"],
  method_ts_round: ["Timestamp rounding", "Tijdstempelafronding"],
  set_use_battery: ["Battery optimization", "Batterijoptimalisatie"],
});

const TEXT = Object.freeze({
  en: Object.freeze({
    summaryTitle: "EMHASS status",
    connected: "Connection",
    connectedOk: "Connected",
    checking: "Checking",
    unavailable: "Unavailable",
    configuration: "Configuration",
    synchronized: "In sync",
    difference: "difference",
    differences: "differences",
    outputs: "Outputs",
    outputsReady: "Configured",
    outputsMissing: "Incomplete",
    syncAction: "Synchronize configuration",
    connectionTitle: "1. Connection & planning",
    connectionDescription: "How EnergyPilot reaches EMHASS and when a new optimization is requested.",
    outputsTitle: "2. Outputs",
    outputsDescription: "Home Assistant entities EnergyPilot expects EMHASS to publish.",
    pricesTitle: "3. Price settings",
    pricesDescription: "Runtime price source and import/export adjustments used by EnergyPilot.",
    controlTitle: "4. EMHASS configuration check",
    controlDescription: "Shows the actual values stored in EMHASS next to the values EnergyPilot requires.",
    setting: "Setting",
    expected: "EnergyPilot expects",
    stored: "EMHASS stored",
    status: "Status",
    differs: "Differs",
    noManaged: "No managed EMHASS values are available yet.",
    energyPilotSaved: "EnergyPilot saved",
    expectedPublication: "Expected EMHASS publication",
    otherTitle: "Other settings",
    otherDescription: "Additional EnergyPilot settings kept for compatibility.",
    note: "The editable fields are EnergyPilot settings. Actual EMHASS config.json values are shown separately in Configuration check, so EnergyPilot-only settings are not presented as if EMHASS stored them.",
  }),
  nl: Object.freeze({
    summaryTitle: "EMHASS status",
    connected: "Verbinding",
    connectedOk: "Verbonden",
    checking: "Controleren",
    unavailable: "Niet beschikbaar",
    configuration: "Configuratie",
    synchronized: "In sync",
    difference: "verschil",
    differences: "verschillen",
    outputs: "Outputs",
    outputsReady: "Geconfigureerd",
    outputsMissing: "Onvolledig",
    syncAction: "Synchroniseer configuratie",
    connectionTitle: "1. Verbinding & planning",
    connectionDescription: "Hoe EnergyPilot EMHASS bereikt en wanneer een nieuwe optimalisatie wordt aangevraagd.",
    outputsTitle: "2. Outputs",
    outputsDescription: "Home Assistant-entiteiten waarvan EnergyPilot verwacht dat EMHASS ze publiceert.",
    pricesTitle: "3. Prijsinstellingen",
    pricesDescription: "Runtime prijsbron en import-/exportcorrecties die EnergyPilot gebruikt.",
    controlTitle: "4. EMHASS configuratiecontrole",
    controlDescription: "Toont de werkelijke waarden uit EMHASS naast de waarden die EnergyPilot vereist.",
    setting: "Instelling",
    expected: "EnergyPilot verwacht",
    stored: "EMHASS opgeslagen",
    status: "Status",
    differs: "Verschilt",
    noManaged: "Er zijn nog geen beheerde EMHASS-configwaarden beschikbaar.",
    energyPilotSaved: "EnergyPilot opgeslagen",
    expectedPublication: "Verwachte EMHASS-publicatie",
    otherTitle: "Overige instellingen",
    otherDescription: "Aanvullende EnergyPilot-instellingen die voor compatibiliteit behouden blijven.",
    note: "De bewerkbare velden zijn EnergyPilot-instellingen. Werkelijke waarden uit EMHASS config.json staan apart bij Configuratiecontrole, zodat EnergyPilot-only instellingen niet ten onrechte als EMHASS-opslag worden getoond.",
  }),
});

function language(panel) {
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function text(panel) {
  return TEXT[language(panel)] || TEXT.en;
}

function displayValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "[]";
  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch (_err) {
      return String(value);
    }
  }
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

function savedFieldMap(panel) {
  const fields = panel.__epV016SettingsData?.sections?.emhass?.fields || [];
  return new Map(fields.map((field) => [field.key, field.value]));
}

function syncState(panel) {
  return panel.__epV028Sync || {
    entryId: panel.__epV016SettingsData?.entry_id || null,
    data: null,
    loading: false,
    applying: false,
    error: null,
  };
}

function ensureStyles(root) {
  if (!root || root.querySelector(`#${STYLE_ID}`)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    .ep-v041-emhass-summary {
      display:grid; grid-template-columns:minmax(0,1.45fr) minmax(210px,.7fr); gap:0;
      margin:0 0 16px; border:1px solid rgba(70,172,230,.18); border-radius:14px;
      overflow:hidden; background:linear-gradient(145deg,rgba(8,37,65,.66),rgba(5,25,47,.76));
    }
    .ep-v041-emhass-summary-main { padding:13px 15px; }
    .ep-v041-emhass-summary-title { margin:0 0 8px; color:#edf9ff; font-size:12px; font-weight:860; }
    .ep-v041-emhass-summary-row {
      display:grid; grid-template-columns:minmax(0,1fr) auto; gap:10px; align-items:center;
      min-height:31px; padding:4px 8px; border-top:1px solid rgba(88,158,199,.07); color:#b4ccda; font-size:9px;
    }
    .ep-v041-emhass-summary-row:first-of-type { border-top:0; }
    .ep-v041-emhass-summary-badge,
    .ep-v041-emhass-sync-badge {
      display:inline-flex; align-items:center; justify-content:center; min-height:20px; padding:3px 8px;
      border:1px solid rgba(109,145,165,.18); border-radius:999px; color:#91a9b8;
      background:rgba(56,72,85,.20); font-size:7px; font-weight:880; white-space:nowrap;
    }
    .ep-v041-emhass-summary-badge.ok,
    .ep-v041-emhass-sync-badge.ok { color:#a6f4ce; border-color:rgba(49,214,153,.31); background:rgba(16,104,75,.30); }
    .ep-v041-emhass-summary-badge.warn,
    .ep-v041-emhass-sync-badge.warn { color:#ffd496; border-color:rgba(232,174,67,.34); background:rgba(114,75,12,.30); }
    .ep-v041-emhass-summary-badge.error { color:#ffc2ba; border-color:rgba(235,126,112,.30); background:rgba(106,44,38,.28); }
    .ep-v041-emhass-summary-action {
      display:flex; align-items:center; justify-content:center; padding:16px;
      border-left:1px solid rgba(76,166,220,.10); background:rgba(4,23,43,.20);
    }
    .ep-v041-emhass-summary-action .ep-v016-action {
      min-height:42px; padding:10px 17px; border-color:rgba(45,218,246,.48); color:#8deeff;
      background:rgba(5,51,81,.50); font-size:9px;
    }
    .ep-v041-emhass-summary-error { grid-column:1/-1; padding:8px 15px 11px; color:#efa8a2; font-size:8px; }
    .ep-v041-emhass-layout {
      display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:12px;
    }
    .ep-v041-emhass-group {
      min-width:0; padding:14px; border:1px solid rgba(71,158,205,.12); border-radius:13px;
      background:linear-gradient(150deg,rgba(7,34,57,.55),rgba(5,25,44,.64));
    }
    .ep-v041-emhass-group-head { margin-bottom:12px; }
    .ep-v041-emhass-group-title { color:#7de5f3; font-size:10px; font-weight:860; }
    .ep-v041-emhass-group-description { margin-top:4px; color:#67899e; font-size:7px; line-height:1.45; }
    .ep-v041-emhass-group-fields { display:grid; gap:9px; }
    .ep-v041-emhass-group .ep-v016-field { padding:10px 11px; background:rgba(4,24,42,.38); }
    .ep-v041-emhass-group .ep-v016-field-label { margin-bottom:6px; }
    .ep-v041-emhass-field-meta {
      margin-top:6px; color:#587b91; font-size:7px; line-height:1.4; word-break:break-word;
    }
    .ep-v041-emhass-field-meta strong { color:#6fcfe3; font-weight:720; }
    .ep-v041-emhass-control {
      margin-top:12px; padding:14px; border:1px solid rgba(70,172,230,.16); border-radius:13px;
      background:linear-gradient(150deg,rgba(7,35,58,.58),rgba(5,24,43,.68));
    }
    .ep-v041-emhass-control-head { margin-bottom:10px; }
    .ep-v041-emhass-control-title { color:#7de5f3; font-size:10px; font-weight:860; }
    .ep-v041-emhass-control-description { margin-top:4px; color:#6f91a5; font-size:8px; line-height:1.45; }
    .ep-v041-emhass-sync-table { display:grid; overflow:hidden; border:1px solid rgba(74,151,192,.10); border-radius:10px; }
    .ep-v041-emhass-sync-row {
      display:grid; grid-template-columns:minmax(170px,.8fr) minmax(180px,1.25fr) minmax(180px,1.25fr) 76px;
      gap:10px; align-items:center; min-height:34px; padding:6px 9px; border-top:1px solid rgba(79,151,190,.08);
      color:#9fb9c8; font-size:7px;
    }
    .ep-v041-emhass-sync-row:first-child { border-top:0; }
    .ep-v041-emhass-sync-row.header { min-height:29px; color:#668da3; font-weight:820; background:rgba(7,29,50,.48); }
    .ep-v041-emhass-sync-name strong { display:block; color:#c5dce7; font-size:8px; }
    .ep-v041-emhass-sync-name code { display:block; margin-top:2px; color:#56798e; font-size:6px; word-break:break-all; }
    .ep-v041-emhass-sync-value { color:#a8c2d0; word-break:break-word; font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
    .ep-v041-emhass-sync-value.expected { color:#c7e2eb; }
    .ep-v041-emhass-sync-empty { padding:13px; color:#6e8ea1; font-size:8px; }
    .ep-v041-emhass-warning { margin-top:8px; padding:8px 9px; border:1px solid rgba(229,172,74,.16); border-radius:8px; color:#d6b270; background:rgba(104,70,15,.18); font-size:7px; line-height:1.45; }
    .ep-v041-emhass-actions { margin-top:14px; }
    .ep-v041-emhass-actions > .ep-v016-action:first-child { margin-right:auto; }
    .ep-v016-emhass-note.ep-v041-emhass-note { color:#789aae; }
    @media (max-width:1050px) {
      .ep-v041-emhass-layout { grid-template-columns:repeat(2,minmax(0,1fr)); }
      .ep-v041-emhass-group[data-group="prices"] { grid-column:1/-1; }
      .ep-v041-emhass-sync-row { grid-template-columns:minmax(150px,.8fr) minmax(160px,1fr) minmax(160px,1fr) 72px; }
    }
    @media (max-width:720px) {
      .ep-v041-emhass-summary { grid-template-columns:1fr; }
      .ep-v041-emhass-summary-action { border-left:0; border-top:1px solid rgba(76,166,220,.10); justify-content:flex-start; }
      .ep-v041-emhass-layout { grid-template-columns:1fr; }
      .ep-v041-emhass-group[data-group="prices"] { grid-column:auto; }
      .ep-v041-emhass-sync-table { overflow-x:auto; }
      .ep-v041-emhass-sync-row { min-width:680px; }
      .ep-v041-emhass-actions > .ep-v016-action:first-child { width:100%; margin-right:0; }
    }
  `;
  root.appendChild(style);
}

function fieldNode(form, key) {
  return form.querySelector(`[data-setting-key="${key}"]`)?.closest(".ep-v016-field") || null;
}

function decorateField(panel, field, key, saved) {
  if (!field || field.querySelector(".ep-v041-emhass-field-meta")) return;
  const copy = text(panel);
  const meta = document.createElement("div");
  meta.className = "ep-v041-emhass-field-meta";
  const outputKey = ["p_batt_entity", "p_grid_entity", "optim_status_entity"].includes(key);
  const label = outputKey ? copy.expectedPublication : copy.energyPilotSaved;
  meta.innerHTML = `<strong>${panel._escape(label)}:</strong> ${panel._escape(displayValue(saved))}`;
  field.appendChild(meta);
}

function groupCopy(copy, groupKey) {
  if (groupKey === "connection") return [copy.connectionTitle, copy.connectionDescription];
  if (groupKey === "outputs") return [copy.outputsTitle, copy.outputsDescription];
  if (groupKey === "prices") return [copy.pricesTitle, copy.pricesDescription];
  return [copy.otherTitle, copy.otherDescription];
}

function buildGroup(panel, form, definition, savedFields, moved) {
  const copy = text(panel);
  const fields = definition.keys
    .map((key) => [key, fieldNode(form, key)])
    .filter(([, field]) => Boolean(field));
  if (!fields.length) return null;

  const group = document.createElement("section");
  group.className = "ep-v041-emhass-group";
  group.dataset.group = definition.key;
  const [title, description] = groupCopy(copy, definition.key);
  group.innerHTML = `
    <div class="ep-v041-emhass-group-head">
      <div class="ep-v041-emhass-group-title">${panel._escape(title)}</div>
      <div class="ep-v041-emhass-group-description">${panel._escape(description)}</div>
    </div>
    <div class="ep-v041-emhass-group-fields"></div>`;
  const target = group.querySelector(".ep-v041-emhass-group-fields");
  for (const [key, field] of fields) {
    decorateField(panel, field, key, savedFields.get(key));
    moved.add(field);
    target.appendChild(field);
  }
  return group;
}

function outputsConfigured(form) {
  return ["p_batt_entity", "p_grid_entity", "optim_status_entity", "optim_required_state"].every((key) => {
    const input = form.querySelector(`[data-setting-key="${key}"]`);
    if (!input) return false;
    return String(input.value ?? "").trim().length > 0;
  });
}

function extractSyncControls(form) {
  const holder = form.querySelector(".ep-v028-sync-tools");
  if (!holder) return { defaults: null, sync: null };
  const buttons = [...holder.querySelectorAll(":scope > button")];
  const defaults = buttons[0] || null;
  const sync = buttons[1] || null;
  defaults?.remove();
  sync?.remove();
  holder.remove();
  return { defaults, sync };
}

function statusBadge(panel, label, value, tone) {
  return `
    <div class="ep-v041-emhass-summary-row">
      <span>${panel._escape(label)}</span>
      <span class="ep-v041-emhass-summary-badge ${tone}">${panel._escape(value)}</span>
    </div>`;
}

function buildSummary(panel, form, current, syncButton) {
  const copy = text(panel);
  const data = current.data;
  const changes = data?.changes?.length || 0;
  const connectionValue = current.loading && !data
    ? copy.checking
    : data?.available
      ? copy.connectedOk
      : copy.unavailable;
  const connectionTone = data?.available ? "ok" : current.loading && !data ? "" : "error";
  const configValue = data?.synchronized
    ? copy.synchronized
    : changes
      ? `${changes} ${changes === 1 ? copy.difference : copy.differences}`
      : current.loading
        ? copy.checking
        : copy.unavailable;
  const configTone = data?.synchronized ? "ok" : changes ? "warn" : "";
  const outputReady = outputsConfigured(form);

  const summary = document.createElement("section");
  summary.className = "ep-v041-emhass-summary";
  summary.innerHTML = `
    <div class="ep-v041-emhass-summary-main">
      <div class="ep-v041-emhass-summary-title">${panel._escape(copy.summaryTitle)}</div>
      ${statusBadge(panel, copy.connected, connectionValue, connectionTone)}
      ${statusBadge(panel, copy.configuration, configValue, configTone)}
      ${statusBadge(panel, copy.outputs, outputReady ? copy.outputsReady : copy.outputsMissing, outputReady ? "ok" : "warn")}
    </div>
    <div class="ep-v041-emhass-summary-action"></div>`;
  if (syncButton) {
    syncButton.classList.add("ep-v041-emhass-sync-action");
    syncButton.textContent = copy.syncAction;
    summary.querySelector(".ep-v041-emhass-summary-action")?.appendChild(syncButton);
  }
  if (current.error) {
    const error = document.createElement("div");
    error.className = "ep-v041-emhass-summary-error";
    error.textContent = current.error;
    summary.appendChild(error);
  }
  return summary;
}

function managedRows(data) {
  return (data?.managed_values || []).filter(
    (item) => item && (item.current !== null || item.required !== null)
  );
}

function buildConfigControl(panel, current) {
  const copy = text(panel);
  const section = document.createElement("section");
  section.className = "ep-v041-emhass-control";
  section.innerHTML = `
    <div class="ep-v041-emhass-control-head">
      <div class="ep-v041-emhass-control-title">${panel._escape(copy.controlTitle)}</div>
      <div class="ep-v041-emhass-control-description">${panel._escape(copy.controlDescription)}</div>
    </div>`;

  const rows = managedRows(current.data);
  const table = document.createElement("div");
  table.className = "ep-v041-emhass-sync-table";
  if (!rows.length) {
    const empty = document.createElement("div");
    empty.className = "ep-v041-emhass-sync-empty";
    empty.textContent = current.loading ? copy.checking : copy.noManaged;
    table.appendChild(empty);
  } else {
    const header = document.createElement("div");
    header.className = "ep-v041-emhass-sync-row header";
    header.innerHTML = `
      <span>${panel._escape(copy.setting)}</span>
      <span>${panel._escape(copy.expected)}</span>
      <span>${panel._escape(copy.stored)}</span>
      <span>${panel._escape(copy.status)}</span>`;
    table.appendChild(header);

    for (const item of rows) {
      const row = document.createElement("div");
      row.className = "ep-v041-emhass-sync-row";
      const labels = SYNC_LABELS[item.key] || [item.key, item.key];
      const friendly = labels[language(panel) === "nl" ? 1 : 0];
      const synchronized = item.synchronized === true;
      row.innerHTML = `
        <div class="ep-v041-emhass-sync-name">
          <strong>${panel._escape(friendly)}</strong>
          <code>${panel._escape(item.key)}</code>
        </div>
        <div class="ep-v041-emhass-sync-value expected">${panel._escape(displayValue(item.required))}</div>
        <div class="ep-v041-emhass-sync-value">${panel._escape(displayValue(item.current))}</div>
        <div><span class="ep-v041-emhass-sync-badge ${synchronized ? "ok" : "warn"}">${panel._escape(synchronized ? copy.synchronized : copy.differs)}</span></div>`;
      table.appendChild(row);
    }
  }
  section.appendChild(table);

  for (const warning of current.data?.warnings || []) {
    const node = document.createElement("div");
    node.className = "ep-v041-emhass-warning";
    node.textContent = warning;
    section.appendChild(node);
  }
  return section;
}

function enhanceEmhassSettings(panel, root) {
  if (!panel.__epV016SettingsOpen || panel.__epV016SettingsTab !== "emhass") return;
  const content = root?.querySelector(".ep-v016-settings-content");
  const form = content?.querySelector('.ep-v016-form[data-section="emhass"]');
  const originalFields = form?.querySelector(":scope > .ep-v016-fields");
  const actions = form?.querySelector(":scope > .ep-v016-actions");
  if (!content || !form || !originalFields || !actions) return;
  if (form.querySelector(":scope > .ep-v041-emhass-layout")) return;

  ensureStyles(root);
  const copy = text(panel);
  const note = content.querySelector(".ep-v016-emhass-note");
  if (note) {
    note.classList.add("ep-v041-emhass-note");
    note.textContent = copy.note;
  }

  const controls = extractSyncControls(form);
  const current = syncState(panel);
  const summary = buildSummary(panel, form, current, controls.sync);
  if (note) note.insertAdjacentElement("afterend", summary);
  else content.querySelector(".ep-v016-section-head")?.insertAdjacentElement("afterend", summary);

  const savedFields = savedFieldMap(panel);
  const moved = new Set();
  const layout = document.createElement("div");
  layout.className = "ep-v041-emhass-layout";
  for (const definition of GROUPS) {
    const group = buildGroup(panel, form, definition, savedFields, moved);
    if (group) layout.appendChild(group);
  }

  const leftovers = [...originalFields.querySelectorAll(":scope > .ep-v016-field")]
    .filter((field) => !moved.has(field));
  if (leftovers.length) {
    const other = document.createElement("section");
    other.className = "ep-v041-emhass-group";
    other.dataset.group = "other";
    other.innerHTML = `
      <div class="ep-v041-emhass-group-head">
        <div class="ep-v041-emhass-group-title">${panel._escape(copy.otherTitle)}</div>
        <div class="ep-v041-emhass-group-description">${panel._escape(copy.otherDescription)}</div>
      </div>
      <div class="ep-v041-emhass-group-fields"></div>`;
    const target = other.querySelector(".ep-v041-emhass-group-fields");
    for (const field of leftovers) {
      const input = field.querySelector("[data-setting-key]");
      const key = input?.dataset?.settingKey || "";
      decorateField(panel, field, key, savedFields.get(key));
      target.appendChild(field);
    }
    layout.appendChild(other);
  }
  originalFields.replaceWith(layout);

  actions.classList.add("ep-v041-emhass-actions");
  if (controls.defaults) {
    controls.defaults.classList.add("ep-v041-emhass-defaults");
    actions.prepend(controls.defaults);
  }
  actions.insertAdjacentElement("beforebegin", buildConfigControl(panel, current));
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (PanelClass && !PanelClass.prototype.__epV041EmhassSettingsInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV041EmhassSettingsRender(...args) {
    const result = previousRender.apply(this, args);
    enhanceEmhassSettings(this, this.shadowRoot);
    return result;
  };
  PanelClass.prototype.__epV041EmhassSettingsInstalled = true;
}
