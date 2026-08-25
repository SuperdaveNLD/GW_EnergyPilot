import "./gw-energy-pilot-v034.js?v=0.35-release2";

const VERSION = "0.35";
const PANEL_NAME = "gw-energypilot-panel";

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (!PanelClass.prototype.__epV035RenderInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV035Render() {
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
  PanelClass.prototype.__epV035RenderInstalled = true;
}
