import "./gw-energy-pilot-v051.js?v=1.1.0-beta.2-settings1";

const VERSION = "1.0.1-beta.4";
const PANEL_NAME = "gw-energypilot-panel";

function patchBetaReleaseVersion(panel) {
  const root = panel?.shadowRoot;
  if (!root) return;
  const versionBadge = root.querySelector(".version");
  const badgeText = `v${VERSION} BETA`;
  if (versionBadge && versionBadge.textContent !== badgeText) {
    versionBadge.textContent = badgeText;
  }
  const footerItems = root.querySelectorAll("footer span");
  const footerText = `GW EnergyPilot v${VERSION} · BETA`;
  if (footerItems.length > 0 && footerItems[0].textContent !== footerText) {
    footerItems[0].textContent = footerText;
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (PanelClass && !PanelClass.prototype.__epV101Installed) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV101BetaRender(...args) {
    const result = previousRender.apply(this, args);
    patchBetaReleaseVersion(this);
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
        patchBetaReleaseVersion(this);
      },
    });
  }

  PanelClass.prototype.__epV101Installed = true;
}
