import "./gw-energy-pilot-v038-runtime.js?v=1.0.1-beta2";
import { localizeV038Controller } from "./gw-energy-pilot-v038-i18n.js?v=1.0.1-beta2";

const VERSION = "0.38";
const PANEL_NAME = "gw-energypilot-panel";
const PROFILE_SELECTOR = "button[data-ep-v038-profile]";
const HOVER_CLASS = "ep-v038-hover-stable";
const HOVER_STYLE_ID = "ep-v038-hover-stability";

function profileFromPointerEvent(event) {
  for (const node of event.composedPath()) {
    if (node instanceof Element && node.matches(PROFILE_SELECTOR)) return node;
  }
  return null;
}

function setStableHover(root, hoveredButton) {
  for (const button of root.querySelectorAll(PROFILE_SELECTOR)) {
    button.classList.toggle(
      HOVER_CLASS,
      button === hoveredButton && !button.disabled
    );
  }
}

function ensureHoverStabilityStyle(root) {
  if (root.querySelector(`#${HOVER_STYLE_ID}`)) return;
  const style = document.createElement("style");
  style.id = HOVER_STYLE_ID;
  style.textContent = `
    .ep-v038-profile.${HOVER_CLASS}:not(:disabled) {
      border-color:rgba(55,213,231,.42);
      background:rgba(7,43,66,.72);
    }
  `;
  root.appendChild(style);
}

function installHoverTracking(panel, root) {
  if (panel.__epV038HoverTrackingInstalled) return;
  panel.__epV038HoverTrackingInstalled = true;

  root.addEventListener(
    "pointermove",
    (event) => {
      if (event.pointerType && event.pointerType !== "mouse") {
        setStableHover(root, null);
        return;
      }
      setStableHover(root, profileFromPointerEvent(event));
    },
    true
  );

  panel.addEventListener(
    "pointerleave",
    () => setStableHover(root, null),
    true
  );
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (!PanelClass.prototype.__epV038HoverStabilityInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV038HoverStableRender() {
    const rootBefore = this.shadowRoot;
    const hoveredBefore = rootBefore?.querySelector(`${PROFILE_SELECTOR}:hover`) || null;

    // v0.34 still rebuilds the ShadowRoot. v0.38 reuses the strategy node, so
    // persist only its visual mouse-hover class across that synchronous detach.
    // This does not defer rendering and does not affect click/touch ownership.
    if (rootBefore && hoveredBefore) setStableHover(rootBefore, hoveredBefore);

    previousRender.call(this);
    const root = this.shadowRoot;
    if (!root) return;

    localizeV038Controller(this, root);
    ensureHoverStabilityStyle(root);
    installHoverTracking(this, root);

    const hoveredAfter = root.querySelector(`${PROFILE_SELECTOR}:hover`);
    if (hoveredAfter) setStableHover(root, hoveredAfter);
  };
  PanelClass.prototype.__epV038HoverStabilityInstalled = true;
}

void VERSION;
