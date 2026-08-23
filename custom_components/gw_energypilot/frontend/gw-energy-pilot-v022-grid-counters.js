import "./gw-energy-pilot-v022.js?v=0.22-pcc1";

const PANEL_NAME = "gw-energypilot-panel";
const DAILY_CACHE_MS = 5 * 60 * 1000;

function formatEnergy(value) {
  return Number.isFinite(value)
    ? `${value.toFixed(value >= 10 ? 1 : 2)} kWh`
    : "—";
}

function localDayBounds(offsetDays = 0) {
  const now = new Date();
  const start = new Date(
    now.getFullYear(),
    now.getMonth(),
    now.getDate() + offsetDays
  );
  const end = offsetDays === 0
    ? now
    : new Date(
        now.getFullYear(),
        now.getMonth(),
        now.getDate() + offsetDays + 1
      );
  return { start, end };
}

function finiteHistoryState(row) {
  const raw = row?.s;
  if (
    raw === null ||
    raw === undefined ||
    raw === "" ||
    raw === "unknown" ||
    raw === "unavailable"
  ) {
    return null;
  }
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
}

async function statisticChange(panel, entityId, start, end) {
  if (!entityId || !panel._hass?.callWS) return null;

  try {
    const result = await panel._hass.callWS({
      type: "recorder/statistic_during_period",
      statistic_id: entityId,
      fixed_period: {
        start_time: start.toISOString(),
        end_time: end.toISOString(),
      },
      types: ["change"],
    });

    // Home Assistant legitimately returns change=null while statistics are
    // warming up or when a complete boundary value is not available. Do not
    // coerce null through Number(null), because that falsely becomes 0 kWh.
    const rawChange = result?.change;
    if (rawChange === null || rawChange === undefined || rawChange === "") {
      return null;
    }

    const value = Number(rawChange);
    return Number.isFinite(value) && value >= 0 ? value : null;
  } catch (err) {
    console.debug(
      "GW EnergyPilot: daily grid statistic unavailable, trying history",
      err
    );
    return null;
  }
}

async function historyCounterChange(panel, entityId, start, end) {
  if (!entityId || !panel._hass?.callWS) return null;

  try {
    const result = await panel._hass.callWS({
      type: "history/history_during_period",
      start_time: start.toISOString(),
      end_time: end.toISOString(),
      entity_ids: [entityId],
      include_start_time_state: true,
      significant_changes_only: false,
      minimal_response: true,
      no_attributes: true,
    });

    const values = (result?.[entityId] || [])
      .map(finiteHistoryState)
      .filter((value) => value !== null);

    if (values.length < 2) return null;

    const change = values[values.length - 1] - values[0];

    // 36015/36017 are lifetime counters and should be monotonic. A decrease
    // is not silently interpreted as energy usage; leave it unavailable so a
    // reset, bad sample or future register semantic change cannot create a
    // false daily total.
    return Number.isFinite(change) && change >= 0 ? change : null;
  } catch (err) {
    console.debug("GW EnergyPilot: daily grid history unavailable", err);
    return null;
  }
}

async function dailyCounterChange(panel, entityId, start, end) {
  const statistic = await statisticChange(panel, entityId, start, end);
  if (statistic !== null) return statistic;
  return historyCounterChange(panel, entityId, start, end);
}

async function loadReliableDailyGridTotals(panel, force = false) {
  const now = Date.now();
  const cached = panel.__epV022ReliableGridDaily;
  if (!force && cached && now - cached.at < DAILY_CACHE_MS) {
    return cached;
  }
  if (panel.__epV022ReliableGridDailyPromise) {
    return panel.__epV022ReliableGridDailyPromise;
  }

  const importId = panel._entityId?.("meter_total_energy_import");
  const exportId = panel._entityId?.("meter_total_energy_export");
  if (!importId || !exportId) return null;

  const today = localDayBounds(0);
  const yesterday = localDayBounds(-1);

  panel.__epV022ReliableGridDailyPromise = Promise.all([
    dailyCounterChange(panel, importId, today.start, today.end),
    dailyCounterChange(panel, exportId, today.start, today.end),
    dailyCounterChange(panel, importId, yesterday.start, yesterday.end),
    dailyCounterChange(panel, exportId, yesterday.start, yesterday.end),
  ])
    .then(([todayImport, todayExport, yesterdayImport, yesterdayExport]) => {
      const totals = {
        at: Date.now(),
        todayImport,
        todayExport,
        yesterdayImport,
        yesterdayExport,
      };
      panel.__epV022ReliableGridDaily = totals;

      // Keep the legacy v0.13 cache aligned as well. Older rendering code may
      // still read it because the frontend is deliberately layered by release.
      panel.__epV013GridDaily = totals;
      return totals;
    })
    .finally(() => {
      panel.__epV022ReliableGridDailyPromise = null;
    });

  return panel.__epV022ReliableGridDailyPromise;
}

function dailySummaryHtml(totals) {
  if (!totals) return "";
  return `
    <div class="ep-v013-grid-daily ep-v022-reliable-grid-daily">
      <div class="ep-v013-grid-day"><strong>Today</strong><br>↓ ${formatEnergy(totals.todayImport)} · ↑ ${formatEnergy(totals.todayExport)}</div>
      <div class="ep-v013-grid-day"><strong>Yesterday</strong><br>↓ ${formatEnergy(totals.yesterdayImport)} · ↑ ${formatEnergy(totals.yesterdayExport)}</div>
    </div>`;
}

function renderReliableDailyGridTotals(panel, root, totals) {
  const card = root.querySelector(".energy-card.grid");
  if (!card) return;

  card.querySelector(".ep-v013-grid-daily")?.remove();
  if (!totals) return;

  const hint = card.querySelector(".ep-v013-grid-hint");
  if (hint) {
    hint.insertAdjacentHTML("beforebegin", dailySummaryHtml(totals));
  }
}

function patchGridModalWhenReady(panel, totalsPromise) {
  const started = Date.now();

  const patch = async () => {
    const modal = document.querySelector(".ep13-backdrop");
    const stats = modal?.querySelectorAll(".ep13-stat strong");

    if (!stats || stats.length < 4) {
      if (Date.now() - started < 5000) {
        window.setTimeout(patch, 50);
      }
      return;
    }

    const totals = await totalsPromise;
    if (!totals || !document.body.contains(modal)) return;

    stats[0].textContent = formatEnergy(totals.todayImport);
    stats[1].textContent = formatEnergy(totals.todayExport);
    stats[2].textContent = formatEnergy(totals.yesterdayImport);
    stats[3].textContent = formatEnergy(totals.yesterdayExport);

    const note = modal.querySelector(".ep13-note");
    if (note && !note.dataset.epReliableCounters) {
      note.dataset.epReliableCounters = "1";
      note.textContent +=
        " Daily totals prefer Home Assistant statistics and fall back to cumulative Recorder history while statistics are warming up; missing data is shown as — instead of 0 kWh.";
    }
  };

  window.setTimeout(patch, 0);
}

function installReliableGridCounters(panel, root) {
  const card = root.querySelector(".energy-card.grid");
  if (!card) return;

  const cached = panel.__epV022ReliableGridDaily;
  renderReliableDailyGridTotals(panel, root, cached || null);

  const totalsPromise = loadReliableDailyGridTotals(panel).then((totals) => {
    if (totals && panel.shadowRoot) {
      renderReliableDailyGridTotals(panel, panel.shadowRoot, totals);
    }
    return totals;
  });

  if (!card.dataset.epReliableCounters) {
    card.dataset.epReliableCounters = "1";
    card.addEventListener("click", () => {
      patchGridModalWhenReady(panel, loadReliableDailyGridTotals(panel, true));
    });
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        patchGridModalWhenReady(panel, loadReliableDailyGridTotals(panel, true));
      }
    });
  }

  void totalsPromise;
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotReliableGridCountersRender() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  installReliableGridCounters(this, root);
};
