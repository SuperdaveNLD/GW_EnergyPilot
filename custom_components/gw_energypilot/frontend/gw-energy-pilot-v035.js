import "./gw-energy-pilot-v034.js?v=0.35-release1";

const VERSION = "0.35";
const PANEL_NAME = "gw-energypilot-panel";
const INTERACTIVE_SELECTOR =
  'button, input, select, textarea, a[href], [role="button"], [tabindex]';

function interactiveTarget(event) {
  for (const node of event.composedPath()) {
    if (node instanceof Element && node.matches(INTERACTIVE_SELECTOR)) {
      return node;
    }
  }
  return null;
}

function relatedInteractiveTarget(root, node) {
  if (!(node instanceof Element) || !root.contains(node)) return null;
  return node.closest(INTERACTIVE_SELECTOR);
}

function interactionActive(panel) {
  return Boolean(
    panel.__epV035HoverActive ||
      panel.__epV035PointerActive ||
      panel.__epV035KeyboardActive
  );
}

function flushDeferredRender(panel) {
  if (interactionActive(panel) || !panel.__epV035RenderDeferred) return;
  panel.__epV035RenderDeferred = false;
  panel._queueRender();
}

function installInteractionGuard(panel, root) {
  if (panel.__epV035InteractionGuardInstalled) return;
  panel.__epV035InteractionGuardInstalled = true;

  // The legacy panel renderer rebuilds the complete shadow DOM. Stabilize
  // actionable controls while the operator is approaching or pressing them so
  // a Home Assistant state update cannot replace the button between pointer
  // down and click. No action semantics are changed; deferred telemetry renders
  // are flushed immediately after the interaction ends.
  root.addEventListener(
    "pointerover",
    (event) => {
      if (event.pointerType !== "mouse" || !interactiveTarget(event)) return;
      panel.__epV035HoverActive = true;
    },
    true
  );

  root.addEventListener(
    "pointerout",
    (event) => {
      if (event.pointerType !== "mouse") return;
      if (relatedInteractiveTarget(root, event.relatedTarget)) return;
      panel.__epV035HoverActive = false;
      flushDeferredRender(panel);
    },
    true
  );

  root.addEventListener(
    "pointerdown",
    (event) => {
      const target = interactiveTarget(event);
      if (!target || (typeof event.button === "number" && event.button !== 0)) return;
      panel.__epV035PointerActive = true;
      // A completed press must be allowed to render its own result immediately.
      panel.__epV035HoverActive = false;
      try {
        target.setPointerCapture?.(event.pointerId);
      } catch (_err) {
        // Pointer capture is only a robustness aid; the click remains usable
        // on browsers that do not expose it for this target.
      }
    },
    true
  );

  const finishPointer = () => {
    panel.__epV035PointerActive = false;
    panel.__epV035HoverActive = false;
    flushDeferredRender(panel);
  };
  root.addEventListener("pointerup", finishPointer, true);
  root.addEventListener("pointercancel", finishPointer, true);

  root.addEventListener(
    "keydown",
    (event) => {
      if (
        (event.key !== "Enter" && event.key !== " ") ||
        !interactiveTarget(event)
      ) {
        return;
      }
      panel.__epV035KeyboardActive = true;
    },
    true
  );

  root.addEventListener(
    "keyup",
    (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      panel.__epV035KeyboardActive = false;
      flushDeferredRender(panel);
    },
    true
  );

  root.addEventListener(
    "focusout",
    () => {
      if (!panel.__epV035KeyboardActive) return;
      panel.__epV035KeyboardActive = false;
      flushDeferredRender(panel);
    },
    true
  );
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (!PanelClass.prototype.__epV035RenderInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV035Render() {
    if (interactionActive(this)) {
      this.__epV035RenderDeferred = true;
      return;
    }

    previousRender.call(this);
    const root = this.shadowRoot;
    if (!root) return;

    installInteractionGuard(this, root);

    const versionBadge = root.querySelector(".version");
    if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;

    const footerItems = root.querySelectorAll("footer span");
    if (footerItems.length > 0) {
      footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
    }
  };
  PanelClass.prototype.__epV035RenderInstalled = true;
}
