import "./gw-energy-pilot-v039.js?v=0.41-stable-dom1";
import {
  FLOW_THRESHOLD_W,
  flowMotionMap,
  resolveHousePower,
} from "./gw-energy-pilot-v038-model.js?v=0.38-model3";
import {
  dashboardLanguage,
  localizedEmsMode,
} from "./gw-energy-pilot-v038-i18n.js?v=0.38-i18n1";

const VERSION = "0.41";
const PANEL_NAME = "gw-energypilot-panel";
const MOTION_STYLE_ID = "ep-v041-no-motion";
const LIVE_PATCH_DELAY_MS = 40;

const COPY = Object.freeze({
  en: Object.freeze({
    autoActive: "AUTO ACTIVE",
    goodweAuto: "GOODWE AUTO",
    automaticOn: "Automatic ON",
    automaticOff: "Automatic OFF",
    balanced: "Balanced",
    importing: "Importing",
    exporting: "Exporting",
    holding: "Holding",
    charging: "Charging",
    discharging: "Discharging",
    totalLoad: "Total load",
    production: "Production",
    waiting: "Waiting",
    modeCharge: "Mode 11 · Charge",
    modeDischarge: "Mode 12 · Discharge",
    modeHold: "Mode 8 · Hold",
    locked: "LOCKED · AUTOMATIC",
    manualReady: "MANUAL READY",
    entitiesMissing: "ENTITIES MISSING",
  }),
  nl: Object.freeze({
    autoActive: "AUTO ACTIEF",
    goodweAuto: "GOODWE AUTO",
    automaticOn: "Automatisch AAN",
    automaticOff: "Automatisch UIT",
    balanced: "In balans",
    importing: "Importeren",
    exporting: "Exporteren",
    holding: "Stand-by",
    charging: "Laden",
    discharging: "Ontladen",
    totalLoad: "Totale belasting",
    production: "Productie",
    waiting: "Wachten",
    modeCharge: "Modus 11 · Laden",
    modeDischarge: "Modus 12 · Ontladen",
    modeHold: "Modus 8 · Stand-by",
    locked: "VERGRENDELD · AUTOMATISCH",
    manualReady: "HANDMATIG GEREED",
    entitiesMissing: "ENTITEITEN ONTBREKEN",
  }),
});

const NO_MOTION_CSS = `
  :host,
  :host *,
  :host *::before,
  :host *::after {
    animation: none !important;
    transition: none !important;
    scroll-behavior: auto !important;
  }
  :host {
    overflow-anchor: auto !important;
  }
  :host .page,
  :host .ep-dashboard-layout,
  :host [data-ep-card],
  :host button,
  :host a,
  :host label {
    touch-action: manipulation;
  }
  :host .ep-layout-menu {
    max-height: calc(100dvh - 104px) !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
  }
  :host .ep-flow-link::after,
  :host .ep-flow-arrows,
  :host .ep-flow-live span,
  :host .ep-flow-hub::after,
  :host .ep-v011-particles span {
    display: none !important;
  }
`;

function language(panel) {
  return dashboardLanguage(panel) === "nl" ? "nl" : "en";
}

function copy(panel) {
  return COPY[language(panel)];
}

function finite(panel, key) {
  const value = panel._numberByKey?.(key, null);
  return Number.isFinite(value) ? value : null;
}

function normalize(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replaceAll("‑", "-")
    .replaceAll("–", "-")
    .replaceAll("—", "-")
    .replace(/\s+/g, " ");
}

function setText(root, selector, value) {
  const node = root?.querySelector(selector);
  if (node && node.textContent !== String(value)) node.textContent = String(value);
  return node;
}

function setStatus(node, active, text) {
  if (!node) return;
  node.classList.toggle("active", active);
  node.classList.toggle("inactive", !active);
  let dot = node.querySelector(".dot");
  if (!dot) {
    dot = document.createElement("span");
    dot.className = "dot";
    node.prepend(dot);
  }
  const trailing = [...node.childNodes].find((child) => child.nodeType === 3);
  if (trailing) trailing.textContent = text;
  else node.append(document.createTextNode(text));
}

function replaceTrailingButtonText(button, text) {
  if (!button) return;
  const trailing = [...button.childNodes]
    .reverse()
    .find((node) => node.nodeType === 3);
  if (trailing) trailing.textContent = ` ${text}`;
  else button.append(document.createTextNode(` ${text}`));
}

function metricByLabels(card, labels) {
  if (!card) return null;
  const wanted = new Set(labels.map(normalize));
  for (const metric of card.querySelectorAll(".metric")) {
    const label = normalize(metric.querySelector(".metric-label")?.textContent);
    if (wanted.has(label)) return metric;
  }
  return null;
}

function patchMetric(card, labels, value, sub = undefined) {
  const metric = metricByLabels(card, labels);
  if (!metric) return;
  const valueNode = metric.querySelector(".metric-value");
  if (valueNode && valueNode.textContent !== String(value)) {
    valueNode.textContent = String(value);
  }
  if (sub !== undefined) {
    const subNode = metric.querySelector(".metric-sub");
    if (subNode && subNode.textContent !== String(sub)) subNode.textContent = String(sub);
  }
}

function patchBalanceRows(card, panel, load, inverter, acActive) {
  const pv = finite(panel, "pv_total_power");
  const grid = finite(panel, "meter_total_power_fast");
  const battery = finite(panel, "battery_power");
  const balance =
    [pv, grid, battery].every(Number.isFinite) ? pv - grid + battery : null;
  for (const row of card?.querySelectorAll(".balance-row") || []) {
    const label = normalize(row.querySelector("span")?.textContent);
    const value = row.querySelector("strong");
    if (!value) continue;
    let next = null;
    if (label.includes("inverter") || label.includes("omvormer")) next = inverter;
    else if (label.includes("ac active") || label.includes("ac actief")) next = acActive;
    else if (label.includes("phase sum") || label.includes("fasesom")) next = load;
    else if (label.includes("system power balance") || label.includes("systeemvermogensbalans")) next = balance;
    if (next !== null) value.textContent = panel._formatPower(next);
  }
}

function gridPresentation(panel, power) {
  const t = copy(panel);
  if (!Number.isFinite(power) || Math.abs(power) < FLOW_THRESHOLD_W) {
    return { css: "hold", text: t.balanced };
  }
  return power > 0
    ? { css: "export", text: t.exporting }
    : { css: "import", text: t.importing };
}

function batteryPresentation(panel, power) {
  const t = copy(panel);
  if (!Number.isFinite(power) || Math.abs(power) < FLOW_THRESHOLD_W) {
    return { css: "hold", text: t.holding };
  }
  return power > 0
    ? { css: "discharge", text: t.discharging }
    : { css: "charge", text: t.charging };
}

function patchPill(card, presentation) {
  const pill = card?.querySelector(".pill");
  if (!pill) return;
  pill.classList.remove("hold", "import", "export", "charge", "discharge");
  pill.classList.add(presentation.css);
  pill.textContent = presentation.text;
}

function externalState(panel, exact, suffixes) {
  return panel._findState?.(exact) || panel._findStateBySuffix?.(suffixes) || null;
}

function patchFlow(panel, root, pv, load, grid, battery, soc) {
  const house = resolveHousePower(load, pv, grid, battery);
  const motion = flowMotionMap({ pv, house, grid, battery }, FLOW_THRESHOLD_W);
  const t = copy(panel);
  const gridMode = gridPresentation(panel, grid);
  const batteryMode = batteryPresentation(panel, battery);

  setText(root, ".ep-flow-house .ep-flow-node-value", panel._formatPower(house));
  setText(root, ".ep-flow-solar .ep-flow-node-value", panel._formatPower(pv));
  setText(root, ".ep-flow-grid .ep-flow-node-value", panel._formatPower(grid));
  setText(root, ".ep-flow-battery .ep-flow-node-value", panel._formatPower(battery));
  setText(root, ".ep-flow-house .ep-flow-node-sub", t.totalLoad);
  setText(root, ".ep-flow-solar .ep-flow-node-sub", t.production);
  setText(root, ".ep-flow-grid .ep-flow-node-sub", gridMode.text);
  setText(
    root,
    ".ep-flow-battery .ep-flow-node-sub",
    `${batteryMode.text}${Number.isFinite(soc) ? ` · ${Math.round(soc)}%` : ""}`
  );

  const semantic = {
    pv: !Number.isFinite(pv) || pv <= FLOW_THRESHOLD_W ? "idle" : "inbound",
    grid: !Number.isFinite(grid) || Math.abs(grid) < FLOW_THRESHOLD_W
      ? "idle"
      : grid > 0 ? "outbound" : "inbound",
    house: !Number.isFinite(house) || house <= FLOW_THRESHOLD_W ? "idle" : "outbound",
    battery: !Number.isFinite(battery) || Math.abs(battery) < FLOW_THRESHOLD_W
      ? "idle"
      : battery > 0 ? "inbound" : "outbound",
  };
  for (const [key, selector] of Object.entries({
    pv: ".ep-link-pv",
    grid: ".ep-link-grid",
    house: ".ep-link-house",
    battery: ".ep-link-battery",
  })) {
    const link = root.querySelector(selector);
    if (!link) continue;
    link.classList.remove("idle", "inbound", "outbound");
    link.classList.add(semantic[key]);
    link.dataset.epV038Motion = motion[key];
  }
}

function patchController(panel, root, automaticOn) {
  const card = root.querySelector(".panel-card.controller");
  if (!card) return;
  const t = copy(panel);
  const button = card.querySelector("#auto-toggle");
  if (button) {
    button.classList.toggle("on", automaticOn);
    button.classList.toggle("off", !automaticOn);
    button.setAttribute("aria-pressed", automaticOn ? "true" : "false");
    replaceTrailingButtonText(button, automaticOn ? t.automaticOn : t.automaticOff);
  }

  const modeState = panel._stateByKey?.("ems_mode");
  const mode = Number(modeState?.state);
  const modeName = Number.isFinite(mode)
    ? localizedEmsMode(language(panel), mode).name
    : modeState?.attributes?.mode_name || "—";
  patchMetric(card, ["EMS mode", "EMS-modus"], `${modeState?.state || "—"} · ${modeName}`);
  patchMetric(card, ["EMS setpoint", "EMS-setpoint"], panel._formatPower(finite(panel, "ems_setpoint")));
  patchMetric(
    card,
    ["EnergyPilot target", "PCC target", "Battery target", "Control target", "PCC-doel", "Batterijdoel", "Regeldoel"],
    panel._formatPower(finite(panel, "target_power"))
  );
  patchMetric(card, ["Command", "Commando"], panel._textByKey?.("control_command") || "—");

  const manual = card.querySelector(".ep-v021-manual-pad");
  if (manual) {
    const controlsReady = Boolean(panel._entityId?.("manual_mode") && panel._entityId?.("manual_power"));
    manual.classList.toggle("locked", automaticOn || !controlsReady);
    const state = manual.querySelector(".ep-v021-manual-state");
    if (state) state.textContent = automaticOn ? t.locked : controlsReady ? t.manualReady : t.entitiesMissing;
    for (const modeButton of manual.querySelectorAll(".ep-v021-mode-button")) {
      const active = Number(modeButton.dataset.mode) === mode;
      modeButton.classList.toggle("active", active);
      modeButton.disabled = automaticOn || !controlsReady || Boolean(panel.__epV021ManualBusy);
    }
    const slider = manual.querySelector(".ep-v021-power-slider");
    if (slider) slider.disabled = automaticOn || !controlsReady || Boolean(panel.__epV021ManualBusy);
  }
}

function patchEmhass(panel, root) {
  const card = root.querySelector(".panel-card.emhass");
  if (!card) return;
  const t = copy(panel);
  const pBattState = externalState(
    panel,
    ["sensor.p_batt_forecast"],
    [".p_batt_forecast", "_p_batt_forecast"]
  );
  const optimState = externalState(
    panel,
    ["sensor.optim_status"],
    [".optim_status", "_optim_status"]
  );
  const socForecast = externalState(
    panel,
    ["sensor.soc_batt_forecast"],
    [".soc_batt_forecast", "_soc_batt_forecast"]
  );
  const loadForecast = externalState(
    panel,
    ["sensor.p_load_forecast"],
    [".p_load_forecast", "_p_load_forecast"]
  );
  const pvForecast = externalState(
    panel,
    ["sensor.p_pv_forecast"],
    [".p_pv_forecast", "_p_pv_forecast"]
  );
  const pBatt = panel._numberState?.(pBattState, null);
  const optimText = optimState?.state || "Not detected";
  setStatus(card.querySelector(".section-title-row .status"), normalize(optimText) === "optimal", optimText);
  setText(card, ".emhass-target strong", panel._formatPower(pBatt));
  patchMetric(card, ["SOC forecast", "SOC-voorspelling"], panel._formatState(socForecast));
  patchMetric(card, ["Load forecast", "Belastingsvoorspelling"], panel._formatState(loadForecast));
  patchMetric(card, ["PV forecast", "PV-voorspelling"], panel._formatState(pvForecast));
  const mapping = !Number.isFinite(pBatt)
    ? t.waiting
    : pBatt < -FLOW_THRESHOLD_W
      ? t.modeCharge
      : pBatt > FLOW_THRESHOLD_W
        ? t.modeDischarge
        : t.modeHold;
  patchMetric(card, ["Mapping", "Toewijzing"], mapping);
}

function patchStrategy(panel, root) {
  const strategy = root.querySelector(".ep-v038-strategy");
  if (!strategy) return;
  for (const input of strategy.querySelectorAll("input[data-ep-v038-soc]")) {
    const kind = input.dataset.epV038Soc;
    const key = kind === "min" ? "emhass_minimum_soc" : "emhass_maximum_soc";
    const value = finite(panel, key);
    if (!Number.isFinite(value)) continue;
    if (root.activeElement !== input) input.value = String(value);
    const label = strategy.querySelector(`[data-ep-v038-soc-value="${kind}"]`);
    if (label) label.textContent = `${Math.round(value)}%`;
  }
}

function patchLiveDom(panel) {
  const root = panel.shadowRoot;
  if (!root?.querySelector("main")) return;
  const pv = finite(panel, "pv_total_power");
  const load = finite(panel, "total_load_power");
  const grid = finite(panel, "meter_total_power_fast");
  const battery = finite(panel, "battery_power");
  const soc = finite(panel, "battery_soc");
  const soh = finite(panel, "battery_soh");
  const inverter = finite(panel, "total_inverter_power");
  const acActive = finite(panel, "ac_active_power");
  const automaticOn = panel._stateByKey?.("automatic_control")?.state === "on";
  const t = copy(panel);

  const headerStatus = root.querySelector("header .status");
  setStatus(headerStatus, automaticOn, automaticOn ? t.autoActive : t.goodweAuto);

  const solar = root.querySelector(".energy-card.solar");
  setText(solar, ".hero-value", panel._formatPower(pv));
  patchMetric(solar, ["PV1"], panel._formatPower(finite(panel, "pv1_power")));
  patchMetric(solar, ["PV2"], panel._formatPower(finite(panel, "pv2_power")));
  patchMetric(solar, ["PV3"], panel._formatPower(finite(panel, "pv3_power")));
  patchMetric(solar, ["PV4"], panel._formatPower(finite(panel, "pv4_power")));

  const home = root.querySelector(".energy-card.home");
  setText(home, ".hero-value", panel._formatPower(load));
  patchBalanceRows(home, panel, load, inverter, acActive);

  const gridCard = root.querySelector(".energy-card.grid");
  setText(gridCard, ".hero-value", panel._formatPower(Number.isFinite(grid) ? Math.abs(grid) : null));
  patchPill(gridCard, gridPresentation(panel, grid));
  for (const [phase, key, voltage, current] of [
    ["L1", "meter_l1_active_power", "meter_l1_voltage", "meter_l1_current"],
    ["L2", "meter_l2_active_power", "meter_l2_voltage", "meter_l2_current"],
    ["L3", "meter_l3_active_power", "meter_l3_voltage", "meter_l3_current"],
  ]) {
    patchMetric(
      gridCard,
      [phase],
      panel._formatPower(finite(panel, key)),
      `${panel._formatState(panel._stateByKey?.(voltage))} · ${panel._formatState(panel._stateByKey?.(current))}`
    );
  }

  const batteryCard = root.querySelector(".energy-card.battery");
  patchPill(batteryCard, batteryPresentation(panel, battery));
  setText(batteryCard, ".soc", Number.isFinite(soc) ? `${Math.round(soc)}%` : "—");
  setText(batteryCard, ".battery-power", panel._formatPower(battery));
  const fill = batteryCard?.querySelector(".soc-fill");
  if (fill) fill.style.width = `${Number.isFinite(soc) ? Math.min(100, Math.max(0, soc)) : 0}%`;
  patchMetric(batteryCard, ["SOH"], Number.isFinite(soh) ? `${Math.round(soh)}%` : "—");
  patchMetric(batteryCard, ["Voltage", "Spanning"], panel._formatState(panel._stateByKey?.("battery_voltage")));
  patchMetric(batteryCard, ["Current", "Stroom"], panel._formatState(panel._stateByKey?.("battery_current")));
  patchMetric(batteryCard, ["Max cell temp", "Maximale celtemperatuur"], panel._formatState(panel._stateByKey?.("battery_max_cell_temperature")));

  patchController(panel, root, automaticOn);
  patchEmhass(panel, root);
  patchStrategy(panel, root);
  patchFlow(panel, root, pv, load, grid, battery, soc);

  const thermal = root.querySelector(".panel-card.thermal");
  patchMetric(thermal, ["Inverter radiator", "Omvormerradiator"], panel._formatState(panel._stateByKey?.("inverter_radiator_temperature")));
  patchMetric(thermal, ["BMS package", "BMS-pakket"], panel._formatState(panel._stateByKey?.("bms_package_temperature")));
  patchMetric(thermal, ["Battery max cell", "Maximale batterijcel"], panel._formatState(panel._stateByKey?.("battery_max_cell_temperature")));
  patchMetric(thermal, ["BMS max charge", "BMS max laden"], panel._formatState(panel._stateByKey?.("bms_max_charge_current")));
  patchMetric(thermal, ["BMS max discharge", "BMS max ontladen"], panel._formatState(panel._stateByKey?.("bms_max_discharge_current")));
}

function ensureNoMotionStyle(root) {
  if (!root || root.querySelector(`#${MOTION_STYLE_ID}`)) return;
  const style = document.createElement("style");
  style.id = MOTION_STYLE_ID;
  style.textContent = NO_MOTION_CSS;
  root.appendChild(style);
}

function contextSignature(hass) {
  const locale = hass?.locale || {};
  const user = hass?.user || {};
  const themes = hass?.themes || {};
  return JSON.stringify({
    language: locale.language || hass?.language || "en",
    numberFormat: locale.number_format || "",
    timeFormat: locale.time_format || "",
    userId: user.id || "",
    admin: Boolean(user.is_admin),
    darkMode: Boolean(themes.darkMode),
    theme: themes.theme || "",
  });
}

function structureSignature(panel) {
  const pBattState = externalState(
    panel,
    ["sensor.p_batt_forecast"],
    [".p_batt_forecast", "_p_batt_forecast"]
  );
  const pBatt = panel._numberState?.(pBattState, null);
  const pv4 = finite(panel, "pv4_power");
  return JSON.stringify({
    registryLoaded: Boolean(panel._registryLoaded),
    entities: Object.keys(panel._entityMap || {}).length,
    pBattState: Boolean(pBattState),
    pBattNumeric: Number.isFinite(pBatt),
    pv4Visible: Number.isFinite(pv4) && Math.abs(pv4) > 20,
  });
}

function scheduleLivePatch(panel) {
  if (panel.__epV041LivePatchTimer) return;
  panel.__epV041LivePatchTimer = globalThis.setTimeout(() => {
    panel.__epV041LivePatchTimer = null;
    patchLiveDom(panel);
  }, LIVE_PATCH_DELAY_MS);
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (PanelClass && !PanelClass.prototype.__epV041Installed) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV041StructuralRender(...args) {
    // The v0.38 interaction guard was necessary only while telemetry could
    // destroy the pressed node. v0.41 patches telemetry in place, so do not
    // install another pointer/touch ownership layer in fresh sessions.
    this.__epV041StableRuntime = true;
    this.__epV038InteractionGuardInstalled = true;
    const result = previousRender.apply(this, args);
    ensureNoMotionStyle(this.shadowRoot);
    const root = this.shadowRoot;
    const versionBadge = root?.querySelector(".version");
    if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
    const footerItems = root?.querySelectorAll("footer span") || [];
    if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
    this.__epV041ContextSignature = contextSignature(this._hass);
    this.__epV041StructureSignature = structureSignature(this);
    patchLiveDom(this);
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
        const previous = this._hass;
        if (!previous || !this._registryLoaded) {
          descriptor.set.call(this, value);
          return;
        }

        this._hass = value;
        if (this.__epV038HassRenderTimer) {
          globalThis.clearTimeout(this.__epV038HassRenderTimer);
          this.__epV038HassRenderTimer = null;
        }
        if (this.__epV016SettingsOpen) return;

        const context = contextSignature(value);
        const structure = structureSignature(this);
        if (
          context !== this.__epV041ContextSignature ||
          structure !== this.__epV041StructureSignature
        ) {
          this._queueRender();
          return;
        }
        scheduleLivePatch(this);
      },
    });
  }

  PanelClass.prototype.__epV041Installed = true;
}
