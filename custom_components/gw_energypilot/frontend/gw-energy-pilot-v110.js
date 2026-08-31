import "./gw-energy-pilot-v101.js?v=1.1.1-stable1";

const VERSION = "1.1.1";
const PANEL_NAME = "gw-energypilot-panel";

function patchStableReleaseVersion(panel) {
  const root = panel?.shadowRoot;
  if (!root) return;
  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} STABLE`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · STABLE`;
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (PanelClass && !PanelClass.prototype.__epV110Installed) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV110StableRender(...args) {
    const result = previousRender.apply(this, args);
    patchStableReleaseVersion(this);
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
        patchStableReleaseVersion(this);
      },
    });
  }

  PanelClass.prototype.__epV110Installed = true;
}
