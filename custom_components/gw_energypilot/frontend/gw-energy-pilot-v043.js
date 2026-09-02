import "./gw-energy-pilot-v042.js?v=1.2.0-beta.6-chart-touch1";

const VERSION = "0.43";
const PANEL_NAME = "gw-energypilot-panel";
const TOUCH_HOVER_STYLE_ID = "ep-v043-touch-hover";

const TOUCH_HOVER_CSS = `
  @media (hover: none), (pointer: coarse) {
    :host .ep-layout-button:hover {
      border-color: rgba(106, 192, 255, .18) !important;
      background: rgba(12, 38, 66, .72) !important;
      transform: none !important;
    }
    :host .ep-optimize-now:hover:not(:disabled) {
      border-color: rgba(40, 222, 255, .34) !important;
      background: linear-gradient(135deg, rgba(20, 116, 164, .42), rgba(20, 190, 142, .30)) !important;
      box-shadow: inset 0 0 18px rgba(35, 225, 255, .06), 0 0 16px rgba(23, 215, 197, .06) !important;
      transform: none !important;
    }
    :host .ep-battery-action:hover:not(:disabled):not(.active) {
      border-color: rgba(82, 175, 233, .18) !important;
      background: rgba(6, 31, 55, .48) !important;
      color: #a9c4d8 !important;
      box-shadow: none !important;
      transform: none !important;
    }
    :host .ep-battery-action[data-action="max_charge"]:hover:not(:disabled):not(.active) {
      border-color: rgba(40, 239, 167, .22) !important;
      color: #8df1c6 !important;
    }
    :host .ep-battery-action[data-action="battery_pause"]:hover:not(:disabled):not(.active) {
      color: #b5d4e6 !important;
    }
    :host .ep-battery-action[data-action="max_export"]:hover:not(:disabled):not(.active) {
      color: #79e6fb !important;
    }
    :host .ep-v016-costfun-button:hover:not(:disabled):not(.active) {
      border-color: rgba(67, 204, 238, .20) !important;
      background: rgba(7, 45, 69, .50) !important;
      color: #a9d8e5 !important;
      box-shadow: none !important;
    }
    :host .ep-v038-profile:hover:not(:disabled):not([aria-pressed="true"]),
    :host .ep-v038-profile.ep-v038-hover-stable:not(:disabled):not([aria-pressed="true"]) {
      border-color: rgba(75, 164, 209, .16) !important;
      background: rgba(5, 27, 47, .52) !important;
      box-shadow: none !important;
      transform: none !important;
    }
  }
`;

function ensureTouchHoverStyle(root) {
  if (!root || root.querySelector(`#${TOUCH_HOVER_STYLE_ID}`)) return;
  const style = document.createElement("style");
  style.id = TOUCH_HOVER_STYLE_ID;
  style.textContent = TOUCH_HOVER_CSS;
  root.appendChild(style);
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (PanelClass && !PanelClass.prototype.__epV043Installed) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV043Render(...args) {
    const result = previousRender.apply(this, args);
    const root = this.shadowRoot;
    ensureTouchHoverStyle(root);
    const versionBadge = root?.querySelector(".version");
    if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
    const footerItems = root?.querySelectorAll("footer span") || [];
    if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
    return result;
  };
  PanelClass.prototype.__epV043Installed = true;
}
