import "./gw-energy-pilot-v038.js?v=1.2.0-beta.4-touch-methods1";

const VERSION = "0.39";
const PANEL_NAME = "gw-energypilot-panel";

function updateVersion(root) {
  const versionBadge = root?.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root?.querySelectorAll("footer span") || [];
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (PanelClass && !PanelClass.prototype.__epV039Installed) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV039Render(...args) {
    const result = previousRender.apply(this, args);
    updateVersion(this.shadowRoot);
    return result;
  };
  PanelClass.prototype.__epV039Installed = true;
}
