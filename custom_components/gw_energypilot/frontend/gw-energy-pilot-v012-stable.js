import "./gw-energy-pilot-v012.js?v=0.12-stable1";

const PANEL_NAME = "gw-energypilot-panel";
const STORAGE_KEY = "gw_energypilot_dashboard_v008";
const DURATION_SECONDS = 5.6;

function readPrefs() {
  try {
    const value = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || "{}");
    return {
      ...value,
      order: Array.isArray(value.order) ? value.order : [],
      hidden: value.hidden && typeof value.hidden === "object" ? value.hidden : {},
    };
  } catch (_err) {
    return { order: [], hidden: {} };
  }
}

function writePrefs(value) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch (_err) {
    // Dashboard remains functional when localStorage is unavailable.
  }
}

function ensureStableStyles(root) {
  if (root.querySelector("#ep-v012-stable-style")) return;

  const style = document.createElement("style");
  style.id = "ep-v012-stable-style";
  style.textContent = `
    /* Controls stay visually fixed while HA state updates are rendered. */
    .ep-optimize-now,
    .ep-optimize-now:hover:not(:disabled),
    .ep-optimize-now:active:not(:disabled),
    .ep-battery-action,
    .ep-battery-action:hover:not(:disabled),
    .ep-battery-action:active:not(:disabled),
    .ep-layout-button,
    .ep-layout-button:hover,
    .ep-layout-button:active {
      transform: none !important;
      animation: none !important;
      transition: none !important;
    }

    .ep-optimize-now:hover:not(:disabled) {
      border-color: rgba(45, 244, 197, .52) !important;
      box-shadow: inset 0 0 18px rgba(35, 225, 255, .06), 0 0 13px rgba(23, 215, 197, .10) !important;
    }

    /* GPU-composited full-track motion. The distance is measured in JS and
       supplied in pixels, avoiding percentage transforms relative to the ball. */
    .ep-v011-particles span {
      left: -8px !important;
      top: calc(50% - 3px) !important;
      opacity: .9 !important;
      animation-duration: ${DURATION_SECONDS}s !important;
      animation-timing-function: linear !important;
      animation-iteration-count: infinite !important;
      will-change: transform !important;
      backface-visibility: hidden;
    }
    .ep-link-pv .ep-v011-particles span,
    .ep-link-grid .ep-v011-particles span {
      animation-name: epV012StableH !important;
    }
    .ep-link-house .ep-v011-particles span,
    .ep-link-battery .ep-v011-particles span {
      left: calc(50% - 3px) !important;
      top: -8px !important;
      animation-name: epV012StableV !important;
    }
    .ep-flow-link.idle .ep-v011-particles {
      display: none !important;
    }
    .ep-animations-off .ep-v011-particles span {
      animation-play-state: paused !important;
      opacity: .18 !important;
    }

    @keyframes epV012StableH {
      from { transform: translate3d(0, 0, 0); }
      to { transform: translate3d(var(--ep-track-distance, 80px), 0, 0); }
    }
    @keyframes epV012StableV {
      from { transform: translate3d(0, 0, 0); }
      to { transform: translate3d(0, var(--ep-track-distance, 80px), 0); }
    }

    @media (prefers-reduced-motion: reduce) {
      .ep-v011-particles span { animation-duration: 9s !important; }
    }
  `;
  root.appendChild(style);
}

function setParticleGeometry(root) {
  const phaseNow = (Date.now() / 1000) % DURATION_SECONDS;

  for (const link of root.querySelectorAll(".ep-flow-link")) {
    const vertical =
      link.classList.contains("ep-link-house") ||
      link.classList.contains("ep-link-battery");
    const distance = Math.max(
      1,
      (vertical ? link.clientHeight : link.clientWidth) + 10
    );
    link.style.setProperty("--ep-track-distance", `${distance}px`);

    const particles = [...link.querySelectorAll(".ep-v011-particles span")];
    particles.forEach((particle, index) => {
      const stagger = (index * DURATION_SECONDS) / Math.max(1, particles.length);
      const phase = (phaseNow + stagger) % DURATION_SECONDS;
      particle.style.animationDelay = `${-phase}s`;
    });
  }
}

function installDiagnosticsDrag(panel, root) {
  const layout = root.querySelector(".ep-dashboard-layout");
  const card = layout?.querySelector('[data-ep-card="diagnostics"]');
  if (!layout || !card || !layout.classList.contains("ep-editing")) return;

  card.draggable = true;
  card.addEventListener("dragstart", (event) => {
    panel.__epV008DraggedCard = "diagnostics";
    card.classList.add("ep-dragging");
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", "diagnostics");
  });

  card.addEventListener("dragover", (event) => {
    if (!panel.__epV008DraggedCard) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    layout
      .querySelectorAll(".ep-drop-target")
      .forEach((node) => node.classList.remove("ep-drop-target"));
  });

  card.addEventListener("drop", (event) => {
    event.preventDefault();
    const source = panel.__epV008DraggedCard || event.dataTransfer.getData("text/plain");
    if (!source || source === "diagnostics") return;

    const prefs = readPrefs();
    const order = prefs.order.filter((id) => id !== source);
    const targetIndex = order.indexOf("diagnostics");
    order.splice(targetIndex < 0 ? order.length : targetIndex, 0, source);
    prefs.order = order;
    writePrefs(prefs);
    panel.__epV008DraggedCard = null;
    panel._queueRender();
  });

  card.addEventListener("dragend", () => {
    panel.__epV008DraggedCard = null;
    layout
      .querySelectorAll(".ep-dragging,.ep-drop-target")
      .forEach((node) => node.classList.remove("ep-dragging", "ep-drop-target"));
  });
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV012StableRender() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  ensureStableStyles(root);
  setParticleGeometry(root);
  installDiagnosticsDrag(this, root);
};
