import "./gw-energy-pilot-v008.js?v=0.08";

const VERSION = "0.09";
const PANEL_NAME = "gw-energypilot-panel";

await customElements.whenDefined(PANEL_NAME);

const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV009Render() {
  previousRender.call(this);

  const root = this.shadowRoot;
  if (!root) return;

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION}`;

  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION}`;
  }
};
