import "./gw-energy-pilot-v010.js?v=1.2.0-beta.6-chart-touch1";

const VERSION = "0.11";
const PANEL_NAME = "gw-energypilot-panel";

function ensureV011Styles(root) {
  if (root.querySelector("#ep-v011-style")) return;

  const style = document.createElement("style");
  style.id = "ep-v011-style";
  style.textContent = `
    /* The v0.08/v0.10 pseudo-particle disappears at the end of every short
       track. Three independent particles now overlap in time, so the flow is
       continuous instead of looking like a repeated blink. */
    .ep-flow-link::after { display: none !important; }
    .ep-flow-arrows { display: none !important; }
    .ep-flow-live span { animation: none !important; opacity: .92; }

    .ep-v011-particles {
      position: absolute;
      inset: 0;
      z-index: 6;
      overflow: hidden;
      pointer-events: none;
    }
    .ep-flow-link.idle .ep-v011-particles { display: none; }
    .ep-v011-particles span {
      position: absolute;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      opacity: .9;
      background: #58f7e1;
      box-shadow: 0 0 6px rgba(65,244,228,.95), 0 0 12px rgba(34,219,255,.58);
      will-change: transform;
    }
    .ep-link-pv .ep-v011-particles span,
    .ep-link-grid .ep-v011-particles span {
      left: -8px;
      top: calc(50% - 3px);
      animation: epV011BallH 2.8s linear infinite;
    }
    .ep-link-house .ep-v011-particles span,
    .ep-link-battery .ep-v011-particles span {
      top: -8px;
      left: calc(50% - 3px);
      animation: epV011BallV 2.8s linear infinite;
    }
    .ep-v011-particles span:nth-child(2) { animation-delay: -.93s; }
    .ep-v011-particles span:nth-child(3) { animation-delay: -1.86s; }

    .ep-link-pv.outbound .ep-v011-particles span,
    .ep-link-grid.inbound .ep-v011-particles span,
    .ep-link-house.outbound .ep-v011-particles span,
    .ep-link-battery.inbound .ep-v011-particles span {
      animation-direction: reverse;
    }

    .ep-animations-off .ep-v011-particles span { animation-play-state: paused !important; opacity: .22; }

    @keyframes epV011BallH {
      0%   { transform: translateX(0) scale(.82); opacity: .35; }
      8%   { opacity: .95; }
      50%  { transform: translateX(calc(50% + 22px)) scale(1); opacity: 1; }
      92%  { opacity: .95; }
      100% { transform: translateX(calc(100% + 54px)) scale(.82); opacity: .35; }
    }
    @keyframes epV011BallV {
      0%   { transform: translateY(0) scale(.82); opacity: .35; }
      8%   { opacity: .95; }
      50%  { transform: translateY(calc(50% + 22px)) scale(1); opacity: 1; }
      92%  { opacity: .95; }
      100% { transform: translateY(calc(100% + 54px)) scale(.82); opacity: .35; }
    }

    .ep-v011-soc-controls {
      display: grid;
      grid-template-columns: repeat(2, minmax(0,1fr));
      gap: 10px;
      margin-top: 11px;
    }
    .ep-v011-soc-control {
      padding: 10px 11px;
      border: 1px solid rgba(77,161,218,.13);
      border-radius: 11px;
      background: rgba(8,29,52,.42);
    }
    .ep-v011-soc-head {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 7px;
      color: #8ba7bd;
      font-size: 9px;
    }
    .ep-v011-soc-head strong { color: #e6f5ff; font-size: 11px; }
    .ep-v011-soc-control input[type="range"] {
      width: 100%;
      accent-color: #23ddb7;
      cursor: pointer;
    }
    .ep-v011-soc-control input:disabled { opacity: .35; cursor: not-allowed; }
    .ep-v011-soc-note {
      grid-column: 1 / -1;
      color: #617c93;
      font-size: 8px;
      line-height: 1.35;
    }

    .panel-card.diagnostics {
      position: relative;
      overflow: hidden;
    }
    .ep-v011-diag-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
    }
    .ep-v011-diag-head h2 { margin: 2px 0 0; }
    .ep-v011-copy {
      padding: 7px 10px;
      border-radius: 9px;
      border: 1px solid rgba(51,205,235,.20);
      background: rgba(7,44,69,.50);
      color: #8deaf8;
      font-size: 9px;
      font-weight: 800;
      cursor: pointer;
    }
    .ep-v011-diag-grid {
      display: grid;
      grid-template-columns: repeat(2,minmax(0,1fr));
      gap: 12px;
    }
    .ep-v011-diag-group {
      border: 1px solid rgba(77,161,218,.11);
      border-radius: 11px;
      overflow: hidden;
      background: rgba(7,27,49,.38);
    }
    .ep-v011-diag-group-title {
      padding: 8px 10px;
      color: #61e4f8;
      font-size: 9px;
      font-weight: 850;
      letter-spacing: .13em;
      border-bottom: 1px solid rgba(77,161,218,.09);
    }
    .ep-v011-diag-row {
      display: grid;
      grid-template-columns: minmax(0,1.35fr) minmax(0,1fr);
      gap: 10px;
      padding: 7px 10px;
      border-bottom: 1px solid rgba(77,161,218,.07);
      font-size: 9px;
    }
    .ep-v011-diag-row:last-child { border-bottom: 0; }
    .ep-v011-diag-row span { color: #7f9ab0; }
    .ep-v011-diag-row strong { color: #e1eef7; text-align: right; overflow-wrap: anywhere; }
    .ep-v011-diag-note {
      margin-top: 10px;
      color: #5d7890;
      font-size: 8px;
      line-height: 1.4;
    }

    @media (max-width: 720px) {
      .ep-v011-soc-controls,
      .ep-v011-diag-grid { grid-template-columns: 1fr; }
      .ep-v011-soc-note { grid-column: auto; }
    }
  `;
  root.appendChild(style);
}

function installSmoothParticles(root) {
  for (const link of root.querySelectorAll(".ep-flow-link")) {
    if (link.querySelector(".ep-v011-particles")) continue;
    const particles = document.createElement("div");
    particles.className = "ep-v011-particles";
    particles.innerHTML = "<span></span><span></span><span></span>";
    link.appendChild(particles);
  }
}

function relabelHouseLoad(root) {
  const homeSub = root.querySelector(".energy-card.home .hero-sub");
  if (homeSub) homeSub.textContent = "House load · GoodWe register 35172";

  const flowSub = root.querySelector(".ep-flow-house .ep-flow-node-sub");
  if (flowSub) flowSub.textContent = "House load";
}

function numberValue(panel, key) {
  const entityId = panel._entityId(key);
  const state = entityId ? panel._state(entityId) : null;
  const value = state ? Number(state.state) : NaN;
  return { entityId, value: Number.isFinite(value) ? value : null };
}

function installSocSliders(panel, root) {
  const card = root.querySelector(".panel-card.emhass");
  if (!card || card.querySelector(".ep-v011-soc-controls")) return;

  const minSoc = numberValue(panel, "emhass_minimum_soc");
  const maxSoc = numberValue(panel, "emhass_maximum_soc");
  const anchor = card.querySelector(".ep-v010-orchestrator") || card.querySelector(".emhass-target");
  if (!anchor) return;

  const wrap = document.createElement("div");
  wrap.className = "ep-v011-soc-controls";
  wrap.innerHTML = `
    <div class="ep-v011-soc-control">
      <div class="ep-v011-soc-head"><span>EMHASS minimum SOC</span><strong data-soc-value="min">${minSoc.value === null ? "—" : `${Math.round(minSoc.value)}%`}</strong></div>
      <input data-soc-slider="min" type="range" min="0" max="100" step="1" value="${minSoc.value ?? 0}" ${minSoc.entityId ? "" : "disabled"} />
    </div>
    <div class="ep-v011-soc-control">
      <div class="ep-v011-soc-head"><span>EMHASS maximum SOC</span><strong data-soc-value="max">${maxSoc.value === null ? "—" : `${Math.round(maxSoc.value)}%`}</strong></div>
      <input data-soc-slider="max" type="range" min="0" max="100" step="1" value="${maxSoc.value ?? 100}" ${maxSoc.entityId ? "" : "disabled"} />
    </div>
    <div class="ep-v011-soc-note">These sliders write the corresponding EMHASS config.json values through EMHASS /get-config and /set-config. They affect subsequent optimizations.</div>`;
  anchor.insertAdjacentElement("afterend", wrap);

  const bind = (kind, ref) => {
    const slider = wrap.querySelector(`[data-soc-slider="${kind}"]`);
    const label = wrap.querySelector(`[data-soc-value="${kind}"]`);
    if (!slider || !ref.entityId) return;
    slider.addEventListener("input", () => {
      slider.dataset.epSocDraft = slider.value;
      label.textContent = `${slider.value}%`;
    });
    slider.addEventListener("change", async () => {
      const requestedValue = Number(slider.value);
      slider.dataset.epSocDraft = String(requestedValue);
      slider.disabled = true;
      try {
        await panel._hass.callService("number", "set_value", {
          entity_id: ref.entityId,
          value: requestedValue,
        });
      } catch (err) {
        delete slider.dataset.epSocDraft;
        console.error("GW EnergyPilot SOC config update failed", err);
        window.alert(`EMHASS SOC update failed: ${err?.message || err}`);
      } finally {
        slider.disabled = false;
        panel._queueRender();
      }
    });
  };

  bind("min", minSoc);
  bind("max", maxSoc);
}

function fmt(panel, value, kind = "text") {
  if (value === null || value === undefined || value === "") return "—";
  if (kind === "power") {
    const number = Number(value);
    return Number.isFinite(number) ? panel._formatPower(number) : String(value);
  }
  if (kind === "percent") {
    const number = Number(value);
    return Number.isFinite(number) ? `${number.toFixed(1)}%` : String(value);
  }
  return String(value);
}

function diagRow(panel, label, value, kind = "text") {
  return `<div class="ep-v011-diag-row"><span>${panel._escape(label)}</span><strong>${panel._escape(fmt(panel, value, kind))}</strong></div>`;
}

function diagnosticSnapshotText(attrs) {
  const pairs = [
    ["EMS mode 47511", `${attrs.ems_mode ?? "—"} - ${attrs.ems_mode_name ?? "Unknown"}`],
    ["EMS setpoint 47512", attrs.ems_setpoint],
    ["Work mode 35187", attrs.work_mode_35187],
    ["Operation mode 35188", attrs.operation_mode_35188],
    ["Grid mode 35136", attrs.grid_mode_35136],
    ["House load register 35172", attrs.house_load_register_35172],
    ["House load phase sum", attrs.house_load_phase_sum],
    ["House load power balance", attrs.house_load_power_balance],
    ["Meter fast total", attrs.meter_total_power_fast],
    ["Inverter power", attrs.total_inverter_power],
    ["Battery power", attrs.battery_power],
    ["Battery SOC", attrs.battery_soc],
    ["Automatic control", attrs.controller_enabled ? "ON" : "OFF"],
    ["Controller command", attrs.controller_command],
    ["Controller target", attrs.controller_target_power],
    ["Expected EMS mode", attrs.controller_expected_mode],
    ["P_batt entity", attrs.p_batt_entity],
    ["P_batt", attrs.p_batt_value],
    ["Optimization status", attrs.optim_status_value],
    ["SOC init", attrs.soc_init],
    ["Orchestrator status", attrs.orchestrator_status],
    ["Last reason", attrs.last_reason],
    ["Price area", attrs.price_area],
    ["Price points", attrs.price_points],
    ["Load forecast points", attrs.load_forecast_points],
    ["Last error", attrs.last_error],
  ];
  return ["GW EnergyPilot diagnostics", ...pairs.map(([key, value]) => `${key}: ${value ?? "—"}`)].join("\n");
}

function installDiagnostics(panel, root) {
  const layout = root.querySelector(".ep-dashboard-layout");
  if (!layout || layout.querySelector(".panel-card.diagnostics")) return;

  const optimizeId = panel._entityId("optimize_now");
  const optimizeState = optimizeId ? panel._state(optimizeId) : null;
  const attrs = optimizeState?.attributes || {};

  const card = document.createElement("article");
  card.className = "panel-card diagnostics";
  card.dataset.epCard = "diagnostics";
  card.dataset.epSpan = "2";
  card.innerHTML = `
    <div class="ep-v011-diag-head">
      <div><div class="card-kicker">SUPPORT</div><h2>Diagnostics snapshot</h2></div>
      <button type="button" class="ep-v011-copy">Copy snapshot</button>
    </div>
    <div class="ep-v011-diag-grid">
      <div class="ep-v011-diag-group">
        <div class="ep-v011-diag-group-title">GOODWE / POWER</div>
        ${diagRow(panel, "EMS mode 47511", attrs.ems_mode === undefined ? "—" : `${attrs.ems_mode} · ${attrs.ems_mode_name || "Unknown"}`)}
        ${diagRow(panel, "EMS setpoint 47512", attrs.ems_setpoint, "power")}
        ${diagRow(panel, "Work mode 35187", attrs.work_mode_35187)}
        ${diagRow(panel, "Operation mode 35188", attrs.operation_mode_35188)}
        ${diagRow(panel, "Grid mode 35136", attrs.grid_mode_35136)}
        ${diagRow(panel, "House load 35172", attrs.house_load_register_35172, "power")}
        ${diagRow(panel, "Load phase sum", attrs.house_load_phase_sum, "power")}
        ${diagRow(panel, "Power-balance load", attrs.house_load_power_balance, "power")}
        ${diagRow(panel, "Meter fast total", attrs.meter_total_power_fast, "power")}
        ${diagRow(panel, "Inverter power", attrs.total_inverter_power, "power")}
        ${diagRow(panel, "Battery power", attrs.battery_power, "power")}
      </div>
      <div class="ep-v011-diag-group">
        <div class="ep-v011-diag-group-title">ENERGYPILOT / EMHASS</div>
        ${diagRow(panel, "Automatic control", attrs.controller_enabled ? "ON" : "OFF")}
        ${diagRow(panel, "Command", attrs.controller_command)}
        ${diagRow(panel, "Controller target", attrs.controller_target_power, "power")}
        ${diagRow(panel, "Expected EMS mode", attrs.controller_expected_mode)}
        ${diagRow(panel, "P_batt", attrs.p_batt_value, "power")}
        ${diagRow(panel, "Optim status", attrs.optim_status_value)}
        ${diagRow(panel, "SOC init", attrs.soc_init === undefined || attrs.soc_init === null ? null : Number(attrs.soc_init) * 100, "percent")}
        ${diagRow(panel, "Orchestrator", attrs.orchestrator_status)}
        ${diagRow(panel, "Last trigger", attrs.last_reason)}
        ${diagRow(panel, "Price points", attrs.price_points)}
        ${diagRow(panel, "Load forecast points", attrs.load_forecast_points)}
      </div>
    </div>
    <div class="ep-v011-diag-note">Register 35172 is the GoodWe total house/load value, not inverter self-consumption. The phase sum and power-balance value are shown next to it so support can spot firmware, metering or AC-coupled-PV differences.</div>`;
  layout.appendChild(card);

  const copy = card.querySelector(".ep-v011-copy");
  copy?.addEventListener("click", async () => {
    const text = diagnosticSnapshotText(attrs);
    try {
      await navigator.clipboard.writeText(text);
      const previous = copy.textContent;
      copy.textContent = "Copied";
      setTimeout(() => { copy.textContent = previous; }, 1200);
    } catch (_err) {
      window.prompt("Copy EnergyPilot diagnostics", text);
    }
  });
}

await customElements.whenDefined(PANEL_NAME);

const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV011Render() {
  previousRender.call(this);

  const root = this.shadowRoot;
  if (!root) return;

  ensureV011Styles(root);
  installSmoothParticles(root);
  relabelHouseLoad(root);
  installSocSliders(this, root);
  installDiagnostics(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION}`;

  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION}`;
};
