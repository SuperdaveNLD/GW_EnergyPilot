import "./gw-energy-pilot-v031-battery-saver.js?v=0.33-release1";
// Load the chart core under a fresh module URL as well. During a live upgrade,
// the browser keeps historical nested ES-module URLs in its module map even
// when the top-level panel URL changes.
import "./gw-energy-pilot-v027-battery-plan-core.js?v=0.33-planrefresh1";

const VERSION = "0.33";
const PANEL_NAME = "gw-energypilot-panel";

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (!PanelClass.prototype.__epV033RenderInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV033Render() {
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
  PanelClass.prototype.__epV033RenderInstalled = true;
}
