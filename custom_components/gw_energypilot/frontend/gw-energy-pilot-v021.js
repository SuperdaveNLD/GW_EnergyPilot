import "./gw-energy-pilot-v020.js?v=1.2.0-beta.6-chart-touch1";

const VERSION = "0.21";
const PANEL_NAME = "gw-energypilot-panel";

const MODE_DEFINITIONS = [
  {
    mode: 1,
    tag: "AUTO",
    option: "1: GoodWe Auto / AI",
    name: "GoodWe Auto / AI",
    tip: "Normal GoodWe self-use control. Setpoint is forced to 0 W.",
  },
  {
    mode: 2,
    tag: "PV+",
    option: "2: PV-priority charging",
    name: "PV-priority charging",
    tip: "Charge with GoodWe-visible PV first; setpoint is the allowed grid-assist limit.",
  },
  {
    mode: 3,
    tag: "PV-",
    option: "3: PV + battery supply",
    name: "PV + battery supply",
    tip: "PV has priority; setpoint is the allowed battery-discharge limit.",
  },
  {
    mode: 4,
    tag: "IMP",
    option: "4: Inverter import / AC charging",
    name: "Inverter import / AC charging",
    tip: "Inverter-level grid-import target. Not the same as direct battery charge power.",
  },
  {
    mode: 5,
    tag: "EXP",
    option: "5: Inverter export power",
    name: "Inverter export power",
    tip: "Inverter-level AC export target. Site load is not controlled like mode 10.",
  },
  {
    mode: 6,
    tag: "RSV",
    option: "6: Reserve / Conserve",
    name: "Reserve / Conserve",
    tip: "Reserve battery energy for off-grid use. Setpoint is forced to 0 W.",
  },
  {
    mode: 7,
    tag: "OFF",
    option: "7: Off-grid",
    name: "Off-grid",
    tip: "Force off-grid operation. Use only when the installation is prepared for it.",
  },
  {
    mode: 8,
    tag: "HOLD",
    option: "8: Battery Hold",
    name: "Battery Hold",
    tip: "Battery standby: no active charge or discharge. Setpoint is forced to 0 W.",
  },
  {
    mode: 9,
    tag: "BUY",
    option: "9: Grid import target",
    name: "Grid import target",
    tip: "Target net import at the GoodWe smart meter/PCC; battery direction may change to hold it.",
  },
  {
    mode: 10,
    tag: "SELL",
    option: "10: Grid export target",
    name: "Grid export target",
    tip: "Target net export at the GoodWe smart meter/PCC. Use 0 W for a zero-export test.",
  },
  {
    mode: 11,
    tag: "CHG",
    option: "11: Battery charge power",
    name: "Battery charge power",
    tip: "Direct battery charge-power target. PV may contribute; grid can fill the remainder.",
  },
  {
    mode: 12,
    tag: "DIS",
    option: "12: Battery discharge power",
    name: "Battery discharge power",
    tip: "Direct battery discharge-power target, bounded by inverter/BMS limits.",
  },
];

const ZERO_POWER_MODES = new Set([1, 6, 7, 8]);

function finiteNumber(value, fallback = null) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function ensureManualModeStyles(root) {
  if (root.querySelector("#ep-v021-manual-mode-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v021-manual-mode-style";
  style.textContent = `
    .ep-v021-manual-pad {
      margin-top: 14px;
      padding: 12px;
      border: 1px solid rgba(68,174,229,.13);
      border-radius: 14px;
      background: linear-gradient(145deg, rgba(5,28,49,.52), rgba(5,19,36,.70));
    }
    .ep-v021-manual-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 10px;
    }
    .ep-v021-manual-pad.compact .ep-v021-manual-head {
      margin-bottom: 0;
    }
    .ep-v021-manual-kicker {
      color: #65dff4;
      font-size: 8px;
      font-weight: 900;
      letter-spacing: .13em;
    }
    .ep-v021-manual-title {
      margin-top: 2px;
      color: #dff3fb;
      font-size: 12px;
      font-weight: 800;
    }
    .ep-v021-manual-state {
      flex: 0 0 auto;
      padding: 4px 7px;
      border: 1px solid rgba(70,202,220,.16);
      border-radius: 999px;
      color: #81cbd9;
      background: rgba(13,55,72,.32);
      font-size: 7px;
      font-weight: 900;
      letter-spacing: .08em;
    }
    .ep-v021-manual-pad.locked {
      border-color: rgba(124,145,160,.09);
      background: rgba(8,23,37,.46);
    }
    .ep-v021-manual-pad.locked .ep-v021-manual-state {
      color: #8393a0;
      border-color: rgba(130,145,160,.12);
      background: rgba(70,80,90,.18);
    }
    .ep-v021-mode-grid {
      display: grid;
      grid-template-columns: repeat(6, 42px);
      gap: 7px;
      align-items: center;
      justify-content: start;
      margin: 2px 0 12px;
    }
    .ep-v021-mode-button {
      position: relative;
      width: 42px;
      height: 42px;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 1px;
      padding: 0;
      border: 1px solid rgba(74,171,222,.18);
      border-radius: 9px;
      color: #9ab4c5;
      background: rgba(7,35,57,.56);
      cursor: pointer;
      transition: transform .12s ease, border-color .12s ease, color .12s ease, background .12s ease, opacity .12s ease;
      z-index: 2;
    }
    .ep-v021-mode-button strong {
      color: inherit;
      font-size: 13px;
      line-height: 1;
      font-weight: 900;
    }
    .ep-v021-mode-button small {
      color: inherit;
      opacity: .72;
      font-size: 6px;
      line-height: 1;
      font-weight: 900;
      letter-spacing: .05em;
    }
    .ep-v021-mode-button:hover:not([aria-disabled="true"]) {
      transform: translateY(-1px);
      color: #eaffff;
      border-color: rgba(49,222,237,.44);
      background: rgba(10,62,82,.72);
      z-index: 20;
    }
    .ep-v021-mode-button.active {
      color: #eafff8;
      border-color: rgba(39,235,174,.70);
      background: linear-gradient(145deg, rgba(11,105,94,.62), rgba(8,63,82,.72));
      box-shadow: inset 0 0 14px rgba(43,239,184,.10), 0 0 12px rgba(43,239,184,.10);
    }
    .ep-v021-mode-button.pending {
      color: #eafcff;
      border-color: rgba(54,208,244,.62);
      box-shadow: 0 0 12px rgba(54,208,244,.12);
    }
    .ep-v021-manual-pad.locked .ep-v021-mode-button {
      opacity: .28;
      filter: saturate(.45);
      cursor: not-allowed;
    }
    .ep-v021-manual-pad.locked .ep-v021-mode-button.active {
      opacity: 1;
      filter: none;
      cursor: default;
    }
    .ep-v021-mode-button::after {
      content: attr(data-tip);
      position: absolute;
      left: 50%;
      bottom: calc(100% + 7px);
      width: 178px;
      box-sizing: border-box;
      padding: 7px 8px;
      border: 1px solid rgba(85,177,221,.18);
      border-radius: 8px;
      color: #cce5ee;
      background: rgba(3,18,31,.97);
      box-shadow: 0 8px 22px rgba(0,0,0,.32);
      font-size: 8px;
      font-weight: 650;
      line-height: 1.35;
      text-align: left;
      white-space: normal;
      opacity: 0;
      visibility: hidden;
      pointer-events: none;
      transform: translate(-50%, 3px);
      transition: opacity .10s ease, transform .10s ease, visibility .10s ease;
      z-index: 50;
    }
    .ep-v021-mode-button:hover::after,
    .ep-v021-mode-button:focus-visible::after {
      opacity: 1;
      visibility: visible;
      transform: translate(-50%, 0);
    }
    .ep-v021-power-row {
      display: grid;
      grid-template-columns: minmax(0,1fr) auto;
      gap: 10px;
      align-items: center;
      padding-top: 10px;
      border-top: 1px solid rgba(91,167,205,.09);
    }
    .ep-v021-power-label {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 6px;
      color: #809caf;
      font-size: 8px;
    }
    .ep-v021-power-label strong {
      color: #d9edf5;
      font-size: 10px;
    }
    .ep-v021-power-slider {
      width: 100%;
      accent-color: #28dcb3;
      cursor: pointer;
    }
    .ep-v021-power-slider:disabled {
      opacity: .25;
      cursor: not-allowed;
    }
    .ep-v021-power-max {
      min-width: 55px;
      color: #607e91;
      font-size: 8px;
      text-align: right;
    }
    .ep-v021-manual-note {
      margin-top: 8px;
      min-height: 14px;
      color: #617f92;
      font-size: 8px;
      line-height: 1.4;
    }
    .ep-v021-manual-pad.compact .ep-v021-manual-note {
      min-height: 0;
      margin-top: 6px;
    }
    .ep-v021-manual-note strong { color: #a9dfe8; }
    .ep-v021-manual-note.error { color: #ef9b94; }
    .ep-v021-manual-note.ok { color: #69dcae; }
    @media (max-width: 520px) {
      .ep-v021-mode-grid { grid-template-columns: repeat(4, 42px); }
      .ep-v021-mode-button::after { left: 0; transform: translate(0, 3px); }
      .ep-v021-mode-button:hover::after,
      .ep-v021-mode-button:focus-visible::after { transform: translate(0, 0); }
    }
  `;
  root.appendChild(style);
}

function actualMode(panel) {
  return finiteNumber(panel._stateByKey?.("ems_mode")?.state, null);
}

function manualPowerModel(panel) {
  const state = panel._stateByKey?.("manual_power");
  const attrs = state?.attributes || {};
  const value = finiteNumber(state?.state, 0);
  const max = Math.max(0, finiteNumber(attrs.max, 15000));
  const step = Math.max(1, finiteNumber(attrs.step, 100));
  return { value: Math.min(max, Math.max(0, value)), max, step };
}

function selectedDraftPower(panel, model) {
  const draft = finiteNumber(panel.__epV021ManualPowerDraft, null);
  if (panel.__epV021ManualPowerDirty && draft !== null) {
    return Math.min(model.max, Math.max(0, draft));
  }
  panel.__epV021ManualPowerDraft = model.value;
  return model.value;
}

async function persistManualPower(panel, value) {
  const entityId = panel._entityId?.("manual_power");
  if (!entityId) throw new Error("Manual power entity is not available");
  await panel._hass.callService("number", "set_value", {
    entity_id: entityId,
    value,
  });
  panel.__epV021ManualPowerDraft = value;
  panel.__epV021ManualPowerDirty = false;
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

async function applyManualMode(panel, definition) {
  if (panel.__epV021ManualBusy) return;
  const automaticOn = panel._stateByKey?.("automatic_control")?.state === "on";
  if (automaticOn) return;

  const modeEntityId = panel._entityId?.("manual_mode");
  if (!modeEntityId) {
    window.alert("GW EnergyPilot manual mode entity is not available.");
    return;
  }

  if (
    definition.mode === 7 &&
    !window.confirm(
      "Force GoodWe off-grid mode?\n\nMode 7 can materially change inverter operating topology. Continue only if this installation is prepared for off-grid operation."
    )
  ) {
    return;
  }

  const model = manualPowerModel(panel);
  const draftPower = selectedDraftPower(panel, model);
  const commandPower = ZERO_POWER_MODES.has(definition.mode) ? 0 : draftPower;

  panel.__epV021ManualBusy = definition.mode;
  panel.__epV021ManualMessage = {
    tone: "",
    text: `Applying mode ${definition.mode} · ${definition.name}${ZERO_POWER_MODES.has(definition.mode) ? " · 0 W" : ` · ${Math.round(commandPower)} W`}…`,
  };
  requestStableLiveRefresh(panel);

  try {
    if (!ZERO_POWER_MODES.has(definition.mode)) {
      await persistManualPower(panel, commandPower);
    }
    await panel._hass.callService("select", "select_option", {
      entity_id: modeEntityId,
      option: definition.option,
    });
    panel.__epV021ManualMessage = {
      tone: "ok",
      text: `Requested mode ${definition.mode} · ${definition.name}${ZERO_POWER_MODES.has(definition.mode) ? " · 0 W" : ` · ${Math.round(commandPower)} W`}. Waiting for Modbus read-back.`,
    };
  } catch (err) {
    console.error("GW EnergyPilot manual EMS mode failed", err);
    panel.__epV021ManualMessage = {
      tone: "error",
      text: `Manual mode failed: ${err?.message || err}`,
    };
  } finally {
    panel.__epV021ManualBusy = null;
    requestStableLiveRefresh(panel);
  }
}

function installManualModePad(panel, root) {
  if (panel.__epControlSurfaceArchitecture) return;
  const card = root.querySelector(".panel-card.controller");
  if (!card || card.querySelector(".ep-v021-manual-pad")) return;

  ensureManualModeStyles(root);

  const automaticOn = panel._stateByKey?.("automatic_control")?.state === "on";
  const mode = actualMode(panel);
  const modeInfo = MODE_DEFINITIONS.find((item) => item.mode === mode);
  const modeEntityId = panel._entityId?.("manual_mode");
  const powerEntityId = panel._entityId?.("manual_power");
  const model = manualPowerModel(panel);
  const power = selectedDraftPower(panel, model);
  const actualSetpoint = finiteNumber(panel._stateByKey?.("ems_setpoint")?.state, null);
  const controlsReady = Boolean(modeEntityId && powerEntityId);
  const locked = automaticOn || !controlsReady;
  const compact = !controlsReady || automaticOn;

  const pad = document.createElement("section");
  pad.id = "ep-v021-manual-pad";
  pad.className = `ep-v021-manual-pad${locked ? " locked" : ""}${compact ? " compact" : ""}`;
  pad.setAttribute("aria-labelledby", "ep-v021-manual-title");
  pad.innerHTML = `
    <div class="ep-v021-manual-head">
      <div>
        <div class="ep-v021-manual-kicker">MANUAL EMS TEST</div>
        <div class="ep-v021-manual-title" id="ep-v021-manual-title">GoodWe modes 1–12</div>
      </div>
      <span class="ep-v021-manual-state" aria-live="polite">${automaticOn ? "LOCKED · AUTOMATIC" : controlsReady ? "MANUAL READY" : "ENTITIES MISSING"}</span>
    </div>
    <div class="ep-v021-mode-grid"${compact ? " hidden" : ""}>
      ${MODE_DEFINITIONS.map((definition) => {
        const active = definition.mode === mode;
        const pending = definition.mode === panel.__epV021ManualBusy;
        const tip = `${definition.mode} · ${definition.name} — ${definition.tip}`;
        return `<button
          type="button"
          class="ep-v021-mode-button${active ? " active" : ""}${pending ? " pending" : ""}"
          data-mode="${definition.mode}"
          data-tip="${panel._escape(tip)}"
          aria-label="${panel._escape(tip)}"
          aria-disabled="${locked || Boolean(panel.__epV021ManualBusy) ? "true" : "false"}"
          ${locked || panel.__epV021ManualBusy ? "disabled" : ""}>
          <strong>${definition.mode}</strong>
          <small>${definition.tag}</small>
        </button>`;
      }).join("")}
    </div>
    <div class="ep-v021-power-row"${compact ? " hidden" : ""}>
      <div>
        <div class="ep-v021-power-label">
          <span>Manual setpoint</span>
          <strong data-manual-power-value>${Math.round(power)} W</strong>
        </div>
        <input
          type="range"
          class="ep-v021-power-slider"
          min="0"
          max="${Math.round(model.max)}"
          step="${Math.round(model.step)}"
          value="${Math.round(power)}"
          ${locked || panel.__epV021ManualBusy ? "disabled" : ""}
          aria-label="Manual GoodWe EMS power setpoint">
      </div>
      <div class="ep-v021-power-max">max ${panel._escape(panel._formatPower(model.max))}</div>
    </div>
    <div class="ep-v021-manual-note ${panel._escape(panel.__epV021ManualMessage?.tone || "")}" data-manual-note>
      ${panel.__epV021ManualMessage
        ? panel._escape(panel.__epV021ManualMessage.text)
        : automaticOn
          ? `<strong>Automatic Control owns the inverter.</strong> Controls are locked; active mode ${panel._escape(mode ?? "—")} still follows live read-back.`
          : !controlsReady
            ? `<strong>Manual controls are unavailable.</strong> The required Home Assistant entities are missing.`
            : `<strong>Live:</strong> mode ${panel._escape(mode ?? "—")}${modeInfo ? ` · ${panel._escape(modeInfo.name)}` : ""} · ${actualSetpoint === null ? "—" : `${Math.round(actualSetpoint)} W`}. Hover a mode for its meaning.`}
    </div>`;

  card.appendChild(pad);

  const slider = pad.querySelector(".ep-v021-power-slider");
  const valueNode = pad.querySelector("[data-manual-power-value]");
  if (slider) {
    slider.addEventListener("input", () => {
      const liveAutomaticOn =
        panel._stateByKey?.("automatic_control")?.state === "on";
      const liveControlsReady = Boolean(
        panel._entityId?.("manual_mode") && panel._entityId?.("manual_power")
      );
      if (slider.disabled || liveAutomaticOn || !liveControlsReady || panel.__epV021ManualBusy) return;
      const value = Math.min(model.max, Math.max(0, finiteNumber(slider.value, 0)));
      panel.__epV021ManualPowerDraft = value;
      panel.__epV021ManualPowerDirty = true;
      if (valueNode) valueNode.textContent = `${Math.round(value)} W`;
    });
    slider.addEventListener("change", async () => {
      const liveAutomaticOn =
        panel._stateByKey?.("automatic_control")?.state === "on";
      const liveControlsReady = Boolean(
        panel._entityId?.("manual_mode") && panel._entityId?.("manual_power")
      );
      if (slider.disabled || liveAutomaticOn || !liveControlsReady || panel.__epV021ManualBusy) return;
      const value = Math.min(model.max, Math.max(0, finiteNumber(slider.value, 0)));
      try {
        await persistManualPower(panel, value);
      } catch (err) {
        console.error("GW EnergyPilot manual power update failed", err);
        panel.__epV021ManualMessage = {
          tone: "error",
          text: `Manual power update failed: ${err?.message || err}`,
        };
        requestStableLiveRefresh(panel);
      }
    });
  }

  pad.querySelectorAll(".ep-v021-mode-button").forEach((button) => {
    button.addEventListener("click", () => {
      const liveAutomaticOn =
        panel._stateByKey?.("automatic_control")?.state === "on";
      const liveControlsReady = Boolean(
        panel._entityId?.("manual_mode") && panel._entityId?.("manual_power")
      );
      if (button.disabled || liveAutomaticOn || !liveControlsReady || panel.__epV021ManualBusy) return;
      const definition = MODE_DEFINITIONS.find(
        (item) => item.mode === Number(button.dataset.mode)
      );
      if (definition) applyManualMode(panel, definition);
    });
  });
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV021Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  installManualModePad(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
};
