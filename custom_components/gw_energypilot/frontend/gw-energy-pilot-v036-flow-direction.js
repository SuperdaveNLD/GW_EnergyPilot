const PANEL_NAME = "gw-energypilot-panel";
const FLOW_THRESHOLD_W = 50;

function finiteNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function flowAnimationDirections(values, threshold = FLOW_THRESHOLD_W) {
  const pv = finiteNumber(values?.pv);
  const grid = finiteNumber(values?.grid);
  const house = finiteNumber(values?.house);
  const battery = finiteNumber(values?.battery);
  const direction = (value, positive, negative) => {
    if (value === null || Math.abs(value) < threshold) return null;
    return value > 0 ? positive : negative;
  };

  return {
    // Physical dashboard geometry:
    // PV is left of the hub; positive production travels left -> right.
    pv: direction(pv, "normal", "reverse"),
    // Grid is right of the hub. GoodWe positive = export (hub -> grid),
    // negative = import (grid -> hub).
    grid: direction(grid, "normal", "reverse"),
    // House is above the hub. Positive load travels bottom -> top.
    house: direction(house, "reverse", "normal"),
    // Battery is below the hub. Positive = discharge (bottom -> top),
    // negative = charge (top -> bottom).
    battery: direction(battery, "reverse", "normal"),
  };
}

function setDirection(link, direction) {
  if (!link) return;
  link.classList.remove("ep-v036-flow-normal", "ep-v036-flow-reverse");
  if (!direction || link.classList.contains("idle")) return;
  link.classList.add(
    direction === "reverse" ? "ep-v036-flow-reverse" : "ep-v036-flow-normal"
  );
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v036-flow-direction-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v036-flow-direction-style";
  style.textContent = `
    /* This final layer is the only animation-direction authority. Earlier
       inbound/outbound and v0.22 semantic classes may still describe flow,
       but they can no longer reverse the rendered particles a second time. */
    main.page .ep-flow-link.ep-v036-flow-normal::after,
    main.page .ep-flow-link.ep-v036-flow-normal .ep-v011-particles span {
      animation-direction:normal!important;
    }
    main.page .ep-flow-link.ep-v036-flow-reverse::after,
    main.page .ep-flow-link.ep-v036-flow-reverse .ep-v011-particles span {
      animation-direction:reverse!important;
    }
  `;
  root.appendChild(style);
}

function enforceFlowDirections(panel, root) {
  const directions = flowAnimationDirections({
    pv: panel._stateByKey?.("pv_total_power")?.state,
    grid: panel._stateByKey?.("meter_total_power_fast")?.state,
    house: panel._stateByKey?.("total_load_power")?.state,
    battery: panel._stateByKey?.("battery_power")?.state,
  });

  setDirection(root.querySelector(".ep-link-pv"), directions.pv);
  setDirection(root.querySelector(".ep-link-grid"), directions.grid);
  setDirection(root.querySelector(".ep-link-house"), directions.house);
  setDirection(root.querySelector(".ep-link-battery"), directions.battery);
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (!PanelClass.prototype.__epV036FlowDirectionRenderInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV036FlowDirectionRender() {
    previousRender.call(this);
    const root = this.shadowRoot;
    if (!root) return;
    ensureStyles(root);
    enforceFlowDirections(this, root);
  };
  PanelClass.prototype.__epV036FlowDirectionRenderInstalled = true;
}
