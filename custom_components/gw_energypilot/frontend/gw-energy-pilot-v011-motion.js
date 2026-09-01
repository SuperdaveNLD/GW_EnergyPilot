import "./gw-energy-pilot-v011.js?v=1.2.0-beta.2-soc-end-sems2-beta-tests1";

const PANEL_NAME = "gw-energypilot-panel";

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV011MotionRender() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root || root.querySelector("#ep-v011-motion-fix")) return;

  const style = document.createElement("style");
  style.id = "ep-v011-motion-fix";
  style.textContent = `
    .ep-link-pv .ep-v011-particles span,
    .ep-link-grid .ep-v011-particles span {
      animation-name: epV011BallHFull !important;
    }
    .ep-link-house .ep-v011-particles span,
    .ep-link-battery .ep-v011-particles span {
      animation-name: epV011BallVFull !important;
    }

    @keyframes epV011BallHFull {
      0%   { left: -8px; opacity: .45; transform: scale(.82); }
      8%   { opacity: .95; }
      50%  { opacity: 1; transform: scale(1); }
      92%  { opacity: .95; }
      100% { left: calc(100% + 2px); opacity: .45; transform: scale(.82); }
    }
    @keyframes epV011BallVFull {
      0%   { top: -8px; opacity: .45; transform: scale(.82); }
      8%   { opacity: .95; }
      50%  { opacity: 1; transform: scale(1); }
      92%  { opacity: .95; }
      100% { top: calc(100% + 2px); opacity: .45; transform: scale(.82); }
    }
  `;
  root.appendChild(style);
};
