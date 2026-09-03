const CLICK_FALLBACK_MS = 120;
const LATE_CLICK_WINDOW_MS = 1000;
const MOVE_THRESHOLD_PX = 12;
const TOUCH_POINTER_TYPE = "touch";
const POINTER_EVENTS = Object.freeze([
  "pointerdown",
  "pointermove",
  "pointerup",
  "pointercancel",
]);

const installations = new WeakMap();

function now() {
  return globalThis.performance?.now?.() ?? Date.now();
}

function isDisabled(element) {
  return Boolean(
    element?.disabled ||
    element?.getAttribute?.("aria-disabled") === "true" ||
    !element?.isConnected
  );
}

function labelControl(label, includeDisabled = false) {
  const control = label?.control || label?.querySelector?.(
    'input[type="checkbox"], input[type="radio"]'
  );
  return control instanceof HTMLInputElement && (includeDisabled || !isDisabled(control))
    ? control
    : null;
}

function nativeActivationElement(node, includeDisabled = false) {
  if (node instanceof HTMLButtonElement) {
    return includeDisabled || !isDisabled(node) ? node : null;
  }
  if (node instanceof HTMLInputElement) {
    const type = String(node.type || "").toLowerCase();
    return ["button", "checkbox", "radio", "reset", "submit"].includes(type) &&
      (includeDisabled || !isDisabled(node))
      ? node
      : null;
  }
  if (node instanceof HTMLLabelElement) return labelControl(node, includeDisabled);
  if (node instanceof HTMLElement && node.tagName === "SUMMARY") {
    return includeDisabled || !isDisabled(node) ? node : null;
  }
  if (
    node instanceof HTMLElement &&
    node.getAttribute("role") === "button" &&
    typeof node.click === "function"
  ) {
    return includeDisabled || !isDisabled(node) ? node : null;
  }
  return null;
}

function activationFromEvent(event, root, includeDisabled = false) {
  const path = typeof event.composedPath === "function" ? event.composedPath() : [];
  for (const node of path) {
    if (node instanceof Element && (
      node.hasAttribute("data-beta-control") ||
      node.getAttribute("data-ep-touch-click-fallback") === "off"
    )) {
      return null;
    }
  }
  for (const node of path) {
    const activation = nativeActivationElement(node, includeDisabled);
    if (activation) return activation;
    if (node === root) break;
  }
  return null;
}

function targetName(element) {
  const semantic = [
    element?.getAttribute?.("data-control-id"),
    element?.getAttribute?.("data-action"),
    element?.getAttribute?.("data-settings-tab"),
    element?.getAttribute?.("data-window-action"),
    element?.id,
    element?.getAttribute?.("aria-label"),
  ].find((value) => String(value || "").trim());
  if (semantic) return String(semantic).trim().slice(0, 80);
  const className = typeof element?.className === "string"
    ? element.className.trim().split(/\s+/).filter(Boolean).slice(0, 2).join(".")
    : "";
  return `${element?.tagName?.toLowerCase?.() || "control"}${className ? `.${className}` : ""}`;
}

function blankStats() {
  return {
    touch_pointerdown: 0,
    touch_pointerup: 0,
    touch_pointercancel: 0,
    moved: 0,
    native_clicks: 0,
    fallback_clicks: 0,
    late_clicks_suppressed: 0,
    stale_fallbacks: 0,
  };
}

function installState(panel, root) {
  const pointers = new Map();
  const pendingByElement = new Map();
  const recentFallbacks = new WeakMap();
  const stats = blankStats();
  const targets = new Map();
  let sequence = 0;
  let internalActivation = null;

  const record = (type, element, details = {}) => {
    const name = targetName(element);
    const targetStats = targets.get(name) || {
      native_clicks: 0,
      fallback_clicks: 0,
      late_clicks_suppressed: 0,
    };
    if (Object.hasOwn(targetStats, type)) targetStats[type] += 1;
    targets.set(name, targetStats);
    globalThis.__epRecordEnergyPilotControlTrace?.(panel, `touch-fallback-${type}`, {
      target: name,
      ...details,
    });
  };

  const consumeLateClick = (event, element) => {
    const recent = recentFallbacks.get(element);
    const physicalClick = event.isTrusted || Number(event.detail) > 0;
    if (
      !physicalClick ||
      !recent ||
      recent.count <= 0 ||
      now() - recent.at > LATE_CLICK_WINDOW_MS
    ) {
      return false;
    }
    recent.count -= 1;
    if (recent.count <= 0) recentFallbacks.delete(element);
    stats.late_clicks_suppressed += 1;
    record("late_clicks_suppressed", element);
    return true;
  };

  const guardDisconnectedLateClick = (element) => {
    let timer = null;
    const remove = () => {
      element.removeEventListener("click", guard, { capture: true });
      globalThis.clearTimeout(timer);
    };
    const guard = (event) => {
      if (element === internalActivation || element.isConnected) return;
      if (!consumeLateClick(event, element)) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      remove();
    };
    element.addEventListener("click", guard, { capture: true });
    timer = globalThis.setTimeout(remove, LATE_CLICK_WINDOW_MS);
  };

  const removePending = (element, pending) => {
    const queue = pendingByElement.get(element);
    if (!queue) return;
    const index = queue.indexOf(pending);
    if (index >= 0) queue.splice(index, 1);
    if (queue.length === 0) pendingByElement.delete(element);
  };

  const scheduleFallback = (element, pointerId) => {
    const pending = { id: ++sequence, pointerId, timer: null };
    const queue = pendingByElement.get(element) || [];
    queue.push(pending);
    pendingByElement.set(element, queue);
    pending.timer = globalThis.setTimeout(() => {
      removePending(element, pending);
      if (isDisabled(element)) {
        stats.stale_fallbacks += 1;
        record("stale", element, { pointerId });
        return;
      }
      const previous = recentFallbacks.get(element);
      recentFallbacks.set(element, {
        at: now(),
        count: (previous && now() - previous.at <= LATE_CLICK_WINDOW_MS
          ? previous.count
          : 0) + 1,
      });
      guardDisconnectedLateClick(element);
      stats.fallback_clicks += 1;
      record("fallback_clicks", element, { pointerId });
      internalActivation = element;
      try {
        element.click();
      } finally {
        internalActivation = null;
      }
    }, CLICK_FALLBACK_MS);
  };

  const onPointer = (event) => {
    const element = activationFromEvent(event, root);
    if (event.type === "pointerdown" && element && event.pointerType !== TOUCH_POINTER_TYPE) {
      // A fresh mouse/pen action is never the delayed click from an earlier touch.
      recentFallbacks.delete(element);
      return;
    }
    if (event.pointerType !== TOUCH_POINTER_TYPE || event.isPrimary === false) return;

    if (event.type === "pointerdown") {
      if (!element || event.button > 0) return;
      stats.touch_pointerdown += 1;
      pointers.set(event.pointerId, {
        element,
        x: Number(event.clientX) || 0,
        y: Number(event.clientY) || 0,
        moved: false,
      });
      return;
    }

    const pointer = pointers.get(event.pointerId);
    if (!pointer) return;
    if (event.type === "pointermove") {
      const distance = Math.hypot(
        (Number(event.clientX) || 0) - pointer.x,
        (Number(event.clientY) || 0) - pointer.y,
      );
      if (!pointer.moved && distance > MOVE_THRESHOLD_PX) {
        pointer.moved = true;
        stats.moved += 1;
      }
      return;
    }

    pointers.delete(event.pointerId);
    if (event.type === "pointercancel") {
      stats.touch_pointercancel += 1;
      return;
    }
    if (event.type !== "pointerup") return;
    stats.touch_pointerup += 1;
    if (pointer.moved || element !== pointer.element || isDisabled(pointer.element)) return;
    scheduleFallback(pointer.element, event.pointerId);
  };

  const onClick = (event) => {
    const element = activationFromEvent(event, root, true);
    if (!element || element === internalActivation) return;

    const queue = pendingByElement.get(element);
    if (queue?.length) {
      const pending = queue.shift();
      globalThis.clearTimeout(pending.timer);
      if (queue.length === 0) pendingByElement.delete(element);
      stats.native_clicks += 1;
      record("native_clicks", element, { pointerId: pending.pointerId });
      return;
    }

    if (consumeLateClick(event, element)) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  };

  for (const eventName of POINTER_EVENTS) {
    root.addEventListener(eventName, onPointer, { capture: true, passive: true });
  }
  root.addEventListener("click", onClick, { capture: true });

  const api = Object.freeze({
    snapshot: () => ({
      enabled: true,
      click_fallback_ms: CLICK_FALLBACK_MS,
      late_click_window_ms: LATE_CLICK_WINDOW_MS,
      move_threshold_px: MOVE_THRESHOLD_PX,
      metrics: { ...stats },
      targets: Object.fromEntries(
        [...targets.entries()].map(([key, value]) => [key, { ...value }])
      ),
    }),
    reset: () => {
      for (const key of Object.keys(stats)) stats[key] = 0;
      targets.clear();
    },
  });
  return { api, onPointer, onClick };
}

export function installEnergyPilotTouchClickFallback(panel, root = panel?.shadowRoot) {
  if (!panel || !root) return null;
  let state = installations.get(root);
  if (!state) {
    state = installState(panel, root);
    installations.set(root, state);
  }
  panel.touchClickFallback = state.api;
  globalThis.__epTouchClickFallback = state.api;
  return state.api;
}

export const ENERGY_PILOT_TOUCH_CLICK_FALLBACK = Object.freeze({
  clickFallbackMs: CLICK_FALLBACK_MS,
  lateClickWindowMs: LATE_CLICK_WINDOW_MS,
  moveThresholdPx: MOVE_THRESHOLD_PX,
});
