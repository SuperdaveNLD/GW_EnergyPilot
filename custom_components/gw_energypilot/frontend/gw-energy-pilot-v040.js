import "./gw-energy-pilot-v039.js?v=0.40-v0391";

const VERSION = "0.40";
const PANEL_NAME = "gw-energypilot-panel";
const SETTLE_CLASS = "ep-v040-render-settle";
const SETTLE_STYLE_ID = "ep-v040-render-settle-style";
const INTERACTIVE_SELECTOR =
  'button, input, select, textarea, a[href], [role="button"], [tabindex]';
const SETTLE_CSS = `
  :host(.${SETTLE_CLASS}) :is(${INTERACTIVE_SELECTOR}),
  :host(.${SETTLE_CLASS}) :is(${INTERACTIVE_SELECTOR}) *,
  :host(.${SETTLE_CLASS}) :is(${INTERACTIVE_SELECTOR})::before,
  :host(.${SETTLE_CLASS}) :is(${INTERACTIVE_SELECTOR})::after,
  :host(.${SETTLE_CLASS}) :is(${INTERACTIVE_SELECTOR}) *::before,
  :host(.${SETTLE_CLASS}) :is(${INTERACTIVE_SELECTOR}) *::after {
    transition: none !important;
  }
`;

function updateVersion(root) {
  const versionBadge = root?.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root?.querySelectorAll("footer span") || [];
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
}

function ensureFallbackSettleStyle(root) {
  if (!root || root.querySelector(`#${SETTLE_STYLE_ID}`)) return;
  const style = document.createElement("style");
  style.id = SETTLE_STYLE_ID;
  style.textContent = SETTLE_CSS;
  root.appendChild(style);
}

function ensurePersistentSettleStyle(panel, root) {
  if (!root) return false;
  const existing = panel.__epV040SettleSheet;
  if (existing && root.adoptedStyleSheets?.includes?.(existing)) return true;

  try {
    if (
      typeof globalThis.CSSStyleSheet === "function" &&
      "adoptedStyleSheets" in root
    ) {
      const sheet = existing || new globalThis.CSSStyleSheet();
      if (!existing) sheet.replaceSync(SETTLE_CSS);
      if (!root.adoptedStyleSheets.includes(sheet)) {
        root.adoptedStyleSheets = [...root.adoptedStyleSheets, sheet];
      }
      panel.__epV040SettleSheet = sheet;
      return true;
    }
  } catch (_err) {
    // The same settle contract is installed as an ordinary style below.
  }

  ensureFallbackSettleStyle(root);
  return false;
}

function scheduleSettleEnd(panel, generation) {
  const finish = () => {
    if (panel.__epV040RenderGeneration !== generation) return;
    panel.classList.remove(SETTLE_CLASS);
  };

  if (typeof globalThis.requestAnimationFrame === "function") {
    // One rAF runs before paint. The second rAF guarantees the freshly rebuilt
    // controls have painted once in their final :hover state without replaying
    // their CSS transition from the detached predecessor node.
    globalThis.requestAnimationFrame(() => {
      globalThis.requestAnimationFrame(finish);
    });
    return;
  }

  globalThis.setTimeout?.(finish, 34);
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (PanelClass && !PanelClass.prototype.__epV040Installed) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV040Render(...args) {
    const generation = (this.__epV040RenderGeneration || 0) + 1;
    this.__epV040RenderGeneration = generation;

    const rootBefore = this.shadowRoot;
    if (rootBefore) ensurePersistentSettleStyle(this, rootBefore);
    this.classList.add(SETTLE_CLASS);

    let result;
    try {
      result = previousRender.apply(this, args);
      const root = this.shadowRoot;
      if (root) {
        if (!ensurePersistentSettleStyle(this, root)) {
          ensureFallbackSettleStyle(root);
        }
        updateVersion(root);
      }
      return result;
    } finally {
      scheduleSettleEnd(this, generation);
    }
  };
  PanelClass.prototype.__epV040Installed = true;
}
