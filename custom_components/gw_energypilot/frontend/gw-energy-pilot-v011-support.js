import "./gw-energy-pilot-v011-motion.js?v=0.11-motion2";

const PANEL_NAME = "gw-energypilot-panel";

function valueText(panel, value, power = false) {
  if (value === null || value === undefined || value === "") return "—";
  if (power) {
    const number = Number(value);
    return Number.isFinite(number) ? panel._formatPower(number) : String(value);
  }
  return String(value);
}

function row(panel, label, value, power = false, marker = "") {
  return `<div class="ep-v011-diag-row"${marker ? ` data-v011-extra="${marker}"` : ""}><span>${panel._escape(label)}</span><strong>${panel._escape(valueText(panel, value, power))}</strong></div>`;
}

function snapshot(attrs) {
  const fields = [
    ["EMS mode 47511", `${attrs.ems_mode ?? "—"} - ${attrs.ems_mode_name ?? "Unknown"}`],
    ["EMS setpoint 47512", attrs.ems_setpoint],
    ["APP / Work 47000", attrs.app_work_mode_47000],
    ["Work mode 35187", attrs.work_mode_35187],
    ["Operation mode 35188", attrs.operation_mode_35188],
    ["Grid mode 35136", attrs.grid_mode_35136],
    ["House load 35172", attrs.house_load_register_35172],
    ["Load phase sum", attrs.house_load_phase_sum],
    ["Power-balance house load", attrs.house_load_power_balance],
    ["Meter fast total", attrs.meter_total_power_fast],
    ["Inverter power", attrs.total_inverter_power],
    ["AC active power", attrs.ac_active_power],
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
    ["Price area", attrs.price_area],
    ["Price points", attrs.price_points],
    ["Load forecast points", attrs.load_forecast_points],
    ["Optimize HTTP", attrs.optimize_http_status],
    ["Publish HTTP", attrs.publish_http_status],
    ["Last error", attrs.last_error],
  ];
  return [
    "GW EnergyPilot diagnostics v0.11",
    ...fields.map(([label, value]) => `${label}: ${value ?? "—"}`),
  ].join("\n");
}

function enrichDiagnostics(panel, root) {
  const card = root.querySelector(".panel-card.diagnostics");
  if (!card) return;

  const optimizeId = panel._entityId("optimize_now");
  const attrs = (optimizeId ? panel._state(optimizeId)?.attributes : null) || {};
  const groups = card.querySelectorAll(".ep-v011-diag-group");

  if (groups[0] && !groups[0].querySelector('[data-v011-extra="app-work"]')) {
    const rows = groups[0].querySelectorAll(".ep-v011-diag-row");
    const emsSetpointRow = rows[1];
    if (emsSetpointRow) {
      emsSetpointRow.insertAdjacentHTML(
        "afterend",
        row(panel, "APP / Work 47000", attrs.app_work_mode_47000, false, "app-work")
      );
    }
  }

  if (groups[1] && !groups[1].querySelector('[data-v011-extra="limits"]')) {
    const targetRows = groups[1].querySelectorAll(".ep-v011-diag-row");
    const targetRow = targetRows[2];
    const html =
      row(panel, "Maximum power", attrs.controller_max_power, true, "limits") +
      row(panel, "Deadband", attrs.controller_deadband, true, "deadband");
    if (targetRow) targetRow.insertAdjacentHTML("afterend", html);
    else groups[1].insertAdjacentHTML("beforeend", html);
  }

  const existingCopy = card.querySelector(".ep-v011-copy");
  if (!existingCopy || existingCopy.dataset.v011Support === "1") return;

  const copy = existingCopy.cloneNode(true);
  copy.dataset.v011Support = "1";
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

PanelClass.prototype._render = function energyPilotV011SupportRender() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;
  enrichDiagnostics(this, root);
};
