import "./gw-energy-pilot-v029.js?v=1.3.0-beta.1";

const VERSION = "0.30";
const PANEL_NAME = "gw-energypilot-panel";
const BATTERY_PLAN_CARD = ".ep-v027-battery-plan-card";

function reconcileBatteryPlanCards(root) {
  const cards = [...root.querySelectorAll(BATTERY_PLAN_CARD)];
  if (cards.length <= 1) return;

  // Prefer a card already decorated by the window-controls layer. This also
  // repairs an already-open browser session that entered the new release with
  // duplicate cards from a previously stacked render wrapper.
  const canonical =
    cards.find((card) =>
      card.querySelector(".ep-v031-card-windowbar, .ep-v028-window-controls")
    ) || cards[0];
  for (const card of cards) {
    if (card !== canonical) card.remove();
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (!PanelClass.prototype.__epV030RenderInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype.__epV030RenderInstalled = true;

  PanelClass.prototype._render = function energyPilotV030Render() {
    previousRender.call(this);
    const root = this.shadowRoot;
    if (!root) return;

    reconcileBatteryPlanCards(root);

    const versionBadge = root.querySelector(".version");
    if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;

    const footerItems = root.querySelectorAll("footer span");
    if (footerItems.length > 0) {
      footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
    }
  };
}
