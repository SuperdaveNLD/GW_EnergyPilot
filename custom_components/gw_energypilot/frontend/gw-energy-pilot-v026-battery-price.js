import "./gw-energy-pilot-v026.js?v=1.1.1-stable1";

const VERSION = "0.26";
const PANEL_NAME = "gw-energypilot-panel";
const DATA_CACHE_MS = 5 * 60 * 1000;
const DASHBOARD_STORAGE_KEY = "gw_energypilot_dashboard_v008";
const CARD_ID = "battery-price";

const TEXT = {
  en: {
    title: "BATTERY & PRICE",
    subtitle: "Today · actual charge / discharge vs market price",
    powerAxis: "Power (kW)",
    priceAxis: "Price ({currency}/kWh)",
    charging: "Charging",
    discharging: "Discharging",
    marketPrice: "Market price",
    chargedToday: "Charged today",
    dischargedToday: "Discharged today",
    currentPrice: "Current price",
    details: "Open detailed battery / price graph",
    loading: "Loading Recorder battery history and runtime prices…",
    noBattery: "Recorder has not collected enough 5-minute battery-power statistics yet.",
    noPrice: "The price line becomes available when EnergyPilot can load timestamped runtime prices.",
    batterySource: "Actual GoodWe battery power · Recorder 5-minute means",
    priceSource: "Market line from the same EnergyPilot runtime prices supplied to EMHASS",
    approximate: "Energy totals are approximate integrations of the displayed 5-minute mean power.",
    updated: "updated {time}",
    waiting: "waiting for data",
    expand: "Expand graph",
    visibleCard: "Battery & price",
    today: "Today",
    now: "NOW",
    close: "Close",
  },
  nl: {
    title: "ACCU & PRIJS",
    subtitle: "Vandaag · werkelijk laden / ontladen versus marktprijs",
    powerAxis: "Vermogen (kW)",
    priceAxis: "Prijs ({currency}/kWh)",
    charging: "Laden",
    discharging: "Ontladen",
    marketPrice: "Marktprijs",
    chargedToday: "Vandaag geladen",
    dischargedToday: "Vandaag ontladen",
    currentPrice: "Huidige prijs",
    details: "Open gedetailleerde accu- / prijsgrafiek",
    loading: "Accuhistorie en runtimeprijzen laden…",
    noBattery: "Recorder heeft nog onvoldoende 5-minutenstatistieken van het accuvermogen.",
    noPrice: "De prijslijn verschijnt zodra EnergyPilot tijdgebonden runtimeprijzen kan laden.",
    batterySource: "Werkelijk GoodWe-accuvermogen · Recorder-gemiddelden van 5 minuten",
    priceSource: "Marktlijn uit dezelfde EnergyPilot-runtimeprijzen die naar EMHASS gaan",
    approximate: "Energietotalen zijn benaderingen uit het getoonde gemiddelde 5-minutenvermogen.",
    updated: "bijgewerkt {time}",
    waiting: "wachten op gegevens",
    expand: "Grafiek vergroten",
    visibleCard: "Accu & prijs",
    today: "Vandaag",
    now: "NU",
    close: "Sluiten",
  },
};

function language(panel) {
  if (typeof panel._epLanguage === "function") return panel._epLanguage();
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function t(panel, key, vars = {}) {
  let value = TEXT[language(panel)]?.[key] ?? TEXT.en[key] ?? key;
  for (const [name, replacement] of Object.entries(vars)) {
    value = value.replaceAll(`{${name}}`, replacement);
  }
  return value;
}

function timestampMs(value) {
  if (typeof value === "number") return value < 1e12 ? value * 1000 : value;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function finiteNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function localDayBounds() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const end = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  return { now, start, end };
}

function normalizeBatteryRows(rows, startMs, endMs) {
  return (rows || [])
    .map((row) => ({ t: timestampMs(row.start), w: finiteNumber(row.mean) }))
    .filter((point) => point.t !== null && point.w !== null && point.t >= startMs && point.t < endMs)
    .sort((a, b) => a.t - b.t);
}

function normalizePricePoints(points, startMs, endMs) {
  return (points || [])
    .map((point) => ({
      t: timestampMs(point.start),
      market: finiteNumber(point.market_price),
      buy: finiteNumber(point.buy_price),
      sell: finiteNumber(point.sell_price),
    }))
    .filter((point) => point.t !== null && point.market !== null && point.t >= startMs && point.t < endMs)
    .sort((a, b) => a.t - b.t);
}

function integrateBattery(rows) {
  const hoursPerBucket = 5 / 60;
  let charged = 0;
  let discharged = 0;
  for (const point of rows) {
    const energy = Math.abs(point.w) / 1000 * hoursPerBucket;
    if (point.w < 0) charged += energy;
    else if (point.w > 0) discharged += energy;
  }
  return { charged, discharged };
}

function currentPrice(points, nowMs) {
  let selected = null;
  for (const point of points) {
    if (point.t > nowMs) break;
    selected = point;
  }
  return selected || points[0] || null;
}

function formatEnergy(value) {
  return Number.isFinite(value)
    ? `${value.toFixed(value >= 10 ? 1 : 2)} kWh`
    : "—";
}

function formatPrice(panel, value, currency = "EUR") {
  if (!Number.isFinite(value)) return "—";
  try {
    const formatted = new Intl.NumberFormat(
      panel?._hass?.locale?.language || panel?._hass?.language || undefined,
      {
        style: "currency",
        currency: currency || "EUR",
        minimumFractionDigits: 3,
        maximumFractionDigits: 3,
      }
    ).format(value);
    return `${formatted}/kWh`;
  } catch (_err) {
    return `${value.toFixed(3)} ${currency || "EUR"}/kWh`;
  }
}

function formatTime(value) {
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

function chartHidden() {
  return Boolean(dashboardPrefs()?.hidden?.[CARD_ID]);
}

function saveChartVisibility(visible) {
  const prefs = dashboardPrefs();
  prefs.hidden = prefs.hidden && typeof prefs.hidden === "object" ? prefs.hidden : {};
  prefs.hidden[CARD_ID] = !visible;
  try {
    window.localStorage.setItem(DASHBOARD_STORAGE_KEY, JSON.stringify(prefs));
  } catch (_err) {
    // Dashboard remains usable if browser storage is unavailable.
  }
}

async function loadBatteryPriceData(panel, force = false) {
  const nowMs = Date.now();
  const cached = panel.__epV026BatteryPriceData;
  if (!force && cached && nowMs - cached.at < DATA_CACHE_MS) return cached;
  if (panel.__epV026BatteryPricePromise) return panel.__epV026BatteryPricePromise;

  const batteryId = panel._entityId?.("battery_power");
  if (!batteryId || !panel._hass?.callWS) return null;

  const bounds = localDayBounds();
  panel.__epV026BatteryPriceLoading = true;
  panel._queueRender();

  const priceRequest = { type: "gw_energypilot/battery_price/get", force };
  const entryId = panel.__epV016SettingsData?.entry_id;
  if (entryId) priceRequest.entry_id = entryId;

  panel.__epV026BatteryPricePromise = Promise.allSettled([
    panel._hass.callWS({
      type: "recorder/statistics_during_period",
      start_time: bounds.start.toISOString(),
      end_time: bounds.now.toISOString(),
      statistic_ids: [batteryId],
      period: "5minute",
      types: ["mean"],
    }),
    panel._hass.callWS(priceRequest),
  ])
    .then(([batteryResult, priceResult]) => {
      const batteryPayload = batteryResult.status === "fulfilled" ? batteryResult.value : {};
      const pricePayload = priceResult.status === "fulfilled" ? priceResult.value : null;
      const data = {
        at: Date.now(),
        startMs: bounds.start.getTime(),
        endMs: bounds.end.getTime(),
        nowMs: bounds.now.getTime(),
        batteryRows: normalizeBatteryRows(
          batteryPayload?.[batteryId] || [],
          bounds.start.getTime(),
          bounds.end.getTime()
        ),
        pricePoints: normalizePricePoints(
          pricePayload?.points || [],
          bounds.start.getTime(),
          bounds.end.getTime()
        ),
        pricePayload,
        batteryError:
          batteryResult.status === "rejected"
            ? batteryResult.reason?.message || String(batteryResult.reason)
            : null,
        priceError:
          priceResult.status === "rejected"
            ? priceResult.reason?.message || String(priceResult.reason)
            : pricePayload?.error || null,
      };
      panel.__epV026BatteryPriceData = data;
      return data;
    })
    .finally(() => {
      panel.__epV026BatteryPriceLoading = false;
      panel.__epV026BatteryPricePromise = null;
      panel._queueRender();
    });

  return panel.__epV026BatteryPricePromise;
}

function nicePowerPeak(rows) {
  const maximum = Math.max(0, ...rows.map((point) => Math.abs(point.w) / 1000));
  if (maximum <= 1) return 1;
  if (maximum <= 2) return 2;
  if (maximum <= 5) return Math.ceil(maximum);
  return Math.ceil(maximum / 5) * 5;
}

function priceRange(points) {
  if (!points.length) return null;
  const values = points.map((point) => point.market);
  let minimum = Math.min(...values);
  let maximum = Math.max(...values);
  if (minimum === maximum) {
    minimum -= 0.05;
    maximum += 0.05;
  } else {
    const padding = Math.max(0.01, (maximum - minimum) * 0.12);
    minimum -= padding;
    maximum += padding;
  }
  return { minimum, maximum };
}

function chartSvg(panel, data, large = false) {
  if (!data) {
    return `<div class="ep-v026-bp-empty">${panel._escape(t(panel, "loading"))}</div>`;
  }

  const batteryRows = data.batteryRows || [];
  const pricePoints = data.pricePoints || [];
  if (!batteryRows.length && !pricePoints.length) {
    return `<div class="ep-v026-bp-empty">${panel._escape(t(panel, "noBattery"))}<br>${panel._escape(t(panel, "noPrice"))}</div>`;
  }

  const width = 920;
  const height = large ? 470 : 360;
  const left = 60;
  const right = 74;
  const top = 38;
  const bottom = 48;
  const plotW = width - left - right;
  const plotH = height - top - bottom;
  const zeroY = top + plotH / 2;
  const peakKw = nicePowerPeak(batteryRows);
  const range = priceRange(pricePoints);
  const x = (timestamp) => left + ((timestamp - data.startMs) / Math.max(1, data.endMs - data.startMs)) * plotW;
  const powerY = (watts) => zeroY - (watts / 1000 / peakKw) * (plotH / 2);
  const priceY = (value) => range
    ? top + ((range.maximum - value) / (range.maximum - range.minimum)) * plotH
    : zeroY;

  const xTicks = [0, 6, 12, 18, 24].map((hour) => {
    const date = new Date(data.startMs);
    date.setHours(hour === 24 ? 24 : hour, 0, 0, 0);
    const xx = x(date.getTime());
    const label = hour === 24 ? "24:00" : `${String(hour).padStart(2, "0")}:00`;
    return `<line x1="${xx.toFixed(1)}" y1="${top}" x2="${xx.toFixed(1)}" y2="${height - bottom}" stroke="rgba(112,170,205,.09)"/><text x="${xx.toFixed(1)}" y="${height - 15}" text-anchor="middle" fill="#7895aa" font-size="11">${label}</text>`;
  }).join("");

  const powerTicks = [-peakKw, -peakKw / 2, 0, peakKw / 2, peakKw].map((value) => {
    const yy = zeroY - (value / peakKw) * (plotH / 2);
    return `<line x1="${left}" y1="${yy.toFixed(1)}" x2="${width - right}" y2="${yy.toFixed(1)}" stroke="rgba(112,170,205,${value === 0 ? ".26" : ".08"})"/><text x="${left - 12}" y="${(yy + 4).toFixed(1)}" text-anchor="end" fill="#829db2" font-size="11">${Number(value.toFixed(1))}</text>`;
  }).join("");

  const barWidth = Math.max(1.2, plotW * (5 * 60 * 1000) / Math.max(1, data.endMs - data.startMs) * 0.88);
  const bars = batteryRows.map((point) => {
    const xx = x(point.t) - barWidth / 2;
    const yy = powerY(point.w);
    const rectY = Math.min(yy, zeroY);
    const rectH = Math.max(1, Math.abs(zeroY - yy));
    const color = point.w < 0 ? "#27e0c1" : "#ffa52f";
    const label = point.w < 0 ? t(panel, "charging") : t(panel, "discharging");
    return `<rect x="${xx.toFixed(1)}" y="${rectY.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${rectH.toFixed(1)}" rx="1.3" fill="${color}" opacity=".86"><title>${panel._escape(`${formatTime(point.t)} · ${label} · ${Math.abs(point.w / 1000).toFixed(2)} kW`)}</title></rect>`;
  }).join("");

  const pricePath = pricePoints.length >= 2
    ? pricePoints.map((point, index) => `${index ? "L" : "M"}${x(point.t).toFixed(1)},${priceY(point.market).toFixed(1)}`).join(" ")
    : "";
  const priceLine = pricePath
    ? `<path d="${pricePath}" fill="none" stroke="#3ee9ff" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round" filter="url(#epV026PriceGlow)"/>`
    : "";
  const priceDots = pricePoints.map((point) => `<circle cx="${x(point.t).toFixed(1)}" cy="${priceY(point.market).toFixed(1)}" r="5" fill="transparent"><title>${panel._escape(`${formatTime(point.t)} · ${formatPrice(panel, point.market, data.pricePayload?.currency)}`)}</title></circle>`).join("");

  const priceTicks = range
    ? [0, .25, .5, .75, 1].map((fraction) => {
        const value = range.minimum + (range.maximum - range.minimum) * fraction;
        const yy = priceY(value);
        return `<text x="${width - right + 12}" y="${(yy + 4).toFixed(1)}" fill="#55dff5" font-size="11">${value.toFixed(2)}</text>`;
      }).join("")
    : "";

  const nowX = data.nowMs >= data.startMs && data.nowMs < data.endMs ? x(data.nowMs) : null;
  const nowLine = nowX === null
    ? ""
    : `<line x1="${nowX.toFixed(1)}" y1="${top}" x2="${nowX.toFixed(1)}" y2="${height - bottom}" stroke="rgba(238,251,255,.26)" stroke-dasharray="4 5"/><text x="${nowX.toFixed(1)}" y="${top - 10}" text-anchor="middle" fill="#b7d2df" font-size="9">${panel._escape(t(panel, "now"))}</text>`;

  const currency = panel._escape(data.pricePayload?.currency || "EUR");
  return `<svg viewBox="0 0 ${width} ${height}" width="100%" role="img" aria-label="${panel._escape(t(panel, "subtitle"))}">
    <defs><filter id="epV026PriceGlow" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="2" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
    <text x="${left}" y="17" fill="#d7ebf5" font-size="11">${panel._escape(t(panel, "powerAxis"))}</text>
    <text x="${width - right}" y="17" text-anchor="end" fill="#55dff5" font-size="11">${panel._escape(t(panel, "priceAxis", { currency }))}</text>
    ${xTicks}${powerTicks}${bars}${priceLine}${priceDots}${priceTicks}${nowLine}
  </svg>`;
}

function summaryHtml(panel, data) {
  const energy = integrateBattery(data?.batteryRows || []);
  const point = currentPrice(data?.pricePoints || [], data?.nowMs || Date.now());
  const currency = data?.pricePayload?.currency || "EUR";
  return `
    <div class="ep-v026-bp-summary">
      <div class="ep-v026-bp-chip charge"><span class="ep-v026-bp-icon">↓</span><div><small>${panel._escape(t(panel, "chargedToday"))}</small><strong>${panel._escape(formatEnergy(energy.charged))}</strong></div></div>
      <div class="ep-v026-bp-chip discharge"><span class="ep-v026-bp-icon">↑</span><div><small>${panel._escape(t(panel, "dischargedToday"))}</small><strong>${panel._escape(formatEnergy(energy.discharged))}</strong></div></div>
      <div class="ep-v026-bp-chip price"><span class="ep-v026-bp-icon">€</span><div><small>${panel._escape(t(panel, "currentPrice"))}</small><strong>${panel._escape(formatPrice(panel, point?.market, currency))}</strong></div></div>
    </div>`;
}

function notesHtml(panel, data) {
  const notes = [];
  if (!data?.batteryRows?.length) notes.push(t(panel, "noBattery"));
  if (!data?.pricePoints?.length) notes.push(data?.priceError || t(panel, "noPrice"));
  if (data?.batteryRows?.length) notes.push(t(panel, "batterySource"));
  if (data?.pricePoints?.length) notes.push(t(panel, "priceSource"));
  notes.push(t(panel, "approximate"));
  return notes.map((note) => `<span>${panel._escape(note)}</span>`).join(" · ");
}

function cardBody(panel, data, large = false) {
  return `
    <div class="ep-v026-bp-chart ${large ? "large" : ""}">${chartSvg(panel, data, large)}</div>
    <div class="ep-v026-bp-legend">
      <span><i class="charge"></i>${panel._escape(t(panel, "charging"))}</span>
      <span><i class="discharge"></i>${panel._escape(t(panel, "discharging"))}</span>
      <span><i class="price"></i>${panel._escape(t(panel, "marketPrice"))}</span>
    </div>
    ${summaryHtml(panel, data)}
    <div class="ep-v026-bp-notes">${notesHtml(panel, data)}</div>`;
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v026-battery-price-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v026-battery-price-style";
  style.textContent = `
    .ep-v026-battery-price-card {
      grid-column: 1 / -1 !important; min-width:0; padding:17px 18px 14px;
      border:1px solid rgba(55,190,235,.22); border-radius:18px;
      background:radial-gradient(circle at 82% 8%,rgba(44,224,255,.055),transparent 18rem),linear-gradient(145deg,rgba(8,30,59,.94),rgba(5,17,36,.97));
      box-shadow:0 14px 44px rgba(0,0,0,.16),inset 0 0 40px rgba(12,97,154,.04);
      position:relative; overflow:hidden;
    }
    .ep-v026-bp-head { display:flex; align-items:flex-start; justify-content:space-between; gap:14px; }
    .ep-v026-bp-kicker { color:#66e7fb; font-size:10px; letter-spacing:.16em; font-weight:850; }
    .ep-v026-bp-subtitle { color:#829db2; font-size:10px; margin-top:4px; }
    .ep-v026-bp-expand { width:34px;height:34px;display:grid;place-items:center;border-radius:10px;border:1px solid rgba(71,202,239,.24);background:rgba(8,47,76,.54);color:#b9effa;cursor:pointer;font-size:18px; }
    .ep-v026-bp-expand:hover { border-color:rgba(52,231,255,.48);background:rgba(10,61,91,.75); }
    .ep-v026-bp-chart { margin-top:8px; min-height:250px; border-radius:13px; background:rgba(1,12,29,.25); overflow:hidden; }
    .ep-v026-bp-chart svg { display:block; }
    .ep-v026-bp-empty { min-height:250px;display:grid;place-items:center;text-align:center;padding:20px;color:#7597ad;font-size:10px;line-height:1.55; }
    .ep-v026-bp-legend { display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:10px 22px;margin:4px 0 12px;color:#91a9bc;font-size:9px; }
    .ep-v026-bp-legend span { display:flex;align-items:center;gap:7px; }
    .ep-v026-bp-legend i { display:inline-block;width:10px;height:10px;border-radius:3px;background:#27e0c1;box-shadow:0 0 9px rgba(39,224,193,.2); }
    .ep-v026-bp-legend i.discharge { background:#ffa52f;box-shadow:0 0 9px rgba(255,165,47,.2); }
    .ep-v026-bp-legend i.price { width:18px;height:2px;border-radius:999px;background:#3ee9ff;box-shadow:0 0 9px rgba(62,233,255,.45); }
    .ep-v026-bp-summary { display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px; }
    .ep-v026-bp-chip { min-width:0;display:flex;align-items:center;gap:10px;padding:10px 11px;border:1px solid rgba(255,255,255,.055);border-radius:11px;background:rgba(255,255,255,.022); }
    .ep-v026-bp-icon { width:28px;height:28px;flex:0 0 28px;display:grid;place-items:center;border-radius:50%;border:1px solid rgba(39,224,193,.65);color:#3ff0cc;font-size:15px;font-weight:800; }
    .ep-v026-bp-chip.discharge .ep-v026-bp-icon { border-color:rgba(255,165,47,.7);color:#ffb449; }
    .ep-v026-bp-chip.price .ep-v026-bp-icon { border-color:rgba(62,233,255,.65);color:#58ecff; }
    .ep-v026-bp-chip small { display:block;color:#849db1;font-size:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
    .ep-v026-bp-chip strong { display:block;margin-top:2px;color:#eef9ff;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis; }
    .ep-v026-bp-notes { margin-top:10px;color:#627f95;font-size:8px;line-height:1.5; }
    .ep-v026-bp-footer { display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:9px;color:#62b9d4;font-size:8px; }
    .ep-v026-bp-footer button { border:0;padding:0;background:transparent;color:#72d7ef;cursor:pointer;font:inherit; }
    .ep-v026-bp-footer span { color:#617e94; }
    @media(max-width:720px) {
      .ep-v026-battery-price-card { padding:14px 13px 12px;border-radius:16px; }
      .ep-v026-bp-chart { min-height:225px; }
      .ep-v026-bp-summary { grid-template-columns:1fr; }
      .ep-v026-bp-chip strong { font-size:13px; }
    }
  `;
  root.appendChild(style);
}

function openModal(panel) {
  document.querySelector(".ep-v026-bp-backdrop")?.remove();
  const data = panel.__epV026BatteryPriceData;
  const backdrop = document.createElement("div");
  backdrop.className = "ep-v026-bp-backdrop";
  backdrop.innerHTML = `
    <style>
      .ep-v026-bp-backdrop{position:fixed;inset:0;z-index:10080;display:grid;place-items:center;padding:18px;background:rgba(1,8,20,.78);backdrop-filter:blur(6px);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#edf8ff}
      .ep-v026-bp-modal{width:min(1080px,97vw);max-height:92vh;overflow:auto;padding:20px;border:1px solid rgba(55,190,235,.26);border-radius:20px;background:linear-gradient(145deg,#0a1e3b,#051124);box-shadow:0 30px 90px rgba(0,0,0,.58)}
      .ep-v026-bp-modal-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;margin-bottom:8px}.ep-v026-bp-modal-head small{display:block;color:#66e7fb;font-size:10px;letter-spacing:.16em;font-weight:850}.ep-v026-bp-modal-head h2{margin:4px 0 0;font-size:24px}.ep-v026-bp-modal-head p{margin:4px 0 0;color:#829db2;font-size:11px}.ep-v026-bp-close{width:36px;height:36px;border-radius:10px;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.04);color:#d9ecf8;font-size:20px;cursor:pointer}
      .ep-v026-bp-modal .ep-v026-bp-chart{margin-top:8px;border-radius:14px;background:rgba(1,12,29,.34)}.ep-v026-bp-modal .ep-v026-bp-chart svg{display:block}.ep-v026-bp-modal .ep-v026-bp-legend{display:flex;justify-content:center;flex-wrap:wrap;gap:12px 24px;margin:6px 0 14px;color:#91a9bc;font-size:10px}.ep-v026-bp-modal .ep-v026-bp-legend span{display:flex;align-items:center;gap:7px}.ep-v026-bp-modal .ep-v026-bp-legend i{display:inline-block;width:11px;height:11px;border-radius:3px;background:#27e0c1}.ep-v026-bp-modal .ep-v026-bp-legend i.discharge{background:#ffa52f}.ep-v026-bp-modal .ep-v026-bp-legend i.price{width:20px;height:2px;border-radius:999px;background:#3ee9ff;box-shadow:0 0 9px rgba(62,233,255,.45)}
      .ep-v026-bp-modal .ep-v026-bp-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.ep-v026-bp-modal .ep-v026-bp-chip{display:flex;align-items:center;gap:10px;padding:12px;border:1px solid rgba(255,255,255,.06);border-radius:12px;background:rgba(255,255,255,.025)}.ep-v026-bp-modal .ep-v026-bp-icon{width:30px;height:30px;display:grid;place-items:center;border-radius:50%;border:1px solid rgba(39,224,193,.65);color:#3ff0cc}.ep-v026-bp-modal .discharge .ep-v026-bp-icon{border-color:rgba(255,165,47,.7);color:#ffb449}.ep-v026-bp-modal .price .ep-v026-bp-icon{border-color:rgba(62,233,255,.65);color:#58ecff}.ep-v026-bp-modal small{color:#849db1}.ep-v026-bp-modal strong{display:block;margin-top:2px}.ep-v026-bp-modal .ep-v026-bp-notes{margin-top:12px;color:#6f8ca1;font-size:9px;line-height:1.55}.ep-v026-bp-empty{min-height:320px;display:grid;place-items:center;text-align:center;color:#7597ad}
      @media(max-width:680px){.ep-v026-bp-modal{padding:14px}.ep-v026-bp-modal-head h2{font-size:20px}.ep-v026-bp-modal .ep-v026-bp-summary{grid-template-columns:1fr}}
    </style>
    <section class="ep-v026-bp-modal">
      <div class="ep-v026-bp-modal-head"><div><small>${panel._escape(t(panel, "today"))}</small><h2>${panel._escape(t(panel, "title"))}</h2><p>${panel._escape(t(panel, "subtitle"))}</p></div><button class="ep-v026-bp-close" aria-label="${panel._escape(t(panel, "close"))}">×</button></div>
      ${cardBody(panel, data, true)}
    </section>`;
  const close = () => backdrop.remove();
  backdrop.querySelector(".ep-v026-bp-close")?.addEventListener("click", close);
  backdrop.addEventListener("click", (event) => { if (event.target === backdrop) close(); });
  const escape = (event) => {
    if (event.key === "Escape") {
      document.removeEventListener("keydown", escape);
      close();
    }
  };
  document.addEventListener("keydown", escape);
  document.body.appendChild(backdrop);
}

function installVisibilityToggle(panel, root) {
  const menu = root.querySelector(".ep-layout-menu");
  if (!menu || menu.querySelector('[data-ep-visible="battery-price"]')) return;
  const reset = menu.querySelector(".ep-menu-reset");
  if (!reset) return;
  const label = document.createElement("label");
  label.className = "ep-menu-row";
  label.innerHTML = `<span>${panel._escape(t(panel, "visibleCard"))}</span><input type="checkbox" data-ep-visible="battery-price" ${chartHidden() ? "" : "checked"} />`;
  reset.before(label);
  label.querySelector("input")?.addEventListener("change", (event) => {
    saveChartVisibility(Boolean(event.currentTarget.checked));
    panel._queueRender();
  });
}

function installCard(panel, root) {
  const layout = root.querySelector(".ep-dashboard-layout");
  if (!layout || root.querySelector(".ep-v026-battery-price-card")) return;

  const data = panel.__epV026BatteryPriceData;
  const card = document.createElement("article");
  card.className = "panel-card ep-v026-battery-price-card";
  card.dataset.epCard = CARD_ID;
  card.dataset.epSpan = "4";
  card.hidden = chartHidden();
  const updated = data?.at
    ? t(panel, "updated", { time: formatTime(data.at) })
    : t(panel, "waiting");
  card.innerHTML = `
    <div class="ep-v026-bp-head">
      <div><div class="ep-v026-bp-kicker">${panel._escape(t(panel, "title"))}</div><div class="ep-v026-bp-subtitle">${panel._escape(t(panel, "subtitle"))}</div></div>
      <button type="button" class="ep-v026-bp-expand" title="${panel._escape(t(panel, "expand"))}" aria-label="${panel._escape(t(panel, "expand"))}">↗</button>
    </div>
    ${cardBody(panel, data, false)}
    <div class="ep-v026-bp-footer"><button type="button">${panel._escape(t(panel, "details"))}</button><span>${panel._escape(updated)}</span></div>`;

  const batteryCard = layout.querySelector('[data-ep-card="battery"]') || layout.querySelector(".energy-card.battery");
  if (batteryCard) batteryCard.insertAdjacentElement("afterend", card);
  else layout.appendChild(card);

  card.querySelector(".ep-v026-bp-expand")?.addEventListener("click", () => openModal(panel));
  card.querySelector(".ep-v026-bp-footer button")?.addEventListener("click", () => openModal(panel));

  if (!data && !panel.__epV026BatteryPricePromise) void loadBatteryPriceData(panel);
  else if (data && Date.now() - data.at >= DATA_CACHE_MS && !panel.__epV026BatteryPricePromise) {
    void loadBatteryPriceData(panel);
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV026BatteryPriceRender() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  ensureStyles(root);
  installCard(this, root);
  installVisibilityToggle(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
};
