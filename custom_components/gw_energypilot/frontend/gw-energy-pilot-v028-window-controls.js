import "./gw-energy-pilot-v028.js?v=1.3.0-beta.1";

const VERSION = "0.28";
const PANEL_NAME = "gw-energypilot-panel";
const STORAGE_KEY = "gw_energypilot_dashboard_v008";
const CARD_ID = "battery-price";

function language(panel) {
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function labels(panel) {
  return language(panel) === "nl"
    ? {
        closeCard: "Kaart verbergen · herstellen via Dashboard layout",
        compact: "Kaart compact maken",
        zoom: "Gedetailleerde grafiek openen",
        closeWindow: "Venster sluiten",
        zoomWindow: "Venster maximaliseren / herstellen",
      }
    : {
        closeCard: "Hide card · restore via Dashboard layout",
        compact: "Make card compact",
        zoom: "Open detailed graph",
        closeWindow: "Close window",
        zoomWindow: "Maximize / restore window",
      };
}

function readPrefs() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (_err) {
    return {};
  }
}

function writePrefs(prefs) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    return true;
  } catch (_err) {
    return false;
  }
}

function hideBatteryPlanCard(panel, card) {
  const prefs = readPrefs();
  prefs.hidden = prefs.hidden && typeof prefs.hidden === "object" ? prefs.hidden : {};
  prefs.hidden[CARD_ID] = true;
  writePrefs(prefs);
  if (card) card.hidden = true;
  panel._queueRender();
}

function controlsHtml(copy, modal = false) {
  const redTitle = modal ? copy.closeWindow : copy.closeCard;
  return `<div class="ep-v028-window-controls${modal ? " modal" : ""}" role="group" aria-label="Window controls">
    <button type="button" class="ep-v028-window-dot close" data-window-action="close" title="${redTitle}" aria-label="${redTitle}"><span>×</span></button>
    <button type="button" class="ep-v028-window-dot minimize" data-window-action="minimize" title="${copy.compact}" aria-label="${copy.compact}"><span>−</span></button>
    <button type="button" class="ep-v028-window-dot zoom" data-window-action="zoom" title="${modal ? copy.zoomWindow : copy.zoom}" aria-label="${modal ? copy.zoomWindow : copy.zoom}"><span>↗</span></button>
  </div>`;
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v028-window-controls-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v028-window-controls-style";
  style.textContent = `
    .ep-v027-head > .ep-v028-window-controls {
      flex: 0 0 auto;
      margin-top: 5px;
    }
    .ep-v027-head > .ep-v028-window-controls + div:not(.ep-v027-head-actions) {
      flex: 1 1 auto;
      min-width: 0;
    }
    .ep-v028-window-controls {
      display: flex;
      align-items: center;
      gap: 7px;
      min-height: 18px;
    }
    .ep-v028-window-dot {
      appearance: none;
      width: 14px;
      height: 14px;
      min-width: 14px;
      padding: 0;
      display: grid;
      place-items: center;
      border: 1px solid rgba(0,0,0,.18);
      border-radius: 50%;
      box-shadow: inset 0 1px 0 rgba(255,255,255,.28), 0 1px 3px rgba(0,0,0,.16);
      cursor: pointer;
      color: rgba(20,25,30,.78);
      font: 800 10px/1 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",sans-serif;
    }
    .ep-v028-window-dot.close { background: #ff5f57; }
    .ep-v028-window-dot.minimize { background: #febc2e; }
    .ep-v028-window-dot.zoom { background: #28c840; }
    .ep-v028-window-dot span {
      opacity: 0;
      transform: translateY(-.3px);
      transition: opacity .12s ease;
      pointer-events: none;
    }
    .ep-v028-window-controls:hover .ep-v028-window-dot span,
    .ep-v028-window-dot:focus-visible span { opacity: .82; }
    .ep-v028-window-dot:focus-visible {
      outline: 2px solid rgba(105,224,255,.75);
      outline-offset: 2px;
    }
    @media (max-width: 720px) {
      .ep-v027-head { flex-wrap: wrap; }
      .ep-v027-head > .ep-v028-window-controls { margin-top: 2px; }
    }
  `;
  root.appendChild(style);
}

function ensureModalStyles(backdrop) {
  if (!backdrop || backdrop.querySelector("#ep-v028-modal-window-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v028-modal-window-style";
  style.textContent = `
    .ep-v027-modal-head { justify-content: flex-start !important; }
    .ep-v027-modal-head > .ep-v028-window-controls { flex: 0 0 auto; margin-top: 7px; }
    .ep-v027-modal-head > .ep-v028-window-controls + div { flex: 1 1 auto; min-width: 0; }
    .ep-v027-modal-head > .ep-v027-close.ep-v028-original-close { display: none !important; }
    .ep-v028-window-controls { display:flex;align-items:center;gap:7px;min-height:18px; }
    .ep-v028-window-dot { appearance:none;width:14px;height:14px;min-width:14px;padding:0;display:grid;place-items:center;border:1px solid rgba(0,0,0,.18);border-radius:50%;box-shadow:inset 0 1px 0 rgba(255,255,255,.28),0 1px 3px rgba(0,0,0,.16);cursor:pointer;color:rgba(20,25,30,.78);font:800 10px/1 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",sans-serif; }
    .ep-v028-window-dot.close{background:#ff5f57}.ep-v028-window-dot.minimize{background:#febc2e}.ep-v028-window-dot.zoom{background:#28c840}
    .ep-v028-window-dot span{opacity:0;pointer-events:none}.ep-v028-window-controls:hover .ep-v028-window-dot span,.ep-v028-window-dot:focus-visible span{opacity:.82}
    .ep-v028-window-dot:focus-visible{outline:2px solid rgba(105,224,255,.75);outline-offset:2px}
    .ep-v027-modal.ep-v028-window-zoomed { width: calc(100vw - 24px) !important; max-height: calc(100vh - 24px) !important; border-radius: 18px !important; }
  `;
  backdrop.appendChild(style);
}

function makeCardCompact(panel, root) {
  const compact = root.querySelector('.ep-v027-battery-plan-card [data-chart-size="compact"]');
  if (compact) compact.click();
  else panel._queueRender();
}

function decorateModal(panel, root) {
  const backdrop = document.querySelector(".ep-v027-backdrop");
  const modal = backdrop?.querySelector(".ep-v027-modal");
  const head = modal?.querySelector(".ep-v027-modal-head");
  const originalClose = head?.querySelector(".ep-v027-close");
  if (!backdrop || !modal || !head || !originalClose || head.querySelector(".ep-v028-window-controls")) return;

  ensureModalStyles(backdrop);
  const copy = labels(panel);
  const holder = document.createElement("div");
  holder.innerHTML = controlsHtml(copy, true);
  const controls = holder.firstElementChild;
  if (!controls) return;
  head.prepend(controls);
  originalClose.classList.add("ep-v028-original-close");

  controls.querySelector('[data-window-action="close"]')?.addEventListener("click", (event) => {
    event.stopPropagation();
    originalClose.click();
  });
  controls.querySelector('[data-window-action="minimize"]')?.addEventListener("click", (event) => {
    event.stopPropagation();
    makeCardCompact(panel, root);
    originalClose.click();
  });
  controls.querySelector('[data-window-action="zoom"]')?.addEventListener("click", (event) => {
    event.stopPropagation();
    modal.classList.toggle("ep-v028-window-zoomed");
  });
}

function installCardControls(panel, root) {
  const card = root.querySelector(".ep-v027-battery-plan-card");
  const head = card?.querySelector(".ep-v027-head");
  if (!card || !head || head.querySelector(".ep-v028-window-controls")) return;

  const copy = labels(panel);
  const holder = document.createElement("div");
  holder.innerHTML = controlsHtml(copy, false);
  const controls = holder.firstElementChild;
  if (!controls) return;
  head.prepend(controls);

  controls.querySelector('[data-window-action="close"]')?.addEventListener("click", (event) => {
    event.stopPropagation();
    hideBatteryPlanCard(panel, card);
  });
  controls.querySelector('[data-window-action="minimize"]')?.addEventListener("click", (event) => {
    event.stopPropagation();
    makeCardCompact(panel, root);
  });
  controls.querySelector('[data-window-action="zoom"]')?.addEventListener("click", (event) => {
    event.stopPropagation();
    card.querySelector(".ep-v027-expand")?.click();
  });

  for (const trigger of card.querySelectorAll('.ep-v027-expand,[data-action="details"]')) {
    trigger.addEventListener("click", () => queueMicrotask(() => decorateModal(panel, root)));
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV028WindowControlsRender() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  ensureStyles(root);
  installCardControls(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
};
