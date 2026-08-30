import "./gw-energy-pilot-v019.js?v=0.49-consolidated1";

const VERSION = "0.19";
const PANEL_NAME = "gw-energypilot-panel";

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV019ConsolidatedRender() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  const strategyNote = root.querySelector(".ep-v016-costfun-note");
  if (strategyNote) {
    strategyNote.innerHTML = "This is one persistent EMHASS setting. Automatic control still uses <strong>P_batt</strong> for battery direction and maximum requested power, and also reads <strong>P_grid</strong>: when EMHASS plans battery charging with grid flow around 0 W, EnergyPilot limits mode 11 from the live GoodWe smart meter instead of importing power just to satisfy an optimistic PV forecast.";
  }

  const command = this._stateByKey?.("control_command")?.state;
  const controllerCard = root.querySelector(".panel-card.controller");
  if (
    controllerCard &&
    command?.startsWith("grid_neutral") &&
    !controllerCard.querySelector(".ep-v019-grid-neutral-note")
  ) {
    const note = document.createElement("div");
    note.className = "ep-v019-grid-neutral-note";
    note.style.cssText = "margin-top:10px;color:#708ba1;font-size:9px;line-height:1.45";
    note.textContent = "Grid-neutral charge active · 30 s meter feedback · fast import reduction · 2 min anti-flap hold before a stopped charge can restart.";
    controllerCard.appendChild(note);
  }

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
};
