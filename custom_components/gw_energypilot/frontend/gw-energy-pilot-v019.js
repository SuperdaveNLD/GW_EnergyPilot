import "./gw-energy-pilot-v018.js?v=0.18-beta-soc-floor1";

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

function validatedSocDisplay(percentValue, rawValue) {
  const percent = finiteNumber(percentValue);
  if (percent !== null) return pct(percent);
  const raw = finiteNumber(rawValue);
  return raw === null ? "—" : `invalid raw ${raw}`;
}

function constraintContext(panel) {
  const optimizeId = panel._entityId("optimize_now");
  const attrs = (optimizeId ? panel._state(optimizeId)?.attributes : null) || {};
  const strategyState = panel._stateByKey("emhass_cost_function");
  const configAttrs = strategyState?.attributes || {};
  const minimumEntityValue = numericState(panel, "emhass_minimum_soc");
  const rawSocInit = finiteNumber(attrs.soc_init);
  const rawRuntimeFinal = finiteNumber(attrs.runtime_soc_final);
  const rawConfiguredRuntimeFinal = finiteNumber(attrs.configured_runtime_soc_final);

  return {
    currentSoc: attrs.battery_soc,
    socInit: rawSocInit === null ? null : rawSocInit * 100,
    runtimeFinal: rawRuntimeFinal === null ? null : rawRuntimeFinal * 100,
    configuredRuntimeFinal: rawConfiguredRuntimeFinal === null
      ? null
      : rawConfiguredRuntimeFinal * 100,
    emhassMinimum: minimumEntityValue ?? configAttrs.emhass_minimum_soc_pct,
    emhassConfigTarget: configAttrs.emhass_config_target_soc_pct,
    emhassConfigTargetRaw: configAttrs.emhass_config_target_soc_raw,
    emhassDeficitThreshold: configAttrs.emhass_soc_deficit_threshold_pct,
    emhassDeficitThresholdRaw: configAttrs.emhass_soc_deficit_threshold_raw,
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
    `Last EnergyPilot optimization SOC init: ${pct(values.socInit)}`,
    `Configured EnergyPilot final SOC target: ${pct(values.configuredRuntimeFinal)}`,
    `Last sent runtime final SOC (soc_final): ${pct(values.runtimeFinal)}`,
    `EMHASS minimum SOC: ${pct(values.emhassMinimum)}`,
    `EMHASS config target SOC (fallback): ${validatedSocDisplay(values.emhassConfigTarget, values.emhassConfigTargetRaw)}`,
    `EMHASS deficit threshold: ${validatedSocDisplay(values.emhassDeficitThreshold, values.emhassDeficitThresholdRaw)}`,
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
    ${diagRow(panel, "Last EnergyPilot optimization SOC init", pct(values.socInit), "init")}
    ${diagRow(panel, "Configured EnergyPilot final SOC target", pct(values.configuredRuntimeFinal), "configured-runtime-final")}
    ${diagRow(panel, "Last sent runtime final SOC (soc_final)", pct(values.runtimeFinal), "runtime-final")}
    ${diagRow(panel, "EMHASS minimum SOC", pct(values.emhassMinimum), "minimum")}
    ${diagRow(panel, "EMHASS config target SOC (fallback)", validatedSocDisplay(values.emhassConfigTarget, values.emhassConfigTargetRaw), "config-target")}
    ${diagRow(panel, "EMHASS deficit threshold", validatedSocDisplay(values.emhassDeficitThreshold, values.emhassDeficitThresholdRaw), "deficit")}
    ${diagRow(panel, "EMHASS deficit cost", `${decimal(values.emhassDeficitCost)} currency/kWh/h`, "deficit-cost")}
    ${diagRow(panel, "GoodWe on-grid minimum SOC 45356", pct(values.goodweOnGridMinimum), "goodwe")}
    <div class="ep-v019-soc-note">
      <span><strong>Last sent runtime final SOC</strong> is populated only after an EnergyPilot-owned optimization succeeds. A manual-only installation may therefore show a configured EnergyPilot target while last sent remains blank. Invalid EMHASS SOC config values are shown as raw diagnostics instead of being presented as valid percentages. GoodWe 45356 remains the inverter-side G20 minimum-SOC setting under field validation.</span>
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
  if (label) label.textContent = "EnergyPilot runtime final SOC target";

  const description = field.querySelector(".ep-v016-field-description");
  if (description) {
    description.textContent = "Used as runtime soc_final when EnergyPilot runs an optimization. This value does not prove it was sent: manual-only or externally orchestrated EMHASS can use a different runtime target. It does not rewrite battery_target_state_of_charge in config.json.";
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
