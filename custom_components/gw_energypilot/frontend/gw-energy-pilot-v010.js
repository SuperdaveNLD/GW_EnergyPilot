import "./gw-energy-pilot-v009.js?v=0.49-consolidated1";

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
  if (
    status === "legacy_yaml_detected" ||
    status?.startsWith("error") ||
    status === "stale_output"
  ) {
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

    /* One-touch GoodWe battery control. The three manual actions take manual
       ownership. AUTO creates a fresh EMHASS plan first and only then returns
       control ownership to the automatic controller. */
    .ep-battery-actions {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 7px;
      margin: 12px 0 9px;
    }
    .ep-battery-action {
      min-width: 0;
      min-height: 43px;
      padding: 7px 5px;
      border-radius: 10px;
      border: 1px solid rgba(82, 175, 233, .18);
      background: rgba(6, 31, 55, .48);
      color: #a9c4d8;
      cursor: pointer;
      font-size: 9px;
      font-weight: 850;
      line-height: 1.15;
      letter-spacing: .04em;
      text-transform: uppercase;
      transition: transform .14s ease, border-color .14s ease, background .14s ease, color .14s ease;
    }
    .ep-battery-action:hover:not(:disabled) {
      transform: translateY(-1px);
      color: #f3fdff;
      border-color: rgba(40, 225, 255, .44);
      background: rgba(11, 54, 83, .70);
    }
    .ep-battery-action[data-action="max_charge"] {
      border-color: rgba(40, 239, 167, .22);
      color: #8df1c6;
    }
    .ep-battery-action[data-action="battery_pause"] {
      color: #b5d4e6;
    }
    .ep-battery-action[data-action="max_export"] {
      color: #79e6fb;
    }
    .ep-battery-action[data-action="resume_auto"] {
      border-color: rgba(37, 235, 171, .34);
      color: #a2f7d3;
      background: rgba(9, 67, 65, .44);
    }
    .ep-battery-action.active {
      border-color: rgba(35, 242, 179, .65);
      color: #e7fff6;
      background: linear-gradient(145deg, rgba(15, 105, 107, .52), rgba(9, 64, 80, .62));
      box-shadow: inset 0 0 16px rgba(30, 241, 176, .08), 0 0 12px rgba(30, 241, 176, .08);
    }
    .ep-battery-action:disabled {
      opacity: .45;
      cursor: not-allowed;
    }
    .ep-battery-action-note {
      margin: -2px 0 8px;
      color: #657e94;
      font-size: 8px;
      line-height: 1.35;
    }

    /* v0.10 flow animation: use moving energy balls only. The old chevrons
       could visually suggest the wrong direction because the glyph itself has
       a direction. A round particle has no orientation; its movement is the
       only direction cue. */
    .ep-flow-arrows {
      display: none !important;
    }
    .ep-flow-link:not(.idle)::after {
      width: 9px !important;
      height: 9px !important;
      border-radius: 50% !important;
      background: currentColor !important;
      opacity: 0;
      box-shadow: 0 0 7px currentColor, 0 0 15px currentColor !important;
    }
    .ep-link-pv:not(.idle)::after,
    .ep-link-grid:not(.idle)::after {
      top: calc(50% - 4.5px) !important;
      left: 0;
    }
    .ep-link-pv.inbound::after,
    .ep-link-grid.outbound::after {
      animation: epV010ParticleH .92s linear infinite !important;
    }
    .ep-link-pv.outbound::after,
    .ep-link-grid.inbound::after {
      animation: epV010ParticleH .92s linear infinite reverse !important;
    }
    .ep-link-house:not(.idle)::after,
    .ep-link-battery:not(.idle)::after {
      left: calc(50% - 4.5px) !important;
      top: 0;
    }
    .ep-link-house.inbound::after,
    .ep-link-battery.outbound::after {
      animation: epV010ParticleV .92s linear infinite !important;
    }
    .ep-link-house.outbound::after,
    .ep-link-battery.inbound::after {
      animation: epV010ParticleV .92s linear infinite reverse !important;
    }
    .ep-animations-off .ep-flow-link::after {
      animation: none !important;
      opacity: .28 !important;
    }

    @keyframes epV010Pulse {
      0%,100% { opacity: .45; transform: scale(.85); }
      50% { opacity: 1; transform: scale(1.18); }
    }
    @keyframes epV010ParticleH {
      0% { left: 0; opacity: 0; transform: scale(.78); }
      13% { opacity: 1; }
      50% { transform: scale(1.08); }
      87% { opacity: 1; }
      100% { left: calc(100% - 9px); opacity: 0; transform: scale(.78); }
    }
    @keyframes epV010ParticleV {
      0% { top: 0; opacity: 0; transform: scale(.78); }
      13% { opacity: 1; }
      50% { transform: scale(1.08); }
      87% { opacity: 1; }
      100% { top: calc(100% - 9px); opacity: 0; transform: scale(.78); }
    }

    @media (max-width: 720px) {
      .ep-v010-emhass-actions { justify-content: flex-start; }
      .panel-card.emhass .section-title-row { align-items: flex-start; }
      .ep-battery-actions { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 5px; }
      .ep-battery-action { min-height: 40px; padding: 6px 4px; font-size: 8px; }
    }
  `;
  root.appendChild(style);
}

function requestStableLiveRefresh(panel) {
  if (
    panel.__epV041StableRuntime &&
    typeof panel.__epV041RefreshLiveDom === "function"
  ) {
    panel.__epV041RefreshLiveDom();
    return;
  }
  panel._queueRender();
}

async function pressNativeButton(panel, buttonElement, entityId, busyText) {
  if (!entityId || buttonElement.disabled) return;
  const original = buttonElement.textContent;
  buttonElement.disabled = true;
  buttonElement.textContent = busyText;
  try {
    await panel._hass.callService("button", "press", { entity_id: entityId });
  } catch (err) {
    console.error("GW EnergyPilot button action failed", err);
    window.alert(`EnergyPilot action failed: ${err?.message || err}`);
  } finally {
    buttonElement.disabled = false;
    buttonElement.textContent = original;
    requestStableLiveRefresh(panel);
  }
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

    button.addEventListener("click", () =>
      pressNativeButton(panel, button, entityId, "Optimizing…")
    );
  }

  const target = card.querySelector(".emhass-target");
  if (target) {
    const tone = orchestratorTone(status);
    const lastSuccess = formatLastSuccess(panel, attrs.last_success);
    const schedule = attrs.automatic_schedule ? "Automatic schedule enabled" : "Manual only";
    const priceSource = attrs.price_runtime_source === "nordpool" ? "Nord Pool runtime prices" : "EMHASS price configuration";
    const priceTrigger = attrs.price_refresh_automation ? "price refresh trigger on" : "price refresh trigger off";
    const errorText = attrs.last_error ? ` · ${attrs.last_error}` : "";
    target.insertAdjacentHTML(
      "afterend",
      `<div class="ep-v010-orchestrator ${tone}">
        <div>
          <strong>EnergyPilot orchestrator · ${panel._escape(status)}</strong>
          <small>${panel._escape(schedule)} · ${panel._escape(priceSource)} · ${panel._escape(priceTrigger)} · Last success: ${panel._escape(lastSuccess)}${panel._escape(errorText)}</small>
        </div>
        <span class="ep-v010-orchestrator-dot"></span>
      </div>`
    );
  }
}

function installBatteryQuickActions(panel, root) {
  const card = root.querySelector(".energy-card.battery");
  if (!card) return;

  const definitions = [
    {
      key: "max_export",
      label: "Max export",
      busy: "Applying…",
      command: "manual_max_export",
      title: "GoodWe mode 10 · maximum configured grid export target",
    },
    {
      key: "battery_pause",
      label: "Pause",
      busy: "Applying…",
      command: "manual_battery_hold",
      title: "GoodWe mode 8 · Battery Hold around 0 W",
    },
    {
      key: "max_charge",
      label: "Max charge",
      busy: "Applying…",
      command: "manual_max_charge",
      title: "GoodWe mode 11 · maximum configured battery charge power",
    },
    {
      key: "resume_auto",
      label: "AUTO",
      busy: "Optimizing…",
      command: null,
      title: "Run one fresh EMHASS optimization, then resume Automatic Control",
    },
  ];

  const currentCommand = panel._textByKey("control_command", "");
  const automaticEntityId = panel._entityId("automatic_control");
  const automaticState = automaticEntityId ? panel._state(automaticEntityId) : null;
  const automaticOn = automaticState?.state === "on";
  const actionWrap = document.createElement("div");
  actionWrap.className = "ep-battery-actions";

  for (const definition of definitions) {
    const entityId = panel._entityId(definition.key);
    const active = automaticOn
      ? definition.key === "resume_auto"
      : currentCommand === definition.command;
    const button = document.createElement("button");
    button.type = "button";
    button.className = `ep-battery-action${active ? " active" : ""}`;
    button.dataset.action = definition.key;
    button.setAttribute("aria-pressed", active ? "true" : "false");
    button.title = definition.title;
    button.disabled = !entityId;
    button.textContent = definition.label;
    button.addEventListener("click", () =>
      pressNativeButton(panel, button, entityId, definition.busy)
    );
    actionWrap.appendChild(button);
  }

  const socTrack = card.querySelector(".soc-track");
  if (socTrack) {
    socTrack.insertAdjacentElement("afterend", actionWrap);
    actionWrap.insertAdjacentHTML(
      "afterend",
      `<div class="ep-battery-action-note">Max export, Pause and Max charge switch to manual control. AUTO first forces one fresh EMHASS optimization and only enables Automatic Control after that optimization succeeds.</div>`
    );
  } else {
    card.appendChild(actionWrap);
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
  installBatteryQuickActions(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION}`;

  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION}`;
  }
};
