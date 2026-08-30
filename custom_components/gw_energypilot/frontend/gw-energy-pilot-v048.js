import "./gw-energy-pilot-v047.js?v=0.48-hybrid-control1";

const VERSION = "0.48";
const PANEL_NAME = "gw-energypilot-panel";

const TEXT = Object.freeze({
  en: Object.freeze({
    hybridDescription: "Holds a neutral P_batt plan in mode 8. Otherwise P_grid uses mode 1 inside the configured deadband and modes 9/10 outside it, with the full grid target as setpoint.",
    strategyNote: "Automatic control strategy:",
    hybridLabel: "Hybrid control",
    evOverride: "EV anti-discharge protection remains active as a safety override.",
  }),
  nl: Object.freeze({
    hybridDescription: "Houdt een neutraal P_batt-plan vast in modus 8. Anders gebruikt P_grid modus 1 binnen de ingestelde deadband en modi 9/10 erbuiten, met het volledige netdoel als setpoint.",
    strategyNote: "Automatische regelstrategie:",
    hybridLabel: "Hybride regeling",
    evOverride: "EV-ontlaadbeveiliging blijft actief als veiligheidsoverride.",
  }),
});

function language(panel) {
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function patchReleasePresentation(panel) {
  const root = panel?.shadowRoot;
  if (!root) return;

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }

  const cache = panel.__epV022SmartMeter || {};
  const strategy = cache.data?.strategy || panel._stateByKey?.("control_strategy")?.state;
  if (strategy !== "hybrid") return;

  const copy = TEXT[language(panel)] || TEXT.en;
  const status = root.querySelector(
    ".ep-v024-control-strategy-field .ep-v022-smart-meter-status"
  );
  if (status && !cache.error && !cache.message) {
    status.textContent = copy.hybridDescription;
  }

  const note = root.querySelector(".ep-v022-strategy-note");
  if (note) {
    note.innerHTML = `<strong>${copy.strategyNote}</strong> ${copy.hybridLabel} · ${copy.hybridDescription} ${copy.evOverride}`;
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (PanelClass && !PanelClass.prototype.__epV048Installed) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV048ReleaseRender(...args) {
    const result = previousRender.apply(this, args);
    patchReleasePresentation(this);
    return result;
  };

  const descriptor = Object.getOwnPropertyDescriptor(PanelClass.prototype, "hass");
  if (descriptor?.set) {
    Object.defineProperty(PanelClass.prototype, "hass", {
      configurable: descriptor.configurable,
      enumerable: descriptor.enumerable,
      get() {
        return descriptor.get ? descriptor.get.call(this) : this._hass;
      },
      set(value) {
        descriptor.set.call(this, value);
        patchReleasePresentation(this);
      },
    });
  }

  PanelClass.prototype.__epV048Installed = true;
}
