import "./gw-energy-pilot-v016.js?v=1.0.1-beta2";
import "./gw-energy-pilot-settings-v016.js?v=1.0.1-beta2";

const VERSION = "0.17";
const PANEL_NAME = "gw-energypilot-panel";

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV017Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  const strategyNote = root.querySelector(".ep-v016-costfun-note");
  if (strategyNote) {
    strategyNote.innerHTML = "This is one persistent EMHASS setting, not three independent modes. The highlighted option is the current <strong>costfun</strong> read from EMHASS. Changing it saves the setting and immediately requests a fresh optimization. GoodWe execution remains P_batt-driven; changing strategy does not change the actuator mapping.";
  }

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
};
