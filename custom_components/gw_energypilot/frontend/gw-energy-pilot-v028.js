import "./gw-energy-pilot-v027-battery-plan.js?v=1.2.0-beta.6-chart-touch1";

const VERSION = "0.28";
const PANEL_NAME = "gw-energypilot-panel";

const TEXT = {
  en: {
    hybridDescription: "Buys/imports through GoodWe mode 9 using P_grid and sells/discharges through mode 12 using P_batt. A neutral battery plan uses mode 8; PV-only charging falls back to GoodWe self-use.",
    strategyNote: "Automatic control strategy:",
    hybridLabel: "Hybrid control",
    evOverride: "EV anti-discharge protection remains active as a safety override.",
  },
  nl: {
    hybridDescription: "Koopt/importeert via GoodWe mode 9 op P_grid en verkoopt/ontlaadt via mode 12 op P_batt. Een neutraal accuplan gebruikt mode 8; PV-only laden valt terug op GoodWe self-use.",
    strategyNote: "Automatische regelstrategie:",
    hybridLabel: "Hybride regeling",
    evOverride: "EV-ontlaadbeveiliging blijft actief als veiligheidsoverride.",
  },
};

function language(panel) {
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function text(panel) {
  return TEXT[language(panel)] || TEXT.en;
}

function clarifyHybridStrategy(panel, root) {
  const cache = panel.__epV022SmartMeter || {};
  if (cache.data?.strategy !== "hybrid") return;

  const copy = text(panel);
  const status = root.querySelector(
    ".ep-v024-control-strategy-field .ep-v022-smart-meter-status"
  );
  if (status && !cache.error && !cache.message) {
    status.textContent = copy.hybridDescription;
  }

  const note = root.querySelector(".ep-v022-strategy-note");
  if (
    note &&
    !note.closest("ep-control-surface") &&
    note.dataset.epReleasePresentationOwner !== "v048-hybrid"
  ) {
    note.innerHTML = `<strong>${copy.strategyNote}</strong> ${copy.hybridLabel} · ${copy.hybridDescription} ${copy.evOverride}`;
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV028Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  clarifyHybridStrategy(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
};
