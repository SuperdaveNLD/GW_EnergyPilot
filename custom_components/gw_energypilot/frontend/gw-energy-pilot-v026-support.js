import "./gw-energy-pilot-v026-complete.js?v=1.0.1-beta3";

const VERSION = "0.26";
const PANEL_NAME = "gw-energypilot-panel";

const TEXT = {
  en: {
    title: "System diagnostics", copy: "Copy support report", copied: "Copied",
    prompt: "Copy GW EnergyPilot support report", goodwe: "GoodWe", live: "LIVE",
    unavailable: "Unavailable", control: "Control", auto: "AUTO", manual: "MANUAL",
    optimizer: "Optimizer", minSoc: "Minimum SOC", synced: "Synced", mismatch: "Mismatch",
    goodweGroup: "GOODWE / LIVE", controlGroup: "CONTROL / EMHASS", socGroup: "SOC / LIMITS",
    mode: "EMS mode 47511", setpoint: "EMS setpoint 47512", grid: "Grid power",
    import: "import", export: "export", balanced: "balanced", battery: "Battery power",
    charging: "charging", discharging: "discharging", holding: "holding",
    load: "House load 35172", batteryState: "Battery SOC / SOH",
    automatic: "Automatic control", command: "Command", target: "Controller target",
    expected: "Expected EMS mode", pBatt: "P_batt target", pGrid: "P_grid target",
    optimization: "Optimization", orchestrator: "Orchestrator", trigger: "Last trigger",
    setpointUpdate: "Last EMS setpoint update",
    error: "Last error", currentSoc: "Current battery SOC",
    minimumPair: "Minimum SOC · EMHASS / GoodWe", maximumSoc: "Maximum SOC",
    optimizationSoc: "Last optimization · init → final", configuredFinal: "Configured next final target",
  },
  nl: {
    title: "Systeemdiagnose", copy: "Kopieer supportrapport", copied: "Gekopieerd",
    prompt: "Kopieer GW EnergyPilot supportrapport", goodwe: "GoodWe", live: "LIVE",
    unavailable: "Niet beschikbaar", control: "Regeling", auto: "AUTO", manual: "HANDMATIG",
    optimizer: "Optimizer", minSoc: "Minimum-SOC", synced: "Gesynchroniseerd", mismatch: "Verschil",
    goodweGroup: "GOODWE / LIVE", controlGroup: "REGELING / EMHASS", socGroup: "SOC / LIMIETEN",
    mode: "EMS-modus 47511", setpoint: "EMS-setpoint 47512", grid: "Netvermogen",
    import: "importeren", export: "exporteren", balanced: "in balans", battery: "Accuvermogen",
    charging: "laden", discharging: "ontladen", holding: "vasthouden",
    load: "Huisverbruik 35172", batteryState: "Accu-SOC / SOH",
    automatic: "Automatische regeling", command: "Commando", target: "Regeldoel",
    expected: "Verwachte EMS-modus", pBatt: "P_batt-doel", pGrid: "P_grid-doel",
    optimization: "Optimalisatie", orchestrator: "Orchestrator", trigger: "Laatste trigger",
    setpointUpdate: "Laatste EMS-setpointupdate",
    error: "Laatste fout", currentSoc: "Huidige accu-SOC",
    minimumPair: "Minimum-SOC · EMHASS / GoodWe", maximumSoc: "Maximum-SOC",
    optimizationSoc: "Laatste optimalisatie · start → eind", configuredFinal: "Volgend ingesteld einddoel",
  },
};

function language(panel) {
  if (typeof panel._epLanguage === "function") return panel._epLanguage();
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function number(value) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function stateNumber(panel, key) {
  const state = panel._stateByKey?.(key);
  return !state || ["unknown", "unavailable"].includes(state.state) ? null : number(state.state);
}

function power(panel, value, absolute = false) {
  const watts = number(value);
  if (watts === null) return "—";
  const display = absolute ? Math.abs(watts) : watts;
  return typeof panel._formatPower === "function" ? panel._formatPower(display) : `${Math.round(display)} W`;
}

function percent(value, decimals = 0) {
  const parsed = number(value);
  return parsed === null ? "—" : `${parsed.toFixed(decimals)}%`;
}

function fractionPercent(value) {
  const parsed = number(value);
  return parsed === null ? null : parsed * 100;
}

function directionalPower(panel, value, negative, positive, neutral) {
  const watts = number(value);
  if (watts === null) return "—";
  const direction = Math.abs(watts) < 50 ? neutral : watts < 0 ? negative : positive;
  return `${power(panel, watts, true)} · ${direction}`;
}

function row(panel, label, value) {
  return `<div class="ep-v011-diag-row"><span>${panel._escape(label)}</span><strong>${panel._escape(value ?? "—")}</strong></div>`;
}

function status(panel, label, value, tone) {
  return `<div class="ep-v026-support-status ${tone}"><span>${panel._escape(label)}</span><strong>${panel._escape(value)}</strong></div>`;
}

function context(panel) {
  const optimizeId = panel._entityId?.("optimize_now");
  const attrs = (optimizeId ? panel._state?.(optimizeId)?.attributes : null) || {};
  const configAttrs = panel._stateByKey?.("emhass_cost_function")?.attributes || {};
  const minimum = stateNumber(panel, "emhass_minimum_soc");
  const maximum = stateNumber(panel, "emhass_maximum_soc");
  const goodweMinimum = number(attrs.battery_discharge_depth_on_grid_45356);
  return {
    attrs, configAttrs, minimum, maximum, goodweMinimum,
    socInit: fractionPercent(attrs.soc_init),
    runtimeFinal: fractionPercent(attrs.runtime_soc_final),
    configuredFinal: fractionPercent(attrs.configured_runtime_soc_final),
    synced: minimum !== null && goodweMinimum !== null ? Math.abs(minimum - goodweMinimum) < 0.5 : null,
  };
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v026-support-clean-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v026-support-clean-style";
  style.textContent = `
    .ep-v026-support-summary { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:8px; margin:0 0 12px; }
    .ep-v026-support-status { min-width:0; padding:8px 10px; border:1px solid rgba(77,161,218,.11); border-radius:10px; background:rgba(7,27,49,.38); }
    .ep-v026-support-status span { display:block; margin-bottom:3px; color:#6f8da1; font-size:8px; font-weight:750; }
    .ep-v026-support-status strong { display:block; color:#dcecf5; font-size:10px; overflow-wrap:anywhere; }
    .ep-v026-support-status.ok strong { color:#72deb5; }
    .ep-v026-support-status.warn strong { color:#efbe78; }
    .ep-v026-support-status.off strong { color:#8199aa; }
    @media (max-width:900px) { .ep-v026-support-summary { grid-template-columns:repeat(2,minmax(0,1fr)); } }
    @media (max-width:520px) { .ep-v026-support-summary { grid-template-columns:1fr; } }
  `;
  root.appendChild(style);
}

function reportValue(value, suffix = "") {
  return value === null || value === undefined || value === "" ? "—" : `${value}${suffix}`;
}

function timestamp(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toISOString();
}

function supportReport(panel) {
  const c = context(panel);
  const a = c.attrs;
  const cfg = c.configAttrs;
  const strategy = panel.__epV022SmartMeter?.data?.strategy || "—";
  const fields = [
    ["Automatic control", a.controller_enabled ? "ON" : "OFF"],
    ["Control strategy", strategy], ["Command", a.controller_command], ["Controller target W", a.controller_target_power],
    ["Expected EMS mode", a.controller_expected_mode], ["Last EMS setpoint update", timestamp(a.last_ems_setpoint_updated_at)],
    ["Last written EMS setpoint W", a.last_ems_setpoint], ["Last written EMS mode", a.last_ems_mode],
    ["P_batt W", a.p_batt_value], ["P_grid W", a.p_grid_value],
    ["Optimization status", a.optim_status_value], ["Orchestrator", a.orchestrator_status], ["Last trigger", a.last_reason], ["Last error", a.last_error],
    ["EMS mode 47511", `${reportValue(a.ems_mode)} · ${reportValue(a.ems_mode_name)}`], ["EMS setpoint 47512 W", a.ems_setpoint],
    ["APP / Work 47000", a.app_work_mode_47000], ["Work mode 35187", a.work_mode_35187], ["Operation mode 35188", a.operation_mode_35188], ["Grid mode 35136", a.grid_mode_35136],
    ["PV total W", a.pv_total_power], ["GoodWe load 35172 W", a.house_load_register_35172], ["Load phase sum W", a.house_load_phase_sum],
    ["System power balance W", a.system_balance_power ?? a.house_load_power_balance], ["Grid meter W", a.meter_total_power_fast],
    ["Inverter total 35138 W", a.total_inverter_power], ["Inverter active 35140 W", a.ac_active_power], ["Battery power W", a.battery_power],
    ["Battery SOC %", a.battery_soc], ["Battery SOH %", a.battery_soh],
    ["Battery charged lifetime kWh", a.battery_charge_energy_total], ["Battery discharged lifetime kWh", a.battery_discharge_energy_total],
    ["Battery charged today kWh", a.battery_charge_energy_today], ["Battery discharged today kWh", a.battery_discharge_energy_today],
    ["EMHASS minimum SOC %", c.minimum], ["GoodWe minimum SOC 45356 %", c.goodweMinimum], ["EMHASS maximum SOC %", c.maximum],
    ["Last SOC init %", c.socInit], ["Configured final SOC %", c.configuredFinal], ["Last runtime final SOC %", c.runtimeFinal],
    ["EMHASS config target raw", cfg.emhass_config_target_soc_raw], ["EMHASS deficit threshold raw", cfg.emhass_soc_deficit_threshold_raw], ["EMHASS deficit cost", cfg.emhass_soc_deficit_cost],
    ["SOC protection 47500", a.battery_soc_protection_47500], ["Off-grid minimum SOC 45358 %", a.battery_discharge_depth_off_grid_45358],
    ["Extended grid export 36104 kWh", a.meter_total_energy_export_extended_candidate], ["Extended grid import 36120 kWh", a.meter_total_energy_import_extended_candidate],
    ["Legacy grid export 36015 kWh", a.meter_total_energy_export], ["Legacy grid import 36017 kWh", a.meter_total_energy_import],
    ["Price source", a.price_runtime_source], ["Price points", a.price_points], ["Load forecast source", a.load_forecast_source], ["Load forecast points", a.load_forecast_points],
    ["EMHASS health", a.emhass_health], ["EMHASS version", a.emhass_version], ["Optimize HTTP", a.optimize_http_status], ["Publish HTTP", a.publish_http_status],
  ];
  return [
    `GW EnergyPilot v${VERSION} support report`, `Created: ${new Date().toISOString()}`, "",
    ...fields.map(([label, value]) => `${label}: ${reportValue(value)}`),
  ].join("\n");
}

function bindCopy(panel, card, text) {
  const oldButton = card.querySelector(".ep-v011-copy");
  if (!oldButton) return;
  if (oldButton.dataset.v026Support === "1") { oldButton.textContent = text.copy; return; }
  const button = oldButton.cloneNode(true);
  button.dataset.v026Support = "1";
  button.textContent = text.copy;
  oldButton.replaceWith(button);
  button.addEventListener("click", async () => {
    const report = supportReport(panel);
    try {
      await navigator.clipboard.writeText(report);
      button.textContent = text.copied;
      setTimeout(() => { button.textContent = text.copy; }, 1200);
    } catch (_err) {
      window.prompt(text.prompt, report);
    }
  });
}

function cleanDiagnostics(panel, root) {
  const card = root.querySelector(".panel-card.diagnostics");
  const grid = card?.querySelector(".ep-v011-diag-grid");
  if (!card || !grid) return;

  ensureStyles(root);
  const text = TEXT[language(panel)] || TEXT.en;
  const c = context(panel);
  const a = c.attrs;
  const title = card.querySelector(".ep-v011-diag-head h2");
  if (title) title.textContent = text.title;
  bindCopy(panel, card, text);

  const goodweLive = a.ems_mode !== null && a.ems_mode !== undefined && a.meter_total_power_fast !== null && a.meter_total_power_fast !== undefined;
  const optim = String(a.optim_status_value || a.orchestrator_status || "—");
  const optimOk = ["optimal", "ready"].includes(optim.toLowerCase());
  const syncLabel = c.synced === null ? text.unavailable : c.synced ? text.synced : text.mismatch;
  const finalSoc = c.runtimeFinal ?? c.configuredFinal;
  const nextTarget = c.configuredFinal !== null && c.runtimeFinal !== null && Math.abs(c.configuredFinal - c.runtimeFinal) >= 0.05
    ? row(panel, text.configuredFinal, percent(c.configuredFinal, 1)) : "";
  const error = a.last_error ? row(panel, text.error, String(a.last_error)) : "";

  grid.innerHTML = `
    <div class="ep-v026-support-summary" style="grid-column:1/-1">
      ${status(panel, text.goodwe, goodweLive ? text.live : text.unavailable, goodweLive ? "ok" : "off")}
      ${status(panel, text.control, a.controller_enabled ? text.auto : text.manual, a.controller_enabled ? "ok" : "off")}
      ${status(panel, text.optimizer, optim, optimOk ? "ok" : "warn")}
      ${status(panel, text.minSoc, syncLabel, c.synced === true ? "ok" : c.synced === false ? "warn" : "off")}
    </div>
    <div class="ep-v011-diag-group">
      <div class="ep-v011-diag-group-title">${panel._escape(text.goodweGroup)}</div>
      ${row(panel, text.mode, a.ems_mode === undefined || a.ems_mode === null ? "—" : `${a.ems_mode} · ${a.ems_mode_name || "Unknown"}`)}
      ${row(panel, text.setpoint, power(panel, a.ems_setpoint))}
      ${row(panel, text.grid, directionalPower(panel, a.meter_total_power_fast, text.import, text.export, text.balanced))}
      ${row(panel, text.battery, directionalPower(panel, a.battery_power, text.charging, text.discharging, text.holding))}
      ${row(panel, text.load, power(panel, a.house_load_register_35172))}
      ${row(panel, text.batteryState, `${percent(a.battery_soc)} / ${percent(a.battery_soh)}`)}
    </div>
    <div class="ep-v011-diag-group">
      <div class="ep-v011-diag-group-title">${panel._escape(text.controlGroup)}</div>
      ${row(panel, text.automatic, a.controller_enabled ? "ON" : "OFF")}
      ${row(panel, text.command, String(a.controller_command ?? "—"))}
      ${row(panel, text.target, power(panel, a.controller_target_power))}
      ${row(panel, text.expected, String(a.controller_expected_mode ?? "—"))}
      ${row(panel, text.setpointUpdate, timestamp(a.last_ems_setpoint_updated_at))}
      ${row(panel, text.pBatt, power(panel, a.p_batt_value))}
      ${row(panel, text.pGrid, power(panel, a.p_grid_value))}
      ${row(panel, text.optimization, String(a.optim_status_value ?? "—"))}
      ${row(panel, text.orchestrator, String(a.orchestrator_status ?? "—"))}
      ${row(panel, text.trigger, String(a.last_reason ?? "—"))}
      ${error}
    </div>
    <div class="ep-v011-diag-group" style="grid-column:1/-1">
      <div class="ep-v011-diag-group-title">${panel._escape(text.socGroup)}</div>
      ${row(panel, text.currentSoc, percent(a.battery_soc, 1))}
      ${row(panel, text.minimumPair, `${percent(c.minimum)} / ${percent(c.goodweMinimum)}${c.synced === null ? "" : ` · ${syncLabel}`}`)}
      ${row(panel, text.maximumSoc, percent(c.maximum, 1))}
      ${row(panel, text.optimizationSoc, `${percent(c.socInit, 1)} → ${percent(finalSoc, 1)}`)}
      ${nextTarget}
    </div>`;

  card.querySelectorAll(".ep-v016-beta-note, .ep-v016-copy, .ep-v011-diag-note, .ep-v019-soc-note").forEach((node) => node.remove());
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV026SupportRender() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;
  cleanDiagnostics(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
};
