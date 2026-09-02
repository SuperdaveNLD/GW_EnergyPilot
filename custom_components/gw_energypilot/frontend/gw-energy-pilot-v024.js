import "./gw-energy-pilot-v023.js?v=1.2.0-beta.3-load-forecast1";

const VERSION = "0.24";
const PANEL_NAME = "gw-energypilot-panel";

const STRATEGY_LABELS = {
  battery: "Accuregeling",
  grid: "Netregeling",
  hybrid: "Hybride regeling",
};

const STRATEGY_DESCRIPTIONS = {
  battery: "Regelt laden en ontladen op het gewenste accuvermogen (GoodWe 11/12).",
  grid: "Regelt import en export op het gewenste netvermogen (GoodWe 9/10).",
  hybrid: "Regelt inkoop/laden op accuvermogen (11) en verkoop/export op netvermogen (10).",
};

async function saveControlStrategy(panel, entryId, strategy, select) {
  const cache = panel.__epV022SmartMeter || (panel.__epV022SmartMeter = {});
  const automaticOn = panel._stateByKey?.("automatic_control")?.state === "on";
  if (
    automaticOn &&
    !window.confirm(
      `Automatic Control is ON.\n\nSwitch to ${STRATEGY_LABELS[strategy]}?\n\nThe active EMHASS plan will be reevaluated immediately.`
    )
  ) {
    select.value = cache.data?.strategy || "battery";
    return;
  }

  cache.saving = true;
  cache.message = "Regelstrategie opslaan…";
  panel._queueRender();
  try {
    const result = await panel._hass.callWS({
      type: "gw_energypilot/smart_meter/set",
      entry_id: entryId,
      strategy,
    });
    cache.entryId = entryId;
    cache.data = result;
    cache.error = null;
    cache.message = `Opgeslagen · ${STRATEGY_LABELS[strategy]}.`;
  } catch (err) {
    console.error("GW EnergyPilot control strategy update failed", err);
    cache.error = err?.message || String(err);
    cache.message = null;
  } finally {
    cache.saving = false;
    panel._queueRender();
  }
}

function installControlStrategy(panel, root) {
  if (!panel.__epV016SettingsOpen || panel.__epV016SettingsTab !== "goodwe") return;
  const form = root.querySelector('.ep-v016-form[data-section="goodwe"]');
  const fields = form?.querySelector(".ep-v016-fields");
  if (!form || !fields) return;

  // v0.22 exposed the old two-state Smart Meter checkbox. Replace it at the
  // active frontend layer while keeping its cache/load mechanism intact.
  fields.querySelector(".ep-v022-smart-meter-field")?.remove();
  if (fields.querySelector(".ep-v024-control-strategy-field")) return;

  const entryId = panel.__epV016SettingsData?.entry_id;
  if (!entryId) return;
  const cache = panel.__epV022SmartMeter || (panel.__epV022SmartMeter = {});
  const data = cache.entryId === entryId ? cache.data : null;
  const strategy = data?.strategy || (data?.enabled ? "grid" : "battery");
  const busy = Boolean(cache.saving || cache.loadingEntry === entryId || !data);
  const meterAvailable = Boolean(data?.meter_available);

  const field = document.createElement("div");
  field.className = `ep-v016-field ep-v024-control-strategy-field${busy ? " busy" : ""}`;
  field.innerHTML = `
    <div>
      <div class="ep-v016-field-label"><span>Automatische regelstrategie</span><span>GoodWe EMS</span></div>
      <div class="ep-v016-field-description">Kies waarop EnergyPilot het invertervermogen regelt.</div>
      <div class="ep-v022-smart-meter-status ${meterAvailable ? "ok" : strategy === "battery" ? "" : "warning"}">
        ${panel._escape(cache.error || cache.message || STRATEGY_DESCRIPTIONS[strategy])}
      </div>
    </div>
    <select class="ep-v016-input" ${busy ? "disabled" : ""} aria-label="Automatische regelstrategie">
      <option value="battery" ${strategy === "battery" ? "selected" : ""}>Accuregeling</option>
      <option value="grid" ${strategy === "grid" ? "selected" : ""}>Netregeling</option>
      <option value="hybrid" ${strategy === "hybrid" ? "selected" : ""}>Hybride regeling</option>
    </select>
  `;
  fields.appendChild(field);

  const select = field.querySelector("select");
  select?.addEventListener("change", () => saveControlStrategy(panel, entryId, select.value, select));
}

function updateStrategyNote(panel, root) {
  const note = root.querySelector(".ep-v022-strategy-note");
  const strategy = panel.__epV022SmartMeter?.data?.strategy;
  if (!note || !strategy) return;
  if (note.closest("ep-control-surface")) return;
  if (note.dataset.epReleasePresentationOwner === "v048-hybrid" && strategy === "hybrid") return;
  note.innerHTML = `<strong>Automatische regelstrategie:</strong> ${STRATEGY_LABELS[strategy]} · ${STRATEGY_DESCRIPTIONS[strategy]} EV anti-discharge protection blijft als veiligheidsoverride actief.`;
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV024Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  installControlStrategy(this, root);
  updateStrategyNote(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
};
