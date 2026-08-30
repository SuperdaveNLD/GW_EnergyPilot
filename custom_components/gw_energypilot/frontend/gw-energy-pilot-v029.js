import "./gw-energy-pilot-v028-consolidated.js?v=0.50-ev1";

const VERSION = "0.29";
const PANEL_NAME = "gw-energypilot-panel";
const PRICE_ADJUSTMENT_KEYS = ["buy_price_adder", "sell_price_deduction"];

function alignPriceAdjustmentPrecision(root) {
  for (const key of PRICE_ADJUSTMENT_KEYS) {
    const input = root.querySelector(`input[data-setting-key="${key}"]`);
    if (input) input.step = "0.0001";
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV029Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  alignPriceAdjustmentPrecision(root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;

  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
};
