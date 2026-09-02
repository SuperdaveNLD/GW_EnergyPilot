import "./gw-energy-pilot-v101.js?v=1.2.0-beta.6-chart-touch1";

const VERSION = "1.2.0-beta.6";
const PANEL_NAME = "gw-energypilot-panel";
const TOUCH_TARGET_STYLE_ID = "ep-v110-chart-touch-target-style";

function ensureChartTouchTargetStyles(panel) {
  const root = panel?.shadowRoot;
  if (!root || root.querySelector(`#${TOUCH_TARGET_STYLE_ID}`)) return;
  const style = document.createElement("style");
  style.id = TOUCH_TARGET_STYLE_ID;
  style.textContent = `
    @media (pointer: coarse), (max-width: 720px) {
      .ep-v027-size-control button {
        width: 44px !important;
        min-width: 44px !important;
        height: 44px !important;
        min-height: 44px !important;
        padding: 0 !important;
      }
      .ep-v027-range-control button {
        min-width: 48px !important;
        height: 44px !important;
        min-height: 44px !important;
        padding: 0 9px !important;
      }
      .ep-v027-expand,
      .ep-v027-footer button,
      .ep-v051-full,
      .ep-v051-history-modal [data-action="close"] {
        min-width: 44px !important;
        min-height: 44px !important;
      }
      .ep-v027-footer button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0 8px !important;
      }
    }
  `;
  root.appendChild(style);
}

function patchBetaReleaseVersion(panel) {
  const root = panel?.shadowRoot;
  if (!root) return;
  ensureChartTouchTargetStyles(panel);
  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (PanelClass && !PanelClass.prototype.__epV110Installed) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV110BetaRender(...args) {
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

  PanelClass.prototype.__epV110Installed = true;
}
