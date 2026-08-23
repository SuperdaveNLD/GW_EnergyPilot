import "./gw-energy-pilot-v018.js?v=0.18-beta-soc-floor1";

const VERSION = "0.19";
const PANEL_NAME = "gw-energypilot-panel";

function numericState(panel, key) {
  const state = panel._stateByKey(key);
  if (!state || ["unknown", "unavailable"].includes(state.state)) return null;
  const value = Number(state.state);
  return Number.isFinite(value) ? value : null;
}

function pct(value, decimals = 1) {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(decimals)}%` : "—";
}

function constraintContext(panel) {
  const optimizeId = panel._entityId("optimize_now");
  const attrs = (optimizeId ? panel._state(optimizeId)?.attributes : null) || {};
  const strategyState = panel._stateByKey("emhass_cost_function");
  const configAttrs = strategyState?.attributes || {};
  const minimumEntityValue = numericState(panel, "emhass_minimum_soc");

  const socInit = attrs.soc_init === null || attrs.soc_init === undefined
    ? null
    : Number(attrs.soc_init) * 100;
  const runtimeFinal = attrs.runtime_soc_final === null || attrs.runtime_soc_final === undefined
    ? null
    : Number(attrs.runtime_soc_final) * 100;

  return {
    currentSoc: attrs.battery_soc,
    socInit,
    runtimeFinal,
    emhassMinimum: minimumEntityValue ?? configAttrs.emhass_minimum_soc_pct,
    emhassConfigTarget: configAttrs.emhass_config_target_soc_pct,
    emhassDeficitThreshold: configAttrs.emhass_soc_deficit_threshold_pct,
    goodweOnGridMinimum: attrs.battery_discharge_depth_on_grid_45356,
  };
}

function diagRow(panel, label, value, marker) {
  return `<div class="ep-v011-diag-row" data-v019-soc="${marker}"><span>${panel._escape(label)}</span><strong>${panel._escape(value)}</strong></div>`;
}

function installSocConstraintDiagnostics(panel, root) {
  const card = root.querySelector(".panel-card.diagnostics");
  const grid = card?.querySelector(".ep-v011-diag-grid");
  if (!card || !grid || grid.querySelector('[data-v019-soc-group="1"]')) return;

  if (!root.querySelector("#ep-v019-soc-style")) {
    const style = document.createElement("style");
    style.id = "ep-v019-soc-style";
    style.textContent = `
      .ep-v019-soc-group { grid-column: 1 / -1; }
      .ep-v019-soc-note {
        padding: 8px 10px;
        color: #66859a;
        font-size: 8px;
        line-height: 1.45;
        border-top: 1px solid rgba(77,161,218,.07);
      }
      .ep-v019-soc-note strong { color: #a9dfe9; }
    `;
    root.appendChild(style);
  }

  const values = constraintContext(panel);
  const group = document.createElement("div");
  group.className = "ep-v011-diag-group ep-v019-soc-group";
  group.dataset.v019SocGroup = "1";
  group.innerHTML = `
    <div class="ep-v011-diag-group-title">SOC / CONSTRAINT LAYERS</div>
    ${diagRow(panel, "Current battery SOC", pct(values.currentSoc), "current")}
    ${diagRow(panel, "Last optimization SOC init", pct(values.socInit), "init")}
    ${diagRow(panel, "Runtime final SOC target (soc_final)", pct(values.runtimeFinal), "runtime-final")}
    ${diagRow(panel, "EMHASS minimum SOC", pct(values.emhassMinimum), "minimum")}
    ${diagRow(panel, "EMHASS config target SOC (fallback)", pct(values.emhassConfigTarget), "config-target")}
    ${diagRow(panel, "EMHASS deficit threshold", pct(values.emhassDeficitThreshold), "deficit")}
    ${diagRow(panel, "GoodWe on-grid minimum SOC 45356", pct(values.goodweOnGridMinimum), "goodwe")}
    <div class="ep-v019-soc-note">
      <strong>Runtime final SOC</strong> is the EnergyPilot value sent as <code>soc_final</code> with each optimization.
      The EMHASS config target is a separate <code>battery_target_state_of_charge</code> value. The deficit threshold is a cost penalty threshold, not a hard SOC floor. GoodWe 45356 is the inverter-side G20 minimum-SOC setting currently under field validation.
    </div>`;
  grid.appendChild(group);
}

function clarifyFinalSocSetting(root) {
  const input = root.querySelector('[data-setting-key="emhass_soc_final_pct"]');
  const field = input?.closest(".ep-v016-field");
  if (!field) return;

  const label = field.querySelector(".ep-v016-field-label span:first-child");
  if (label) label.textContent = "Runtime final SOC target";

  const description = field.querySelector(".ep-v016-field-description");
  if (description) {
    description.textContent = "Sent to EMHASS as runtime soc_final for every EnergyPilot optimization. This does not rewrite EMHASS battery_target_state_of_charge in config.json.";
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV019Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  installSocConstraintDiagnostics(this, root);
  clarifyFinalSocSetting(root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
};
