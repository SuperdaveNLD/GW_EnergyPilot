import "./gw-energy-pilot-v042.js?v=0.43-release1";

const VERSION = "0.43";
const PANEL_NAME = "gw-energypilot-panel";

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (PanelClass && !PanelClass.prototype.__epV043Installed) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV043Render(...args) {
    const result = previousRender.apply(this, args);
    const root = this.shadowRoot;
    const versionBadge = root?.querySelector(".version");
    if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
    const footerItems = root?.querySelectorAll("footer span") || [];
    if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
    return result;
  };
  PanelClass.prototype.__epV043Installed = true;
}
