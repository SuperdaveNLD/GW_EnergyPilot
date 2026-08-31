import "./gw-energy-pilot-v050.js?v=1.0.1-beta4";
import { refreshHistoryCard } from "./gw-energy-pilot-v051-history.js?v=1.0.1-beta4";

const VERSION = "0.51";
const PANEL_NAME = "gw-energypilot-panel";

function patchReleaseVersion(panel) {
  const root = panel?.shadowRoot;
  if (!root) return;
  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (PanelClass && !PanelClass.prototype.__epV051Installed) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV051ReleaseRender(...args) {
    const result = previousRender.apply(this, args);
    patchReleaseVersion(this);
    refreshHistoryCard(this);
    return result;
  };

  const descriptor = Object.getOwnPropertyDescriptor(PanelClass.prototype, "hass");
  if (descriptor?.set) {
    Object.defineProperty(PanelClass.prototype, "hass", {
      configurable: descriptor.configurable,
      enumerable: descriptor.enumerable,
      get() {
        return descriptor.get ? descriptor.get.call(this) : this._hass;
      },
      set(value) {
        descriptor.set.call(this, value);
        patchReleaseVersion(this);
        refreshHistoryCard(this);
      },
    });
  }

  PanelClass.prototype.__epV051Installed = true;
}
