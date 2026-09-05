import "./gw-energy-pilot-v026-battery-price.js?v=1.3.0-beta.4";

const VERSION = "0.26";
const PANEL_NAME = "gw-energypilot-panel";

const SOC_TEXT = {
  en: {
    note: "Minimum SOC synchronizes EMHASS battery_minimum_state_of_charge with the GoodWe on-grid minimum SOC floor (register 45356). The inverter write is verified before EMHASS is updated. Maximum SOC remains EMHASS-only.",
    beta: "BETA: on-grid minimum SOC 45356 is synchronized from the EMHASS minimum-SOC slider with verified read-back. 45358 remains available only through the low-level Beta API for diagnostics/backwards-compatible tooling. 47500, 36104 and 36120 remain read-only diagnostics.",
    diagnostic: "On-grid minimum SOC 45356 · synced",
    fieldTest: " <strong>Minimum SOC:</strong> on-grid 45356 is synchronized from the EMHASS minimum-SOC slider. The legacy direct minimum-SOC write panel is no longer shown.",
  },
  nl: {
    note: "Minimum-SOC synchroniseert EMHASS battery_minimum_state_of_charge met de GoodWe on-grid minimum-SOC grens (register 45356). De inverter-write wordt eerst teruggelezen en geverifieerd. Maximum-SOC blijft alleen een EMHASS-limiet.",
    beta: "BETA: on-grid minimum-SOC 45356 wordt vanuit de EMHASS minimum-SOC slider gesynchroniseerd met geverifieerde read-back. 45358 blijft alleen via de low-level Beta-API beschikbaar voor diagnostiek/backwards-compatible tooling. 47500, 36104 en 36120 blijven read-only diagnostiek.",
    diagnostic: "On-grid minimum-SOC 45356 · gesynchroniseerd",
    fieldTest: " <strong>Minimum-SOC:</strong> on-grid 45356 wordt gesynchroniseerd vanuit de EMHASS minimum-SOC slider. Het oude directe minimum-SOC schrijfpaneel wordt niet meer getoond.",
  },
};

function language(panel) {
  if (typeof panel._epLanguage === "function") return panel._epLanguage();
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function alignMinimumSocUi(panel, root) {
  const text = SOC_TEXT[language(panel)] || SOC_TEXT.en;

  const socNote = root.querySelector(".ep-v011-soc-note");
  if (socNote) socNote.textContent = text.note;

  root.querySelector(".ep-v018-beta-soc")?.remove();

  const betaNote = root.querySelector(".ep-v016-beta-note");
  if (betaNote) betaNote.textContent = text.beta;

  const onGridDiagnostic = root.querySelector('[data-v016-beta="soc-on-grid"] span');
  if (onGridDiagnostic) onGridDiagnostic.textContent = text.diagnostic;

  const connectionNote = root.querySelector(".ep-v016-goodwe-note");
  if (connectionNote?.innerHTML) {
    connectionNote.innerHTML = connectionNote.innerHTML.replace(
      / <strong>(?:G20 field test:|G20 veldtest:)<\/strong>[^<]*(?:\.|$)/,
      text.fieldTest
    );
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV026CompleteRender() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  alignMinimumSocUi(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
};
