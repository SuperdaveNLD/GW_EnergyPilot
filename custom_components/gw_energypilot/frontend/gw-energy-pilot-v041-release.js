import "./gw-energy-pilot-v041.js?v=0.41-stable-dom3";

const PANEL_NAME = "gw-energypilot-panel";
const PANEL_STYLE_ID = "ep-v041-release-no-motion";
const GLOBAL_STYLE_ID = "ep-v041-release-global-no-motion";
const STATIC_ATTRIBUTE = "data-ep-v041-static";
const STATIC_SELECTOR = `[${STATIC_ATTRIBUTE}][${STATIC_ATTRIBUTE}][${STATIC_ATTRIBUTE}][${STATIC_ATTRIBUTE}][${STATIC_ATTRIBUTE}][${STATIC_ATTRIBUTE}][${STATIC_ATTRIBUTE}][${STATIC_ATTRIBUTE}]`;

const PANEL_CSS = `
  :host([data-ep-v041-no-motion]) ${STATIC_SELECTOR}::before,
  :host([data-ep-v041-no-motion]) ${STATIC_SELECTOR}::after {
    animation: none !important;
    animation-name: none !important;
    animation-duration: 0s !important;
    animation-delay: 0s !important;
    animation-iteration-count: 1 !important;
    transition: none !important;
    transition-property: none !important;
    transition-duration: 0s !important;
    transition-delay: 0s !important;
  }
`;

const GLOBAL_CSS = `
  body[data-ep-v041-no-motion] .ep-v027-backdrop,
  body[data-ep-v041-no-motion] .ep-v027-backdrop *,
  body[data-ep-v041-no-motion] .ep-v027-backdrop *::before,
  body[data-ep-v041-no-motion] .ep-v027-backdrop *::after,
  body[data-ep-v041-no-motion] .ep-v026-bp-backdrop,
  body[data-ep-v041-no-motion] .ep-v026-bp-backdrop *,
  body[data-ep-v041-no-motion] .ep-v026-bp-backdrop *::before,
  body[data-ep-v041-no-motion] .ep-v026-bp-backdrop *::after,
  body[data-ep-v041-no-motion] .ep13-backdrop,
  body[data-ep-v041-no-motion] .ep13-backdrop *,
  body[data-ep-v041-no-motion] .ep13-backdrop *::before,
  body[data-ep-v041-no-motion] .ep13-backdrop *::after {
    animation: none !important;
    transition: none !important;
    scroll-behavior: auto !important;
  }
  body[data-ep-v041-no-motion] .ep-v027-backdrop,
  body[data-ep-v041-no-motion] .ep-v026-bp-backdrop,
  body[data-ep-v041-no-motion] .ep13-backdrop {
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
  }
`;

function freezeElement(element) {
  if (!(element instanceof Element)) return;
  element.setAttribute(STATIC_ATTRIBUTE, "");
  element.style.setProperty("animation", "none", "important");
  element.style.setProperty("animation-name", "none", "important");
  element.style.setProperty("animation-duration", "0s", "important");
  element.style.setProperty("transition", "none", "important");
  element.style.setProperty("transition-property", "none", "important");
  element.style.setProperty("transition-duration", "0s", "important");
  element.style.setProperty("scroll-behavior", "auto", "important");
}

function freezeGlobalMotion() {
  if (!globalThis.document) return;
  document.body?.setAttribute("data-ep-v041-no-motion", "");
  if (!document.getElementById(GLOBAL_STYLE_ID)) {
    const style = document.createElement("style");
    style.id = GLOBAL_STYLE_ID;
    style.textContent = GLOBAL_CSS;
    document.head.appendChild(style);
  }
  for (const element of document.querySelectorAll(
    ".ep-v027-backdrop, .ep-v027-backdrop *, .ep-v026-bp-backdrop, .ep-v026-bp-backdrop *, .ep13-backdrop, .ep13-backdrop *"
  )) {
    freezeElement(element);
  }
}

function freezePanelMotion(panel) {
  const root = panel?.shadowRoot;
  if (!root) return;
  panel.setAttribute("data-ep-v041-no-motion", "");
  if (!root.querySelector(`#${PANEL_STYLE_ID}`)) {
    const style = document.createElement("style");
    style.id = PANEL_STYLE_ID;
    style.textContent = PANEL_CSS;
    root.appendChild(style);
  }
  for (const element of root.querySelectorAll("*")) freezeElement(element);
  for (const element of root.querySelectorAll(
    ".ep-flow-arrows, .ep-flow-live span, .ep-v011-particles, .ep-v011-particles span"
  )) {
    element.style.setProperty("display", "none", "important");
  }
  freezeGlobalMotion();
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (PanelClass && !PanelClass.prototype.__epV041ReleaseMotionInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV041ReleaseRender(...args) {
    const result = previousRender.apply(this, args);
    this.__epV041FreezeMotion = () => freezePanelMotion(this);
    freezePanelMotion(this);
    return result;
  };
  PanelClass.prototype.__epV041ReleaseMotionInstalled = true;
}
