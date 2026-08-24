export const VERSION = "0.27";
export const PANEL_NAME = "gw-energypilot-panel";
export const DATA_CACHE_MS = 5 * 60 * 1000;
export const DASHBOARD_STORAGE_KEY = "gw_energypilot_dashboard_v008";
export const CARD_ID = "battery-price";
const VALID_SIZES = new Set(["compact", "normal", "large"]);

const TEXT = {
  en: {
    title: "BATTERY · PLAN · PRICE",
    subtitle: "Today · actual battery power, active EMHASS plan and market price",
    powerAxis: "Power (kW)", priceAxis: "Price ({currency}/kWh)",
    actualCharge: "Actual charging", actualDischarge: "Actual discharging",
    actual: "Actual", plan: "EMHASS plan", marketPrice: "Market price",
    chargedToday: "Charged today", dischargedToday: "Discharged today",
    plannedCharge: "Plan charge", plannedDischarge: "Plan discharge",
    currentPrice: "Current price", goodweCounter: "GoodWe day counter",
    graphEstimate: "Graph estimate ± {value}", approximate: "Approx. from Recorder",
    planHistory: "Past plan = Recorder history of the published P_batt target; future plan = current EMHASS forecast horizon.",
    energySource: "Daily totals use GoodWe 35208/35211 when available. Recorder integration remains visible as a comparison.",
    noActual: "Recorder has not collected enough actual battery-power statistics yet.",
    noPlan: "No usable EMHASS P_batt history or forecast horizon is available yet.",
    noPrice: "The market-price line is unavailable until timestamped runtime prices can be loaded.",
    discrepancy: "The native GoodWe day counter and the visual 5-minute integration differ. The counter is used for the headline total.",
    now: "NOW", updated: "updated {time}", waiting: "waiting for data",
    expand: "Open large graph", details: "Open detailed graph", close: "Close",
    compact: "Compact", normal: "Normal", large: "Large",
    refresh: "Refresh chart data", future: "Forecast",
  },
  nl: {
    title: "ACCU · PLAN · PRIJS",
    subtitle: "Vandaag · werkelijk accuvermogen, actief EMHASS-plan en marktprijs",
    powerAxis: "Vermogen (kW)", priceAxis: "Prijs ({currency}/kWh)",
    actualCharge: "Werkelijk laden", actualDischarge: "Werkelijk ontladen",
    actual: "Werkelijk", plan: "EMHASS-plan", marketPrice: "Marktprijs",
    chargedToday: "Vandaag geladen", dischargedToday: "Vandaag ontladen",
    plannedCharge: "Gepland laden", plannedDischarge: "Gepland ontladen",
    currentPrice: "Huidige prijs", goodweCounter: "GoodWe-dagteller",
    graphEstimate: "Grafiekbenadering ± {value}", approximate: "Benadering uit Recorder",
    planHistory: "Verleden plan = Recorder-historie van het gepubliceerde P_batt-doel; toekomst = de actuele EMHASS-forecast.",
    energySource: "Dagtotalen gebruiken GoodWe 35208/35211 wanneer beschikbaar. De Recorder-integratie blijft zichtbaar als vergelijking.",
    noActual: "Recorder heeft nog onvoldoende statistieken van het werkelijke accuvermogen.",
    noPlan: "Er is nog geen bruikbare EMHASS P_batt-historie of forecast-horizon beschikbaar.",
    noPrice: "De marktprijslijn verschijnt zodra tijdgebonden runtimeprijzen beschikbaar zijn.",
    discrepancy: "De GoodWe-dagteller en de visuele 5-minutenintegratie verschillen. Voor het hoofdtotaal wordt de inverterteller gebruikt.",
    now: "NU", updated: "bijgewerkt {time}", waiting: "wachten op gegevens",
    expand: "Open grote grafiek", details: "Open gedetailleerde grafiek", close: "Sluiten",
    compact: "Klein", normal: "Normaal", large: "Groot",
    refresh: "Grafiekgegevens verversen", future: "Forecast",
  },
};

export function language(panel) {
  if (typeof panel._epLanguage === "function") return panel._epLanguage();
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

export function t(panel, key, vars = {}) {
  let value = TEXT[language(panel)]?.[key] ?? TEXT.en[key] ?? key;
  for (const [name, replacement] of Object.entries(vars)) {
    value = value.replaceAll(`{${name}}`, String(replacement));
  }
  return value;
}

export function finiteNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function timestampMs(value) {
  if (typeof value === "number") return value < 1e12 ? value * 1000 : value;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function localDayBounds() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  return { now, start, end };
}

function normalizeStatisticRows(rows, startMs, endMs) {
  return (rows || [])
    .map((row) => ({ t: timestampMs(row.start), w: finiteNumber(row.mean) }))
    .filter((p) => p.t !== null && p.w !== null && p.t >= startMs && p.t < endMs)
    .sort((a, b) => a.t - b.t);
}

function normalizePricePoints(points, startMs, endMs) {
  return (points || [])
    .map((p) => ({
      t: timestampMs(p.start), market: finiteNumber(p.market_price),
      buy: finiteNumber(p.buy_price), sell: finiteNumber(p.sell_price),
    }))
    .filter((p) => p.t !== null && p.market !== null && p.t >= startMs && p.t < endMs)
    .sort((a, b) => a.t - b.t);
}

function normalizeFuturePlan(points, startMs, endMs) {
  return (points || [])
    .map((p) => ({ t: timestampMs(p.start), w: finiteNumber(p.value_w) }))
    .filter((p) => p.t !== null && p.w !== null && p.t >= startMs && p.t < endMs)
    .sort((a, b) => a.t - b.t);
}

function normalizeHistoryRows(payload, entityId, startMs, endMs) {
  const rows = entityId ? payload?.[entityId] || [] : [];
  return rows
    .map((row) => ({
      t: timestampMs(
        row.last_updated ?? row.last_changed ?? row.last_reported ??
        row.lu ?? row.lc ?? row.lr ?? row.timestamp
      ),
      w: finiteNumber(row.state ?? row.s),
    }))
    .filter((p) => p.t !== null && p.w !== null && p.t >= startMs && p.t < endMs)
    .sort((a, b) => a.t - b.t);
}

function integrateMeanBuckets(rows, rangeStartMs, rangeEndMs, minutes = 5) {
  const nominalDuration = minutes * 60 * 1000;
  let charged = 0;
  let discharged = 0;
  for (const point of rows || []) {
    const start = Math.max(rangeStartMs, point.t);
    const end = Math.min(rangeEndMs, point.t + nominalDuration);
    if (end <= start) continue;
    const energy = Math.abs(point.w) / 1000 * ((end - start) / 3_600_000);
    if (point.w < 0) charged += energy;
    else if (point.w > 0) discharged += energy;
  }
  return { charged, discharged };
}

export function inferredPlanInterval(points) {
  const intervals = [];
  for (let index = 1; index < points.length; index += 1) {
    const delta = points[index].t - points[index - 1].t;
    if (delta > 0 && delta <= 4 * 60 * 60 * 1000) intervals.push(delta);
  }
  intervals.sort((a, b) => a - b);
  return intervals.length ? intervals[Math.floor(intervals.length / 2)] : 60 * 60 * 1000;
}

function integrateStepPlan(points, rangeStartMs, rangeEndMs) {
  const sorted = [...(points || [])].sort((a, b) => a.t - b.t);
  const fallback = inferredPlanInterval(sorted);
  let charged = 0;
  let discharged = 0;
  for (let index = 0; index < sorted.length; index += 1) {
    const point = sorted[index];
    const nextT = sorted[index + 1]?.t ?? rangeEndMs ?? point.t + fallback;
    const start = Math.max(rangeStartMs, point.t);
    const end = Math.min(rangeEndMs, nextT);
    if (end <= start) continue;
    const energy = Math.abs(point.w) / 1000 * ((end - start) / 3_600_000);
    if (point.w < 0) charged += energy;
    else if (point.w > 0) discharged += energy;
  }
  return { charged, discharged };
}

export function currentPrice(points, nowMs) {
  let selected = null;
  for (const point of points || []) {
    if (point.t > nowMs) break;
    selected = point;
  }
  return selected || points?.[0] || null;
}

export function formatEnergy(value) {
  return Number.isFinite(value) ? `${value.toFixed(value >= 10 ? 1 : 2)} kWh` : "—";
}

export function formatPower(value) {
  return Number.isFinite(value) ? `${Math.abs(value / 1000).toFixed(2)} kW` : "—";
}

export function formatPrice(panel, value, currency = "EUR") {
  if (!Number.isFinite(value)) return "—";
  try {
    const locale = panel?._hass?.locale?.language || panel?._hass?.language || undefined;
    const formatted = new Intl.NumberFormat(locale, {
      style: "currency", currency: currency || "EUR",
      minimumFractionDigits: 3, maximumFractionDigits: 3,
    }).format(value);
    return `${formatted}/kWh`;
  } catch (_err) {
    return `${value.toFixed(3)} ${currency || "EUR"}/kWh`;
  }
}

export function formatTime(value) {
  const date = value ? new Date(value) : null;
  if (!date || Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function dashboardPrefs() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(DASHBOARD_STORAGE_KEY) || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (_err) {
    return {};
  }
}

function savePrefs(prefs) {
  try {
    window.localStorage.setItem(DASHBOARD_STORAGE_KEY, JSON.stringify(prefs));
  } catch (_err) {
    // Private browsing may reject storage; the chart remains usable.
  }
}

export function chartHidden() {
  return Boolean(dashboardPrefs()?.hidden?.[CARD_ID]);
}

export function chartSize() {
  const value = dashboardPrefs()?.sizes?.[CARD_ID];
  return VALID_SIZES.has(value) ? value : "normal";
}

export function saveChartSize(size) {
  if (!VALID_SIZES.has(size)) return;
  const prefs = dashboardPrefs();
  prefs.sizes = prefs.sizes && typeof prefs.sizes === "object" ? prefs.sizes : {};
  prefs.sizes[CARD_ID] = size;
  savePrefs(prefs);
}

export async function loadChartData(panel, force = false) {
  const nowMs = Date.now();
  const cached = panel.__epV027BatteryPlanData;
  if (!force && cached && nowMs - cached.at < DATA_CACHE_MS) return cached;
  if (panel.__epV027BatteryPlanPromise) return panel.__epV027BatteryPlanPromise;

  const batteryId = panel._entityId?.("battery_power");
  if (!batteryId || !panel._hass?.callWS) return null;

  const bounds = localDayBounds();
  panel.__epV027BatteryPlanLoading = true;
  panel._queueRender();

  const request = { type: "gw_energypilot/battery_price/get", force };
  const entryId = panel.__epV016SettingsData?.entry_id;
  if (entryId) request.entry_id = entryId;

  panel.__epV027BatteryPlanPromise = panel._hass.callWS(request)
    .then(async (payload) => {
      const planEntityId = payload?.battery_plan?.entity_id || null;
      const actualRequest = panel._hass.callWS({
        type: "recorder/statistics_during_period",
        start_time: bounds.start.toISOString(), end_time: bounds.now.toISOString(),
        statistic_ids: [batteryId], period: "5minute", types: ["mean"],
      });
      const planRequest = planEntityId
        ? panel._hass.callWS({
            type: "history/history_during_period",
            start_time: bounds.start.toISOString(), end_time: bounds.now.toISOString(),
            entity_ids: [planEntityId], include_start_time_state: true,
            significant_changes_only: false, minimal_response: false, no_attributes: true,
          })
        : Promise.resolve({});

      const [actualResult, planResult] = await Promise.allSettled([actualRequest, planRequest]);
      const actualStats = actualResult.status === "fulfilled" ? actualResult.value : {};
      const planHistory = planResult.status === "fulfilled" ? planResult.value : {};
      const errors = [
        actualResult.status === "rejected" ? actualResult.reason?.message || String(actualResult.reason) : null,
        planResult.status === "rejected" ? planResult.reason?.message || String(planResult.reason) : null,
      ].filter(Boolean);
      const inherited = panel.__epV026BatteryPriceData;
      const startMs = bounds.start.getTime();
      const endMs = bounds.end.getTime();
      const data = {
        at: Date.now(), startMs, endMs, nowMs: bounds.now.getTime(),
        actualRows: normalizeStatisticRows(actualStats?.[batteryId] || inherited?.batteryRows || [], startMs, endMs),
        historicalPlanRows: normalizeHistoryRows(planHistory, planEntityId, startMs, bounds.now.getTime()),
        futurePlanPoints: normalizeFuturePlan(payload?.battery_plan?.points || [], startMs, endMs),
        pricePoints: normalizePricePoints(payload?.points || inherited?.pricePoints || [], startMs, endMs),
        payload, statisticsError: errors.join(" · ") || null,
      };
      panel.__epV027BatteryPlanData = data;
      return data;
    })
    .catch((err) => {
      const inherited = panel.__epV026BatteryPriceData;
      const data = {
        at: Date.now(), startMs: bounds.start.getTime(), endMs: bounds.end.getTime(),
        nowMs: bounds.now.getTime(), actualRows: inherited?.batteryRows || [],
        historicalPlanRows: [], futurePlanPoints: [], pricePoints: inherited?.pricePoints || [],
        payload: inherited?.pricePayload || null, statisticsError: err?.message || String(err),
      };
      panel.__epV027BatteryPlanData = data;
      return data;
    })
    .finally(() => {
      panel.__epV027BatteryPlanLoading = false;
      panel.__epV027BatteryPlanPromise = null;
      panel._queueRender();
    });

  return panel.__epV027BatteryPlanPromise;
}

export function nicePowerPeak(data) {
  const values = [
    ...(data?.actualRows || []), ...(data?.historicalPlanRows || []),
    ...(data?.futurePlanPoints || []),
  ].map((p) => Math.abs(p.w) / 1000);
  const maximum = Math.max(0, ...values);
  if (maximum <= 1) return 1;
  if (maximum <= 2) return 2;
  if (maximum <= 5) return Math.ceil(maximum);
  return Math.ceil(maximum / 5) * 5;
}

export function energyComparison(data) {
  const graph = integrateMeanBuckets(
    data?.actualRows || [], data?.startMs || 0, data?.nowMs || Date.now()
  );
  const nativeCharge = finiteNumber(data?.payload?.battery_energy?.charged_today_kwh);
  const nativeDischarge = finiteNumber(data?.payload?.battery_energy?.discharged_today_kwh);
  return {
    graph,
    charged: nativeCharge ?? graph.charged,
    discharged: nativeDischarge ?? graph.discharged,
    chargeNative: nativeCharge !== null,
    dischargeNative: nativeDischarge !== null,
    chargeDifference: nativeCharge === null ? 0 : Math.abs(nativeCharge - graph.charged),
    dischargeDifference: nativeDischarge === null ? 0 : Math.abs(nativeDischarge - graph.discharged),
  };
}

export function planEnergy(data) {
  if (!data) return { charged: 0, discharged: 0 };
  const past = integrateStepPlan(data.historicalPlanRows || [], data.startMs, data.nowMs);
  const future = integrateStepPlan(
    (data.futurePlanPoints || []).filter((p) => p.t >= data.nowMs),
    data.nowMs, data.endMs
  );
  return { charged: past.charged + future.charged, discharged: past.discharged + future.discharged };
}
