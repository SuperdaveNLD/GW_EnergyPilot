import "./gw-energy-pilot-v029.js?v=0.30-base1";

const VERSION = "0.30";
const PANEL_NAME = "gw-energypilot-panel";
const STORAGE_KEY = "gw_energypilot_dashboard_v008";
const BATTERY_CARD_ID = "battery-price";
const SIZE_ORDER = ["compact", "normal", "large"];

function language(panel) {
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function copy(panel) {
  return language(panel) === "nl"
    ? {
        close: "Kaart verbergen · herstellen via Dashboard layout",
        resize: "Kaartformaat wijzigen",
        expand: "Gedetailleerde grafiek openen",
      }
    : {
        close: "Hide card · restore via Dashboard layout",
        resize: "Resize card",
        expand: "Open detailed graph",
      };
}

function readPrefs() {
  try {
    const value = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "{}");
    return value && typeof value === "object" ? value : {};
  } catch (_err) {
    return {};
  }
}

function writePrefs(value) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch (_err) {
    // Dashboard remains usable when localStorage is unavailable.
  }
}

function hideCard(panel, card) {
  const id = card?.dataset?.epCard;
  if (!id) return;
  const prefs = readPrefs();
  prefs.hidden = prefs.hidden && typeof prefs.hidden === "object" ? prefs.hidden : {};
  prefs.hidden[id] = true;
  writePrefs(prefs);
  card.hidden = true;
  panel._queueRender();
}

function currentBatterySize(card) {
  if (card.classList.contains("size-compact")) return "compact";
  if (card.classList.contains("size-large")) return "large";
  return "normal";
}

function cycleBatterySize(panel, card) {
  const current = currentBatterySize(card);
  const index = SIZE_ORDER.indexOf(current);
  const next = SIZE_ORDER[(index + 1) % SIZE_ORDER.length];
  const button = card.querySelector(`[data-chart-size="${next}"]`);
  if (button) button.click();
  else panel._queueRender();
}

function chromeHtml(panel, battery = false) {
  const text = copy(panel);
  return `<div class="ep-v030-card-chrome${battery ? " battery" : ""}" role="group" aria-label="Card controls">
    <button type="button" class="ep-v030-chrome-button close" data-v030-action="close" title="${text.close}" aria-label="${text.close}">×</button>
    ${battery ? `<button type="button" class="ep-v030-chrome-button resize" data-v030-action="resize" title="${text.resize}" aria-label="${text.resize}">−</button><button type="button" class="ep-v030-chrome-button expand" data-v030-action="expand" title="${text.expand}" aria-label="${text.expand}">↗</button>` : ""}
  </div>`;
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v030-card-chrome-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v030-card-chrome-style";
  style.textContent = `
    .ep-v030-card-chrome{display:flex;align-items:center;gap:7px;z-index:80}
    .ep-v030-card-chrome:not(.battery){position:absolute;top:7px;right:7px;opacity:.82;transition:opacity .14s ease}
    [data-ep-card]:hover>.ep-v030-card-chrome:not(.battery),.ep-v030-card-chrome:focus-within{opacity:1}
    .ep-v030-chrome-button{appearance:none;width:16px;height:16px;min-width:16px;padding:0;display:grid;place-items:center;border-radius:50%;cursor:pointer;font:800 11px/1 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",sans-serif;box-shadow:inset 0 1px 0 rgba(255,255,255,.20),0 2px 8px rgba(0,0,0,.22);transition:filter .14s ease,transform .14s ease;color:#061523}
    .ep-v030-chrome-button:hover{filter:brightness(1.11);transform:scale(1.06)}
    .ep-v030-chrome-button:focus-visible{outline:2px solid rgba(102,231,251,.78);outline-offset:2px}
    .ep-v030-chrome-button.close{background:#ff6070;border:1px solid rgba(255,124,137,.62);color:#45101a}
    .ep-v030-chrome-button.resize{background:#37d7ff;border:1px solid rgba(111,226,255,.64);color:#06273a}
    .ep-v030-chrome-button.expand{background:#27e5b0;border:1px solid rgba(103,244,205,.58);color:#063329}
    .ep-v030-card-chrome.battery{flex:0 0 auto;margin-top:5px}
    .ep-v030-card-chrome.battery .ep-v030-chrome-button{width:20px;height:20px;min-width:20px;font-size:12px}
    .ep-v027-head>.ep-v030-card-chrome.battery+div{flex:1 1 auto;min-width:0}
    .ep-v027-size-control{display:none!important}
    .ep-v027-expand{display:none!important}
    .ep-v028-window-controls{display:none!important}
    @media(max-width:720px){.ep-v030-card-chrome:not(.battery){top:6px;right:6px}.ep-v030-card-chrome.battery{margin-top:2px}}
  `;
  root.appendChild(style);
}

function decorateDetailedGraph() {
  const backdrop = document.querySelector(".ep-v027-backdrop");
  if (!backdrop || backdrop.querySelector("#ep-v030-modal-chrome-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v030-modal-chrome-style";
  style.textContent = `
    .ep-v028-window-dot.close{background:#ff6070!important;border-color:rgba(255,124,137,.62)!important}
    .ep-v028-window-dot.minimize{background:#37d7ff!important;border-color:rgba(111,226,255,.64)!important}
    .ep-v028-window-dot.zoom{background:#27e5b0!important;border-color:rgba(103,244,205,.58)!important}
    .ep-v028-window-dot span{opacity:.86!important;color:#061523!important}
  `;
  backdrop.appendChild(style);
}

function installGenericClose(panel, root) {
  const cards = root.querySelectorAll(".ep-dashboard-layout > [data-ep-card]");
  for (const card of cards) {
    if (card.dataset.epCard === BATTERY_CARD_ID) continue;
    if (card.querySelector(":scope > .ep-v030-card-chrome")) continue;
    const holder = document.createElement("div");
    holder.innerHTML = chromeHtml(panel, false);
    const controls = holder.firstElementChild;
    if (!controls) continue;
    card.prepend(controls);
    controls.querySelector('[data-v030-action="close"]')?.addEventListener("click", (event) => {
      event.stopPropagation();
      hideCard(panel, card);
    });
  }
}

function installBatteryChrome(panel, root) {
  const card = root.querySelector('.ep-v027-battery-plan-card[data-ep-card="battery-price"]');
  const head = card?.querySelector(".ep-v027-head");
  if (!card || !head) return;

  head.querySelector(":scope > .ep-v028-window-controls")?.remove();
  if (head.querySelector(":scope > .ep-v030-card-chrome")) return;

  const holder = document.createElement("div");
  holder.innerHTML = chromeHtml(panel, true);
  const controls = holder.firstElementChild;
  if (!controls) return;
  head.prepend(controls);

  controls.querySelector('[data-v030-action="close"]')?.addEventListener("click", (event) => {
    event.stopPropagation();
    hideCard(panel, card);
  });
  controls.querySelector('[data-v030-action="resize"]')?.addEventListener("click", (event) => {
    event.stopPropagation();
    cycleBatterySize(panel, card);
  });
  controls.querySelector('[data-v030-action="expand"]')?.addEventListener("click", (event) => {
    event.stopPropagation();
    card.querySelector(".ep-v027-expand")?.click();
    queueMicrotask(decorateDetailedGraph);
  });

  for (const trigger of card.querySelectorAll('[data-action="details"]')) {
    trigger.addEventListener("click", () => queueMicrotask(decorateDetailedGraph));
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV030Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  ensureStyles(root);
  installGenericClose(this, root);
  installBatteryChrome(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
};
