import "./gw-energy-pilot-v026-battery-price.js?v=0.26-battery-price1";

const VERSION = "0.26";
const PANEL_NAME = "gw-energypilot-panel";

const SOC_TEXT = {
  en: {
    note: "Minimum SOC synchronizes EMHASS battery_minimum_state_of_charge with the GoodWe on-grid minimum SOC floor (register 45356). The inverter write is verified before EMHASS is updated. Maximum SOC remains EMHASS-only.",
    heading: "Off-grid minimum SOC field test",
    copy: "On-grid minimum SOC (45356) is managed by the EMHASS minimum-SOC slider so the optimizer and inverter floor stay synchronized. The remaining control below is the independent off-grid register 45358 field test.",
    beta: "BETA: on-grid minimum SOC 45356 is synchronized from the EMHASS minimum-SOC slider with verified read-back. 45358 remains a manual off-grid field-test setting. 47500, 36104 and 36120 remain read-only diagnostics.",
    diagnostic: "On-grid minimum SOC 45356 · synced",
    fieldTest: " <strong>G20 field test:</strong> off-grid minimum SOC 45358 remains available below; on-grid 45356 is synchronized from the EMHASS minimum-SOC slider.",
  },
  nl: {
    note: "Minimum-SOC synchroniseert EMHASS battery_minimum_state_of_charge met de GoodWe on-grid minimum-SOC grens (register 45356). De inverter-write wordt eerst teruggelezen en geverifieerd. Maximum-SOC blijft alleen een EMHASS-limiet.",
    heading: "Off-grid minimum-SOC veldtest",
    copy: "On-grid minimum-SOC (45356) wordt beheerd met de EMHASS minimum-SOC slider zodat optimizer en invertergrens gelijk blijven. Hieronder blijft alleen de onafhankelijke off-grid veldtest voor register 45358 over.",
    beta: "BETA: on-grid minimum-SOC 45356 wordt vanuit de EMHASS minimum-SOC slider gesynchroniseerd met geverifieerde read-back. 45358 blijft een handmatige off-grid veldtest. 47500, 36104 en 36120 blijven read-only diagnostiek.",
    diagnostic: "On-grid minimum-SOC 45356 · gesynchroniseerd",
    fieldTest: " <strong>G20 veldtest:</strong> off-grid minimum-SOC 45358 blijft hieronder beschikbaar; on-grid 45356 wordt gesynchroniseerd vanuit de EMHASS minimum-SOC slider.",
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

  const onGridInput = root.querySelector(
    '[data-beta-soc-input="battery_discharge_depth_on_grid"]'
  );
  onGridInput?.closest(".ep-v018-beta-card")?.remove();

  const betaSection = root.querySelector(".ep-v018-beta-soc");
  if (betaSection) {
    const heading = betaSection.querySelector("h4");
    if (heading) heading.textContent = text.heading;
    const copy = betaSection.querySelector(".ep-v018-beta-soc-copy");
    if (copy) copy.textContent = text.copy;
  }

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
