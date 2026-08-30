import "./gw-energy-pilot-v015.js?v=1.0.1-beta1";

const VERSION = "0.16";
const PANEL_NAME = "gw-energypilot-panel";

const STRATEGIES = [
  { option: "Profit", raw: "profit", label: "Profit", legacyKey: "emhass_costfun_profit" },
  { option: "Cost", raw: "cost", label: "Cost", legacyKey: "emhass_costfun_cost" },
  { option: "Self-consumption", raw: "self-consumption", label: "Self-consumption", legacyKey: "emhass_costfun_self_consumption" },
];

function valueText(value, suffix = "") {
  if (value === null || value === undefined || value === "") return "—";
  return `${value}${suffix}`;
}

function betaRow(panel, label, value, suffix, marker) {
  return `<div class="ep-v011-diag-row" data-v016-beta="${marker}"><span>${panel._escape(label)}</span><strong>${panel._escape(valueText(value, suffix))}</strong></div>`;
}

function betaSnapshot(attrs) {
  const fields = [
    ["SOC protection candidate 47500", attrs.battery_soc_protection_47500],
    ["On-grid discharge depth candidate 45356", attrs.battery_discharge_depth_on_grid_45356],
    ["Off-grid discharge depth candidate 45358", attrs.battery_discharge_depth_off_grid_45358],
    ["Extended grid export candidate 36104 kWh", attrs.meter_total_energy_export_extended_candidate],
    ["Extended grid import candidate 36120 kWh", attrs.meter_total_energy_import_extended_candidate],
    ["Legacy grid export 36015 kWh", attrs.meter_total_energy_export],
    ["Legacy grid import 36017 kWh", attrs.meter_total_energy_import],
    ["Battery SOC", attrs.battery_soc],
    ["EMS mode 47511", attrs.ems_mode],
    ["EMS setpoint 47512", attrs.ems_setpoint],
  ];
  return [
    "GW EnergyPilot v0.16 beta G20 diagnostics",
    "Read-only candidate registers; do not treat semantics as confirmed.",
    ...fields.map(([label, value]) => `${label}: ${value ?? "—"}`),
  ].join("\n");
}

function ensureStrategyStyles(root) {
  if (root.querySelector("#ep-v016-strategy-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v016-strategy-style";
  style.textContent = `
    .ep-v016-costfun {
      margin: 11px 0 4px;
      padding: 11px;
      border: 1px solid rgba(81, 181, 230, .15);
      border-radius: 12px;
      background: rgba(5, 27, 49, .38);
    }
    .ep-v016-costfun-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 9px;
    }
    .ep-v016-costfun-title {
      color: #dff6ff;
      font-size: 10px;
      font-weight: 850;
      letter-spacing: .04em;
    }
    .ep-v016-costfun-active {
      padding: 4px 7px;
      border-radius: 999px;
      border: 1px solid rgba(45, 238, 181, .35);
      background: rgba(17, 105, 83, .28);
      color: #91f5d0;
      font-size: 8px;
      font-weight: 850;
      letter-spacing: .06em;
      text-transform: uppercase;
      white-space: nowrap;
    }
    .ep-v016-costfun-active.pending {
      border-color: rgba(91, 179, 226, .22);
      background: rgba(20, 65, 94, .24);
      color: #7d9db4;
    }
    .ep-v016-costfun-actions {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 7px;
    }
    .ep-v016-costfun-button {
      min-width: 0;
      min-height: 40px;
      padding: 7px 8px;
      border-radius: 10px;
      border: 1px solid rgba(67, 204, 238, .20);
      background: rgba(7, 45, 69, .50);
      color: #a9d8e5;
      font-size: 9px;
      font-weight: 850;
      letter-spacing: .035em;
      cursor: pointer;
      transition: border-color .12s linear, background-color .12s linear, color .12s linear;
    }
    .ep-v016-costfun-button:hover:not(:disabled):not(.active) {
      border-color: rgba(47, 236, 190, .46);
      color: #efffff;
      background: rgba(10, 68, 81, .62);
    }
    .ep-v016-costfun-button.active {
      border-color: rgba(35, 242, 179, .68);
      background: linear-gradient(145deg, rgba(15, 105, 107, .58), rgba(9, 64, 80, .70));
      color: #e9fff7;
      box-shadow: inset 0 0 16px rgba(30, 241, 176, .08), 0 0 12px rgba(30, 241, 176, .08);
      cursor: default;
    }
    .ep-v016-costfun-button:disabled {
      opacity: .42;
      cursor: not-allowed;
    }
    .ep-v016-costfun-note {
      margin-top: 8px;
      color: #637f96;
      font-size: 8px;
      line-height: 1.45;
    }
    @media (max-width: 720px) {
      .ep-v016-costfun-head { align-items: flex-start; flex-direction: column; }
      .ep-v016-costfun-actions { grid-template-columns: 1fr; }
    }
  `;
  root.appendChild(style);
}

function activeRawValue(panel) {
  const state = panel._stateByKey("emhass_cost_function");
  if (!state || ["unknown", "unavailable"].includes(state.state)) return null;
  const raw = state.attributes?.emhass_costfun;
  if (raw) return String(raw);
  return STRATEGIES.find((item) => item.option === state.state)?.raw || null;
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

async function chooseStrategy(panel, definition) {
  if (panel.__epV016CostfunBusy) return;
  const activeRaw = activeRawValue(panel);
  if (definition.raw === activeRaw) return;

  const selectEntityId = panel._entityId("emhass_cost_function");
  const fallbackEntityId = panel._entityId(definition.legacyKey);
  if (!selectEntityId && !fallbackEntityId) return;

  panel.__epV016CostfunBusy = definition.raw;
  requestStableLiveRefresh(panel);

  try {
    if (selectEntityId) {
      await panel._hass.callService("select", "select_option", {
        entity_id: selectEntityId,
        option: definition.option,
      });
    } else {
      await panel._hass.callService("button", "press", {
        entity_id: fallbackEntityId,
      });
    }
  } catch (err) {
    console.error("GW EnergyPilot: EMHASS strategy change failed", err);
    window.alert(err?.message || String(err));
  } finally {
    panel.__epV016CostfunBusy = null;
    requestStableLiveRefresh(panel);
  }
}

function installStrategySelector(panel, root) {
  const old = root.querySelector(".ep-v015-costfun");
  if (!old) return;

  const activeRaw = activeRawValue(panel);
  const activeDefinition = STRATEGIES.find((item) => item.raw === activeRaw);
  const selectEntityId = panel._entityId("emhass_cost_function");
  const busyRaw = panel.__epV016CostfunBusy || null;

  const wrap = document.createElement("div");
  wrap.className = "ep-v016-costfun";
  wrap.innerHTML = `
    <div class="ep-v016-costfun-head">
      <span class="ep-v016-costfun-title">EMHASS optimization strategy</span>
      <span class="ep-v016-costfun-active ${busyRaw || !activeDefinition ? "pending" : ""}">
        ${busyRaw
          ? `Applying · ${panel._escape(STRATEGIES.find((item) => item.raw === busyRaw)?.label || busyRaw)}…`
          : activeDefinition
            ? `Active · ${panel._escape(activeDefinition.label)}`
            : "Reading active strategy…"}
      </span>
    </div>
    <div class="ep-v016-costfun-actions"></div>
    <div class="ep-v016-costfun-note">
      This is one persistent EMHASS setting, not three independent modes. The highlighted option is the current <strong>costfun</strong> read from EMHASS. Changing it saves the setting and immediately requests a fresh optimization. GoodWe execution remains P_batt-driven in v0.16.
    </div>`;

  wrap.setAttribute("aria-busy", busyRaw ? "true" : "false");
  const actions = wrap.querySelector(".ep-v016-costfun-actions");
  for (const definition of STRATEGIES) {
    const fallbackEntityId = panel._entityId(definition.legacyKey);
    const isActive = definition.raw === activeRaw;
    const button = document.createElement("button");
    button.type = "button";
    button.className = `ep-v016-costfun-button${isActive ? " active" : ""}`;
    button.dataset.costfun = definition.raw;
    button.dataset.costfunLabel = definition.label;
    button.setAttribute("aria-pressed", isActive ? "true" : "false");
    button.textContent = busyRaw === definition.raw
      ? "Applying…"
      : `${isActive ? "✓ " : ""}${definition.label}`;
    button.title = isActive
      ? `${definition.label} is the active EMHASS cost function`
      : `Set EMHASS costfun to ${definition.raw} and run a fresh optimization`;
    button.disabled = Boolean(busyRaw) || (!selectEntityId && !fallbackEntityId);
    button.addEventListener("click", () => chooseStrategy(panel, definition));
    actions.appendChild(button);
  }

  old.replaceWith(wrap);
}

function enrichBetaDiagnostics(panel, root) {
  const card = root.querySelector(".panel-card.diagnostics");
  if (!card) return;

  const optimizeId = panel._entityId("optimize_now");
  const attrs = (optimizeId ? panel._state(optimizeId)?.attributes : null) || {};
  const group = card.querySelector(".ep-v011-diag-group");

  if (group && !group.querySelector('[data-v016-beta="soc-protection"]')) {
    group.insertAdjacentHTML(
      "beforeend",
      betaRow(panel, "BETA · SOC protection 47500", attrs.battery_soc_protection_47500, "", "soc-protection") +
      betaRow(panel, "BETA · On-grid discharge depth 45356", attrs.battery_discharge_depth_on_grid_45356, "%", "soc-on-grid") +
      betaRow(panel, "BETA · Off-grid discharge depth 45358", attrs.battery_discharge_depth_off_grid_45358, "%", "soc-off-grid") +
      betaRow(panel, "BETA · Extended grid export 36104", attrs.meter_total_energy_export_extended_candidate, " kWh", "grid-export") +
      betaRow(panel, "BETA · Extended grid import 36120", attrs.meter_total_energy_import_extended_candidate, " kWh", "grid-import")
    );
  }

  if (!card.querySelector(".ep-v016-beta-note")) {
    const note = document.createElement("div");
    note.className = "ep-v011-diag-note ep-v016-beta-note";
    note.textContent = "BETA / read-only: 45356, 45358, 47500, 36104 and 36120 are collected for ETA-G20 field validation. They are not used for control or canonical energy accounting.";
    card.appendChild(note);
  }

  if (!card.querySelector(".ep-v016-copy")) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "ep-v011-copy ep-v016-copy";
    button.textContent = "Copy beta diagnostics";
    button.addEventListener("click", async () => {
      const text = betaSnapshot(attrs);
      try {
        await navigator.clipboard.writeText(text);
        const previous = button.textContent;
        button.textContent = "Copied";
        setTimeout(() => { button.textContent = previous; }, 1200);
      } catch (_err) {
        window.prompt("Copy EnergyPilot beta diagnostics", text);
      }
    });
    card.appendChild(button);
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV016Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  ensureStrategyStyles(root);
  installStrategySelector(this, root);
  enrichBetaDiagnostics(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
};
