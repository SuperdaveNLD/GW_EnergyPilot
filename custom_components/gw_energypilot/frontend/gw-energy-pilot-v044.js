import "./gw-energy-pilot-v043.js?v=0.47-custom-battery1";

const VERSION = "0.44";
const PANEL_NAME = "gw-energypilot-panel";
const OPTIMIZE_MARKER = "epV044StableOptimize";
const FLOATING_STYLE_ID = "ep-v044-floating-optimize";
const RUNNING_STATES = new Set([
  "preparing",
  "reading_history",
  "getting_prices",
  "optimizing",
  "publishing",
  "waiting_for_output",
]);

const COPY = Object.freeze({
  en: Object.freeze({
    optimize: "Optimize now",
    optimizing: "Optimizing…",
    unavailable: "not available",
    scheduleOn: "Automatic schedule enabled",
    scheduleOff: "Manual only",
    nordPool: "Nord Pool runtime prices",
    emhassPrices: "EMHASS price configuration",
    priceTriggerOn: "price refresh trigger on",
    priceTriggerOff: "price refresh trigger off",
    lastSuccess: "Last success",
    actionFailed: "EnergyPilot optimization failed",
  }),
  nl: Object.freeze({
    optimize: "Nu optimaliseren",
    optimizing: "Optimaliseren…",
    unavailable: "niet beschikbaar",
    scheduleOn: "Automatische planning ingeschakeld",
    scheduleOff: "Alleen handmatig",
    nordPool: "Nord Pool-runtimeprijzen",
    emhassPrices: "EMHASS-prijsconfiguratie",
    priceTriggerOn: "prijsverversing actief",
    priceTriggerOff: "prijsverversing uit",
    lastSuccess: "Laatste succes",
    actionFailed: "EnergyPilot-optimalisatie mislukt",
  }),
});

const FLOATING_OPTIMIZE_CSS = `
  :host main[data-ep-v041-stable-dom="1"] {
    padding-bottom: calc(96px + env(safe-area-inset-bottom)) !important;
  }
  :host .ep-optimize-now[data-ep-v044-stable-optimize="1"] {
    position: fixed !important;
    z-index: 9000;
    right: calc(16px + env(safe-area-inset-right));
    bottom: calc(16px + env(safe-area-inset-bottom));
    min-width: 44px;
    min-height: 44px;
    max-width: calc(100vw - 32px - env(safe-area-inset-left) - env(safe-area-inset-right));
    padding: 11px 16px;
    white-space: nowrap;
  }
  @media (max-width: 720px) {
    :host .ep-optimize-now[data-ep-v044-stable-optimize="1"] {
      right: calc(12px + env(safe-area-inset-right));
      bottom: calc(12px + env(safe-area-inset-bottom));
      max-width: calc(100vw - 24px - env(safe-area-inset-left) - env(safe-area-inset-right));
    }
  }
`;

function language(panel) {
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function copy(panel) {
  return COPY[language(panel)] || COPY.en;
}

function formatLastSuccess(panel, value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  const locale = panel?._hass?.locale?.language || panel?._hass?.language || undefined;
  return new Intl.DateTimeFormat(locale, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

function orchestratorTone(status) {
  if (status === "ready" || status === "scheduled") return "ok";
  if (status === "manual_only") return "info";
  if (RUNNING_STATES.has(status)) return "running";
  if (
    status === "legacy_yaml_detected" ||
    status.startsWith("error") ||
    status.startsWith("waiting") ||
    status === "stale_output"
  ) {
    return "error";
  }
  return "info";
}

function optimizeSnapshot(panel) {
  const entityId = panel?._entityId?.("optimize_now") || null;
  const state = entityId ? panel?._state?.(entityId) : null;
  return {
    entityId,
    attributes: state?.attributes || {},
  };
}

function ensureFloatingOptimizeStyle(root) {
  if (!root || root.querySelector(`#${FLOATING_STYLE_ID}`)) return;
  const style = document.createElement("style");
  style.id = FLOATING_STYLE_ID;
  style.textContent = FLOATING_OPTIMIZE_CSS;
  root.appendChild(style);
}

function patchOrchestrator(panel, root, attributes) {
  const block = root?.querySelector(".ep-v010-orchestrator");
  if (!block) return;

  const text = copy(panel);
  const status = String(attributes.orchestrator_status || text.unavailable);
  block.classList.remove("ok", "info", "running", "error");
  block.classList.add(orchestratorTone(status));

  const title = block.querySelector("strong");
  if (title) title.textContent = `EnergyPilot orchestrator · ${status}`;

  const detail = block.querySelector("small");
  if (!detail) return;
  const schedule = attributes.automatic_schedule ? text.scheduleOn : text.scheduleOff;
  const priceSource =
    attributes.price_runtime_source === "nordpool" ? text.nordPool : text.emhassPrices;
  const priceTrigger = attributes.price_refresh_automation
    ? text.priceTriggerOn
    : text.priceTriggerOff;
  const lastSuccess = formatLastSuccess(panel, attributes.last_success);
  const error = attributes.last_error ? ` · ${attributes.last_error}` : "";
  detail.textContent =
    `${schedule} · ${priceSource} · ${priceTrigger} · ` +
    `${text.lastSuccess}: ${lastSuccess}${error}`;
}

function installStableOptimizeButton(panel, root) {
  let button = root?.querySelector(".ep-optimize-now");
  if (!button || button.dataset[OPTIMIZE_MARKER] === "1") return button;

  // The inherited v0.10 listener requests a complete dashboard render after
  // every completed optimization. Replace only that listener and preserve the
  // established entity/service contract so the touched DOM remains connected.
  const replacement = button.cloneNode(true);
  replacement.dataset[OPTIMIZE_MARKER] = "1";
  button.replaceWith(replacement);
  button = replacement;

  // Keep one canonical action outside the optional EMHASS card so layout
  // visibility preferences cannot hide it. Fixed positioning then makes the
  // same stable node reachable throughout native dashboard scrolling.
  const main = root.querySelector("main");
  if (main) main.appendChild(button);

  button.addEventListener("click", async (event) => {
    event.preventDefault();
    const pressedButton = event.currentTarget;
    const entityId = panel?._entityId?.("optimize_now");
    if (
      !(pressedButton instanceof HTMLButtonElement) ||
      !entityId ||
      panel.__epV044OptimizePending ||
      pressedButton.disabled
    ) {
      return;
    }

    panel.__epV044OptimizePending = true;
    patchOptimizeUi(panel);
    try {
      await panel._hass.callService("button", "press", { entity_id: entityId });
    } catch (err) {
      console.error("GW EnergyPilot optimization failed", err);
      const message = err?.message || String(err);
      window.alert(`${copy(panel).actionFailed}: ${message}`);
    } finally {
      panel.__epV044OptimizePending = false;
      patchOptimizeUi(panel);
    }
  });

  return button;
}

function patchOptimizeUi(panel) {
  const root = panel?.shadowRoot;
  if (!root) return;

  ensureFloatingOptimizeStyle(root);
  const snapshot = optimizeSnapshot(panel);
  const button = installStableOptimizeButton(panel, root);
  const status = String(snapshot.attributes.orchestrator_status || "");
  const busy = Boolean(panel.__epV044OptimizePending) || RUNNING_STATES.has(status);
  if (button) {
    button.disabled = !snapshot.entityId || busy;
    button.textContent = busy ? copy(panel).optimizing : copy(panel).optimize;
    button.setAttribute("aria-busy", busy ? "true" : "false");
  }
  patchOrchestrator(panel, root, snapshot.attributes);
}

function patchReleaseVersion(panel) {
  const root = panel?.shadowRoot;
  if (!root) return;
  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (PanelClass && !PanelClass.prototype.__epV044Installed) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV044OptimizeStableRender(...args) {
    const result = previousRender.apply(this, args);
    patchOptimizeUi(this);
    patchReleaseVersion(this);
    return result;
  };

  const descriptor = Object.getOwnPropertyDescriptor(PanelClass.prototype, "hass");
  if (descriptor?.set) {
    Object.defineProperty(PanelClass.prototype, "hass", {
      configurable: descriptor.configurable,
      enumerable: descriptor.enumerable,
      get() {
        return descriptor.get ? descriptor.get.call(this) : this._hass;
      },
      set(value) {
        descriptor.set.call(this, value);
        patchOptimizeUi(this);
        patchReleaseVersion(this);
      },
    });
  }

  PanelClass.prototype.__epV044Installed = true;
}
