import "./gw-energy-pilot-v0363-control-stability.js?v=0.37-stable-controls1";

const VERSION = "0.37";
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

if (!PanelClass.prototype.__epV037ReleaseInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV037ReleaseRender() {
    previousRender.call(this);
    updateVersion(this.shadowRoot);
  };
  PanelClass.prototype.__epV037ReleaseInstalled = true;
}
