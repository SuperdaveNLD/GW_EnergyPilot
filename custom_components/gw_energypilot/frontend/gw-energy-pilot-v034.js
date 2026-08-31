import "./gw-energy-pilot-v031-battery-saver.js?v=1.1.0-stable1";
import "./gw-energy-pilot-v027-battery-plan-core.js?v=1.1.0-stable1";

const VERSION = "0.34";
const PANEL_NAME = "gw-energypilot-panel";
const FLOW_COMPACT_BREAKPOINT_PX = 430;
const FLOW_TIGHT_BREAKPOINT_PX = 340;

function ensureFlowStyles(root) {
  if (root.querySelector("#ep-v034-flow-style")) return;

  const style = document.createElement("style");
  style.id = "ep-v034-flow-style";
  style.textContent = `
    /* v0.22 still contains two-class !important reversal rules. Match that
       specificity at the active layer so the geometry-specific v0.13
       animation names remain the only direction mechanism. */
    .ep-flow-link.ep-v022-to-hub .ep-v011-particles span,
    .ep-flow-link.ep-v022-from-hub .ep-v011-particles span {
      animation-direction: normal !important;
    }

    /* Compact flow geometry is enabled only for an actual narrow HA panel.
       It uses measured card dimensions, so phones, safe areas and rotation do
       not depend on one fixed viewport assumption. */
    .ep-flow-overview.ep-v034-flow-compact {
      padding: 12px 12px 16px !important;
      min-height: 0 !important;
      max-width: 100%;
      overflow: hidden;
    }
    .ep-dashboard-layout > .ep-flow-overview.ep-v034-flow-compact {
      height: auto !important;
      min-height: 0 !important;
    }
    .ep-flow-overview.ep-v034-flow-compact::before {
      width: 72%;
      height: 72%;
      left: 14%;
      top: 20%;
    }
    .ep-v034-flow-compact > .ep-v031-card-windowbar,
    .ep-v034-flow-compact > .ep-v028-window-controls {
      margin-bottom: 6px !important;
    }
    .ep-v034-flow-compact .ep-flow-heading {
      gap: 8px;
      align-items: center;
    }
    .ep-v034-flow-compact .ep-flow-kicker {
      font-size: 9px;
    }
    .ep-v034-flow-compact .ep-flow-title {
      font-size: 16px;
    }
    .ep-v034-flow-compact .ep-flow-live {
      flex: 0 0 auto;
      padding: 4px 7px;
      font-size: 8px;
    }
    .ep-v034-flow-compact .ep-flow-stage {
      height: var(--ep-v034-stage-height) !important;
      margin-top: 4px;
    }
    .ep-v034-flow-compact .ep-flow-node {
      width: var(--ep-v034-node-width) !important;
      height: var(--ep-v034-node-height) !important;
      min-height: var(--ep-v034-node-height) !important;
      padding: 5px 5px 4px !important;
      border-radius: 12px;
      overflow: hidden;
    }
    .ep-v034-flow-compact .ep-flow-icon {
      height: 20px;
      margin: 2px auto 1px;
    }
    .ep-v034-flow-compact .ep-flow-icon svg {
      width: 22px;
      height: 22px;
    }
    .ep-v034-flow-compact .ep-flow-node-value {
      font-size: 12px;
    }
    .ep-v034-flow-compact .ep-flow-node-sub {
      margin-top: 2px;
      font-size: 7px;
    }
    .ep-v034-flow-compact .ep-flow-hub {
      width: var(--ep-v034-hub-size) !important;
      height: var(--ep-v034-hub-size) !important;
    }
    .ep-v034-flow-compact .ep-flow-hub svg {
      width: calc(var(--ep-v034-hub-size) - 8px) !important;
      height: calc(var(--ep-v034-hub-size) - 8px) !important;
    }
    .ep-v034-flow-compact .ep-link-pv {
      left: calc(var(--ep-v034-node-width) - 2px) !important;
      right: calc(50% + var(--ep-v034-hub-half) - 2px) !important;
      width: auto !important;
    }
    .ep-v034-flow-compact .ep-link-grid {
      left: calc(50% + var(--ep-v034-hub-half) - 2px) !important;
      right: calc(var(--ep-v034-node-width) - 2px) !important;
      width: auto !important;
    }
    .ep-v034-flow-compact .ep-link-house {
      top: calc(var(--ep-v034-node-height) - 2px) !important;
      bottom: calc(50% + var(--ep-v034-hub-half) - 2px) !important;
      height: auto !important;
    }
    .ep-v034-flow-compact .ep-link-battery {
      top: calc(50% + var(--ep-v034-hub-half) - 2px) !important;
      bottom: calc(var(--ep-v034-node-height) - 2px) !important;
      height: auto !important;
    }
    .ep-v034-flow-tight .ep-flow-kicker {
      font-size: 8px;
    }
    .ep-v034-flow-tight .ep-flow-title {
      font-size: 15px;
    }
    .ep-v034-flow-tight .ep-flow-node-sub {
      display: none !important;
    }
  `;
  root.appendChild(style);
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function updateParticleGeometry(flow) {
  for (const link of flow.querySelectorAll(".ep-flow-link")) {
    const vertical =
      link.classList.contains("ep-link-house") ||
      link.classList.contains("ep-link-battery");
    const distance = Math.max(
      1,
      Math.round((vertical ? link.clientHeight : link.clientWidth) + 10)
    );
    const next = `${distance}px`;
    if (link.style.getPropertyValue("--ep-track-distance") !== next) {
      link.style.setProperty("--ep-track-distance", next);
    }
  }
}

function updateResponsiveFlowLayout(panel, flow) {
  const width = flow.getBoundingClientRect().width;
  const narrowPanel =
    panel.narrow === true ||
    panel._narrow === true ||
    globalThis.matchMedia?.("(max-width: 720px)")?.matches === true;
  const compact =
    narrowPanel && width > 0 && width <= FLOW_COMPACT_BREAKPOINT_PX;
  const tight = compact && width <= FLOW_TIGHT_BREAKPOINT_PX;

  flow.classList.toggle("ep-v034-flow-compact", compact);
  flow.classList.toggle("ep-v034-flow-tight", tight);

  const propertyNames = [
    "--ep-v034-node-width",
    "--ep-v034-node-height",
    "--ep-v034-hub-size",
    "--ep-v034-hub-half",
    "--ep-v034-stage-height",
  ];

  if (!compact) {
    if (flow.dataset.epV034Layout) {
      delete flow.dataset.epV034Layout;
      propertyNames.forEach((name) => flow.style.removeProperty(name));
    }
    updateParticleGeometry(flow);
    return;
  }

  const stage = flow.querySelector(".ep-flow-stage");
  const stageWidth =
    stage?.getBoundingClientRect().width || Math.max(1, width - 24);
  const nodeWidth = clamp(stageWidth * 0.235, 70, 82);
  const hubSize = clamp(stageWidth * 0.16, 50, 56);
  const nodeHeight = tight
    ? clamp(stageWidth * 0.19, 58, 64)
    : clamp(stageWidth * 0.20, 64, 68);
  const verticalGap = clamp(stageWidth * 0.045, 14, 18);
  const stageHeight = Math.ceil(
    2 * (nodeHeight + verticalGap + hubSize / 2)
  );
  const layout = [nodeWidth, nodeHeight, hubSize, stageHeight]
    .map((value) => value.toFixed(1))
    .join(":");

  if (flow.dataset.epV034Layout !== layout) {
    flow.dataset.epV034Layout = layout;
    flow.style.setProperty("--ep-v034-node-width", `${nodeWidth.toFixed(1)}px`);
    flow.style.setProperty("--ep-v034-node-height", `${nodeHeight.toFixed(1)}px`);
    flow.style.setProperty("--ep-v034-hub-size", `${hubSize.toFixed(1)}px`);
    flow.style.setProperty("--ep-v034-hub-half", `${(hubSize / 2).toFixed(1)}px`);
    flow.style.setProperty("--ep-v034-stage-height", `${stageHeight}px`);
  }

  updateParticleGeometry(flow);
}

function installFlowResizeObserver(panel, root) {
  const flow = root.querySelector(".ep-flow-overview");
  const observer = panel.__epV034FlowResizeObserver;
  const previousFlow = panel.__epV034ObservedFlow;

  if (!flow) {
    if (observer && previousFlow) observer.unobserve(previousFlow);
    panel.__epV034ObservedFlow = null;
    return;
  }

  if (
    !panel.__epV034FlowResizeObserver &&
    typeof globalThis.ResizeObserver === "function"
  ) {
    panel.__epV034FlowResizeObserver = new globalThis.ResizeObserver((entries) => {
      const currentFlow = panel.__epV034ObservedFlow;
      if (!currentFlow) return;
      for (const entry of entries) {
        if (entry.target === currentFlow) {
          updateResponsiveFlowLayout(panel, currentFlow);
          break;
        }
      }
    });
  }

  const activeObserver = panel.__epV034FlowResizeObserver;
  if (previousFlow !== flow) {
    if (activeObserver && previousFlow) activeObserver.unobserve(previousFlow);
    panel.__epV034ObservedFlow = flow;
    activeObserver?.observe(flow);
  }

  updateResponsiveFlowLayout(panel, flow);
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (!PanelClass.prototype.__epV034RenderInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV034Render() {
    previousRender.call(this);
    const root = this.shadowRoot;
    if (!root) return;

    ensureFlowStyles(root);
    installFlowResizeObserver(this, root);

    const versionBadge = root.querySelector(".version");
    if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;

    const footerItems = root.querySelectorAll("footer span");
    if (footerItems.length > 0) {
      footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
    }
  };
  PanelClass.prototype.__epV034RenderInstalled = true;
}
