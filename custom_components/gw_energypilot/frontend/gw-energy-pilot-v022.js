import "./gw-energy-pilot-v021.js?v=1.1.0-stable1";

const VERSION = "0.22";
const PANEL_NAME = "gw-energypilot-panel";

function ensureV022Styles(root) {
  if (root.querySelector("#ep-v022-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v022-style";
  style.textContent = `
    /* v0.22 makes particle direction explicit at the active frontend layer.
       Older layers use inbound/outbound names with geometry-specific reversals;
       these semantic to-hub/from-hub classes are authoritative. */
    .ep-link-pv.ep-v022-to-hub .ep-v011-particles span { animation-direction: normal !important; }
    .ep-link-pv.ep-v022-from-hub .ep-v011-particles span { animation-direction: reverse !important; }
    .ep-link-grid.ep-v022-to-hub .ep-v011-particles span { animation-direction: reverse !important; }
    .ep-link-grid.ep-v022-from-hub .ep-v011-particles span { animation-direction: normal !important; }
    .ep-link-house.ep-v022-to-hub .ep-v011-particles span { animation-direction: normal !important; }
    .ep-link-house.ep-v022-from-hub .ep-v011-particles span { animation-direction: reverse !important; }
    .ep-link-battery.ep-v022-to-hub .ep-v011-particles span { animation-direction: reverse !important; }
    .ep-link-battery.ep-v022-from-hub .ep-v011-particles span { animation-direction: normal !important; }

    .ep-v022-smart-meter-status {
      margin-top: 7px;
      font-size: 8px;
      line-height: 1.45;
      color: #6f91a7;
    }
    .ep-v022-smart-meter-status.ok { color: #63d9ad; }
    .ep-v022-smart-meter-status.warning { color: #e8b36f; }
    .ep-v022-smart-meter-field.busy { opacity: .65; }
    .ep-v022-strategy-note {
      margin-top: 10px;
      padding: 8px 10px;
      border: 1px solid rgba(65,191,221,.12);
      border-radius: 10px;
      color: #7799ae;
      background: rgba(7,35,57,.28);
      font-size: 8px;
      line-height: 1.45;
    }
    .ep-v022-strategy-note strong { color: #bfe9f3; }
  `;
  root.appendChild(style);
}

function finiteNumber(value, fallback = null) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function setSemanticFlow(link, direction) {
  if (!link) return;
  link.classList.remove("ep-v022-to-hub", "ep-v022-from-hub");
  if (!direction || link.classList.contains("idle")) return;
  link.classList.add(direction === "to" ? "ep-v022-to-hub" : "ep-v022-from-hub");
}

function enforceFlowDirections(panel, root) {
  const pv = finiteNumber(panel._stateByKey?.("pv_total_power")?.state);
  const grid = finiteNumber(panel._stateByKey?.("meter_total_power_fast")?.state);
  const battery = finiteNumber(panel._stateByKey?.("battery_power")?.state);

  const pvLink = root.querySelector(".ep-link-pv");
  const gridLink = root.querySelector(".ep-link-grid");
  const houseLink = root.querySelector(".ep-link-house");
  const batteryLink = root.querySelector(".ep-link-battery");

  // PV generation always flows from the PV node toward the EnergyPilot hub.
  setSemanticFlow(pvLink, Number.isFinite(pv) && pv > 50 ? "to" : null);

  // GoodWe meter convention: positive = export, negative = import.
  setSemanticFlow(
    gridLink,
    !Number.isFinite(grid) || Math.abs(grid) < 50
      ? null
      : grid > 0
        ? "from"
        : "to"
  );

  // Normal positive house load flows from the hub toward the house.
  setSemanticFlow(houseLink, houseLink?.classList.contains("idle") ? null : "from");

  // GoodWe battery convention: positive = discharge, negative = charge.
  setSemanticFlow(
    batteryLink,
    !Number.isFinite(battery) || Math.abs(battery) < 50
      ? null
      : battery > 0
        ? "to"
        : "from"
  );
}

function smartMeterCache(panel) {
  panel.__epV022SmartMeter = panel.__epV022SmartMeter || {};
  return panel.__epV022SmartMeter;
}

async function loadSmartMeterSetting(panel, entryId) {
  if (!panel._hass?.callWS || !entryId) return;
  const cache = smartMeterCache(panel);
  if (cache.loadingEntry === entryId) return;
  cache.loadingEntry = entryId;
  try {
    const result = await panel._hass.callWS({
      type: "gw_energypilot/smart_meter/get",
      entry_id: entryId,
    });
    cache.entryId = entryId;
    cache.data = result;
    cache.error = null;
  } catch (err) {
    console.error("GW EnergyPilot smart-meter setting load failed", err);
    cache.error = err?.message || String(err);
  } finally {
    cache.loadingEntry = null;
    panel._queueRender();
  }
}

async function saveSmartMeterSetting(panel, entryId, enabled, input) {
  const cache = smartMeterCache(panel);
  const automaticOn = panel._stateByKey?.("automatic_control")?.state === "on";
  const strategy = enabled
    ? "P_grid will control GoodWe modes 9/10, with mode 1 around zero grid flow."
    : "P_batt will control direct battery modes 11/12, with mode 8 around zero battery power.";

  if (
    automaticOn &&
    !window.confirm(
      `Automatic Control is ON.\n\n${strategy}\n\nChanging this setting will immediately reevaluate the active EMHASS plan. Continue?`
    )
  ) {
    input.checked = !enabled;
    return;
  }

  cache.saving = true;
  cache.message = "Saving control strategy…";
  panel._queueRender();
  try {
    const result = await panel._hass.callWS({
      type: "gw_energypilot/smart_meter/set",
      entry_id: entryId,
      enabled,
    });
    cache.entryId = entryId;
    cache.data = result;
    cache.error = null;
    cache.message = enabled
      ? "Saved · Automatic Control uses P_grid → modes 9/10."
      : "Saved · Automatic Control uses P_batt → modes 11/12.";
  } catch (err) {
    console.error("GW EnergyPilot smart-meter setting update failed", err);
    cache.error = err?.message || String(err);
    cache.message = null;
    input.checked = !enabled;
  } finally {
    cache.saving = false;
    panel._queueRender();
  }
}

function installSmartMeterSetting(panel, root) {
  if (!panel.__epV016SettingsOpen || panel.__epV016SettingsTab !== "goodwe") return;
  const form = root.querySelector('.ep-v016-form[data-section="goodwe"]');
  const fields = form?.querySelector(".ep-v016-fields");
  if (!form || !fields || fields.querySelector(".ep-v022-smart-meter-field")) return;

  const entryId = panel.__epV016SettingsData?.entry_id;
  if (!entryId) return;

  const cache = smartMeterCache(panel);
  if (cache.entryId !== entryId && cache.loadingEntry !== entryId) {
    loadSmartMeterSetting(panel, entryId);
  }

  const data = cache.entryId === entryId ? cache.data : null;
  const enabled = data?.enabled !== false;
  const meterAvailable = Boolean(data?.meter_available);
  const meterPower = finiteNumber(data?.meter_power);
  const busy = Boolean(cache.saving || cache.loadingEntry === entryId);

  const field = document.createElement("div");
  field.className = `ep-v016-field boolean ep-v022-smart-meter-field${busy ? " busy" : ""}`;
  const liveText = !data
    ? "Reading current setting…"
    : meterAvailable
      ? `Live GoodWe meter available${meterPower === null ? "" : ` · ${Math.round(meterPower)} W signed grid power`}.`
      : "GoodWe meter telemetry is not currently available. Do not enable PCC control until the meter is working.";
  field.innerHTML = `
    <div>
      <div class="ep-v016-field-label"><span>GoodWe smart meter active</span><span>PCC control</span></div>
      <div class="ep-v016-field-description">
        ON: Automatic Control uses EMHASS P_grid with GoodWe mode 9 for import and mode 10 for export; around 0 W it uses mode 1 Auto/self-use. OFF: Automatic Control falls back to direct P_batt modes 11/12 and mode 8 Hold.
      </div>
      <div class="ep-v022-smart-meter-status ${data ? (meterAvailable ? "ok" : "warning") : ""}">${panel._escape(cache.error || cache.message || liveText)}</div>
    </div>
    <input class="ep-v016-switch" type="checkbox" ${enabled ? "checked" : ""} ${busy || !data ? "disabled" : ""} aria-label="Use GoodWe smart meter for automatic PCC control">
  `;
  fields.appendChild(field);

  const input = field.querySelector("input");
  input?.addEventListener("change", () => {
    saveSmartMeterSetting(panel, entryId, Boolean(input.checked), input);
  });
}

function updateSettingField(root, labelText, nextLabel, description) {
  for (const field of root.querySelectorAll(".ep-v016-field")) {
    const label = field.querySelector(".ep-v016-field-label span:first-child");
    if (label?.textContent?.trim() !== labelText) continue;
    if (nextLabel) label.textContent = nextLabel;
    const descriptionNode = field.querySelector(".ep-v016-field-description");
    if (descriptionNode) descriptionNode.textContent = description;
    return;
  }
}

function relabelSettingsFields(panel, root) {
  if (!panel.__epV016SettingsOpen) return;
  if (panel.__epV016SettingsTab === "energypilot") {
    updateSettingField(
      root,
      "Maximum control power",
      "Maximum control power",
      "Caps the GoodWe mode-specific setpoint: PCC import/export target with Smart Meter control ON, or direct battery target with it OFF."
    );
    updateSettingField(
      root,
      "Battery deadband",
      "Control deadband",
      "Tolerance around 0 W. Applied to EMHASS P_grid when Smart Meter control is ON and to P_batt when it is OFF."
    );
    updateSettingField(
      root,
      "EV coordination",
      "EV anti-discharge protection",
      "Prevents the home battery from discharging while EV charging is active. Explicit EMHASS battery-charge plans remain allowed, so independent EV charging such as supplier or grid-reward sessions does not unnecessarily block battery charging."
    );
  }
  if (panel.__epV016SettingsTab === "emhass") {
    updateSettingField(
      root,
      "P_batt output entity",
      "P_batt output entity",
      "Published battery plan. Used as the direct actuator target when GoodWe Smart Meter control is OFF; retained as a required plan/diagnostic output when it is ON."
    );
    updateSettingField(
      root,
      "P_grid output entity",
      "P_grid output entity",
      "Published site-grid target. With GoodWe Smart Meter control ON: positive import drives mode 9, negative export drives mode 10, and a target near zero uses mode 1 Auto/self-use."
    );
  }
}

function relabelControllerTarget(panel, root) {
  const command = String(panel._stateByKey?.("control_command")?.state || "");
  const card = root.querySelector(".panel-card.controller");
  if (!card) return;

  for (const label of card.querySelectorAll(".metric-label")) {
    if (label.textContent?.trim() !== "EnergyPilot target") continue;
    if (command.startsWith("grid_") || command === "goodwe_auto") {
      label.textContent = "PCC target";
    } else if (command.startsWith("battery_") || command.startsWith("ev_")) {
      label.textContent = "Battery target";
    } else {
      label.textContent = "Control target";
    }
  }

  const manualPad = card.querySelector(".ep-v021-manual-pad");
  if (manualPad && !card.querySelector(".ep-v022-strategy-note")) {
    const note = document.createElement("div");
    note.className = "ep-v022-strategy-note";
    note.innerHTML = `<strong>Automatic strategy:</strong> GoodWe smart meter ON uses P_grid → 9/10 (mode 1 around zero). Smart meter OFF uses P_batt → 11/12 (mode 8 around zero). EV anti-discharge protection overrides both strategies while the EV is actively charging: discharge is held, explicit battery charging remains allowed. Manual buttons always remain direct operator commands.`;
    manualPad.insertAdjacentElement("afterend", note);
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV022Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  ensureV022Styles(root);
  enforceFlowDirections(this, root);
  installSmartMeterSetting(this, root);
  relabelSettingsFields(this, root);
  relabelControllerTarget(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
};
