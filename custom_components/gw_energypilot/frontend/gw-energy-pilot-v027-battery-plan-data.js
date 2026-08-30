export const VERSION = "0.27";
export const PANEL_NAME = "gw-energypilot-panel";
export const DATA_CACHE_MS = 5 * 60 * 1000;
export const DASHBOARD_STORAGE_KEY = "gw_energypilot_dashboard_v008";
export const CARD_ID = "battery-price";
const VALID_SIZES = new Set(["compact", "normal", "large"]);

const TEXT = {
  en: {
    title: "BATTERY · PLAN · PRICE",
    subtitle: "Today · battery power, actual/forecast SOC and market price",
    powerAxis: "Power (kW)", priceAxis: "Price ({currency}/kWh)", priceAxisShort: "{currency}/kWh",
    socAxis: "SOC (%)",
    actualCharge: "Actual charging", actualDischarge: "Actual discharging",
    actual: "Actual", plan: "EMHASS plan", marketPrice: "Market price",
    actualSoc: "Actual SOC", forecastSoc: "Forecast SOC", wantedSoc: "Wanted SOC",
    gridToBattery: "Grid → Battery", solarToBattery: "Solar → Battery",
    unknownSource: "Unknown", batteryToGrid: "Battery → Grid", solarToGrid: "Solar → Grid",
    sourceEstimate: "Source split is estimated from Recorder PV, load, battery and grid actuals.",
    chargedToday: "Charged today", dischargedToday: "Discharged today",
    plannedCharge: "Plan charge", plannedDischarge: "Plan discharge",
    currentPrice: "Current price", goodweCounter: "GoodWe day counter",
    graphEstimate: "Recorder power integral {value}", approximate: "Approx. from Recorder",
    planHistory: "Past plan = Recorder history of the published P_batt target; future plan = current EMHASS battery schedule.",
    energySource: "Daily totals use GoodWe 35208/35211 when available. Recorder power integration remains visible as a comparison.",
    noActual: "Recorder has not collected enough actual battery-power statistics yet.",
    noPlan: "No usable EMHASS P_batt history or battery schedule is available yet.",
    noActualSoc: "Recorder has not collected enough actual GoodWe SOC statistics yet.",
    noForecastSoc: "No safe EMHASS SOC_opt forecast is available from the official plan mirror.",
    socSource: "Actual SOC is the Recorder 5-minute mean of the existing GoodWe battery_soc percentage sensor. Forecast SOC is validated EMHASS SOC_opt (0..1) normalized to percent.",
    noPrice: "The market-price line is unavailable until timestamped runtime prices can be loaded.",
    discrepancy: "The native GoodWe day counter and Recorder power integral use different measurement paths and can differ. The GoodWe counter remains the headline total.",
    now: "NOW", updated: "updated {time}", waiting: "waiting for data",
    expand: "Open large graph", details: "Open detailed graph", close: "Close",
    compact: "Compact", normal: "Normal", large: "Large",
    refresh: "Refresh chart data", future: "Forecast",
    evChargeAllowed: "EV active · battery charging allowed",
    evDischargeBlocked: "EV anti-discharge · Battery Hold",
    evHistory: "Striped green = verified charging while the EV is active; solid green = verified mode 8 Battery Hold that blocks discharge.",
  },
  nl: {
    title: "ACCU · PLAN · PRIJS",
    subtitle: "Vandaag · accuvermogen, werkelijke/verwachte SOC en marktprijs",
    powerAxis: "Vermogen (kW)", priceAxis: "Prijs ({currency}/kWh)", priceAxisShort: "{currency}/kWh",
    socAxis: "SOC (%)",
    actualCharge: "Werkelijk laden", actualDischarge: "Werkelijk ontladen",
    actual: "Werkelijk", plan: "EMHASS-plan", marketPrice: "Marktprijs",
    actualSoc: "Werkelijke SOC", forecastSoc: "Verwachte SOC", wantedSoc: "Gewenste SOC",
    gridToBattery: "Net → accu", solarToBattery: "Zon → accu",
    unknownSource: "Onbekend", batteryToGrid: "Accu → net", solarToGrid: "Zon → net",
    sourceEstimate: "De bronverdeling is geschat uit Recorder-actuals voor PV, belasting, accu en net.",
    chargedToday: "Vandaag geladen", dischargedToday: "Vandaag ontladen",
    plannedCharge: "Gepland laden", plannedDischarge: "Gepland ontladen",
    currentPrice: "Huidige prijs", goodweCounter: "GoodWe-dagteller",
    graphEstimate: "Recorder-vermogensintegratie {value}", approximate: "Benadering uit Recorder",
    planHistory: "Verleden plan = Recorder-historie van het gepubliceerde P_batt-doel; toekomst = het actuele EMHASS-accuschema.",
    energySource: "Dagtotalen gebruiken GoodWe 35208/35211 wanneer beschikbaar. De Recorder-vermogensintegratie blijft zichtbaar als vergelijking.",
    noActual: "Recorder heeft nog onvoldoende statistieken van het werkelijke accuvermogen.",
    noPlan: "Er is nog geen bruikbare EMHASS P_batt-historie of accuschema beschikbaar.",
    noActualSoc: "Recorder heeft nog onvoldoende statistieken van de werkelijke GoodWe-SOC.",
    noForecastSoc: "De officiële planmirror bevat nog geen veilig bruikbare EMHASS SOC_opt-prognose.",
    socSource: "Werkelijke SOC is het Recorder-gemiddelde per 5 minuten van de bestaande GoodWe battery_soc-percentagesensor. Verwachte SOC is gevalideerde EMHASS SOC_opt (0..1), omgerekend naar procent.",
    noPrice: "De marktprijslijn verschijnt zodra tijdgebonden runtimeprijzen beschikbaar zijn.",
    discrepancy: "De GoodWe-dagteller en Recorder-vermogensintegratie gebruiken verschillende meetpaden en kunnen afwijken. Voor het hoofdtotaal blijft de GoodWe-teller leidend.",
    now: "NU", updated: "bijgewerkt {time}", waiting: "wachten op gegevens",
    expand: "Open grote grafiek", details: "Open gedetailleerde grafiek", close: "Sluiten",
    compact: "Klein", normal: "Normaal", large: "Groot",
    refresh: "Grafiekgegevens verversen", future: "Forecast",
    evChargeAllowed: "EV actief · thuisaccu laden toegestaan",
    evDischargeBlocked: "EV-ontlaadbeveiliging · Battery Hold",
    evHistory: "Gestreept groen = geverifieerd laden terwijl de EV actief is; effen groen = geverifieerde modus 8 Battery Hold die ontladen blokkeert.",
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

function requestPanelRefresh(panel) {
  if (
    panel?.__epV041StableRuntime === true &&
    typeof panel.__epV041RefreshBatteryPlan === "function"
  ) {
    panel.__epV041RefreshBatteryPlan();
    return;
  }
  panel?._queueRender?.();
}

function normalizeStatisticRows(rows, startMs, endMs) {
  return (rows || [])
    .map((row) => ({ t: timestampMs(row.start), w: finiteNumber(row.mean) }))
    .filter((p) => p.t !== null && p.w !== null && p.t >= startMs && p.t < endMs)
    .sort((a, b) => a.t - b.t);
}

function statisticRowMap(rows) {
  return new Map((rows || []).map((row) => [row.t, row.w]));
}

export function attributeActualRows(batteryRows, pvRows, loadRows, gridRows) {
  const pvByTime = statisticRowMap(pvRows);
  const loadByTime = statisticRowMap(loadRows);
  const gridByTime = statisticRowMap(gridRows);
  return (batteryRows || []).map((batteryPoint) => {
    const battery = finiteNumber(batteryPoint.w);
    const pv = finiteNumber(pvByTime.get(batteryPoint.t));
    const load = finiteNumber(loadByTime.get(batteryPoint.t));
    const grid = finiteNumber(gridByTime.get(batteryPoint.t));
    const charge = Math.max(-(battery ?? 0), 0);
    const discharge = Math.max(battery ?? 0, 0);
    const gridImport = grid === null ? 0 : Math.max(-grid, 0);
    const gridExport = grid === null ? 0 : Math.max(grid, 0);
    const solarSurplus = pv === null || load === null ? 0 : Math.max(pv - load, 0);
    const solarToBattery = Math.min(charge, solarSurplus);
    const gridToBattery = Math.min(Math.max(charge - solarToBattery, 0), gridImport);
    const unknownCharge = Math.max(charge - solarToBattery - gridToBattery, 0);
    const remainingSolar = Math.max(solarSurplus - solarToBattery, 0);
    const solarToGrid = Math.min(gridExport, remainingSolar);
    const batteryToGrid = Math.min(Math.max(gridExport - solarToGrid, 0), discharge);
    const unknownExport = Math.max(gridExport - solarToGrid - batteryToGrid, 0);
    const complete = pv !== null && load !== null && grid !== null && battery !== null;
    return {
      t: batteryPoint.t,
      batteryW: battery,
      pvW: pv,
      loadW: load,
      gridW: grid,
      gridToBatteryW: gridToBattery,
      solarToBatteryW: solarToBattery,
      unknownChargeW: unknownCharge,
      batteryToGridW: batteryToGrid,
      solarToGridW: solarToGrid,
      unknownExportW: unknownExport,
      confidence: !complete
        ? "partial"
        : unknownCharge + unknownExport > Math.max(100, (charge + gridExport) * 0.1)
          ? "residual"
          : "high",
    };
  });
}

export function normalizeSocStatisticRows(rows, startMs, endMs) {
  return (rows || [])
    .map((row) => ({ t: timestampMs(row.start), pct: finiteNumber(row.mean) }))
    .filter((p) => (
      p.t !== null && p.pct !== null && p.pct >= 0 && p.pct <= 100 &&
      p.t >= startMs && p.t < endMs
    ))
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

export function normalizeSocPlanPoints(points, startMs, endMs) {
  return (points || [])
    .map((p) => ({ t: timestampMs(p.start), pct: finiteNumber(p.value_pct) }))
    .filter((p) => (
      p.t !== null && p.pct !== null && p.pct >= 0 && p.pct <= 100 &&
      p.t >= startMs && p.t < endMs
    ))
    .sort((a, b) => a.t - b.t);
}

export function normalizeExecutionSocHistory(events, startMs, endMs) {
  const byTimestamp = new Map();
  for (const event of events || []) {
    const t = timestampMs(event?.occurred_at);
    const pct = finiteNumber(event?.plan?.soc_opt_pct);
    if (t === null || pct === null || pct < 0 || pct > 100) continue;
    if (t < startMs || t >= endMs) continue;
    byTimestamp.set(t, { t, pct });
  }
  return [...byTimestamp.values()].sort((left, right) => left.t - right.t);
}

export function normalizeExecutionEvIntervals(execution, startMs, endMs) {
  const chargeCommands = new Set([
    "ev_charge_allowed",
    "ev_battery_charge",
    "ev_grid_import_charge",
    "ev_charge_fallback",
  ]);
  const currentSession = String(execution?.runtime_session_id || "");
  const executionNow = timestampMs(execution?.now);
  const history = (execution?.history || [])
    .filter((event) => timestampMs(event?.occurred_at) !== null)
    .sort((left, right) => (
      timestampMs(left.occurred_at) - timestampMs(right.occurred_at)
    ));
  const intervals = [];

  for (let index = 0; index < history.length; index += 1) {
    const event = history[index];
    const outcome = event?.outcome || {};
    const session = String(event?.runtime_session_id || "");
    const command = String(outcome.command || "");
    const kind = command === "ev_anti_discharge_hold"
      ? "discharge_blocked"
      : chargeCommands.has(command)
        ? "battery_charge_allowed"
        : null;
    if (
      !kind || !session || event?.configuration?.ev_active !== true ||
      outcome.verification_status !== "verified"
    ) {
      continue;
    }

    const start = timestampMs(
      outcome.readback_at || outcome.write_completed_at || event.occurred_at
    );
    const next = history[index + 1];
    const sameSessionNext = next && String(next?.runtime_session_id || "") === session;
    const end = sameSessionNext
      ? timestampMs(next.occurred_at)
      : index === history.length - 1 && session === currentSession
        ? executionNow
        : null;
    if (
      start === null || end === null || end <= start ||
      end <= startMs || start >= endMs
    ) {
      continue;
    }
    intervals.push({
      start: Math.max(startMs, start),
      end: Math.min(endMs, end),
      kind,
      command,
      mode: finiteNumber(outcome.readback_mode ?? outcome.expected_mode),
      setpointW: finiteNumber(
        outcome.readback_setpoint_w ?? outcome.expected_setpoint_w
      ),
      execution: String(outcome.write_status || ""),
    });
  }
  return intervals;
}

function normalizeHistoryRows(payload, entityId, startMs, endMs) {
  const rows = entityId ? payload?.[entityId] || [] : [];
  const byTimestamp = new Map();
  for (const row of rows) {
    const rawTimestamp = timestampMs(
      row.last_updated ?? row.last_changed ?? row.last_reported ??
      row.lu ?? row.lc ?? row.lr ?? row.timestamp
    );
    const w = finiteNumber(row.state ?? row.s);
    if (rawTimestamp === null || w === null || rawTimestamp >= endMs) continue;
    // Home Assistant include_start_time_state intentionally returns the last
    // state from before the requested window with its original timestamp.
    // That state was active at local midnight, so retain it at the boundary.
    const t = Math.max(startMs, rawTimestamp);
    byTimestamp.set(t, { t, w });
  }
  return [...byTimestamp.values()].sort((a, b) => a.t - b.t);
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

export async function loadChartData(panel, force = false, backendForce = force) {
  const nowMs = Date.now();
  const cached = panel.__epV027BatteryPlanData;
  if (!force && cached && nowMs - cached.at < DATA_CACHE_MS) return cached;
  if (panel.__epV027BatteryPlanPromise) return panel.__epV027BatteryPlanPromise;

  const batteryId = panel._entityId?.("battery_power");
  const batterySocId = panel._entityId?.("battery_soc");
  const pvId = panel._entityId?.("pv_generation_power");
  const loadId = panel._entityId?.("total_load_power");
  const gridId = panel._entityId?.("meter_total_power_fast");
  if (!batteryId || !panel._hass?.callWS) return null;

  const bounds = localDayBounds();
  panel.__epV027BatteryPlanLoading = true;
  requestPanelRefresh(panel);

  const request = { type: "gw_energypilot/battery_price/get", force: backendForce };
  const entryId = panel.__epV016SettingsData?.entry_id;
  if (entryId) request.entry_id = entryId;

  panel.__epV027BatteryPlanPromise = panel._hass.callWS(request)
    .then(async (payload) => {
      const planEntityId = payload?.battery_plan?.entity_id || null;
      const statisticIds = [...new Set([
        batteryId, batterySocId, pvId, loadId, gridId,
      ].filter(Boolean))];
      const actualRequest = panel._hass.callWS({
        type: "recorder/statistics_during_period",
        start_time: bounds.start.toISOString(), end_time: bounds.now.toISOString(),
        statistic_ids: statisticIds, period: "5minute", types: ["mean"],
      });
      const planRequest = planEntityId
        ? panel._hass.callWS({
            type: "history/history_during_period",
            start_time: bounds.start.toISOString(), end_time: bounds.now.toISOString(),
            entity_ids: [planEntityId], include_start_time_state: true,
            significant_changes_only: false, minimal_response: false, no_attributes: true,
          })
        : Promise.resolve({});

      const [actualResult, planResult] = await Promise.allSettled([
        actualRequest, planRequest,
      ]);
      const actualStats = actualResult.status === "fulfilled" ? actualResult.value : {};
      const planHistory = planResult.status === "fulfilled" ? planResult.value : {};
      const errors = [
        actualResult.status === "rejected" ? actualResult.reason?.message || String(actualResult.reason) : null,
        planResult.status === "rejected" ? planResult.reason?.message || String(planResult.reason) : null,
      ].filter(Boolean);
      const inherited = panel.__epV026BatteryPriceData;
      const startMs = bounds.start.getTime();
      const endMs = bounds.end.getTime();
      const actualRows = normalizeStatisticRows(
        actualStats?.[batteryId] || inherited?.batteryRows || [], startMs, endMs
      );
      const pvRows = normalizeStatisticRows(actualStats?.[pvId] || [], startMs, endMs);
      const loadRows = normalizeStatisticRows(actualStats?.[loadId] || [], startMs, endMs);
      const gridRows = normalizeStatisticRows(actualStats?.[gridId] || [], startMs, endMs);
      const data = {
        at: Date.now(), startMs, endMs, nowMs: bounds.now.getTime(),
        actualRows,
        actualSocRows: normalizeSocStatisticRows(actualStats?.[batterySocId] || [], startMs, endMs),
        pvRows, loadRows, gridRows,
        attributionRows: attributeActualRows(actualRows, pvRows, loadRows, gridRows),
        historicalPlanRows: normalizeHistoryRows(planHistory, planEntityId, startMs, bounds.now.getTime()),
        futurePlanPoints: normalizeFuturePlan(payload?.battery_plan?.points || [], startMs, endMs),
        socPlanPoints: normalizeSocPlanPoints(payload?.battery_soc_plan?.points || [], startMs, endMs),
        historicalSocWantedRows: normalizeExecutionSocHistory(
          payload?.execution?.history || [], startMs, bounds.now.getTime()
        ),
        evProtectionIntervals: normalizeExecutionEvIntervals(
          payload?.execution, startMs, endMs
        ),
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
        actualSocRows: [], pvRows: [], loadRows: [], gridRows: [], attributionRows: [],
        historicalPlanRows: [], futurePlanPoints: [], socPlanPoints: [],
        historicalSocWantedRows: [], evProtectionIntervals: [],
        pricePoints: inherited?.pricePoints || [],
        payload: inherited?.pricePayload || null, statisticsError: err?.message || String(err),
      };
      panel.__epV027BatteryPlanData = data;
      return data;
    })
    .finally(() => {
      panel.__epV027BatteryPlanLoading = false;
      panel.__epV027BatteryPlanPromise = null;
      requestPanelRefresh(panel);
    });

  return panel.__epV027BatteryPlanPromise;
}

export function nicePowerPeak(data) {
  const values = [
    ...(data?.actualRows || []), ...(data?.historicalPlanRows || []),
    ...(data?.futurePlanPoints || []),
  ].map((p) => Math.abs(p.w) / 1000);
  for (const row of data?.attributionRows || []) {
    values.push(
      (row.gridToBatteryW + row.solarToBatteryW + row.unknownChargeW) / 1000,
      (row.batteryToGridW + row.solarToGridW + row.unknownExportW) / 1000,
    );
  }
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
  if (!data) return { charged: null, discharged: null, available: false };
  const historical = data.historicalPlanRows || [];
  const futurePoints = data.futurePlanPoints || [];
  if (!historical.length && !futurePoints.length) {
    return { charged: null, discharged: null, available: false };
  }
  const past = integrateStepPlan(historical, data.startMs, data.nowMs);
  // Keep the schedule point that began before NOW when its interval is still
  // active. integrateStepPlan clips elapsed intervals at rangeStartMs.
  const future = integrateStepPlan(futurePoints, data.nowMs, data.endMs);
  return {
    charged: past.charged + future.charged,
    discharged: past.discharged + future.discharged,
    available: true,
  };
}
