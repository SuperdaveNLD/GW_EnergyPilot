import "./gw-energy-pilot-v018.js?v=1.2.0-beta.3-load-forecast1";

const VERSION = "0.19";
const PANEL_NAME = "gw-energypilot-panel";

function numericState(panel, key) {
  const state = panel._stateByKey(key);
  if (!state || ["unknown", "unavailable"].includes(state.state)) return null;
  const value = Number(state.state);
  return Number.isFinite(value) ? value : null;
}

function finiteNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function pct(value, decimals = 1) {
  const number = finiteNumber(value);
  return number === null ? "—" : `${number.toFixed(decimals)}%`;
}

function decimal(value, decimals = 4) {
  const number = finiteNumber(value);
  return number === null ? "—" : number.toFixed(decimals);
}

function constraintContext(panel) {
  const optimizeId = panel._entityId("optimize_now");
  const attrs = (optimizeId ? panel._state(optimizeId)?.attributes : null) || {};
  const strategyState = panel._stateByKey("emhass_cost_function");
  const configAttrs = strategyState?.attributes || {};
  const minimumEntityValue = numericState(panel, "emhass_minimum_soc");
  const rawSocInit = finiteNumber(attrs.soc_init);
  const rawRuntimeFinal = finiteNumber(attrs.runtime_soc_final);

  return {
    currentSoc: attrs.battery_soc,
    socInit: rawSocInit === null ? null : rawSocInit * 100,
    runtimeFinal: rawRuntimeFinal === null ? null : rawRuntimeFinal * 100,
    emhassMinimum: minimumEntityValue ?? configAttrs.emhass_minimum_soc_pct,
    emhassConfigTarget: configAttrs.emhass_config_target_soc_pct,
    emhassDeficitThreshold: configAttrs.emhass_soc_deficit_threshold_pct,
    emhassDeficitCost: configAttrs.emhass_soc_deficit_cost,
    goodweOnGridMinimum: attrs.battery_discharge_depth_on_grid_45356,
  };
}

function diagRow(panel, label, value, marker) {
  return `<div class="ep-v011-diag-row" data-v019-soc="${marker}"><span>${panel._escape(label)}</span><strong>${panel._escape(value)}</strong></div>`;
}

function socConstraintSnapshot(values) {
  return [
    "GW EnergyPilot SOC constraint diagnostics",
    `Current battery SOC: ${pct(values.currentSoc)}`,
    `Last optimization SOC init: ${pct(values.socInit)}`,
    `Runtime final SOC target (soc_final): ${pct(values.runtimeFinal)}`,
    `EMHASS minimum SOC: ${pct(values.emhassMinimum)}`,
    `EMHASS config target SOC (fallback): ${pct(values.emhassConfigTarget)}`,
    `EMHASS deficit threshold: ${pct(values.emhassDeficitThreshold)}`,
    `EMHASS deficit cost: ${decimal(values.emhassDeficitCost)} currency/kWh/h`,
    `GoodWe on-grid minimum SOC 45356: ${pct(values.goodweOnGridMinimum)}`,
  ].join("\n");
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
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 8px 10px;
        color: #66859a;
        font-size: 8px;
        line-height: 1.45;
        border-top: 1px solid rgba(77,161,218,.07);
      }
      .ep-v019-soc-note span { min-width: 0; }
      .ep-v019-soc-note strong { color: #a9dfe9; }
      .ep-v019-soc-copy {
        flex: 0 0 auto;
        padding: 6px 8px;
        border: 1px solid rgba(51,205,235,.18);
        border-radius: 8px;
        color: #8deaf8;
        background: rgba(7,44,69,.44);
        cursor: pointer;
        font-size: 8px;
        font-weight: 800;
      }
      @media (max-width: 720px) {
        .ep-v019-soc-note { align-items: stretch; flex-direction: column; }
      }
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
    ${diagRow(panel, "EMHASS deficit cost", `${decimal(values.emhassDeficitCost)} currency/kWh/h`, "deficit-cost")}
    ${diagRow(panel, "GoodWe on-grid minimum SOC 45356", pct(values.goodweOnGridMinimum), "goodwe")}
    <div class="ep-v019-soc-note">
      <span><strong>Runtime final SOC</strong> is sent as <code>soc_final</code> and overrides the EMHASS config target for that EnergyPilot run. The deficit threshold adds a virtual cost below that SOC; it is not a hard floor. GoodWe 45356 is the inverter-side G20 minimum-SOC setting currently under field validation.</span>
      <button type="button" class="ep-v019-soc-copy">Copy SOC constraints</button>
    </div>`;
  grid.appendChild(group);

  const copy = group.querySelector(".ep-v019-soc-copy");
  copy?.addEventListener("click", async () => {
    const text = socConstraintSnapshot(constraintContext(panel));
    try {
      await navigator.clipboard.writeText(text);
      const previous = copy.textContent;
      copy.textContent = "Copied";
      setTimeout(() => { copy.textContent = previous; }, 1200);
    } catch (_err) {
      window.prompt("Copy EnergyPilot SOC constraints", text);
    }
  });
}

function clarifyFinalSocSetting(root) {
  const input = root.querySelector('[data-setting-key="emhass_soc_final_pct"]');
  const field = input?.closest(".ep-v016-field");
  if (!field) return;

  const label = field.querySelector(".ep-v016-field-label span:first-child");
  if (label) label.textContent = "Runtime final SOC target";

  const description = field.querySelector(".ep-v016-field-description");
  if (description) {
    description.textContent = "Sent to EMHASS as runtime soc_final for every EnergyPilot optimization. This runtime value overrides the EMHASS config target for that run and does not rewrite battery_target_state_of_charge in config.json.";
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
