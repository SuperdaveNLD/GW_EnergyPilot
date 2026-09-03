import "./gw-energy-pilot-v011-support.js?v=1.2.0-stable1";

const VERSION = "0.12";
const PANEL_NAME = "gw-energypilot-panel";
const STORAGE_KEY = "gw_energypilot_dashboard_v008";
const PARTICLE_DURATION_SECONDS = 4.8;

function dashboardPrefs() {
  try {
    const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "{}");
    return {
      ...stored,
      order: Array.isArray(stored.order) ? stored.order : [],
      hidden: stored.hidden && typeof stored.hidden === "object" ? stored.hidden : {},
    };
  } catch (_err) {
    return { order: [], hidden: {} };
  }
}

function saveDashboardPrefs(prefs) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch (_err) {
    // Layout remains usable when browser storage is unavailable.
  }
}

function relevantStateSignature(panel, hass) {
  const ids = new Set(Object.values(panel._entityMap || {}));
  [
    "sensor.p_batt_forecast",
    "sensor.optim_status",
    "sensor.soc_batt_forecast",
    "sensor.p_load_forecast",
    "sensor.p_pv_forecast",
  ].forEach((entityId) => ids.add(entityId));

  const stateSignature = [...ids]
    .sort()
    .map((entityId) => {
      const state = hass?.states?.[entityId];
      return `${entityId}:${state?.state || ""}:${state?.last_updated || ""}`;
    })
    .join("|");

  return `${hass?.config?.unit_system?.temperature || ""}|${stateSignature}`;
}

function installSelectiveHassRendering(PanelClass) {
  const descriptor = Object.getOwnPropertyDescriptor(PanelClass.prototype, "hass");
  if (!descriptor || PanelClass.prototype.__epV012HassPatched) return;

  Object.defineProperty(PanelClass.prototype, "hass", {
    configurable: descriptor.configurable,
    enumerable: descriptor.enumerable,
    get: descriptor.get,
    set(value) {
      this._hass = value;
      if (!this._registryLoaded && !this._registryLoading) {
        this._loadRegistry();
      }

      const signature = relevantStateSignature(this, value);
      if (!this._registryLoaded || signature !== this.__epV012StateSignature) {
        this.__epV012StateSignature = signature;
        this._queueRender();
      }
    },
  });
  PanelClass.prototype.__epV012HassPatched = true;
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v012-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v012-style";
  style.textContent = `
    /* Stable controls: no lift/scale animation while the dashboard updates. */
    .ep-optimize-now,
    .ep-optimize-now:hover:not(:disabled),
    .ep-battery-action,
    .ep-battery-action:hover:not(:disabled) {
      transform: none !important;
      transition: border-color .12s linear, color .12s linear, background-color .12s linear !important;
    }
    .ep-optimize-now:hover:not(:disabled) {
      border-color: rgba(45, 244, 197, .48) !important;
      background: linear-gradient(135deg, rgba(20, 116, 164, .42), rgba(20, 190, 142, .30)) !important;
    }

    /* Full-track particles. Position, rather than transform percentages, is
       animated because transform percentages are relative to the 6 px ball. */
    .ep-v011-particles span {
      transform: none !important;
      opacity: .88 !important;
      animation-duration: ${PARTICLE_DURATION_SECONDS}s !important;
      animation-timing-function: linear !important;
      animation-iteration-count: infinite !important;
      will-change: left, top !important;
    }
    .ep-link-pv .ep-v011-particles span,
    .ep-link-grid .ep-v011-particles span {
      animation-name: epV012ParticleH !important;
    }
    .ep-link-house .ep-v011-particles span,
    .ep-link-battery .ep-v011-particles span {
      animation-name: epV012ParticleV !important;
    }
    .ep-flow-live span {
      animation: none !important;
      opacity: .9 !important;
    }
    @keyframes epV012ParticleH {
      from { left: -8px; opacity: .88; }
      to { left: calc(100% + 2px); opacity: .88; }
    }
    @keyframes epV012ParticleV {
      from { top: -8px; opacity: .88; }
      to { top: calc(100% + 2px); opacity: .88; }
    }

    .ep-v012-price-warning {
      margin-top: 8px;
      padding: 8px 10px;
      border: 1px solid rgba(255, 181, 76, .22);
      border-radius: 10px;
      color: #e8c98e;
      background: rgba(109, 67, 9, .15);
      font-size: 9px;
      line-height: 1.4;
    }
  `;
  root.appendChild(style);
}

function synchronizeParticles(root) {
  const absolutePhase = (Date.now() / 1000) % PARTICLE_DURATION_SECONDS;
  for (const link of root.querySelectorAll(".ep-flow-link")) {
    const holder = link.querySelector(".ep-v011-particles");
    if (!holder) continue;

    while (holder.children.length < 4) {
      holder.appendChild(document.createElement("span"));
    }

    const particles = [...holder.querySelectorAll("span")];
    particles.forEach((particle, index) => {
      const stagger = (index * PARTICLE_DURATION_SECONDS) / particles.length;
      const phase = (absolutePhase + stagger) % PARTICLE_DURATION_SECONDS;
      particle.style.animationDelay = `${-phase}s`;
    });
  }
}

function calculatedHomePower(panel) {
  const pv = panel._numberByKey("pv_total_power");
  const grid = panel._numberByKey("meter_total_power_fast");
  const battery = panel._numberByKey("battery_power");
  if (![pv, grid, battery].every(Number.isFinite)) return null;

  const value = pv - grid + battery;
  return Number.isFinite(value) && value >= 0 && value <= 30000 ? value : null;
}

function updateHomeCard(panel, root) {
  const calculated = calculatedHomePower(panel);
  const raw = panel._numberByKey("total_load_power");
  const home = Number.isFinite(calculated) ? calculated : raw;
  if (!Number.isFinite(home)) return;

  const card = root.querySelector(".energy-card.home");
  if (card) {
    const hero = card.querySelector(".hero-value");
    const sub = card.querySelector(".hero-sub");
    if (hero) hero.textContent = panel._formatPower(home);
    if (sub) sub.textContent = Number.isFinite(calculated)
      ? "Calculated house load · PV - grid + battery"
      : "House load · GoodWe register 35172";

    const rows = card.querySelectorAll(".balance-row");
    if (rows[0]) {
      const label = rows[0].querySelector("span");
      const value = rows[0].querySelector("strong");
      if (label) label.textContent = "GoodWe register 35172";
      if (value) value.textContent = panel._formatPower(raw);
    }
    if (rows[1]) {
      const label = rows[1].querySelector("span");
      const value = rows[1].querySelector("strong");
      if (label) label.textContent = "Power balance";
      if (value) value.textContent = panel._formatPower(calculated);
    }
  }

  const flowValue = root.querySelector(".ep-flow-house .ep-flow-node-value");
  const flowSub = root.querySelector(".ep-flow-house .ep-flow-node-sub");
  if (flowValue) flowValue.textContent = panel._formatPower(home);
  if (flowSub) flowSub.textContent = Number.isFinite(calculated)
    ? "Calculated house load"
    : "GoodWe load register";

  const link = root.querySelector(".ep-link-house");
  if (link) {
    link.classList.remove("idle", "inbound", "outbound");
    link.classList.add(home > 50 ? "outbound" : "idle");
  }
}

function synchronizeDiagnosticsVisibility(panel, root) {
  const layout = root.querySelector(".ep-dashboard-layout");
  const diagnostics = layout?.querySelector('[data-ep-card="diagnostics"]');
  if (!layout || !diagnostics) return;

  const prefs = dashboardPrefs();
  if (!prefs.order.includes("diagnostics")) prefs.order.push("diagnostics");
  diagnostics.hidden = Boolean(prefs.hidden.diagnostics);

  for (const id of prefs.order) {
    const card = layout.querySelector(`[data-ep-card="${id}"]`);
    if (card) layout.appendChild(card);
  }
  saveDashboardPrefs(prefs);

  const menu = root.querySelector(".ep-layout-menu");
  if (!menu || menu.querySelector('[data-ep-visible="diagnostics"]')) return;

  const row = document.createElement("label");
  row.className = "ep-menu-row";
  row.innerHTML = `<span>Diagnostics</span><input type="checkbox" data-ep-visible="diagnostics" ${prefs.hidden.diagnostics ? "" : "checked"} />`;
  const reset = menu.querySelector(".ep-menu-reset");
  if (reset) menu.insertBefore(row, reset);
  else menu.appendChild(row);

  row.querySelector("input")?.addEventListener("change", (event) => {
    const next = dashboardPrefs();
    next.hidden.diagnostics = !event.currentTarget.checked;
    if (!next.order.includes("diagnostics")) next.order.push("diagnostics");
    saveDashboardPrefs(next);
    panel._queueRender();
  });
}

function showPriceSourceWarning(panel, root) {
  const optimizeId = panel._entityId("optimize_now");
  const attrs = optimizeId ? panel._state(optimizeId)?.attributes || {} : {};
  if (attrs.price_runtime_source !== "missing") return;

  const card = root.querySelector(".panel-card.emhass");
  if (!card || card.querySelector(".ep-v012-price-warning")) return;
  card.insertAdjacentHTML(
    "beforeend",
    `<div class="ep-v012-price-warning">Runtime Nord Pool pricing is enabled, but no supported official service or raw_today/raw_tomorrow price sensor was found. Configure a price source or disable runtime pricing so EMHASS uses its own price configuration.</div>`
  );
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
installSelectiveHassRendering(PanelClass);

const previousRender = PanelClass.prototype._render;
PanelClass.prototype._render = function energyPilotV012Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  ensureStyles(root);
  synchronizeParticles(root);
  updateHomeCard(this, root);
  synchronizeDiagnosticsVisibility(this, root);
  showPriceSourceWarning(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION}`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION}`;
};
