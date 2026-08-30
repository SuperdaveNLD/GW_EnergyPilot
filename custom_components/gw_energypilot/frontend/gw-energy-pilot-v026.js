import "./gw-energy-pilot-v025.js?v=0.47-custom-battery1";

const VERSION = "0.26";
const PANEL_NAME = "gw-energypilot-panel";

const TEXT = {
  en: {
    configuration: "Configuration",
    dashboard: "Dashboard",
    loadingConfiguration: "Loading EnergyPilot configuration…",
    configurationUnavailable: "Configuration is not available yet.",
    changesStored: "Changes are stored in the existing Home Assistant config entry.",
    discardChanges: "Discard changes",
    saveChanges: "Save changes",
    saving: "Saving…",
    goodweSafetyTitle: "Connection safety:",
    goodweSafety: "host, port and unit ID are tested against the inverter before they are saved. A successful change reloads the integration.",
    emhassNoteTitle: "EMHASS:",
    emhassNote: "this page owns EnergyPilot's EMHASS connection, scheduling, output mapping and price-source settings. Live SOC and cost-function controls remain available on the dashboard.",
    controlStrategy: "Automatic control strategy",
    controlStrategyHelp: "Choose what EnergyPilot uses to control inverter power.",
    batteryControl: "Battery control",
    gridControl: "Grid control",
    hybridControl: "Hybrid control",
    batteryDescription: "Controls charging and discharging using the requested battery power (GoodWe 11/12).",
    gridDescription: "Controls import and export using the requested grid power (GoodWe 9/10).",
    hybridDescription: "Uses battery power for buying/charging (11) and grid power for selling/export (10).",
    savingStrategy: "Saving control strategy…",
    savedStrategy: "Saved",
    strategyNote: "Automatic control strategy:",
    evOverride: "EV anti-discharge protection remains active as a safety override.",
    confirmAutoStrategy: "Automatic Control is ON.",
    confirmSwitch: "Switch to {strategy}?",
    confirmReevaluate: "The active EMHASS plan will be reevaluated immediately.",
    optimizationLog: "Optimization log",
    logDescription: "Persistent diagnostics for the latest 50 EnergyPilot-owned optimization attempts. Manual, scheduled and event-triggered runs use the same log.",
    newestFirst: "Newest run first · read-only · stored per GW EnergyPilot config entry.",
    refresh: "Refresh",
    refreshing: "Refreshing…",
    loadingLog: "Loading optimization history…",
    noLog: "No EnergyPilot-owned optimization attempts have been recorded yet.",
    unableLog: "Unable to load optimization history:",
    success: "SUCCESS",
    failed: "FAILED",
    error: "Error:",
    prices: "Prices",
    forecast: "Forecast",
    duration: "Duration",
    today: "Today",
    yesterday: "Yesterday",
    clickGraph: "Click for 24h graph",
    dailyImportExport: "daily import / export ›",
    automaticOn: "Automatic ON",
    automaticOff: "Automatic OFF",
    controller: "Controller",
    systemHealth: "System health",
    diagnostics: "Diagnostics snapshot",
    copySnapshot: "Copy snapshot",
    copied: "Copied",
    solar: "SOLAR",
    home: "HOME",
    grid: "GRID",
    battery: "BATTERY",
    currentPv: "Current PV production",
    stateOfCharge: "State of charge",
    holding: "Holding",
    charging: "Charging",
    discharging: "Discharging",
    balanced: "Balanced",
    importing: "Importing",
    exporting: "Exporting",
    liveEnergyFlow: "LIVE ENERGY FLOW",
    powerOverview: "Power overview",
    house: "HOUSE",
    totalLoad: "Total load",
    production: "Production",
    goodweLoad: "GoodWe load · register 35172",
    loadPhaseSum: "Load phase sum",
    systemPowerBalance: "System power balance",
    importGrid: "Import from grid · GoodWe smart meter",
    exportGrid: "Export to grid · GoodWe smart meter",
    gridBalanced: "Grid balanced · GoodWe smart meter",
    energyPilotTarget: "EnergyPilot target",
    pccTarget: "PCC target",
    batteryTarget: "Battery target",
    controlTarget: "Control target",
    command: "Command",
    emsMode: "EMS mode",
    emsSetpoint: "EMS setpoint",
    socForecast: "SOC forecast",
    loadForecast: "Load forecast",
    pvForecast: "PV forecast",
    mapping: "Mapping",
    waiting: "Waiting",
    optimizeNow: "Optimize now",
    optimizing: "Optimizing…",
    maxExport: "Max export",
    pause: "Pause",
    maxCharge: "Max charge",
    manualSetpoint: "Manual setpoint",
    manualReady: "MANUAL READY",
    automaticLocked: "LOCKED · AUTOMATIC",
    entitiesMissing: "ENTITIES MISSING",
    logTab: "LOG",
  },
  nl: {
    configuration: "Configuratie",
    dashboard: "Dashboard",
    loadingConfiguration: "EnergyPilot-configuratie laden…",
    configurationUnavailable: "Configuratie is nog niet beschikbaar.",
    changesStored: "Wijzigingen worden opgeslagen in de bestaande Home Assistant-configuratie.",
    discardChanges: "Wijzigingen verwerpen",
    saveChanges: "Wijzigingen opslaan",
    saving: "Opslaan…",
    goodweSafetyTitle: "Veilige verbinding:",
    goodweSafety: "host, poort en unit-ID worden eerst op de omvormer getest. Na een succesvolle wijziging wordt de integratie herladen.",
    emhassNoteTitle: "EMHASS:",
    emhassNote: "deze pagina beheert de EMHASS-verbinding, planning, outputkoppeling en prijsbron van EnergyPilot. Live SOC- en optimalisatiestrategiebediening blijft beschikbaar op het dashboard.",
    controlStrategy: "Automatische regelstrategie",
    controlStrategyHelp: "Kies waarop EnergyPilot het omvormervermogen regelt.",
    batteryControl: "Accuregeling",
    gridControl: "Netregeling",
    hybridControl: "Hybride regeling",
    batteryDescription: "Regelt laden en ontladen op het gewenste accuvermogen (GoodWe 11/12).",
    gridDescription: "Regelt import en export op het gewenste netvermogen (GoodWe 9/10).",
    hybridDescription: "Regelt inkoop/laden op accuvermogen (11) en verkoop/export op netvermogen (10).",
    savingStrategy: "Regelstrategie opslaan…",
    savedStrategy: "Opgeslagen",
    strategyNote: "Automatische regelstrategie:",
    evOverride: "EV-ontlaadbeveiliging blijft actief als veiligheidsoverride.",
    confirmAutoStrategy: "Automatische regeling staat AAN.",
    confirmSwitch: "Omschakelen naar {strategy}?",
    confirmReevaluate: "Het actieve EMHASS-plan wordt direct opnieuw beoordeeld.",
    optimizationLog: "Optimalisatielog",
    logDescription: "Permanente diagnostiek van de laatste 50 door EnergyPilot uitgevoerde optimalisaties. Handmatige, geplande en gebeurtenisgestuurde runs gebruiken hetzelfde log.",
    newestFirst: "Nieuwste run eerst · alleen-lezen · opgeslagen per GW EnergyPilot-configuratie.",
    refresh: "Vernieuwen",
    refreshing: "Vernieuwen…",
    loadingLog: "Optimalisatiegeschiedenis laden…",
    noLog: "Er zijn nog geen door EnergyPilot uitgevoerde optimalisaties vastgelegd.",
    unableLog: "Optimalisatiegeschiedenis kan niet worden geladen:",
    success: "GESLAAGD",
    failed: "MISLUKT",
    error: "Fout:",
    prices: "Prijzen",
    forecast: "Prognose",
    duration: "Duur",
    today: "Vandaag",
    yesterday: "Gisteren",
    clickGraph: "Klik voor 24-uursgrafiek",
    dailyImportExport: "dagelijkse import / export ›",
    automaticOn: "Automatisch AAN",
    automaticOff: "Automatisch UIT",
    controller: "Regelaar",
    systemHealth: "Systeemstatus",
    diagnostics: "Diagnostische momentopname",
    copySnapshot: "Momentopname kopiëren",
    copied: "Gekopieerd",
    solar: "ZON",
    home: "HUIS",
    grid: "NET",
    battery: "ACCU",
    currentPv: "Huidige PV-productie",
    stateOfCharge: "Laadstatus",
    holding: "Vasthouden",
    charging: "Laden",
    discharging: "Ontladen",
    balanced: "In balans",
    importing: "Importeren",
    exporting: "Exporteren",
    liveEnergyFlow: "LIVE ENERGIESTROOM",
    powerOverview: "Vermogensoverzicht",
    house: "HUIS",
    totalLoad: "Totaal verbruik",
    production: "Productie",
    goodweLoad: "GoodWe-belasting · register 35172",
    loadPhaseSum: "Som belasting fasen",
    systemPowerBalance: "Systeemvermogensbalans",
    importGrid: "Import van net · GoodWe smart meter",
    exportGrid: "Export naar net · GoodWe smart meter",
    gridBalanced: "Net in balans · GoodWe smart meter",
    energyPilotTarget: "EnergyPilot-doel",
    pccTarget: "PCC-doel",
    batteryTarget: "Accudoel",
    controlTarget: "Regeldoel",
    command: "Commando",
    emsMode: "EMS-modus",
    emsSetpoint: "EMS-setpoint",
    socForecast: "SOC-prognose",
    loadForecast: "Verbruiksprognose",
    pvForecast: "PV-prognose",
    mapping: "Aansturing",
    waiting: "Wachten",
    optimizeNow: "Nu optimaliseren",
    optimizing: "Optimaliseren…",
    maxExport: "Max. export",
    pause: "Pauze",
    maxCharge: "Max. laden",
    manualSetpoint: "Handmatig setpoint",
    manualReady: "HANDMATIG GEREED",
    automaticLocked: "VERGRENDELD · AUTOMATISCH",
    entitiesMissing: "ENTITEITEN ONTBREKEN",
    logTab: "LOG",
  },
};

const STRATEGY_KEYS = {
  battery: ["batteryControl", "batteryDescription"],
  grid: ["gridControl", "gridDescription"],
  hybrid: ["hybridControl", "hybridDescription"],
};

const FIELD_NL = {
  max_power_kw: ["Maximaal regelvermogen", "Begrenst het modespecifieke GoodWe-setpoint."],
  deadband: ["Regeldodeband", "Tolerantie rond 0 W voor de actieve automatische regelstrategie."],
  scan_interval: ["GoodWe telemetrie-verversing", "Interval voor lokale GoodWe Modbus-telemetrie."],
  enable_ev_coordination: ["EV-ontlaadbeveiliging", "Voorkomt ontladen van de thuisaccu terwijl de EV actief laadt."],
  ev_mode_entity: ["EV-modusentiteit", "Optionele Home Assistant-entiteit voor de laadstatus van de EV."],
  ev_power_entity: ["EV-vermogensentiteit", "Optionele Home Assistant-vermogensentiteit voor EV-coördinatie."],
  ev_online_entity: ["EV-online-entiteit", "Optionele Home Assistant-entiteit die aangeeft of de laadpaal bereikbaar is."],
  ev_deadband: ["EV-actiefdrempel", "Vermogensdrempel om actieve EV-lading te herkennen."],
  enable_emhass_orchestrator: ["Ingebouwde EMHASS-orchestrator", "Laat EnergyPilot EMHASS-optimalisaties plannen en publiceren."],
  emhass_url: ["EMHASS-URL", "Adres waarmee Home Assistant Core de EMHASS-webserver bereikt."],
  emhass_optimization_interval: ["Optimalisatie-interval", "Periodiek interval; gebeurtenissen kunnen direct optimaliseren."],
  emhass_soc_final_pct: ["EnergyPilot-doel-SOC aan einde", "Wordt als runtime soc_final naar EMHASS gestuurd bij een EnergyPilot-optimalisatie."],
  emhass_fallback_load: ["Fallback-verbruik", "Wordt gebruikt wanneer geen geldige actuele/historische belasting beschikbaar is."],
  p_batt_entity: ["P_batt-outputentiteit", "Gepubliceerd accuvermogensplan; directe actuator bij Accuregeling."],
  p_grid_entity: ["P_grid-outputentiteit", "Gepubliceerd netvermogensplan; PCC-doel bij Netregeling."],
  optim_status_entity: ["Optimalisatiestatus-entiteit", "EMHASS-entiteit met de huidige optimalisatiestatus."],
  optim_required_state: ["Vereiste optimalisatiestatus", "EnergyPilot voert alleen een plan uit als deze status overeenkomt."],
  use_nordpool_prices: ["Nord Pool-runtimeprijzen gebruiken", "Gebruik Home Assistant Nord Pool-prijzen voor EMHASS-runtimeprognoses."],
  optimize_on_tomorrow_prices: ["Optimaliseren zodra morgenprijzen beschikbaar zijn", "Maak direct een nieuw plan wanneer de prijzen voor morgen verschijnen."],
  nordpool_area: ["Nord Pool-regio", "Optionele marktregio; leeg laten om de geconfigureerde bron te gebruiken."],
  nordpool_currency: ["Nord Pool-valuta", "Valuta voor runtimeprijzen."],
  buy_price_adder: ["Opslag importprijs", "Variabele kosten/toeslagen boven op de marktprijs in EUR/kWh."],
  sell_price_deduction: ["Aftrek exportprijs", "Bedrag dat van de marktprijs voor teruglevering wordt afgetrokken."],
  hardware_target: ["Gevalideerd hardwaredoel", "EnergyPilot wordt primair ontwikkeld en gevalideerd voor de GoodWe ETA-G20-generatie."],
  host: ["Omvormerhost", "Lokaal IP-adres of oplosbare hostnaam van de omvormer."],
  port: ["Modbus TCP-poort", "Modbus TCP-poort van de omvormer."],
  slave: ["Modbus unit-ID", "Modbus unit-ID van de omvormer."],
};

function language(panel) {
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function t(panel, key, vars = {}) {
  let value = TEXT[language(panel)]?.[key] ?? TEXT.en[key] ?? key;
  for (const [name, replacement] of Object.entries(vars)) {
    value = value.replaceAll(`{${name}}`, replacement);
  }
  return value;
}

function strategyText(panel, strategy) {
  const keys = STRATEGY_KEYS[strategy] || STRATEGY_KEYS.battery;
  return { label: t(panel, keys[0]), description: t(panel, keys[1]) };
}

async function saveStrategy(panel, entryId, strategy, select) {
  const cache = panel.__epV022SmartMeter || (panel.__epV022SmartMeter = {});
  const automaticOn = panel._stateByKey?.("automatic_control")?.state === "on";
  const next = strategyText(panel, strategy);
  if (automaticOn) {
    const confirmed = window.confirm(
      `${t(panel, "confirmAutoStrategy")}\n\n${t(panel, "confirmSwitch", { strategy: next.label })}\n\n${t(panel, "confirmReevaluate")}`
    );
    if (!confirmed) {
      select.value = cache.data?.strategy || "battery";
      return;
    }
  }

  cache.saving = true;
  cache.message = t(panel, "savingStrategy");
  panel._queueRender();
  try {
    const result = await panel._hass.callWS({
      type: "gw_energypilot/smart_meter/set",
      entry_id: entryId,
      strategy,
    });
    cache.entryId = entryId;
    cache.data = result;
    cache.error = null;
    cache.message = `${t(panel, "savedStrategy")} · ${next.label}.`;
  } catch (err) {
    console.error("GW EnergyPilot control strategy update failed", err);
    cache.error = err?.message || String(err);
    cache.message = null;
  } finally {
    cache.saving = false;
    panel._queueRender();
  }
}

function localizeControlStrategy(panel, root) {
  const old = root.querySelector(".ep-v024-control-strategy-field");
  if (!old) return;
  const entryId = panel.__epV016SettingsData?.entry_id;
  if (!entryId) return;

  const cache = panel.__epV022SmartMeter || (panel.__epV022SmartMeter = {});
  const data = cache.entryId === entryId ? cache.data : null;
  const strategy = data?.strategy || (data?.enabled ? "grid" : "battery");
  const busy = Boolean(cache.saving || cache.loadingEntry === entryId || !data);
  const meterAvailable = Boolean(data?.meter_available);
  const current = strategyText(panel, strategy);

  old.innerHTML = `
    <div>
      <div class="ep-v016-field-label"><span>${panel._escape(t(panel, "controlStrategy"))}</span><span>GoodWe EMS</span></div>
      <div class="ep-v016-field-description">${panel._escape(t(panel, "controlStrategyHelp"))}</div>
      <div class="ep-v022-smart-meter-status ${meterAvailable ? "ok" : strategy === "battery" ? "" : "warning"}">
        ${panel._escape(cache.error || cache.message || current.description)}
      </div>
    </div>
    <select class="ep-v016-input" ${busy ? "disabled" : ""} aria-label="${panel._escape(t(panel, "controlStrategy"))}">
      ${["battery", "grid", "hybrid"].map((value) => `<option value="${value}" ${strategy === value ? "selected" : ""}>${panel._escape(strategyText(panel, value).label)}</option>`).join("")}
    </select>`;

  const select = old.querySelector("select");
  select?.addEventListener("change", () => saveStrategy(panel, entryId, select.value, select));

  const note = root.querySelector(".ep-v022-strategy-note");
  if (note) {
    note.innerHTML = `<strong>${panel._escape(t(panel, "strategyNote"))}</strong> ${panel._escape(current.label)} · ${panel._escape(current.description)} ${panel._escape(t(panel, "evOverride"))}`;
  }
}

function localizeSettings(panel, root) {
  if (!panel.__epV016SettingsOpen) return;
  const shell = root.querySelector(".ep-v016-settings");
  if (!shell) return;

  const heading = shell.querySelector(".ep-v016-settings-head h2");
  if (heading) heading.textContent = t(panel, "configuration");
  const back = shell.querySelector(".ep-v016-back");
  if (back) back.textContent = `← ${t(panel, "dashboard")}`;

  const lang = language(panel);
  if (lang === "nl") {
    shell.querySelectorAll("[data-setting-key]").forEach((input) => {
      const field = input.closest(".ep-v016-field");
      const translation = FIELD_NL[input.dataset.settingKey];
      if (!field || !translation) return;
      const label = field.querySelector(".ep-v016-field-label span:first-child");
      const description = field.querySelector(".ep-v016-field-description");
      if (label) label.textContent = translation[0];
      if (description && translation[1]) description.textContent = translation[1];
    });

    const sectionHead = shell.querySelector(".ep-v016-section-head");
    const tab = panel.__epV016SettingsTab;
    if (sectionHead && tab === "energypilot") sectionHead.querySelector("p").textContent = "Regelaar, telemetrie en optionele EV-ontlaadbeveiliging.";
    if (sectionHead && tab === "emhass") sectionHead.querySelector("p").textContent = "Verbinding, orchestratie, outputentiteiten en runtime-prijsintegratie.";
    if (sectionHead && tab === "goodwe") sectionHead.querySelector("p").textContent = "Lokale Modbus TCP-verbinding. Wijzigingen worden vóór opslag op de omvormer gevalideerd.";
  }

  const goodweNote = shell.querySelector(".ep-v016-goodwe-note");
  if (goodweNote) goodweNote.innerHTML = `<strong>${t(panel, "goodweSafetyTitle")}</strong> ${t(panel, "goodweSafety")}`;
  const emhassNote = shell.querySelector(".ep-v016-emhass-note");
  if (emhassNote) emhassNote.innerHTML = `<strong>${t(panel, "emhassNoteTitle")}</strong> ${t(panel, "emhassNote")}`;

  const message = shell.querySelector(".ep-v016-message:not(.ok):not(.error)");
  if (message && /Changes are stored/.test(message.textContent || "")) message.textContent = t(panel, "changesStored");
  const discard = shell.querySelector("[data-discard]");
  if (discard) discard.textContent = t(panel, "discardChanges");
  const submit = shell.querySelector('button[type="submit"]');
  if (submit) submit.textContent = panel.__epV016Saving ? t(panel, "saving") : t(panel, "saveChanges");
}

function replaceText(root, selector, from, to) {
  root.querySelectorAll(selector).forEach((node) => {
    if (node.textContent?.trim() === from) node.textContent = to;
  });
}

function localizeDashboard(panel, root) {
  if (language(panel) !== "nl" || panel.__epV016SettingsOpen) return;

  replaceText(root, ".energy-card.solar .card-kicker", "SOLAR", t(panel, "solar"));
  replaceText(root, ".energy-card.home .card-kicker", "HOME", t(panel, "home"));
  replaceText(root, ".energy-card.grid .card-kicker", "GRID", t(panel, "grid"));
  replaceText(root, ".energy-card.battery .card-kicker", "BATTERY", t(panel, "battery"));
  replaceText(root, ".energy-card.solar .hero-sub", "Current PV production", t(panel, "currentPv"));
  replaceText(root, ".energy-card.battery .hero-sub", "State of charge", t(panel, "stateOfCharge"));
  replaceText(root, ".panel-card.controller h2", "Controller", t(panel, "controller"));
  replaceText(root, ".panel-card.thermal h2", "System health", t(panel, "systemHealth"));
  replaceText(root, ".panel-card.diagnostics h2", "Diagnostics snapshot", t(panel, "diagnostics"));
  replaceText(root, ".ep-v011-copy", "Copy snapshot", t(panel, "copySnapshot"));
  replaceText(root, ".ep-flow-kicker", "LIVE ENERGY FLOW", t(panel, "liveEnergyFlow"));
  replaceText(root, ".ep-flow-title", "Power overview", t(panel, "powerOverview"));
  replaceText(root, ".ep-flow-house .ep-flow-node-title", "HOUSE", t(panel, "house"));
  replaceText(root, ".ep-flow-house .ep-flow-node-sub", "GoodWe load 35172", "GoodWe-belasting 35172");
  replaceText(root, ".ep-flow-solar .ep-flow-node-sub", "Production", t(panel, "production"));
  replaceText(root, ".ep-v013-grid-hint span:first-child", "Click for 24h graph", t(panel, "clickGraph"));
  replaceText(root, ".ep-v013-grid-hint span:last-child", "daily import / export ›", t(panel, "dailyImportExport"));
  replaceText(root, ".auto-button", "Automatic ON", t(panel, "automaticOn"));
  replaceText(root, ".auto-button", "Automatic OFF", t(panel, "automaticOff"));
  replaceText(root, ".ep-optimize-now", "Optimize now", t(panel, "optimizeNow"));
  replaceText(root, '.ep-battery-action[data-action="max_export"]', "Max export", t(panel, "maxExport"));
  replaceText(root, '.ep-battery-action[data-action="battery_pause"]', "Pause", t(panel, "pause"));
  replaceText(root, '.ep-battery-action[data-action="max_charge"]', "Max charge", t(panel, "maxCharge"));
  replaceText(root, ".ep-v021-power-label span", "Manual setpoint", t(panel, "manualSetpoint"));
  replaceText(root, ".ep-v021-manual-state", "MANUAL READY", t(panel, "manualReady"));
  replaceText(root, ".ep-v021-manual-state", "LOCKED · AUTOMATIC", t(panel, "automaticLocked"));
  replaceText(root, ".ep-v021-manual-state", "ENTITIES MISSING", t(panel, "entitiesMissing"));

  root.querySelectorAll(".ep-v013-grid-day strong").forEach((node) => {
    if (node.textContent === "Today") node.textContent = t(panel, "today");
    if (node.textContent === "Yesterday") node.textContent = t(panel, "yesterday");
  });

  const homeSub = root.querySelector(".energy-card.home .hero-sub");
  if (homeSub?.textContent === "GoodWe load · register 35172") homeSub.textContent = t(panel, "goodweLoad");
  const rows = root.querySelectorAll(".energy-card.home .balance-row span");
  if (rows[0]?.textContent === "Load phase sum") rows[0].textContent = t(panel, "loadPhaseSum");
  if (rows[1]?.textContent === "System power balance") rows[1].textContent = t(panel, "systemPowerBalance");

  const gridSub = root.querySelector(".energy-card.grid .hero-sub");
  if (gridSub?.textContent.startsWith("Import from grid")) gridSub.textContent = t(panel, "importGrid");
  else if (gridSub?.textContent.startsWith("Export to grid")) gridSub.textContent = t(panel, "exportGrid");
  else if (gridSub?.textContent.startsWith("Grid balanced")) gridSub.textContent = t(panel, "gridBalanced");

  const pillMap = {
    Holding: "holding", Charging: "charging", Discharging: "discharging",
    Balanced: "balanced", Importing: "importing", Exporting: "exporting",
  };
  root.querySelectorAll(".pill").forEach((pill) => {
    const key = pillMap[pill.textContent?.trim()];
    if (key) pill.textContent = t(panel, key);
  });

  const metricMap = {
    "EMS mode": "emsMode", "EMS setpoint": "emsSetpoint", "EnergyPilot target": "energyPilotTarget",
    "PCC target": "pccTarget", "Battery target": "batteryTarget", "Control target": "controlTarget",
    Command: "command", "SOC forecast": "socForecast", "Load forecast": "loadForecast",
    "PV forecast": "pvForecast", Mapping: "mapping",
  };
  root.querySelectorAll(".metric-label").forEach((node) => {
    const key = metricMap[node.textContent?.trim()];
    if (key) node.textContent = t(panel, key);
  });
}

function localizeLog(panel, root) {
  const logTab = root.querySelector("[data-v025-log-tab] span");
  if (logTab) logTab.textContent = t(panel, "logTab");
  if (!panel.__epV025LogOpen) return;
  const content = root.querySelector(".ep-v016-settings-content");
  if (!content) return;

  const heading = content.querySelector(".ep-v016-section-head h3");
  const description = content.querySelector(".ep-v016-section-head p");
  if (heading) heading.textContent = t(panel, "optimizationLog");
  if (description) description.textContent = t(panel, "logDescription");
  const toolbar = content.querySelector(".ep-v025-log-toolbar span");
  if (toolbar) toolbar.textContent = t(panel, "newestFirst");
  const refresh = content.querySelector(".ep-v025-log-refresh");
  if (refresh) refresh.textContent = panel.__epV025LogLoading ? t(panel, "refreshing") : t(panel, "refresh");

  content.querySelectorAll(".ep-v025-log-status").forEach((node) => {
    if (node.textContent === "SUCCESS") node.textContent = t(panel, "success");
    if (node.textContent === "FAILED") node.textContent = t(panel, "failed");
  });
  content.querySelectorAll(".ep-v025-log-error strong").forEach((node) => { node.textContent = t(panel, "error"); });
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
PanelClass.prototype._epLanguage = function energyPilotLanguage() { return language(this); };
PanelClass.prototype._epT = function energyPilotTranslate(key, vars) { return t(this, key, vars); };

const previousRender = PanelClass.prototype._render;
PanelClass.prototype._render = function energyPilotV026Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  localizeSettings(this, root);
  localizeControlStrategy(this, root);
  localizeLog(this, root);
  localizeDashboard(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
};
