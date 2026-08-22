import "./gw-energy-pilot-v009.js?v=0.09-brand2";

const VERSION = "0.10";
const PANEL_NAME = "gw-energypilot-panel";

const RUNNING_STATES = new Set([
  "preparing",
  "reading_history",
  "getting_prices",
  "optimizing",
  "publishing",
  "waiting_for_output",
]);

function formatLastSuccess(panel, value) {
  if (!value) return "Never";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  const language = panel._hass?.locale?.language || panel._hass?.language || undefined;
  return new Intl.DateTimeFormat(language, {
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
  if (status === "legacy_yaml_detected" || status?.startsWith("error") || status === "stale_output") {
    return "error";
  }
  return "info";
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v010-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v010-style";
  style.textContent = `
    .ep-v010-emhass-actions {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      flex-wrap: wrap;
    }
    .ep-optimize-now {
      min-height: 34px;
      padding: 8px 12px;
      border: 1px solid rgba(40, 222, 255, .34);
      border-radius: 11px;
      color: #dffcff;
      background: linear-gradient(135deg, rgba(20, 116, 164, .42), rgba(20, 190, 142, .30));
      box-shadow: inset 0 0 18px rgba(35, 225, 255, .06), 0 0 16px rgba(23, 215, 197, .06);
      font-size: 11px;
      font-weight: 800;
      letter-spacing: .02em;
      cursor: pointer;
      transition: transform .14s ease, border-color .14s ease, background .14s ease;
    }
    .ep-optimize-now:hover:not(:disabled) {
      transform: translateY(-1px);
      border-color: rgba(45, 244, 197, .60);
      background: linear-gradient(135deg, rgba(19, 139, 190, .56), rgba(18, 206, 145, .40));
    }
    .ep-optimize-now:disabled {
      opacity: .48;
      cursor: not-allowed;
    }
    .ep-v010-orchestrator {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      align-items: center;
      margin: 10px 0 4px;
      padding: 9px 11px;
      border-radius: 11px;
      border: 1px solid rgba(85, 176, 235, .12);
      background: rgba(4, 23, 43, .34);
    }
    .ep-v010-orchestrator strong {
      display: block;
      color: #d8effb;
      font-size: 11px;
      text-transform: capitalize;
    }
    .ep-v010-orchestrator small {
      display: block;
      margin-top: 2px;
      color: #718da5;
      font-size: 9px;
    }
    .ep-v010-orchestrator-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #6b8298;
      box-shadow: 0 0 8px rgba(107,130,152,.35);
    }
    .ep-v010-orchestrator.ok .ep-v010-orchestrator-dot {
      background: #28f1a5;
      box-shadow: 0 0 10px rgba(40,241,165,.65);
    }
    .ep-v010-orchestrator.running .ep-v010-orchestrator-dot {
      background: #29dfff;
      box-shadow: 0 0 10px rgba(41,223,255,.72);
      animation: epV010Pulse 1s ease-in-out infinite;
    }
    .ep-v010-orchestrator.error .ep-v010-orchestrator-dot {
      background: #ff7c73;
      box-shadow: 0 0 10px rgba(255,124,115,.55);
    }
    @keyframes epV010Pulse {
      0%,100% { opacity: .45; transform: scale(.85); }
      50% { opacity: 1; transform: scale(1.18); }
    }
    @media (max-width: 720px) {
      .ep-v010-emhass-actions { justify-content: flex-start; }
      .panel-card.emhass .section-title-row { align-items: flex-start; }
    }
  `;
  root.appendChild(style);
}

function installOptimizeNow(panel, root) {
  const card = root.querySelector(".panel-card.emhass");
  if (!card) return;

  const entityId = panel._entityId("optimize_now");
  const entityState = entityId ? panel._state(entityId) : null;
  const attrs = entityState?.attributes || {};
  const status = attrs.orchestrator_status || "not available";
  const running = RUNNING_STATES.has(status);

  const titleRow = card.querySelector(".section-title-row");
  if (titleRow) {
    const statusPill = titleRow.querySelector(".status");
    const actions = document.createElement("div");
    actions.className = "ep-v010-emhass-actions";
    if (statusPill) actions.appendChild(statusPill);

    const button = document.createElement("button");
    button.type = "button";
    button.className = "ep-optimize-now";
    button.disabled = !entityId || running;
    button.textContent = running ? "Optimizing…" : "Optimize now";
    actions.appendChild(button);
    titleRow.appendChild(actions);

    button.addEventListener("click", async () => {
      if (!entityId || button.disabled) return;
      button.disabled = true;
      button.textContent = "Optimizing…";
      try {
        await panel._hass.callService("button", "press", { entity_id: entityId });
      } catch (err) {
        console.error("GW EnergyPilot: Optimize now failed", err);
        window.alert(`EnergyPilot optimization failed: ${err?.message || err}`);
      } finally {
        panel._queueRender();
      }
    });
  }

  const target = card.querySelector(".emhass-target");
  if (target) {
    const tone = orchestratorTone(status);
    const lastSuccess = formatLastSuccess(panel, attrs.last_success);
    const schedule = attrs.automatic_schedule ? "Automatic schedule enabled" : "Manual only";
    const errorText = attrs.last_error ? ` · ${attrs.last_error}` : "";
    target.insertAdjacentHTML(
      "afterend",
      `<div class="ep-v010-orchestrator ${tone}">
        <div>
          <strong>EnergyPilot orchestrator · ${panel._escape(status)}</strong>
          <small>${panel._escape(schedule)} · Last success: ${panel._escape(lastSuccess)}${panel._escape(errorText)}</small>
        </div>
        <span class="ep-v010-orchestrator-dot"></span>
      </div>`
    );
  }
}

await customElements.whenDefined(PANEL_NAME);

const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV010Render() {
  previousRender.call(this);

  const root = this.shadowRoot;
  if (!root) return;

  ensureStyles(root);
  installOptimizeNow(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION}`;

  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION}`;
  }
};
