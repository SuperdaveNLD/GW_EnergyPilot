import "./gw-energy-pilot-v0362-scroll-stability.js?v=0.36.3-control-stability1";

const VERSION = "0.36.3";
const PANEL_NAME = "gw-energypilot-panel";
const BUTTON_SELECTOR = "button";

function normalizedText(button) {
  return String(button?.textContent || "").replace(/\s+/g, " ").trim();
}

function dataSignature(button) {
  return [...(button?.attributes || [])]
    .filter((attribute) => attribute.name.startsWith("data-"))
    .map((attribute) => `${attribute.name}=${attribute.value}`)
    .sort()
    .join("|");
}

function buttonContext(button) {
  const card = button?.closest?.("[data-ep-card]");
  if (card) return `card:${card.getAttribute("data-ep-card") || ""}`;

  const panelCard = button?.closest?.(".panel-card");
  if (panelCard) return `panel:${panelCard.className || ""}`;

  return "root";
}

function buttonIdentity(button) {
  if (!(button instanceof HTMLButtonElement)) return "";
  return [
    buttonContext(button),
    button.id || "",
    button.getAttribute("name") || "",
    button.getAttribute("type") || "",
    button.getAttribute("aria-label") || "",
    button.getAttribute("title") || "",
    button.className || "",
    dataSignature(button),
    normalizedText(button),
  ].join("::");
}

function captureStableButtons(panel) {
  const root = panel?.shadowRoot;
  if (!root) return null;

  const buttons = [...root.querySelectorAll(BUTTON_SELECTOR)];
  if (!buttons.length) return null;

  return {
    buttons,
    identities: buttons.map((button) => buttonIdentity(button)),
    focusedIndex: buttons.indexOf(root.activeElement),
  };
}

function sameButtonStructure(snapshot, buttons) {
  if (!snapshot || snapshot.buttons.length !== buttons.length) return false;
  return buttons.every(
    (button, index) => buttonIdentity(button) === snapshot.identities[index]
  );
}

function syncAttributes(target, source) {
  const sourceNames = new Set(
    [...source.attributes].map((attribute) => attribute.name)
  );

  for (const attribute of [...target.attributes]) {
    if (!sourceNames.has(attribute.name)) target.removeAttribute(attribute.name);
  }

  for (const attribute of [...source.attributes]) {
    if (target.getAttribute(attribute.name) !== attribute.value) {
      target.setAttribute(attribute.name, attribute.value);
    }
  }

  target.disabled = source.disabled;
  target.value = source.value;
}

function restoreStableButtons(panel, snapshot) {
  const root = panel?.shadowRoot;
  if (!root || !snapshot) return;

  const renderedButtons = [...root.querySelectorAll(BUTTON_SELECTOR)];
  if (!sameButtonStructure(snapshot, renderedButtons)) return;

  renderedButtons.forEach((renderedButton, index) => {
    const stableButton = snapshot.buttons[index];
    syncAttributes(stableButton, renderedButton);

    if (stableButton.innerHTML !== renderedButton.innerHTML) {
      stableButton.innerHTML = renderedButton.innerHTML;
    }

    renderedButton.replaceWith(stableButton);
  });

  const focused = snapshot.buttons[snapshot.focusedIndex];
  if (focused?.isConnected) {
    try {
      focused.focus({ preventScroll: true });
    } catch (_err) {
      focused.focus();
    }
  }
}

function updateVersion(root) {
  const versionBadge = root?.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;

  const footerItems = root?.querySelectorAll("footer span") || [];
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (!PanelClass.prototype.__epV0363ControlStabilityInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV0363ControlStableRender() {
    // The legacy dashboard still rebuilds the complete Shadow DOM for relevant
    // telemetry updates. Keep existing button nodes when the rendered control
    // structure is unchanged so polling cannot reset hover/focus or visually
    // flash controls. A genuine control/structure change falls back to the new
    // render untouched.
    const buttonSnapshot = captureStableButtons(this);

    previousRender.call(this);
    restoreStableButtons(this, buttonSnapshot);
    updateVersion(this.shadowRoot);
  };
  PanelClass.prototype.__epV0363ControlStabilityInstalled = true;
}
