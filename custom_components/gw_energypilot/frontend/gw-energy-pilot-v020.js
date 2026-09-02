import "./gw-energy-pilot-v019-merged.js?v=1.2.0-beta.5-touch-fallback1";

const VERSION = "0.20";
const PANEL_NAME = "gw-energypilot-panel";

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

function numericState(panel, key) {
  const state = panel._stateByKey?.(key);
  if (!state || ["unknown", "unavailable"].includes(state.state)) return null;
  return finiteNumber(state.state);
}

function constraintContext(panel) {
  const optimizeId = panel._entityId?.("optimize_now");
  const attrs = (optimizeId ? panel._state?.(optimizeId)?.attributes : null) || {};
  const strategyState = panel._stateByKey?.("emhass_cost_function");
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

function setRow(panel, row, label, value) {
  if (!row) return;
  const labelNode = row.querySelector("span");
  const valueNode = row.querySelector("strong");
  if (labelNode) labelNode.textContent = label;
  if (valueNode) valueNode.textContent = value;
}

function makeRow(panel, marker, label, value) {
  const row = document.createElement("div");
  row.className = "ep-v011-diag-row";
  row.dataset.v020Soc = marker;
  row.innerHTML = `<span>${panel._escape(label)}</span><strong>${panel._escape(value)}</strong>`;
  return row;
}

function socConstraintSnapshot(values) {
  return [
    "GW EnergyPilot SOC constraint diagnostics",
    `Current battery SOC: ${pct(values.currentSoc)}`,
    `Last EnergyPilot optimization SOC init: ${pct(values.socInit)}`,
    `Configured EnergyPilot final SOC target: ${pct(values.configuredRuntimeFinal)}`,
    `Last successful EnergyPilot runtime final SOC (soc_final): ${pct(values.runtimeFinal)}`,
    `EMHASS minimum SOC: ${pct(values.emhassMinimum)}`,
    `EMHASS config target SOC (fallback): ${validatedSocDisplay(values.emhassConfigTarget, values.emhassConfigTargetRaw)}`,
    `EMHASS deficit threshold: ${validatedSocDisplay(values.emhassDeficitThreshold, values.emhassDeficitThresholdRaw)}`,
    `EMHASS deficit cost: ${decimal(values.emhassDeficitCost)} currency/kWh/h`,
    `GoodWe on-grid minimum SOC 45356: ${pct(values.goodweOnGridMinimum)}`,
  ].join("\n");
}

function updateSocConstraintDiagnostics(panel, root) {
  const group = root.querySelector('[data-v019-soc-group="1"]');
  if (!group) return;

  const values = constraintContext(panel);
  const currentRow = group.querySelector('[data-v019-soc="current"]');
  const initRow = group.querySelector('[data-v019-soc="init"]');
  const runtimeRow = group.querySelector('[data-v019-soc="runtime-final"]');
  const minimumRow = group.querySelector('[data-v019-soc="minimum"]');
  const configTargetRow = group.querySelector('[data-v019-soc="config-target"]');
  const deficitRow = group.querySelector('[data-v019-soc="deficit"]');
  const deficitCostRow = group.querySelector('[data-v019-soc="deficit-cost"]');
  const goodweRow = group.querySelector('[data-v019-soc="goodwe"]');

  setRow(panel, currentRow, "Current battery SOC", pct(values.currentSoc));
  setRow(panel, initRow, "Last EnergyPilot optimization SOC init", pct(values.socInit));

  let configuredRow = group.querySelector('[data-v020-soc="configured-runtime-final"]');
  if (!configuredRow && runtimeRow) {
    configuredRow = makeRow(
      panel,
      "configured-runtime-final",
      "Configured EnergyPilot final SOC target",
      pct(values.configuredRuntimeFinal),
    );
    runtimeRow.before(configuredRow);
  }
  setRow(
    panel,
    configuredRow,
    "Configured EnergyPilot final SOC target",
    pct(values.configuredRuntimeFinal),
  );
  setRow(
    panel,
    runtimeRow,
    "Last successful EnergyPilot runtime final SOC (soc_final)",
    pct(values.runtimeFinal),
  );
  setRow(panel, minimumRow, "EMHASS minimum SOC", pct(values.emhassMinimum));
  setRow(
    panel,
    configTargetRow,
    "EMHASS config target SOC (fallback)",
    validatedSocDisplay(values.emhassConfigTarget, values.emhassConfigTargetRaw),
  );
  setRow(
    panel,
    deficitRow,
    "EMHASS deficit threshold",
    validatedSocDisplay(values.emhassDeficitThreshold, values.emhassDeficitThresholdRaw),
  );
  setRow(
    panel,
    deficitCostRow,
    "EMHASS deficit cost",
    `${decimal(values.emhassDeficitCost)} currency/kWh/h`,
  );
  setRow(
    panel,
    goodweRow,
    "GoodWe on-grid minimum SOC 45356",
    pct(values.goodweOnGridMinimum),
  );

  const note = group.querySelector(".ep-v019-soc-note span");
  if (note) {
    note.innerHTML = "<strong>Last successful EnergyPilot runtime final SOC</strong> is populated only after an EnergyPilot-owned optimization and publish cycle succeeds. In manual-only or externally orchestrated installations the configured EnergyPilot target can therefore differ from the actual EMHASS runtime target. Invalid EMHASS SOC config values are kept as raw diagnostics instead of being presented as valid percentages. GoodWe 45356 remains the inverter-side G20 minimum-SOC setting under field validation.";
  }

  const oldCopy = group.querySelector(".ep-v019-soc-copy");
  if (oldCopy && !oldCopy.dataset.v020Bound) {
    const copy = oldCopy.cloneNode(true);
    copy.dataset.v020Bound = "1";
    copy.textContent = "Copy SOC constraints";
    oldCopy.replaceWith(copy);
    copy.addEventListener("click", async () => {
      const text = socConstraintSnapshot(constraintContext(panel));
      try {
        await navigator.clipboard.writeText(text);
        copy.textContent = "Copied";
        setTimeout(() => { copy.textContent = "Copy SOC constraints"; }, 1200);
      } catch (_err) {
        window.prompt("Copy EnergyPilot SOC constraints", text);
      }
    });
  }
}

function clarifyFinalSocSetting(root) {
  const input = root.querySelector('[data-setting-key="emhass_soc_final_pct"]');
  const field = input?.closest(".ep-v016-field");
  if (!field) return;

  const label = field.querySelector(".ep-v016-field-label span:first-child");
  if (label) label.textContent = "EnergyPilot runtime final SOC target";

  const description = field.querySelector(".ep-v016-field-description");
  if (description) {
    description.textContent = "Used as runtime soc_final when EnergyPilot itself runs an optimization. A manual-only or externally orchestrated EMHASS installation can use a different runtime target. This setting does not rewrite battery_target_state_of_charge in EMHASS config.json.";
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV020Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  updateSocConstraintDiagnostics(this, root);
  clarifyFinalSocSetting(root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
};
