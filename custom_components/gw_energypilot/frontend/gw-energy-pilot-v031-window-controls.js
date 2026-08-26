import "./gw-energy-pilot-v031.js?v=0.31-debug2";

const PANEL_NAME = "gw-energypilot-panel";
const DASHBOARD_STORAGE_KEY = "gw_energypilot_dashboard_v008";
const WINDOW_STORAGE_KEY = "gw_energypilot_window_state_v031";
const WINDOW_BAR_SELECTOR = ":scope > .ep-v036-card-windowbar";
const WINDOW_ACTION_SELECTOR = "[data-ep-window-action]";

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
      }
    : {
        controls: "Window controls",
        close: "Hide card · restore via Dashboard layout",
        minimize: "Collapse / restore card",
        maximize: "Full width / restore card",
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
    // The dashboard remains usable if browser storage is unavailable.
  }
}

function windowState() {
  const state = readJson(WINDOW_STORAGE_KEY);
  state.collapsed =
    state.collapsed && typeof state.collapsed === "object" ? state.collapsed : {};
  state.maximized =
    state.maximized && typeof state.maximized === "object" ? state.maximized : {};
  return state;
}

function hideCard(card) {
  const id = card?.dataset?.epCard;
  if (!id) return;
  const prefs = readJson(DASHBOARD_STORAGE_KEY);
  prefs.hidden = prefs.hidden && typeof prefs.hidden === "object" ? prefs.hidden : {};
  prefs.hidden[id] = true;
  writeJson(DASHBOARD_STORAGE_KEY, prefs);
  card.hidden = true;
}

function toggleCollapsed(card) {
  const id = card?.dataset?.epCard;
  if (!id) return;
  const state = windowState();
  state.collapsed[id] = !state.collapsed[id];
  if (state.collapsed[id]) state.maximized[id] = false;
  writeJson(WINDOW_STORAGE_KEY, state);
  applyWindowState(card, state);
}

function toggleMaximized(card) {
  const id = card?.dataset?.epCard;
  if (!id) return;
  const state = windowState();
  state.maximized[id] = !state.maximized[id];
  if (state.maximized[id]) state.collapsed[id] = false;
  writeJson(WINDOW_STORAGE_KEY, state);
  applyWindowState(card, state);
}

function applyWindowState(card, state) {
  const id = card?.dataset?.epCard;
  if (!id) return;
  card.classList.toggle("ep-v036-card-collapsed", Boolean(state.collapsed[id]));
  card.classList.toggle("ep-v036-card-maximized", Boolean(state.maximized[id]));
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
  if (root.querySelector("#ep-v036-window-controls-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v036-window-controls-style";
  style.textContent = `
    .ep-dashboard-layout > [data-ep-card] { position:relative; }
    .ep-v036-card-windowbar {
      position:relative;
      z-index:70;
      display:flex;
      align-items:center;
      gap:7px;
      min-height:18px;
      margin:-3px 0 10px;
      user-select:none;
    }
    .ep-v036-card-windowlabel {
      min-width:0;
      margin-left:4px;
      overflow:hidden;
      text-overflow:ellipsis;
      white-space:nowrap;
      color:#66879a;
      font-size:8px;
      font-weight:760;
      letter-spacing:.025em;
      opacity:.72;
    }
    .ep-v036-card-window-controls {
      display:flex;
      align-items:center;
      gap:6px;
      flex:0 0 auto;
    }
    .ep-v036-window-button {
      appearance:none;
      position:relative;
      width:14px;
      height:14px;
      min-width:14px;
      padding:0;
      display:grid;
      place-items:center;
      border:1px solid rgba(0,0,0,.24);
      border-radius:50%;
      cursor:pointer;
      color:rgba(30,24,20,.82);
      box-shadow:inset 0 1px 0 rgba(255,255,255,.38),0 1px 3px rgba(0,0,0,.28);
      font:900 9px/1 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",sans-serif;
      -webkit-tap-highlight-color:transparent;
      touch-action:manipulation;
    }
    .ep-v036-window-button.close { background:#ff5f57; }
    .ep-v036-window-button.minimize { background:#febc2e; }
    .ep-v036-window-button.maximize { background:#28c840; }
    .ep-v036-window-button > span {
      display:grid;
      place-items:center;
      width:100%;
      height:100%;
      opacity:0;
      pointer-events:none;
    }
    .ep-v036-window-button:hover,
    .ep-v036-window-button:focus-visible {
      filter:brightness(1.16);
      box-shadow:inset 0 1px 0 rgba(255,255,255,.52),0 0 0 2px rgba(118,220,247,.22),0 2px 6px rgba(0,0,0,.30);
    }
    .ep-v036-window-button:hover > span,
    .ep-v036-window-button:focus-visible > span,
    .ep-v036-window-button:active > span { opacity:.82; }
    .ep-v036-window-button:active {
      filter:brightness(.93);
      transform:scale(.93);
    }
    .ep-v036-window-button:focus-visible {
      outline:2px solid rgba(91,224,249,.72);
      outline-offset:2px;
    }
    .ep-dashboard-layout > .ep-v036-card-collapsed {
      min-height:0!important;
      height:auto!important;
      align-self:start!important;
      padding-bottom:11px!important;
    }
    .ep-dashboard-layout > .ep-v036-card-collapsed > :not(.ep-v036-card-windowbar) {
      display:none!important;
    }
    .ep-dashboard-layout > .ep-v036-card-collapsed .ep-v036-card-windowbar {
      margin-bottom:0;
    }
    .ep-dashboard-layout > .ep-v036-card-maximized { grid-column:1/-1!important; }
    .ep-dashboard-layout.ep-editing .ep-v036-card-windowbar { cursor:default; }
    @media (hover:none), (pointer:coarse) {
      .ep-v036-window-button > span { opacity:.62; }
    }
    @media(max-width:720px) {
      .ep-v036-card-windowbar { margin-top:-2px; }
      .ep-v036-card-maximized { grid-column:1!important; }
    }
  `;
  root.appendChild(style);
}

function createWindowBar(panel, card) {
  const labels = copy(panel);
  const bar = document.createElement("div");
  bar.className = "ep-v036-card-windowbar";
  bar.innerHTML = `
    <div class="ep-v036-card-window-controls" role="group" aria-label="${panel._escape(labels.controls)}">
      <button type="button" draggable="false" class="ep-v036-window-button close" data-ep-window-action="close" title="${panel._escape(labels.close)}" aria-label="${panel._escape(labels.close)}"><span aria-hidden="true">×</span></button>
      <button type="button" draggable="false" class="ep-v036-window-button minimize" data-ep-window-action="minimize" title="${panel._escape(labels.minimize)}" aria-label="${panel._escape(labels.minimize)}"><span aria-hidden="true">−</span></button>
      <button type="button" draggable="false" class="ep-v036-window-button maximize" data-ep-window-action="maximize" title="${panel._escape(labels.maximize)}" aria-label="${panel._escape(labels.maximize)}"><span aria-hidden="true">+</span></button>
    </div>
    <span class="ep-v036-card-windowlabel">${panel._escape(cardLabel(card))}</span>`;
  return bar;
}

function eventActionButton(event) {
  for (const node of event.composedPath()) {
    if (node instanceof Element && node.matches(WINDOW_ACTION_SELECTOR)) return node;
  }
  return null;
}

function installDelegatedActions(panel, root) {
  if (panel.__epV036WindowActionsInstalled) return;
  panel.__epV036WindowActionsInstalled = true;

  // One click listener lives on the persistent ShadowRoot. Individual buttons
  // carry no pointer handlers, pointer capture or JavaScript hover state.
  root.addEventListener("click", (event) => {
    const button = eventActionButton(event);
    if (!button) return;
    const card = button.closest("[data-ep-card]");
    if (!card) return;

    event.preventDefault();
    event.stopPropagation();
    const action = button.dataset.epWindowAction;
    if (action === "close") hideCard(card);
    else if (action === "minimize") toggleCollapsed(card);
    else if (action === "maximize") toggleMaximized(card);
  });

  root.addEventListener("dragstart", (event) => {
    if (eventActionButton(event)) event.preventDefault();
  });
}

function installWindowControls(panel, root) {
  const layout = root.querySelector(".ep-dashboard-layout");
  if (!layout) return;
  const state = windowState();

  for (const card of layout.querySelectorAll(":scope > [data-ep-card]")) {
    const id = card.dataset.epCard;
    if (!id) continue;

    // Remove every earlier implementation. The v0.36 bar is the single
    // canonical control surface and uses root-level event delegation.
    card
      .querySelectorAll(":scope > .ep-v031-card-windowbar, :scope > .ep-v028-window-controls")
      .forEach((node) => node.remove());

    card.classList.remove("ep-v031-card-collapsed", "ep-v031-card-maximized");
    applyWindowState(card, state);

    if (!card.querySelector(WINDOW_BAR_SELECTOR)) {
      card.prepend(createWindowBar(panel, card));
    }
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (!PanelClass.prototype.__epV036WindowControlsRenderInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV036WindowControlsRender() {
    previousRender.call(this);
    const root = this.shadowRoot;
    if (!root) return;
    ensureStyles(root);
    installDelegatedActions(this, root);
    installWindowControls(this, root);
  };
  PanelClass.prototype.__epV036WindowControlsRenderInstalled = true;
}
