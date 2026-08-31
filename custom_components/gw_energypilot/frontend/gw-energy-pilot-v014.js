import "./gw-energy-pilot-v013.js?v=1.0.1-beta4";

const VERSION = "0.14";
const PANEL_NAME = "gw-energypilot-panel";

function energyText(value) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(number >= 100 ? 0 : 1)} kWh` : "—";
}

function percentText(value) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(0)}%` : "—";
}

function diagnosticRow(panel, label, value, marker) {
  return `<div class="ep-v011-diag-row" data-v014-battery="${marker}"><span>${panel._escape(label)}</span><strong>${panel._escape(value)}</strong></div>`;
}

function batterySnapshot(attrs) {
  const fields = [
    ["EMS mode 47511", `${attrs.ems_mode ?? "—"} - ${attrs.ems_mode_name ?? "Unknown"}`],
    ["EMS setpoint 47512", attrs.ems_setpoint],
    ["APP / Work 47000", attrs.app_work_mode_47000],
    ["Work mode 35187", attrs.work_mode_35187],
    ["Operation mode 35188", attrs.operation_mode_35188],
    ["Grid mode 35136", attrs.grid_mode_35136],
    ["GoodWe load 35172", attrs.house_load_register_35172],
    ["Load phase sum", attrs.house_load_phase_sum],
    ["System power balance", attrs.system_balance_power ?? attrs.house_load_power_balance],
    ["Grid meter fast total", attrs.meter_total_power_fast],
    ["Inverter total power 35138", attrs.total_inverter_power],
    ["Inverter active power 35140", attrs.ac_active_power],
    ["Grid energy imported total", attrs.meter_total_energy_import],
    ["Grid energy exported total", attrs.meter_total_energy_export],
    ["Battery power", attrs.battery_power],
    ["Battery SOC", attrs.battery_soc],
    ["Battery SOH", attrs.battery_soh],
    ["Battery charge energy total 35206", attrs.battery_charge_energy_total],
    ["Battery charge energy today 35208", attrs.battery_charge_energy_today],
    ["Battery discharge energy total 35209", attrs.battery_discharge_energy_total],
    ["Battery discharge energy today 35211", attrs.battery_discharge_energy_today],
    ["Automatic control", attrs.controller_enabled ? "ON" : "OFF"],
    ["Controller command", attrs.controller_command],
    ["Controller target", attrs.controller_target_power],
    ["Expected EMS mode", attrs.controller_expected_mode],
    ["Maximum power", attrs.controller_max_power],
    ["Battery Hold deadband", attrs.controller_deadband],
    ["GoodWe Auto deadband", attrs.controller_goodwe_auto_deadband],
    ["P_batt entity", attrs.p_batt_entity],
    ["P_batt", attrs.p_batt_value],
    ["Optimization status entity", attrs.optim_status_entity],
    ["Optimization status", attrs.optim_status_value],
    ["SOC init", attrs.soc_init],
    ["Orchestrator status", attrs.orchestrator_status],
    ["Last reason", attrs.last_reason],
    ["Telemetry refresh", attrs.telemetry_refresh_seconds],
    ["Optimization interval", attrs.optimization_interval_minutes],
    ["EMHASS health", attrs.emhass_health],
    ["EMHASS version", attrs.emhass_version],
    ["Price source", attrs.price_runtime_source],
    ["Price entity", attrs.price_entity],
    ["Price area", attrs.price_area],
    ["Price points", attrs.price_points],
    ["Load forecast source", attrs.load_forecast_source],
    ["Load forecast points", attrs.load_forecast_points],
    ["Optimize HTTP", attrs.optimize_http_status],
    ["Publish HTTP", attrs.publish_http_status],
    ["Parallel GoodWe entries", Array.isArray(attrs.parallel_goodwe_entries) ? attrs.parallel_goodwe_entries.join(", ") : attrs.parallel_goodwe_entries],
    ["Last error", attrs.last_error],
  ];
  return [
    "GW EnergyPilot diagnostics",
    ...fields.map(([label, value]) => `${label}: ${value ?? "—"}`),
  ].join("\n");
}

function enrichBatteryDiagnostics(panel, root) {
  const card = root.querySelector(".panel-card.diagnostics");
  if (!card) return;

  const optimizeId = panel._entityId("optimize_now");
  const attrs = (optimizeId ? panel._state(optimizeId)?.attributes : null) || {};
  const group = card.querySelector(".ep-v011-diag-group");
  if (!group) return;

  if (!group.querySelector('[data-v014-battery="soh"]')) {
    group.insertAdjacentHTML(
      "beforeend",
      diagnosticRow(panel, "Battery SOH", percentText(attrs.battery_soh), "soh") +
      diagnosticRow(panel, "Battery charged lifetime", energyText(attrs.battery_charge_energy_total), "charged-total") +
      diagnosticRow(panel, "Battery discharged lifetime", energyText(attrs.battery_discharge_energy_total), "discharged-total") +
      diagnosticRow(panel, "Battery charged today", energyText(attrs.battery_charge_energy_today), "charged-today") +
      diagnosticRow(panel, "Battery discharged today", energyText(attrs.battery_discharge_energy_today), "discharged-today")
    );
  }

  const existingCopy = card.querySelector(".ep-v011-copy");
  if (!existingCopy || existingCopy.dataset.v014Battery === "1") return;

  const copy = existingCopy.cloneNode(true);
  copy.dataset.v014Battery = "1";
  existingCopy.replaceWith(copy);
  copy.addEventListener("click", async () => {
    const text = batterySnapshot(attrs);
    try {
      await navigator.clipboard.writeText(text);
      const previous = copy.textContent;
      copy.textContent = "Copied";
      setTimeout(() => { copy.textContent = previous; }, 1200);
    } catch (_err) {
      window.prompt("Copy EnergyPilot diagnostics", text);
    }
  });
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV014Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  enrichBatteryDiagnostics(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION}`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION}`;
};
