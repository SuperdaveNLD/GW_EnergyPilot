import "./gw-energy-pilot-v034.js?v=0.35-release1";

const VERSION = "0.35";
const PANEL_NAME = "gw-energypilot-panel";
const HASS_RENDER_BATCH_MS = 80;
const INTERACTIVE_SELECTOR =
  'button, input, select, textarea, a[href], [role="button"], [tabindex]';
const LEGACY_EXTERNAL_ENTITIES = [
  "sensor.p_batt_forecast",
  "sensor.optim_status",
  "sensor.soc_batt_forecast",
  "sensor.p_load_forecast",
  "sensor.p_pv_forecast",
];
const LEGACY_EXTERNAL_SUFFIXES = [
  ".p_batt_forecast",
  "_p_batt_forecast",
  ".optim_status",
  "_optim_status",
  ".soc_batt_forecast",
  "_soc_batt_forecast",
  ".p_load_forecast",
  "_p_load_forecast",
  ".p_pv_forecast",
  "_p_pv_forecast",
];

function interactiveTarget(event) {
  for (const node of event.composedPath()) {
    if (node instanceof Element && node.matches(INTERACTIVE_SELECTOR)) {
      return node;
    }
  }
  return null;
}

function interactionActive(panel) {
  return Boolean(panel.__epV035PointerActive || panel.__epV035KeyboardActive);
}

function flushDeferredRender(panel) {
  if (interactionActive(panel) || !panel.__epV035RenderDeferred) return;
  panel.__epV035RenderDeferred = false;
  panel._queueRender();
}

function finishPointerInteraction(panel) {
  if (!panel.__epV035PointerActive) return;
  panel.__epV035PointerActive = false;
  flushDeferredRender(panel);
}

function installInteractionGuard(panel, root) {
  if (panel.__epV035InteractionGuardInstalled) return;
  panel.__epV035InteractionGuardInstalled = true;

  // The legacy renderer replaces the complete shadow DOM. Keep the current
  // target alive only for the duration of an actual press so a relevant state
  // update cannot remove it between pointer-down and the browser click event.
  // Hover alone never freezes telemetry updates.
  root.addEventListener(
    "pointerdown",
    (event) => {
      const target = interactiveTarget(event);
      if (!target || (typeof event.button === "number" && event.button !== 0)) return;
      panel.__epV035PointerActive = true;
      try {
        target.setPointerCapture?.(event.pointerId);
      } catch (_err) {
        // Pointer capture is only a robustness aid.
      }
    },
    true
  );

  // A click is dispatched after pointer-up. Finish in the next task so the
  // target's existing click listener always gets the completed interaction
  // before a deferred destructive render may run.
  root.addEventListener(
    "pointerup",
    () => window.setTimeout(() => finishPointerInteraction(panel), 0),
    true
  );
  root.addEventListener(
    "pointercancel",
    () => finishPointerInteraction(panel),
    true
  );

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
      window.setTimeout(() => {
        panel.__epV035KeyboardActive = false;
        flushDeferredRender(panel);
      }, 0);
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

function refreshLegacyExternalEntityIds(panel, hass, force = false) {
  const states = hass?.states || {};
  const stateCount = Object.keys(states).length;
  if (
    !force &&
    panel.__epV035LegacyExternalEntityIds &&
    panel.__epV035ObservedStateCount === stateCount
  ) {
    return panel.__epV035LegacyExternalEntityIds;
  }

  const ids = new Set(LEGACY_EXTERNAL_ENTITIES);
  for (const entityId of Object.keys(states)) {
    if (LEGACY_EXTERNAL_SUFFIXES.some((suffix) => entityId.endsWith(suffix))) {
      ids.add(entityId);
    }
  }
  panel.__epV035LegacyExternalEntityIds = [...ids];
  panel.__epV035ObservedStateCount = stateCount;
  return panel.__epV035LegacyExternalEntityIds;
}

function configuredExternalEntityIds(panel, hass) {
  const ids = new Set();
  const optimizeId = panel._entityId?.("optimize_now");
  const optimizeState = optimizeId ? hass?.states?.[optimizeId] : null;
  const attrs = optimizeState?.attributes || {};
  for (const key of ["p_batt_entity", "p_grid_entity", "optim_status_entity"]) {
    const entityId = attrs[key];
    if (typeof entityId === "string" && entityId.includes(".")) ids.add(entityId);
  }

  const planEntity = panel.__epV027BatteryPlanData?.payload?.battery_plan?.entity_id;
  if (typeof planEntity === "string" && planEntity.includes(".")) ids.add(planEntity);
  return ids;
}

function relevantEntityIds(panel, previousHass, nextHass) {
  const ids = new Set(Object.values(panel._entityMap || {}).filter(Boolean));
  const previousCount = Object.keys(previousHass?.states || {}).length;
  const nextCount = Object.keys(nextHass?.states || {}).length;
  const legacy = refreshLegacyExternalEntityIds(
    panel,
    nextHass,
    previousCount !== nextCount
  );
  for (const entityId of legacy) ids.add(entityId);
  for (const entityId of configuredExternalEntityIds(panel, previousHass)) ids.add(entityId);
  for (const entityId of configuredExternalEntityIds(panel, nextHass)) ids.add(entityId);
  return ids;
}

function hassContextChanged(previousHass, nextHass) {
  if (!previousHass || !nextHass) return true;
  return (
    previousHass.locale !== nextHass.locale ||
    previousHass.language !== nextHass.language ||
    previousHass.user !== nextHass.user ||
    previousHass.themes !== nextHass.themes
  );
}

function relevantHassStateChanged(panel, previousHass, nextHass) {
  if (!previousHass?.states || !nextHass?.states) return true;
  for (const entityId of relevantEntityIds(panel, previousHass, nextHass)) {
    const previousState = previousHass.states[entityId];
    const nextState = nextHass.states[entityId];
    if (previousState !== nextState) return true;
  }
  return false;
}

function scheduleHassRender(panel) {
  if (panel.__epV035HassRenderTimer) return;
  panel.__epV035HassRenderTimer = window.setTimeout(() => {
    panel.__epV035HassRenderTimer = null;
    panel._queueRender();
  }, HASS_RENDER_BATCH_MS);
}

function installHassRenderGuard(PanelClass) {
  if (PanelClass.prototype.__epV035HassRenderGuardInstalled) return;
  const descriptor = Object.getOwnPropertyDescriptor(PanelClass.prototype, "hass");
  if (!descriptor?.set) return;

  Object.defineProperty(PanelClass.prototype, "hass", {
    configurable: descriptor.configurable,
    enumerable: descriptor.enumerable,
    get() {
      return descriptor.get ? descriptor.get.call(this) : this._hass;
    },
    set(value) {
      const previousHass = this._hass;

      // Preserve the original initialization/registry-discovery path. Once the
      // registry is known, keep the latest hass object without treating every
      // unrelated Home Assistant state update as a reason to rebuild the DOM.
      if (!previousHass || !this._registryLoaded) {
        descriptor.set.call(this, value);
        return;
      }

      this._hass = value;
      if (!this._registryLoaded && !this._registryLoading) this._loadRegistry();

      // v0.16 intentionally keeps settings forms stable while editing. Retain
      // that contract; explicit settings actions already request their renders.
      if (this.__epV016SettingsOpen) return;

      if (
        hassContextChanged(previousHass, value) ||
        relevantHassStateChanged(this, previousHass, value)
      ) {
        scheduleHassRender(this);
      }
    },
  });
  PanelClass.prototype.__epV035HassRenderGuardInstalled = true;
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
installHassRenderGuard(PanelClass);

if (!PanelClass.prototype.__epV035RenderInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV035Render() {
    if (interactionActive(this)) {
      this.__epV035RenderDeferred = true;
      return;
    }

    // Any render consumes the latest hass snapshot, including an explicit
    // operator-requested render that happened before the short hass batch timer.
    if (this.__epV035HassRenderTimer) {
      window.clearTimeout(this.__epV035HassRenderTimer);
      this.__epV035HassRenderTimer = null;
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
