import "./gw-energy-pilot-v031.js?v=1.3.0-beta.4";

const PANEL_NAME = "gw-energypilot-panel";
const DASHBOARD_STORAGE_KEY = "gw_energypilot_dashboard_v008";
const WINDOW_STORAGE_KEY = "gw_energypilot_window_state_v031";
const FLOW_CARD_ID = "flow";
const FLOW_CARD_SIZES = new Set(["small", "medium", "large"]);

const CARD_LABELS = {
  flow: "Power overview",
  solar: "Solar",
  home: "Home",
  grid: "Grid",
  battery: "Battery",
  controller: "Controller",
  emhass: "EMHASS",
  thermal: "System health",
  diagnostics: "Support",
  "battery-price": "Battery · Plan · Price",
};

function language(panel) {
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function copy(panel) {
  return language(panel) === "nl"
    ? {
        controls: "Vensterbediening",
        close: "Kaart verbergen · herstellen via Dashboard layout",
        minimize: "Kaart inklappen / herstellen",
        maximize: "Kaart volle breedte / herstellen",
        flowSize: "Kaartbreedte",
        flowSmall: "Eén kaartkolom",
        flowMedium: "Twee kaartkolommen",
        flowLarge: "Volledige dashboardbreedte",
      }
    : {
        controls: "Window controls",
        close: "Hide card · restore via Dashboard layout",
        minimize: "Collapse / restore card",
        maximize: "Full width / restore card",
        flowSize: "Card width",
        flowSmall: "One card column",
        flowMedium: "Two card columns",
        flowLarge: "Full dashboard width",
      };
}

function readJson(key) {
  try {
    const value = JSON.parse(window.localStorage.getItem(key) || "{}");
    return value && typeof value === "object" ? value : {};
  } catch (_err) {
    return {};
  }
}

function writeJson(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch (_err) {
    // The dashboard remains usable if localStorage is unavailable.
  }
}

function hideCard(panel, card) {
  const id = card?.dataset?.epCard;
  if (!id) return;
  const prefs = readJson(DASHBOARD_STORAGE_KEY);
  prefs.hidden = prefs.hidden && typeof prefs.hidden === "object" ? prefs.hidden : {};
  prefs.hidden[id] = true;
  writeJson(DASHBOARD_STORAGE_KEY, prefs);
  card.hidden = true;
  panel._queueRender();
}

function windowState() {
  const state = readJson(WINDOW_STORAGE_KEY);
  state.collapsed = state.collapsed && typeof state.collapsed === "object" ? state.collapsed : {};
  state.maximized = state.maximized && typeof state.maximized === "object" ? state.maximized : {};
  return state;
}

function flowCardSize(state = windowState()) {
  const prefs = readJson(DASHBOARD_STORAGE_KEY);
  const stored = prefs.sizes?.[FLOW_CARD_ID];
  if (FLOW_CARD_SIZES.has(stored)) return stored;
  return state.maximized[FLOW_CARD_ID] ? "large" : "small";
}

function setFlowCardSize(panel, size) {
  if (!FLOW_CARD_SIZES.has(size)) return;
  const prefs = readJson(DASHBOARD_STORAGE_KEY);
  prefs.sizes = prefs.sizes && typeof prefs.sizes === "object" ? prefs.sizes : {};
  prefs.sizes[FLOW_CARD_ID] = size;
  writeJson(DASHBOARD_STORAGE_KEY, prefs);

  // The former green-dot state represented only normal/full width. Once an
  // explicit S/M/L choice exists it must not compete with that saved width.
  const state = windowState();
  state.maximized[FLOW_CARD_ID] = false;
  writeJson(WINDOW_STORAGE_KEY, state);
  panel._queueRender();
}

function toggleCollapsed(panel, id) {
  const state = windowState();
  state.collapsed[id] = !state.collapsed[id];
  if (state.collapsed[id]) state.maximized[id] = false;
  writeJson(WINDOW_STORAGE_KEY, state);
  panel._queueRender();
}

function toggleMaximized(panel, id) {
  if (id === FLOW_CARD_ID) {
    setFlowCardSize(panel, flowCardSize() === "large" ? "small" : "large");
    return;
  }
  const state = windowState();
  state.maximized[id] = !state.maximized[id];
  if (state.maximized[id]) state.collapsed[id] = false;
  writeJson(WINDOW_STORAGE_KEY, state);
  panel._queueRender();
}

function cardLabel(card) {
  const id = card?.dataset?.epCard || "";
  if (CARD_LABELS[id]) return CARD_LABELS[id];
  const text =
    card?.querySelector("h2")?.textContent ||
    card?.querySelector(".card-kicker")?.textContent ||
    card?.querySelector(".ep-flow-title")?.textContent ||
    id;
  return String(text || "Card").trim();
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v031-window-controls-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v031-window-controls-style";
  style.textContent = `
    .ep-dashboard-layout > [data-ep-card] { position:relative; }
    .ep-v031-card-windowbar {
      position:relative; z-index:70; display:flex; align-items:center; gap:7px;
      min-height:16px; margin:-3px 0 10px; user-select:none;
    }
    .ep-v031-card-windowlabel {
      min-width:0; margin-left:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
      color:#66879a; font-size:8px; font-weight:760; letter-spacing:.025em; opacity:.72;
    }
    .ep-v031-card-window-controls { display:flex; align-items:center; gap:6px; flex:0 0 auto; }
    .ep-v031-window-dot {
      appearance:none; position:relative; width:14px; height:14px; min-width:14px; padding:0;
      display:grid; place-items:center; overflow:hidden;
      border:1px solid rgba(77,178,220,.22); border-radius:50%; cursor:pointer;
      background:linear-gradient(145deg,rgba(14,48,76,.96),rgba(5,25,45,.98));
      box-shadow:inset 0 1px 0 rgba(184,237,255,.10),0 2px 7px rgba(0,0,0,.24);
      color:#061b2c; font:900 9px/1 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",sans-serif;
      transition:transform .12s ease,border-color .12s ease,box-shadow .12s ease,background .12s ease;
    }
    .ep-v031-window-dot::before {
      content:""; width:7px; height:7px; border-radius:50%;
      box-shadow:0 0 8px currentColor; opacity:.90;
    }
    .ep-v031-window-dot.close { color:#d86f6b; }
    .ep-v031-window-dot.minimize { color:#d1aa58; }
    .ep-v031-window-dot.maximize { color:#2bc99b; }
    .ep-v031-window-dot.close::before { background:#d86f6b; }
    .ep-v031-window-dot.minimize::before { background:#d1aa58; }
    .ep-v031-window-dot.maximize::before { background:#2bc99b; }
    .ep-v031-window-dot:hover {
      transform:translateY(-1px);
      border-color:rgba(96,215,244,.42);
      background:linear-gradient(145deg,rgba(18,58,91,.98),rgba(7,31,54,.99));
      box-shadow:inset 0 1px 0 rgba(191,241,255,.14),0 0 10px rgba(25,217,255,.10),0 3px 8px rgba(0,0,0,.25);
    }
    .ep-v031-window-dot span {
      position:absolute; inset:0; display:grid; place-items:center;
      opacity:0; pointer-events:none; color:rgba(227,248,255,.90); text-shadow:0 1px 2px rgba(0,0,0,.55);
      transition:opacity .12s ease;
    }
    .ep-v031-card-window-controls:hover .ep-v031-window-dot::before,
    .ep-v031-window-dot:focus-visible::before { opacity:.35; }
    .ep-v031-card-window-controls:hover .ep-v031-window-dot span,
    .ep-v031-window-dot:focus-visible span { opacity:.90; }
    .ep-v031-window-dot:focus-visible { outline:2px solid rgba(91,224,249,.70); outline-offset:2px; }
    .ep-dashboard-layout > .ep-v031-card-collapsed {
      min-height:0!important; height:auto!important; align-self:start!important; padding-bottom:11px!important;
    }
    .ep-dashboard-layout > .ep-v031-card-collapsed > :not(.ep-v031-card-windowbar) { display:none!important; }
    .ep-dashboard-layout > .ep-v031-card-collapsed .ep-v031-card-windowbar { margin-bottom:0; }
    .ep-dashboard-layout > .ep-v031-card-maximized { grid-column:1/-1!important; }
    .ep-dashboard-layout > [data-ep-card="flow"].ep-v031-flow-size-small {
      grid-column:span 1!important;
    }
    .ep-dashboard-layout > [data-ep-card="flow"].ep-v031-flow-size-medium {
      grid-column:span 2!important;
    }
    .ep-dashboard-layout > [data-ep-card="flow"].ep-v031-flow-size-large {
      grid-column:1/-1!important;
    }
    .ep-v031-flow-size-control {
      display:flex; align-items:center; flex:0 0 auto; margin-left:auto; padding:2px;
      border:1px solid rgba(255,255,255,.075); border-radius:999px;
      background:rgba(1,12,28,.42); box-shadow:inset 0 1px 8px rgba(0,0,0,.20);
    }
    .ep-v031-flow-size-control button {
      appearance:none; width:27px; height:24px; padding:0; border:0; border-radius:999px;
      background:transparent; color:#7793a7; cursor:pointer;
      font:700 9px -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",sans-serif;
    }
    .ep-v031-flow-size-control button.active {
      color:#f0fbff; background:rgba(255,255,255,.13);
      box-shadow:0 1px 8px rgba(0,0,0,.25),inset 0 1px 0 rgba(255,255,255,.12);
    }
    .ep-dashboard-layout.ep-editing .ep-v031-card-windowbar { cursor:default; }
    @media(max-width:720px) {
      .ep-v031-card-windowbar { margin-top:-2px; }
      .ep-v031-card-maximized { grid-column:1!important; }
      .ep-dashboard-layout > [data-ep-card="flow"][class*="ep-v031-flow-size-"] {
        grid-column:1!important;
      }
    }
    @media(pointer:coarse) {
      .ep-v031-flow-size-control button {
        width:44px; min-width:44px; height:44px; min-height:44px;
      }
    }
  `;
  root.appendChild(style);
}

function createWindowBar(panel, card, id) {
  const labels = copy(panel);
  const size = id === FLOW_CARD_ID ? flowCardSize() : null;
  const bar = document.createElement("div");
  bar.className = "ep-v031-card-windowbar";
  bar.innerHTML = `
    <div class="ep-v031-card-window-controls" role="group" aria-label="${panel._escape(labels.controls)}">
      <button type="button" draggable="false" class="ep-v031-window-dot close" data-window-action="close" title="${panel._escape(labels.close)}" aria-label="${panel._escape(labels.close)}"><span>×</span></button>
      <button type="button" draggable="false" class="ep-v031-window-dot minimize" data-window-action="minimize" title="${panel._escape(labels.minimize)}" aria-label="${panel._escape(labels.minimize)}"><span>−</span></button>
      <button type="button" draggable="false" class="ep-v031-window-dot maximize" data-window-action="maximize" title="${panel._escape(labels.maximize)}" aria-label="${panel._escape(labels.maximize)}"><span>+</span></button>
    </div>
    <span class="ep-v031-card-windowlabel">${panel._escape(cardLabel(card))}</span>
    ${size ? `<div class="ep-v031-flow-size-control" role="group" aria-label="${panel._escape(labels.flowSize)}">
      <button type="button" data-flow-size="small" class="${size === "small" ? "active" : ""}" title="${panel._escape(labels.flowSmall)}" aria-pressed="${size === "small"}">S</button>
      <button type="button" data-flow-size="medium" class="${size === "medium" ? "active" : ""}" title="${panel._escape(labels.flowMedium)}" aria-pressed="${size === "medium"}">M</button>
      <button type="button" data-flow-size="large" class="${size === "large" ? "active" : ""}" title="${panel._escape(labels.flowLarge)}" aria-pressed="${size === "large"}">L</button>
    </div>` : ""}`;

  bar.addEventListener("pointerdown", (event) => event.stopPropagation());
  bar.addEventListener("dragstart", (event) => event.preventDefault());
  bar.querySelector('[data-window-action="close"]')?.addEventListener("click", (event) => {
    event.stopPropagation();
    hideCard(panel, card);
  });
  bar.querySelector('[data-window-action="minimize"]')?.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleCollapsed(panel, id);
  });
  bar.querySelector('[data-window-action="maximize"]')?.addEventListener("click", (event) => {
    event.stopPropagation();
    toggleMaximized(panel, id);
  });
  bar.querySelectorAll("[data-flow-size]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      setFlowCardSize(panel, button.dataset.flowSize);
    });
  });
  return bar;
}

function installWindowControls(panel, root) {
  const layout = root.querySelector(".ep-dashboard-layout");
  if (!layout) return;
  const state = windowState();

  for (const card of layout.querySelectorAll(":scope > [data-ep-card]")) {
    const id = card.dataset.epCard;
    if (!id) continue;

    if (card.dataset.epFixedCard === "true") {
      card.querySelectorAll(":scope > .ep-v031-card-windowbar").forEach(
        (node) => node.remove()
      );
      card.classList.remove("ep-v031-card-collapsed", "ep-v031-card-maximized");
      continue;
    }

    // Remove the earlier Battery-only implementation so v0.31 has one
    // consistent control surface for every dashboard card.
    card.querySelectorAll(".ep-v028-window-controls").forEach((node) => node.remove());

    card.classList.toggle("ep-v031-card-collapsed", Boolean(state.collapsed[id]));
    card.classList.toggle("ep-v031-card-maximized", Boolean(state.maximized[id]));
    if (id === FLOW_CARD_ID) {
      const size = flowCardSize(state);
      for (const candidate of FLOW_CARD_SIZES) {
        card.classList.toggle(`ep-v031-flow-size-${candidate}`, candidate === size);
      }
    }

    if (!card.querySelector(":scope > .ep-v031-card-windowbar")) {
      card.prepend(createWindowBar(panel, card, id));
    }
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV031WindowControlsRender() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;
  ensureStyles(root);
  installWindowControls(this, root);
};
