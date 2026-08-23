import "./gw-energy-pilot-v013.js?v=0.13-grid1";

const VERSION = "0.14";
const PANEL_NAME = "gw-energypilot-panel";

function diagValue(value, suffix = "") {
  if (value === null || value === undefined || value === "") return "—";
  return `${value}${suffix}`;
}

function diagRow(panel, label, value, suffix = "", marker = "") {
  const text = diagValue(value, suffix);
  return `<div class="ep-v011-diag-row"${marker ? ` data-v014-extra="${marker}"` : ""}><span>${panel._escape(label)}</span><strong>${panel._escape(text)}</strong></div>`;
}

function snapshot(attrs) {
  const fields = [
    ["EMS mode 47511", `${attrs.ems_mode ?? "—"} - ${attrs.ems_mode_name ?? "Unknown"}`],
    ["EMS setpoint 47512", attrs.ems_setpoint],
    ["SOC protection 47500", attrs.battery_soc_protection_47500],
    ["On-grid discharge depth 45356", attrs.battery_discharge_depth_on_grid_45356],
    ["Off-grid discharge depth 45358", attrs.battery_discharge_depth_off_grid_45358],
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
    ["Automatic control", attrs.controller_enabled ? "ON" : "OFF"],
    ["Controller command", attrs.controller_command],
    ["Controller target", attrs.controller_target_power],
    ["Expected EMS mode", attrs.controller_expected_mode],
    ["Maximum power", attrs.controller_max_power],
    ["Deadband", attrs.controller_deadband],
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
    "SOC protection registers are read-only candidate ETA-G20 diagnostics.",
    ...fields.map(([label, value]) => `${label}: ${value ?? "—"}`),
  ].join("\n");
}

function enrichSocProtectionDiagnostics(panel, root) {
  const card = root.querySelector(".panel-card.diagnostics");
  if (!card) return;

  const optimizeId = panel._entityId("optimize_now");
  const attrs = (optimizeId ? panel._state(optimizeId)?.attributes : null) || {};
  const group = card.querySelector(".ep-v011-diag-group");

  if (group && !group.querySelector('[data-v014-extra="soc-protection"]')) {
    const rows = [...group.querySelectorAll(".ep-v011-diag-row")];
    const appWorkRow = rows.find((item) => item.querySelector("span")?.textContent?.includes("APP / Work"));
    const html =
      diagRow(panel, "SOC protection 47500", attrs.battery_soc_protection_47500, "", "soc-protection") +
      diagRow(panel, "On-grid discharge depth 45356", attrs.battery_discharge_depth_on_grid_45356, "%", "soc-on-grid") +
      diagRow(panel, "Off-grid discharge depth 45358", attrs.battery_discharge_depth_off_grid_45358, "%", "soc-off-grid");
    if (appWorkRow) appWorkRow.insertAdjacentHTML("beforebegin", html);
    else group.insertAdjacentHTML("beforeend", html);
  }

  let note = card.querySelector(".ep-v014-soc-note");
  if (!note) {
    note = document.createElement("div");
    note.className = "ep-v011-diag-note ep-v014-soc-note";
    note.textContent = "Registers 45356, 45358 and 47500 are read-only diagnostics. Their ETA-G20 semantics remain candidate/validation data until confirmed against SolarGo/SEMS+ on tested hardware.";
    card.appendChild(note);
  }

  const existingCopy = card.querySelector(".ep-v011-copy");
  if (!existingCopy || existingCopy.dataset.v014 === "1") return;

  const copy = existingCopy.cloneNode(true);
  copy.dataset.v014 = "1";
  existingCopy.replaceWith(copy);
  copy.addEventListener("click", async () => {
    const text = snapshot(attrs);
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

  enrichSocProtectionDiagnostics(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION}`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION}`;
};
