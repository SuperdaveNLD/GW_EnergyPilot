import "./gw-energy-pilot-v034.js?v=0.50-ev1";
import { FLOW_THRESHOLD_W, flowMotionMap } from "./gw-energy-pilot-v038-model.js?v=0.50-ev1";
import { ensureV038Styles } from "./gw-energy-pilot-v038-styles.js?v=0.50-ev1";
import {
  installV038CustomerStrategy,
  installV038DelegatedControls,
} from "./gw-energy-pilot-v038-strategy.js?v=0.50-ev1";

const VERSION = "0.38";
const PANEL_NAME = "gw-energypilot-panel";
const HASS_RENDER_BATCH_MS = 150;
const MOBILE_SCROLL_BREAKPOINT_PX = 720;
const TOUCH_SCROLL_THRESHOLD_PX = 8;
const TOUCH_SCROLL_SETTLE_MS = 350;
const INTERACTION_SAFETY_TIMEOUT_MS = 3000;
const INTERACTIVE_SELECTOR =
  'button, input, select, textarea, a[href], [role="button"], [tabindex]';
const LEGACY_EXTERNAL_ENTITIES = [
  "sensor.p_batt_forecast",
  "sensor.p_grid_forecast",
  "sensor.optim_status",
  "sensor.soc_batt_forecast",
  "sensor.p_load_forecast",
  "sensor.p_pv_forecast",
];
const LEGACY_EXTERNAL_SUFFIXES = [
  ".p_batt_forecast",
  "_p_batt_forecast",
  ".p_grid_forecast",
  "_p_grid_forecast",
  ".optim_status",
  "_optim_status",
  ".soc_batt_forecast",
  "_soc_batt_forecast",
  ".p_load_forecast",
  "_p_load_forecast",
  ".p_pv_forecast",
  "_p_pv_forecast",
];

function stableRuntimeActive(panel) {
  return panel?.__epV041StableRuntime === true;
}

function finitePower(panel, key) {
  const raw = panel._numberByKey?.(key, null);
  const value = Number(raw);
  return raw !== null && raw !== undefined && Number.isFinite(value) ? value : null;
}

function setFlowMotion(root, selector, motion) {
  const link = root.querySelector(selector);
  if (link) link.dataset.epV038Motion = motion;
}

function synchronizeFlowDirections(panel, root) {
  const motion = flowMotionMap(
    {
      pv: finitePower(panel, "pv_total_power"),
      grid: finitePower(panel, "meter_total_power_fast"),
      house: finitePower(panel, "total_load_power"),
      battery: finitePower(panel, "battery_power"),
    },
    FLOW_THRESHOLD_W
  );
  setFlowMotion(root, ".ep-link-pv", motion.pv);
  setFlowMotion(root, ".ep-link-grid", motion.grid);
  setFlowMotion(root, ".ep-link-house", motion.house);
  setFlowMotion(root, ".ep-link-battery", motion.battery);
}

function eventInteractiveElement(event) {
  for (const node of event.composedPath()) {
    if (node instanceof Element && node.matches(INTERACTIVE_SELECTOR)) return node;
  }
  return null;
}

function interactionState(panel) {
  panel.__epV038Interaction = panel.__epV038Interaction || {
    pointerId: null,
    pointerType: null,
    startX: 0,
    startY: 0,
    touchMoved: false,
    keyboard: false,
    pointerFinishTimer: null,
    pointerSafetyTimer: null,
    keyboardSafetyTimer: null,
  };
  return panel.__epV038Interaction;
}

function interactionActive(panel) {
  const state = interactionState(panel);
  return state.pointerId !== null || state.keyboard;
}

function touchInteractionActive(panel) {
  const state = interactionState(panel);
  return state.pointerId !== null && state.pointerType === "touch";
}

function flushDeferredRender(panel) {
  if (interactionActive(panel) || !panel.__epV038RenderDeferred) return;
  panel.__epV038RenderDeferred = false;
  panel._queueRender();
}

function completePointerInteraction(panel) {
  const state = interactionState(panel);
  if (state.pointerFinishTimer) window.clearTimeout(state.pointerFinishTimer);
  if (state.pointerSafetyTimer) window.clearTimeout(state.pointerSafetyTimer);
  state.pointerFinishTimer = null;
  state.pointerSafetyTimer = null;
  state.pointerId = null;
  state.pointerType = null;
  state.startX = 0;
  state.startY = 0;
  state.touchMoved = false;
  flushDeferredRender(panel);
}

function finishPointerInteraction(panel, settleTouchScroll = false) {
  const state = interactionState(panel);
  if (state.pointerId === null) return;
  const touchScroll = state.pointerType === "touch" && state.touchMoved;
  if (settleTouchScroll && touchScroll) {
    if (state.pointerFinishTimer) window.clearTimeout(state.pointerFinishTimer);
    state.pointerFinishTimer = window.setTimeout(
      () => completePointerInteraction(panel),
      TOUCH_SCROLL_SETTLE_MS
    );
    return;
  }
  completePointerInteraction(panel);
}

function completeKeyboardInteraction(panel) {
  const state = interactionState(panel);
  if (state.keyboardSafetyTimer) window.clearTimeout(state.keyboardSafetyTimer);
  state.keyboardSafetyTimer = null;
  state.keyboard = false;
  flushDeferredRender(panel);
}

function completeAllInteractions(panel) {
  completePointerInteraction(panel);
  completeKeyboardInteraction(panel);
  flushDeferredRender(panel);
}

function installInteractionGuard(panel, root) {
  if (stableRuntimeActive(panel) || panel.__epV038InteractionGuardInstalled) return;
  panel.__epV038InteractionGuardInstalled = true;
  const state = interactionState(panel);

  root.addEventListener(
    "pointerdown",
    (event) => {
      const touchPointer = event.pointerType === "touch";
      if (!touchPointer && !eventInteractiveElement(event)) return;
      if (typeof event.button === "number" && event.button !== 0) return;

      const settlingTouch = Boolean(state.pointerFinishTimer);
      if (state.pointerFinishTimer) window.clearTimeout(state.pointerFinishTimer);
      state.pointerFinishTimer = null;
      if (event.isPrimary === false || (state.pointerId !== null && !settlingTouch)) return;

      if (state.pointerSafetyTimer) window.clearTimeout(state.pointerSafetyTimer);
      state.pointerId = event.pointerId;
      state.pointerType = event.pointerType || "";
      state.startX = event.clientX;
      state.startY = event.clientY;
      state.touchMoved = false;
      state.pointerSafetyTimer = window.setTimeout(
        () => completePointerInteraction(panel),
        INTERACTION_SAFETY_TIMEOUT_MS
      );
    },
    true
  );

  globalThis.addEventListener?.(
    "pointermove",
    (event) => {
      if (state.pointerId !== event.pointerId || state.pointerType !== "touch") return;
      const distance = Math.max(
        Math.abs(event.clientX - state.startX),
        Math.abs(event.clientY - state.startY)
      );
      if (distance >= TOUCH_SCROLL_THRESHOLD_PX) state.touchMoved = true;
    },
    true
  );

  globalThis.addEventListener?.(
    "pointerup",
    (event) => {
      if (state.pointerId !== event.pointerId) return;
      window.setTimeout(() => finishPointerInteraction(panel, true), 0);
    },
    true
  );
  globalThis.addEventListener?.(
    "pointercancel",
    (event) => {
      if (state.pointerId !== event.pointerId) return;
      if (state.pointerType === "touch") state.touchMoved = true;
      finishPointerInteraction(panel, true);
    },
    true
  );
  globalThis.addEventListener?.("blur", () => completeAllInteractions(panel));

  root.addEventListener(
    "keydown",
    (event) => {
      if (
        (event.key !== "Enter" && event.key !== " ") ||
        !eventInteractiveElement(event)
      ) {
        return;
      }
      if (state.keyboardSafetyTimer) window.clearTimeout(state.keyboardSafetyTimer);
      state.keyboard = true;
      state.keyboardSafetyTimer = window.setTimeout(
        () => completeKeyboardInteraction(panel),
        INTERACTION_SAFETY_TIMEOUT_MS
      );
    },
    true
  );
  root.addEventListener(
    "keyup",
    (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      window.setTimeout(() => completeKeyboardInteraction(panel), 0);
    },
    true
  );
  root.addEventListener(
    "focusout",
    () => completeKeyboardInteraction(panel),
    true
  );
}

function refreshLegacyExternalEntityIds(panel, hass, force = false) {
  const states = hass?.states || {};
  const stateCount = Object.keys(states).length;
  if (
    !force &&
    panel.__epV038LegacyExternalEntityIds &&
    panel.__epV038ObservedStateCount === stateCount
  ) {
    return panel.__epV038LegacyExternalEntityIds;
  }

  const ids = new Set(LEGACY_EXTERNAL_ENTITIES);
  for (const entityId of Object.keys(states)) {
    if (LEGACY_EXTERNAL_SUFFIXES.some((suffix) => entityId.endsWith(suffix))) {
      ids.add(entityId);
    }
  }
  panel.__epV038LegacyExternalEntityIds = [...ids];
  panel.__epV038ObservedStateCount = stateCount;
  return panel.__epV038LegacyExternalEntityIds;
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
  for (const entityId of refreshLegacyExternalEntityIds(
    panel,
    nextHass,
    previousCount !== nextCount
  )) {
    ids.add(entityId);
  }
  for (const entityId of configuredExternalEntityIds(panel, previousHass)) {
    ids.add(entityId);
  }
  for (const entityId of configuredExternalEntityIds(panel, nextHass)) {
    ids.add(entityId);
  }
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
    if (previousHass.states[entityId] !== nextHass.states[entityId]) return true;
  }
  return false;
}

function scheduleHassRender(panel) {
  if (panel.__epV038HassRenderTimer) return;
  panel.__epV038HassRenderTimer = window.setTimeout(() => {
    panel.__epV038HassRenderTimer = null;
    panel._queueRender();
  }, HASS_RENDER_BATCH_MS);
}

function installHassRenderGuard(PanelClass) {
  if (PanelClass.prototype.__epV038HassRenderGuardInstalled) return;
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
      if (!previousHass || !this._registryLoaded) {
        descriptor.set.call(this, value);
        return;
      }

      this._hass = value;
      if (this.__epV016SettingsOpen) return;
      if (
        hassContextChanged(previousHass, value) ||
        relevantHassStateChanged(this, previousHass, value)
      ) {
        scheduleHassRender(this);
      }
    },
  });
  PanelClass.prototype.__epV038HassRenderGuardInstalled = true;
}

function composedParent(node) {
  if (node?.parentElement) return node.parentElement;
  const root = node?.getRootNode?.();
  const host = root?.host;
  return host instanceof Element ? host : null;
}

function shouldPreserveScroll(panel) {
  return Boolean(
    panel?.narrow === true ||
      panel?._narrow === true ||
      globalThis.matchMedia?.(`(max-width: ${MOBILE_SCROLL_BREAKPOINT_PX}px)`)
        ?.matches === true
  );
}

function scrollSnapshot(element) {
  if (!(element instanceof Element)) return null;
  const scrollTop = Number(element.scrollTop || 0);
  const scrollLeft = Number(element.scrollLeft || 0);
  const scrollRange =
    Number(element.scrollHeight || 0) - Number(element.clientHeight || 0);
  if (scrollRange <= 1 && scrollTop <= 0) return null;
  const overflowY = globalThis.getComputedStyle?.(element)?.overflowY || "";
  if (scrollTop <= 0 && !/(auto|scroll|overlay)/.test(overflowY)) return null;
  return { element, scrollTop, scrollLeft };
}

function captureScrollPositions(panel) {
  const snapshots = [];
  const seen = new Set();
  let node = panel;
  while (node) {
    const snapshot = scrollSnapshot(node);
    if (snapshot && !seen.has(snapshot.element)) {
      snapshots.push(snapshot);
      seen.add(snapshot.element);
    }
    node = composedParent(node);
  }
  const documentScroller = globalThis.document?.scrollingElement;
  const documentSnapshot = scrollSnapshot(documentScroller);
  if (documentSnapshot && !seen.has(documentSnapshot.element)) {
    snapshots.push(documentSnapshot);
  }
  return snapshots;
}

function restoreScrollPositions(snapshots) {
  for (const snapshot of snapshots) {
    const element = snapshot.element;
    if (!element?.isConnected) continue;
    const maxTop = Math.max(
      0,
      Number(element.scrollHeight || 0) - Number(element.clientHeight || 0)
    );
    const maxLeft = Math.max(
      0,
      Number(element.scrollWidth || 0) - Number(element.clientWidth || 0)
    );
    element.scrollTop = Math.min(snapshot.scrollTop, maxTop);
    element.scrollLeft = Math.min(snapshot.scrollLeft, maxLeft);
  }
}

function stabilizeScrollAfterRender(panel, snapshots) {
  if (!snapshots.length) return;
  restoreScrollPositions(snapshots);
  globalThis.requestAnimationFrame?.(() => {
    // A touch may begin after the synchronous render but before this callback.
    // In that case the browser now owns scrollTop; never overwrite the user's
    // native pan or momentum movement with an older telemetry snapshot.
    if (touchInteractionActive(panel)) return;
    restoreScrollPositions(snapshots);
    globalThis.requestAnimationFrame?.(() => {
      if (touchInteractionActive(panel)) return;
      restoreScrollPositions(snapshots);
    });
  });
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
installHassRenderGuard(PanelClass);

if (!PanelClass.prototype.__epV038Installed) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV038Render() {
    const stableRuntime = stableRuntimeActive(this);
    if (!stableRuntime && interactionActive(this)) {
      this.__epV038RenderDeferred = true;
      return;
    }

    const rootBefore = this.shadowRoot;
    const reusableStrategy = rootBefore?.querySelector(".ep-v038-strategy") || null;
    const focusedProfile = rootBefore?.activeElement?.dataset?.epV038Profile || null;
    const preserveScroll = !stableRuntime && shouldPreserveScroll(this);
    const scrollSnapshots = preserveScroll ? captureScrollPositions(this) : [];
    if (stableRuntime) this.style.removeProperty("overflow-anchor");
    else if (preserveScroll) this.style.setProperty("overflow-anchor", "none");
    else this.style.removeProperty("overflow-anchor");

    if (this.__epV038HassRenderTimer) {
      window.clearTimeout(this.__epV038HassRenderTimer);
      this.__epV038HassRenderTimer = null;
    }

    previousRender.call(this);
    const root = this.shadowRoot;
    if (!root) return;

    ensureV038Styles(root);
    installV038DelegatedControls(this, root);
    if (!stableRuntime) installInteractionGuard(this, root);
    const strategy = installV038CustomerStrategy(this, root, reusableStrategy);
    synchronizeFlowDirections(this, root);
    updateVersion(root);
    if (!stableRuntime) stabilizeScrollAfterRender(this, scrollSnapshots);

    if (focusedProfile && strategy) {
      const focused = [...strategy.querySelectorAll("[data-ep-v038-profile]")].find(
        (button) => button.dataset.epV038Profile === focusedProfile
      );
      try {
        focused?.focus({ preventScroll: true });
      } catch (_err) {
        focused?.focus();
      }
    }
  };
  PanelClass.prototype.__epV038Installed = true;
}
