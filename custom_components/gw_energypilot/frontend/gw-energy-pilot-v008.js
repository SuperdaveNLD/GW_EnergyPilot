import "./gw-energy-pilot-v007.js?v=1.2.0-stable1";

const VERSION = "0.08";
const PANEL_NAME = "gw-energypilot-panel";
const STORAGE_KEY = "gw_energypilot_dashboard_v008";

const CARD_DEFS = [
  { id: "flow", label: "Energy flow", selector: ".ep-flow-overview", span: 1 },
  { id: "solar", label: "Solar", selector: ".energy-card.solar", span: 1 },
  { id: "home", label: "Home", selector: ".energy-card.home", span: 1 },
  { id: "grid", label: "Grid", selector: ".energy-card.grid", span: 1 },
  { id: "battery", label: "Battery", selector: ".energy-card.battery", span: 1 },
  { id: "controller", label: "Controller", selector: ".panel-card.controller", span: 2 },
  { id: "emhass", label: "EMHASS", selector: ".panel-card.emhass", span: 2 },
  { id: "thermal", label: "System health", selector: ".panel-card.thermal", span: 1 },
];

const DEFAULT_ORDER = CARD_DEFS.map((card) => card.id);

function defaultPrefs() {
  return {
    order: [...DEFAULT_ORDER],
    hidden: {},
    edit: false,
    animations: true,
  };
}

function loadPrefs() {
  const fallback = defaultPrefs();
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return fallback;
    const stored = JSON.parse(raw);
    const storedOrder = Array.isArray(stored.order) ? stored.order : [];
    const order = [
      ...storedOrder.filter((id) => DEFAULT_ORDER.includes(id)),
      ...DEFAULT_ORDER.filter((id) => !storedOrder.includes(id)),
    ];
    return {
      order,
      hidden: stored.hidden && typeof stored.hidden === "object" ? stored.hidden : {},
      edit: Boolean(stored.edit),
      animations: stored.animations !== false,
    };
  } catch (_err) {
    return fallback;
  }
}

function savePrefs(prefs) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch (_err) {
    // The dashboard keeps working even when browser storage is unavailable.
  }
}

function layoutIcon() {
  return `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 5h16M7 12h10M9 19h6"/>
      <circle cx="8" cy="5" r="2"/>
      <circle cx="15" cy="12" r="2"/>
      <circle cx="12" cy="19" r="2"/>
    </svg>`;
}

function menuHtml(prefs) {
  const toggles = CARD_DEFS.map(
    (card) => `
      <label class="ep-menu-row">
        <span>${card.label}</span>
        <input type="checkbox" data-ep-visible="${card.id}" ${prefs.hidden[card.id] ? "" : "checked"} />
      </label>`
  ).join("");

  return `
    <div class="ep-layout-menu" role="dialog" aria-label="Dashboard layout">
      <div class="ep-menu-head">
        <div>
          <div class="ep-menu-kicker">DASHBOARD</div>
          <strong>Layout & visibility</strong>
        </div>
        <button class="ep-menu-close" type="button" aria-label="Close">×</button>
      </div>
      <label class="ep-menu-row ep-menu-feature">
        <span><strong>Edit layout</strong><small>Drag cards to reorder</small></span>
        <input type="checkbox" data-ep-setting="edit" ${prefs.edit ? "checked" : ""} />
      </label>
      <label class="ep-menu-row ep-menu-feature">
        <span><strong>Flow animations</strong><small>Moving energy particles</small></span>
        <input type="checkbox" data-ep-setting="animations" ${prefs.animations ? "checked" : ""} />
      </label>
      <div class="ep-menu-divider"></div>
      <div class="ep-menu-label">VISIBLE CARDS</div>
      ${toggles}
      <button class="ep-menu-reset" type="button">Reset dashboard layout</button>
    </div>`;
}

function dashboardStyles() {
  return `
    .ep-layout-button {
      width: 38px;
      height: 38px;
      display: grid;
      place-items: center;
      border-radius: 12px;
      border: 1px solid rgba(106, 192, 255, .18);
      color: #9edff4;
      background: rgba(12, 38, 66, .72);
      cursor: pointer;
      transition: border-color .18s ease, background .18s ease, transform .18s ease;
    }
    .ep-layout-button:hover {
      border-color: rgba(36, 226, 255, .42);
      background: rgba(13, 50, 86, .92);
      transform: translateY(-1px);
    }
    .ep-layout-button svg {
      width: 20px;
      height: 20px;
      fill: none;
      stroke: currentColor;
      stroke-width: 1.8;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .ep-layout-menu {
      position: fixed;
      z-index: 9999;
      right: 24px;
      top: 82px;
      width: min(330px, calc(100vw - 28px));
      max-height: calc(100vh - 104px);
      overflow: auto;
      padding: 15px;
      border-radius: 18px;
      color: #edf8ff;
      border: 1px solid rgba(75, 174, 255, .25);
      background:
        radial-gradient(circle at 90% 0%, rgba(31, 239, 167, .08), transparent 16rem),
        linear-gradient(145deg, rgba(9, 31, 59, .98), rgba(5, 16, 34, .99));
      box-shadow: 0 24px 70px rgba(0, 0, 0, .42);
      backdrop-filter: blur(18px);
    }
    .ep-menu-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 11px;
    }
    .ep-menu-kicker,
    .ep-menu-label {
      color: #63e4f8;
      font-size: 9px;
      font-weight: 850;
      letter-spacing: .15em;
    }
    .ep-menu-head strong { display: block; margin-top: 3px; font-size: 16px; }
    .ep-menu-close {
      width: 30px;
      height: 30px;
      border: 0;
      border-radius: 9px;
      background: rgba(255, 255, 255, .05);
      color: #9cb1c6;
      font-size: 21px;
      cursor: pointer;
    }
    .ep-menu-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      min-height: 38px;
      padding: 7px 2px;
      color: #c8d7e5;
      font-size: 12px;
    }
    .ep-menu-row small {
      display: block;
      margin-top: 2px;
      color: #6f879e;
      font-size: 10px;
      font-weight: 500;
    }
    .ep-menu-row input {
      appearance: none;
      position: relative;
      width: 34px;
      height: 19px;
      flex: 0 0 34px;
      border-radius: 999px;
      background: #263d55;
      cursor: pointer;
      transition: background .15s ease;
    }
    .ep-menu-row input::after {
      content: "";
      position: absolute;
      top: 3px;
      left: 3px;
      width: 13px;
      height: 13px;
      border-radius: 50%;
      background: #dfeaf1;
      transition: transform .16s ease;
    }
    .ep-menu-row input:checked { background: rgba(28, 229, 163, .50); }
    .ep-menu-row input:checked::after {
      transform: translateX(15px);
      background: #caffed;
      box-shadow: 0 0 11px rgba(32, 244, 157, .44);
    }
    .ep-menu-feature {
      padding: 10px 9px;
      margin: 6px 0;
      border-radius: 11px;
      background: rgba(255, 255, 255, .025);
      border: 1px solid rgba(255, 255, 255, .045);
    }
    .ep-menu-divider { height: 1px; margin: 12px 0; background: rgba(255,255,255,.07); }
    .ep-menu-label { margin-bottom: 5px; }
    .ep-menu-reset {
      width: 100%;
      margin-top: 11px;
      padding: 10px 12px;
      border-radius: 11px;
      border: 1px solid rgba(70, 181, 255, .18);
      color: #b9d8e8;
      background: rgba(18, 54, 86, .38);
      font-weight: 700;
      cursor: pointer;
    }

    .ep-dashboard-layout {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      grid-auto-flow: dense;
      gap: 14px;
      margin-top: 4px;
      align-items: stretch;
    }
    .hero-grid,
    .secondary-grid { display: none !important; }
    .ep-dashboard-layout > .ep-flow-overview {
      width: 100% !important;
      margin: 0 !important;
      min-height: 300px;
    }
    .ep-dashboard-layout > .energy-card,
    .ep-dashboard-layout > .panel-card,
    .ep-dashboard-layout > .ep-flow-overview {
      min-width: 0;
      height: 100%;
    }
    .ep-dashboard-layout [data-ep-span="2"] { grid-column: span 2; }
    .ep-dashboard-layout [hidden] { display: none !important; }

    .ep-dashboard-layout.ep-editing > [data-ep-card] {
      cursor: grab;
      outline: 1px dashed rgba(90, 217, 255, .42);
      outline-offset: -5px;
      transition: opacity .14s ease, transform .14s ease, box-shadow .14s ease;
    }
    .ep-dashboard-layout.ep-editing > [data-ep-card]::before {
      content: "DRAG";
      position: absolute;
      z-index: 40;
      top: 9px;
      right: 10px;
      padding: 4px 7px;
      border-radius: 999px;
      color: #91eaff;
      background: rgba(4, 28, 50, .78);
      border: 1px solid rgba(79, 208, 255, .20);
      font-size: 8px;
      font-weight: 850;
      letter-spacing: .12em;
      pointer-events: none;
    }
    .ep-dashboard-layout.ep-editing > [data-ep-card]:active { cursor: grabbing; }
    .ep-dashboard-layout .ep-dragging { opacity: .35; transform: scale(.985); }
    .ep-dashboard-layout .ep-drop-target {
      box-shadow: 0 0 0 2px rgba(31, 239, 167, .50), 0 18px 55px rgba(0,0,0,.22) !important;
    }

    /* Strong moving energy particles. The original chevrons remain as the
       direction cue; this layer makes movement clearly visible. */
    .ep-flow-link:not(.idle)::after {
      content: "";
      position: absolute;
      z-index: 5;
      pointer-events: none;
      border-radius: 999px;
      opacity: 0;
    }
    .ep-link-pv:not(.idle)::after,
    .ep-link-grid:not(.idle)::after {
      width: 30px;
      height: 5px;
      top: calc(50% - 2.5px);
      left: 0;
      background: linear-gradient(90deg, transparent, #71fff0 35%, #21f1b0 70%, transparent);
      box-shadow: 0 0 13px rgba(35, 241, 181, .95), 0 0 26px rgba(29, 217, 255, .45);
    }
    .ep-link-pv.inbound::after,
    .ep-link-grid.outbound::after { animation: epV008ParticleH .82s linear infinite; }
    .ep-link-pv.outbound::after,
    .ep-link-grid.inbound::after { animation: epV008ParticleH .82s linear infinite reverse; }

    .ep-link-house:not(.idle)::after,
    .ep-link-battery:not(.idle)::after {
      width: 5px;
      height: 30px;
      top: 0;
      left: calc(50% - 2.5px);
      background: linear-gradient(180deg, transparent, #65eaff 35%, #22f4aa 70%, transparent);
      box-shadow: 0 0 13px rgba(34, 232, 255, .95), 0 0 26px rgba(34, 244, 170, .42);
    }
    .ep-link-house.inbound::after,
    .ep-link-battery.outbound::after { animation: epV008ParticleV .82s linear infinite; }
    .ep-link-house.outbound::after,
    .ep-link-battery.inbound::after { animation: epV008ParticleV .82s linear infinite reverse; }

    .ep-animations-off .ep-flow-link::after,
    .ep-animations-off .ep-flow-arrows,
    .ep-animations-off .ep-flow-live span,
    .ep-animations-off .ep-flow-hub::after {
      animation: none !important;
    }

    @keyframes epV008ParticleH {
      0% { left: 0; opacity: 0; }
      14% { opacity: 1; }
      86% { opacity: 1; }
      100% { left: calc(100% - 30px); opacity: 0; }
    }
    @keyframes epV008ParticleV {
      0% { top: 0; opacity: 0; }
      14% { opacity: 1; }
      86% { opacity: 1; }
      100% { top: calc(100% - 30px); opacity: 0; }
    }

    @media (max-width: 1180px) {
      .ep-dashboard-layout { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .ep-dashboard-layout [data-ep-span="2"] { grid-column: span 2; }
    }
    @media (max-width: 720px) {
      .ep-layout-menu { right: 14px; top: 74px; }
      .ep-dashboard-layout { grid-template-columns: 1fr; }
      .ep-dashboard-layout [data-ep-span="2"] { grid-column: span 1; }
      .ep-dashboard-layout.ep-editing > [data-ep-card]::before { content: "DRAG"; }
    }
  `;
}

function installMenu(panel, root, prefs) {
  const headerActions = root.querySelector(".header-actions");
  if (!headerActions) return;

  const button = document.createElement("button");
  button.type = "button";
  button.className = "ep-layout-button";
  button.setAttribute("aria-label", "Dashboard layout");
  button.innerHTML = layoutIcon();
  headerActions.prepend(button);

  button.addEventListener("click", () => {
    panel.__epV008MenuOpen = !panel.__epV008MenuOpen;
    panel._queueRender();
  });

  if (!panel.__epV008MenuOpen) return;

  const menu = document.createElement("div");
  menu.innerHTML = menuHtml(prefs);
  const menuNode = menu.firstElementChild;
  root.appendChild(menuNode);

  menuNode.querySelector(".ep-menu-close")?.addEventListener("click", () => {
    panel.__epV008MenuOpen = false;
    panel._queueRender();
  });

  menuNode.querySelectorAll("[data-ep-visible]").forEach((input) => {
    input.addEventListener("change", () => {
      const id = input.dataset.epVisible;
      prefs.hidden[id] = !input.checked;
      savePrefs(prefs);
      panel._queueRender();
    });
  });

  menuNode.querySelector('[data-ep-setting="edit"]')?.addEventListener("change", (event) => {
    prefs.edit = Boolean(event.currentTarget.checked);
    savePrefs(prefs);
    panel._queueRender();
  });

  menuNode.querySelector('[data-ep-setting="animations"]')?.addEventListener("change", (event) => {
    prefs.animations = Boolean(event.currentTarget.checked);
    savePrefs(prefs);
    panel._queueRender();
  });

  menuNode.querySelector(".ep-menu-reset")?.addEventListener("click", () => {
    const reset = defaultPrefs();
    savePrefs(reset);
    panel.__epV008MenuOpen = true;
    panel._queueRender();
  });
}

function collectCards(root) {
  const result = new Map();
  for (const def of CARD_DEFS) {
    const node = root.querySelector(def.selector);
    if (node) {
      result.set(def.id, { def, node });
    }
  }
  return result;
}

function installDragAndDrop(panel, layout, prefs) {
  const cards = [...layout.querySelectorAll("[data-ep-card]")];
  for (const card of cards) {
    card.draggable = prefs.edit;

    card.addEventListener("dragstart", (event) => {
      if (!prefs.edit) {
        event.preventDefault();
        return;
      }
      const id = card.dataset.epCard;
      panel.__epV008DraggedCard = id;
      card.classList.add("ep-dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", id);
    });

    card.addEventListener("dragover", (event) => {
      if (!prefs.edit || !panel.__epV008DraggedCard) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      layout.querySelectorAll(".ep-drop-target").forEach((node) => node.classList.remove("ep-drop-target"));
      if (card.dataset.epCard !== panel.__epV008DraggedCard) {
        card.classList.add("ep-drop-target");
      }
    });

    card.addEventListener("drop", (event) => {
      if (!prefs.edit) return;
      event.preventDefault();
      const sourceId = panel.__epV008DraggedCard || event.dataTransfer.getData("text/plain");
      const targetId = card.dataset.epCard;
      if (!sourceId || !targetId || sourceId === targetId) return;

      const order = prefs.order.filter((id) => id !== sourceId);
      const targetIndex = order.indexOf(targetId);
      order.splice(targetIndex < 0 ? order.length : targetIndex, 0, sourceId);
      prefs.order = order;
      savePrefs(prefs);
      panel.__epV008DraggedCard = null;
      panel._queueRender();
    });

    card.addEventListener("dragend", () => {
      panel.__epV008DraggedCard = null;
      layout.querySelectorAll(".ep-dragging,.ep-drop-target").forEach((node) => {
        node.classList.remove("ep-dragging", "ep-drop-target");
      });
    });
  }
}

function applyLayout(panel, root, prefs) {
  const cards = collectCards(root);
  if (cards.size === 0) return;

  let layout = root.querySelector(".ep-dashboard-layout");
  if (!layout) {
    layout = document.createElement("section");
    layout.className = "ep-dashboard-layout";
    const heroGrid = root.querySelector(".hero-grid");
    if (heroGrid) heroGrid.before(layout);
    else root.querySelector("footer")?.before(layout);
  }

  layout.classList.toggle("ep-editing", prefs.edit);
  layout.classList.toggle("ep-animations-off", !prefs.animations);

  for (const id of prefs.order) {
    const item = cards.get(id);
    if (!item) continue;
    const { def, node } = item;
    node.dataset.epCard = id;
    node.dataset.epSpan = String(def.span);
    node.hidden = Boolean(prefs.hidden[id]);
    layout.appendChild(node);
  }

  installDragAndDrop(panel, layout, prefs);
}

await customElements.whenDefined(PANEL_NAME);

const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV008Render() {
  previousRender.call(this);

  const root = this.shadowRoot;
  if (!root) return;

  const style = document.createElement("style");
  style.id = "ep-v008-style";
  style.textContent = dashboardStyles();
  root.appendChild(style);

  const prefs = loadPrefs();
  applyLayout(this, root, prefs);
  installMenu(this, root, prefs);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION}`;

  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION}`;
};
