import "./gw-energy-pilot-v022.js?v=1.2.0-beta.3-load-forecast1";

const PANEL_NAME = "gw-energypilot-panel";

function ensureFlowDirectionFix(root) {
  if (root.querySelector("#ep-v022-flow-direction-fix")) return;

  const style = document.createElement("style");
  style.id = "ep-v022-flow-direction-fix";
  style.textContent = `
    /*
     * v0.13 already selects geometry-correct Forward/Reverse keyframes from
     * the live inbound/outbound classes. Older frontend layers also applied
     * animation-direction: reverse, and v0.22 repeated that reversal for some
     * semantic to-hub/from-hub states. That double reversal made e.g. grid
     * import animate from the hub toward the grid.
     *
     * Keep animation-name as the single direction mechanism. This fixes all
     * four links consistently without changing GoodWe power sign semantics.
     */
    .ep-flow-link .ep-v011-particles span {
      animation-direction: normal !important;
    }
  `;
  root.appendChild(style);
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotFlowDirectionFixRender() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  ensureFlowDirectionFix(root);
};
