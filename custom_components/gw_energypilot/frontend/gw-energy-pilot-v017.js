import "./gw-energy-pilot-v016.js?v=0.16-beta-g20-strategy2";
import "./gw-energy-pilot-settings-v016.js?v=0.17-settings1";

const VERSION = "0.17";
const PANEL_NAME = "gw-energypilot-panel";

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV017Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
};
