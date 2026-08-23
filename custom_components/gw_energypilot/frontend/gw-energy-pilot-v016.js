import "./gw-energy-pilot-v015.js?v=0.15-costfun1";

const VERSION = "0.16";
const PANEL_NAME = "gw-energypilot-panel";

function valueText(value, suffix = "") {
  if (value === null || value === undefined || value === "") return "—";
  return `${value}${suffix}`;
}

function betaRow(panel, label, value, suffix, marker) {
  return `<div class="ep-v011-diag-row" data-v016-beta="${marker}"><span>${panel._escape(label)}</span><strong>${panel._escape(valueText(value, suffix))}</strong></div>`;
}

function betaSnapshot(attrs) {
  const fields = [
    ["SOC protection candidate 47500", attrs.battery_soc_protection_47500],
    ["On-grid discharge depth candidate 45356", attrs.battery_discharge_depth_on_grid_45356],
    ["Off-grid discharge depth candidate 45358", attrs.battery_discharge_depth_off_grid_45358],
    ["Extended grid export candidate 36104 kWh", attrs.meter_total_energy_export_extended_candidate],
    ["Extended grid import candidate 36120 kWh", attrs.meter_total_energy_import_extended_candidate],
    ["Legacy grid export 36015 kWh", attrs.meter_total_energy_export],
    ["Legacy grid import 36017 kWh", attrs.meter_total_energy_import],
    ["Battery SOC", attrs.battery_soc],
    ["EMS mode 47511", attrs.ems_mode],
    ["EMS setpoint 47512", attrs.ems_setpoint],
  ];
  return [
    "GW EnergyPilot v0.16 beta G20 diagnostics",
    "Read-only candidate registers; do not treat semantics as confirmed.",
    ...fields.map(([label, value]) => `${label}: ${value ?? "—"}`),
  ].join("\n");
}

function enrichBetaDiagnostics(panel, root) {
  const card = root.querySelector(".panel-card.diagnostics");
  if (!card) return;

  const optimizeId = panel._entityId("optimize_now");
  const attrs = (optimizeId ? panel._state(optimizeId)?.attributes : null) || {};
  const group = card.querySelector(".ep-v011-diag-group");

  if (group && !group.querySelector('[data-v016-beta="soc-protection"]')) {
    group.insertAdjacentHTML(
      "beforeend",
      betaRow(panel, "BETA · SOC protection 47500", attrs.battery_soc_protection_47500, "", "soc-protection") +
      betaRow(panel, "BETA · On-grid discharge depth 45356", attrs.battery_discharge_depth_on_grid_45356, "%", "soc-on-grid") +
      betaRow(panel, "BETA · Off-grid discharge depth 45358", attrs.battery_discharge_depth_off_grid_45358, "%", "soc-off-grid") +
      betaRow(panel, "BETA · Extended grid export 36104", attrs.meter_total_energy_export_extended_candidate, " kWh", "grid-export") +
      betaRow(panel, "BETA · Extended grid import 36120", attrs.meter_total_energy_import_extended_candidate, " kWh", "grid-import")
    );
  }

  if (!card.querySelector(".ep-v016-beta-note")) {
    const note = document.createElement("div");
    note.className = "ep-v011-diag-note ep-v016-beta-note";
    note.textContent = "BETA / read-only: 45356, 45358, 47500, 36104 and 36120 are collected for ETA-G20 field validation. They are not used for control or canonical energy accounting.";
    card.appendChild(note);
  }

  if (!card.querySelector(".ep-v016-copy")) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "ep-v011-copy ep-v016-copy";
    button.textContent = "Copy beta diagnostics";
    button.addEventListener("click", async () => {
      const text = betaSnapshot(attrs);
      try {
        await navigator.clipboard.writeText(text);
        const previous = button.textContent;
        button.textContent = "Copied";
        setTimeout(() => { button.textContent = previous; }, 1200);
      } catch (_err) {
        window.prompt("Copy EnergyPilot beta diagnostics", text);
      }
    });
    card.appendChild(button);
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV016Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  enrichBetaDiagnostics(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION}`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION}`;
};
