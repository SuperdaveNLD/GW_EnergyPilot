import "./gw-energy-pilot-v014.js?v=0.47-custom-battery1";

const VERSION = "0.15";
const PANEL_NAME = "gw-energypilot-panel";

function ensureStyles(root) {
  if (root.querySelector("#ep-v015-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v015-style";
  style.textContent = `
    .ep-v015-costfun {
      margin: 11px 0 4px;
      padding: 10px 11px;
      border: 1px solid rgba(81, 181, 230, .13);
      border-radius: 11px;
      background: rgba(5, 27, 49, .34);
    }
    .ep-v015-costfun-head {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 8px;
    }
    .ep-v015-costfun-head strong {
      color: #dff6ff;
      font-size: 10px;
      letter-spacing: .04em;
    }
    .ep-v015-costfun-head span {
      color: #6e8da5;
      font-size: 8px;
    }
    .ep-v015-costfun-actions {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 7px;
    }
    .ep-v015-costfun-button {
      min-width: 0;
      min-height: 38px;
      padding: 7px 6px;
      border-radius: 10px;
      border: 1px solid rgba(67, 204, 238, .20);
      background: rgba(7, 45, 69, .50);
      color: #bdeef6;
      font-size: 9px;
      font-weight: 850;
      letter-spacing: .035em;
      cursor: pointer;
    }
    .ep-v015-costfun-button:hover:not(:disabled) {
      border-color: rgba(47, 236, 190, .46);
      color: #efffff;
      background: rgba(10, 68, 81, .62);
    }
    .ep-v015-costfun-button:disabled {
      opacity: .42;
      cursor: not-allowed;
    }
    .ep-v015-costfun-note {
      margin-top: 7px;
      color: #607d94;
      font-size: 8px;
      line-height: 1.4;
    }
    @media (max-width: 720px) {
      .ep-v015-costfun-actions { grid-template-columns: 1fr; }
    }
  `;
  root.appendChild(style);
}

async function selectCostFunction(panel, button, entityId, label) {
  if (!entityId || button.disabled) return;
  const original = button.textContent;
  button.disabled = true;
  button.textContent = "Applying…";
  try {
    await panel._hass.callService("button", "press", { entity_id: entityId });
  } catch (err) {
    console.error(`GW EnergyPilot: unable to select EMHASS ${label}`, err);
    window.alert(`EMHASS cost function update failed: ${err?.message || err}`);
  } finally {
    button.disabled = false;
    button.textContent = original;
    panel._queueRender();
  }
}

function installCostFunctionActions(panel, root) {
  const card = root.querySelector(".panel-card.emhass");
  if (!card || card.querySelector(".ep-v015-costfun")) return;

  const definitions = [
    ["emhass_costfun_profit", "Profit", "profit"],
    ["emhass_costfun_cost", "Cost", "cost"],
    ["emhass_costfun_self_consumption", "Self-consumption", "self-consumption"],
  ];

  const wrap = document.createElement("div");
  wrap.className = "ep-v015-costfun";
  wrap.innerHTML = `
    <div class="ep-v015-costfun-head">
      <strong>EMHASS cost function</strong>
      <span>config.json · costfun</span>
    </div>
    <div class="ep-v015-costfun-actions"></div>
    <div class="ep-v015-costfun-note">Selecting a strategy writes the complete current EMHASS configuration back with only <strong>costfun</strong> changed, then immediately creates and publishes a fresh optimization. GoodWe control still follows the existing P_batt mapping in v0.15.</div>`;

  const actions = wrap.querySelector(".ep-v015-costfun-actions");
  for (const [key, label, value] of definitions) {
    const entityId = panel._entityId(key);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "ep-v015-costfun-button";
    button.textContent = label;
    button.title = `Set EMHASS costfun to ${value} and run a fresh optimization`;
    button.disabled = !entityId;
    button.addEventListener("click", () =>
      selectCostFunction(panel, button, entityId, value)
    );
    actions.appendChild(button);
  }

  const socControls = card.querySelector(".ep-v011-soc-controls");
  const orchestrator = card.querySelector(".ep-v010-orchestrator");
  if (socControls) socControls.insertAdjacentElement("beforebegin", wrap);
  else if (orchestrator) orchestrator.insertAdjacentElement("afterend", wrap);
  else card.appendChild(wrap);
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV015Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  ensureStyles(root);
  installCostFunctionActions(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION}`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION}`;
};
