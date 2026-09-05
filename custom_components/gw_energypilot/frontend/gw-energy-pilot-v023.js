import "./gw-energy-pilot-v022-flow-direction.js?v=1.3.0-beta.3";

const VERSION = "0.23";
const PANEL_NAME = "gw-energypilot-panel";

function finiteNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function formatEnergy(value) {
  const number = finiteNumber(value);
  return number === null
    ? "—"
    : `${number.toFixed(number >= 10 ? 1 : 2)} kWh`;
}

function accountingTotals(panel) {
  const imported = panel._stateByKey?.("grid_energy_imported_today");
  const exported = panel._stateByKey?.("grid_energy_exported_today");
  if (!imported || !exported) return null;

  return {
    at: Date.now(),
    todayImport: finiteNumber(imported.state),
    todayExport: finiteNumber(exported.state),
    yesterdayImport: finiteNumber(imported.attributes?.last_period),
    yesterdayExport: finiteNumber(exported.attributes?.last_period),
    day: imported.attributes?.accounting_day || null,
    bootstrapComplete:
      imported.attributes?.bootstrap_complete === true &&
      exported.attributes?.bootstrap_complete === true,
  };
}

function summaryHtml(totals) {
  return `
    <div class="ep-v013-grid-daily ep-v023-accounting-grid-daily">
      <div class="ep-v013-grid-day"><strong>Today</strong><br>↓ ${formatEnergy(totals.todayImport)} · ↑ ${formatEnergy(totals.todayExport)}</div>
      <div class="ep-v013-grid-day"><strong>Yesterday</strong><br>↓ ${formatEnergy(totals.yesterdayImport)} · ↑ ${formatEnergy(totals.yesterdayExport)}</div>
    </div>`;
}

function renderAccountingSummary(panel, root) {
  const totals = accountingTotals(panel);
  if (!totals) return;

  // Keep the legacy v0.13 cache aligned so the old layered renderer does not
  // launch a competing Recorder-only daily calculation on later renders.
  panel.__epV013GridDaily = totals;

  const card = root.querySelector(".energy-card.grid");
  const hint = card?.querySelector(".ep-v013-grid-hint");
  if (!card || !hint) return;

  card.querySelector(".ep-v013-grid-daily")?.remove();
  hint.insertAdjacentHTML("beforebegin", summaryHtml(totals));
}

function patchOpenGridModal(panel) {
  const started = Date.now();

  const patch = () => {
    const modal = document.querySelector(".ep13-backdrop");
    const stats = modal?.querySelectorAll(".ep13-stat strong");
    if (!modal || !stats || stats.length < 4) {
      if (Date.now() - started < 5000) window.setTimeout(patch, 50);
      return;
    }

    const totals = accountingTotals(panel);
    if (!totals) return;

    stats[0].textContent = formatEnergy(totals.todayImport);
    stats[1].textContent = formatEnergy(totals.todayExport);
    stats[2].textContent = formatEnergy(totals.yesterdayImport);
    stats[3].textContent = formatEnergy(totals.yesterdayExport);

    const note = modal.querySelector(".ep13-note");
    if (note && !note.dataset.epV023Accounting) {
      note.dataset.epV023Accounting = "1";
      note.textContent =
        "Signed graph: export is above zero, import below zero. Daily import/export totals come from EnergyPilot's persistent accounting layer, derived from the canonical GoodWe lifetime counters. Recorder is only used once to bootstrap an existing installation when boundary history is available.";
    }
  };

  window.setTimeout(patch, 0);
}

function installGridAccountingInteraction(panel, root) {
  const card = root.querySelector(".energy-card.grid");
  if (!card || card.dataset.epV023Accounting === "1") return;
  card.dataset.epV023Accounting = "1";

  card.addEventListener("click", () => patchOpenGridModal(panel));
  card.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      patchOpenGridModal(panel);
    }
  });
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV023Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  renderAccountingSummary(this, root);
  installGridAccountingInteraction(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
  }
};
