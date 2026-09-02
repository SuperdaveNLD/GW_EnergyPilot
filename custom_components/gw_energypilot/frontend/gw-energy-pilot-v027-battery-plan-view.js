import {
  chartSubtitle, currentPrice, energyComparison, formatChartTime, formatEnergy,
  formatPower, formatPrice, inferredPlanInterval, nicePowerPeak, planEnergy, t,
} from "./gw-energy-pilot-v027-battery-plan-data.js?v=1.2.0-beta.5-touch-fallback1";

const ACTUAL_IDLE_W = 50;

function priceRange(points) {
  if (!points?.length) return null;
  const values = points.map((p) => p.market);
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

function dimensions(size, modal) {
  if (modal || size === "large") {
    return { width: 1040, height: 470, left: 66, right: 118, top: 42, bottom: 52, maxXTicks: 7 };
  }
  if (size === "compact") {
    return { width: 760, height: 215, left: 45, right: 96, top: 26, bottom: 38, maxXTicks: 3 };
  }
  return { width: 920, height: 340, left: 58, right: 112, top: 36, bottom: 46, maxXTicks: 5 };
}

function selectTicks(ticks, maximum) {
  if ((ticks || []).length <= maximum) return ticks || [];
  const selected = [];
  for (let index = 0; index < maximum; index += 1) {
    const sourceIndex = Math.round(index * (ticks.length - 1) / (maximum - 1));
    selected.push(ticks[sourceIndex]);
  }
  return selected;
}

function linePath(points, x, y, valueKey) {
  return (points || []).map((point, index) => {
    const command = index === 0 ? "M" : "L";
    return `${command}${x(point.t).toFixed(1)},${y(point[valueKey]).toFixed(1)}`;
  }).join(" ");
}

function inferredPriceInterval(points) {
  const intervals = [];
  for (let index = 1; index < (points || []).length; index += 1) {
    const delta = points[index].t - points[index - 1].t;
    if (delta > 0 && delta <= 2 * 60 * 60 * 1000) intervals.push(delta);
  }
  intervals.sort((a, b) => a - b);
  return intervals.length ? intervals[Math.floor(intervals.length / 2)] : 60 * 60 * 1000;
}

function steppedPricePath(points, x, priceY, endMs) {
  if (!points?.length) return "";
  const sorted = [...points].sort((a, b) => a.t - b.t);
  let path = `M${x(sorted[0].t).toFixed(1)},${priceY(sorted[0].market).toFixed(1)}`;
  for (let index = 1; index < sorted.length; index += 1) {
    const point = sorted[index];
    const xx = x(point.t).toFixed(1);
    path += ` H${xx} V${priceY(point.market).toFixed(1)}`;
  }
  const last = sorted[sorted.length - 1];
  const lastEnd = Math.min(endMs, last.t + inferredPriceInterval(sorted));
  if (lastEnd > last.t) path += ` H${x(lastEnd).toFixed(1)}`;
  return path;
}

function desiredSocPoints(data) {
  const history = data?.historicalSocWantedRows || [];
  const currentPlan = data?.socPlanPoints || [];
  if (!history.length) return currentPlan;
  const byTimestamp = new Map(history.map((point) => [point.t, point]));
  for (const point of currentPlan) {
    if (point.t >= data.nowMs) byTimestamp.set(point.t, point);
  }
  return [...byTimestamp.values()].sort((left, right) => left.t - right.t);
}

function attributionBars(panel, rows, x, powerY, zeroY, actualWidth) {
  const definitions = {
    gridToBatteryW: ["gridToBattery", "#41b96f", -1],
    solarToBatteryW: ["solarToBattery", "#d9a928", -1],
    unknownChargeW: ["unknownSource", "url(#epV051UnknownHatch)", -1],
    batteryToGridW: ["batteryToGrid", "#eb6a24", 1],
    solarToGridW: ["solarToGrid", "#f0b52f", 1],
    unknownExportW: ["unknownSource", "url(#epV051UnknownHatch)", 1],
  };
  return (rows || []).map((row) => {
    const xx = x(row.t) - actualWidth / 2;
    const cursors = { "-1": 0, "1": 0 };
    return Object.entries(definitions).map(([key, [labelKey, color, direction]]) => {
      const value = Number(row[key]) || 0;
      if (value < ACTUAL_IDLE_W) return "";
      const start = cursors[String(direction)];
      const end = start + value;
      cursors[String(direction)] = end;
      const firstY = powerY(direction * start);
      const secondY = powerY(direction * end);
      const rectY = Math.min(firstY, secondY);
      const rectH = Math.max(1, Math.abs(firstY - secondY));
      const title = `${formatChartTime(panel, row.t)} · ${t(panel, labelKey)} · ${formatPower(value)} · ${row.confidence}`;
      return `<rect data-source-series="${key}" x="${xx.toFixed(1)}" y="${rectY.toFixed(1)}" width="${actualWidth.toFixed(1)}" height="${rectH.toFixed(1)}" rx="1.3" fill="${color}" opacity=".94"><title>${panel._escape(title)}</title></rect>`;
    }).join("");
  }).join("");
}

function chartSvg(panel, data, size, modal) {
  if (!data) return `<div class="ep-v027-empty">${panel._escape(t(panel, "waiting"))}</div>`;
  const d = dimensions(size, modal);
  const { width, height, left, right, top, bottom, maxXTicks } = d;
  const plotW = width - left - right;
  const plotH = height - top - bottom;
  const zeroY = top + plotH / 2;
  const peakKw = nicePowerPeak(data);
  const range = priceRange(data.pricePoints);
  const x = (timestamp) => left + ((timestamp - data.startMs) / Math.max(1, data.endMs - data.startMs)) * plotW;
  const powerY = (watts) => zeroY - (watts / 1000 / peakKw) * (plotH / 2);
  const socY = (percent) => top + ((100 - percent) / 100) * plotH;
  const priceY = (value) => range ? top + ((range.maximum - value) / (range.maximum - range.minimum)) * plotH : zeroY;

  const stripePatternId = `epV027EvChargeStripes-${modal ? "modal" : size}`;
  const evUnderlays = (data.evProtectionIntervals || []).map((interval) => {
    const startT = Math.max(data.startMs, interval.start);
    const endT = Math.min(data.endMs, interval.end);
    if (endT <= startT) return "";
    const xx = x(startT);
    const blockWidth = Math.max(1, x(endT) - xx);
    const chargeAllowed = interval.kind === "battery_charge_allowed";
    const label = t(panel, chargeAllowed ? "evChargeAllowed" : "evDischargeBlocked");
    const mode = Number.isFinite(interval.mode) ? ` · mode ${interval.mode}` : "";
    const fill = chargeAllowed ? `url(#${stripePatternId})` : "#79e68c";
    const opacity = chargeAllowed ? ".72" : ".16";
    return `<rect data-series="ev-protection" data-ev-kind="${interval.kind}" x="${xx.toFixed(1)}" y="${top}" width="${blockWidth.toFixed(1)}" height="${plotH}" fill="${fill}" opacity="${opacity}" stroke="#8cf29b" stroke-opacity="${chargeAllowed ? ".22" : ".30"}" stroke-width=".8"><title>${panel._escape(`${formatChartTime(panel, startT, data.chartTime?.timeZone)}–${formatChartTime(panel, endT, data.chartTime?.timeZone)} · ${label}${mode}`)}</title></rect>`;
  }).join("");

  const grid = selectTicks(data.xTicks || [], maxXTicks).map((tick) => {
    const xx = x(tick.t);
    const label = formatChartTime(
      panel, tick.t, data.chartTime?.timeZone, tick.dayOffset
    );
    return `<line x1="${xx.toFixed(1)}" y1="${top}" x2="${xx.toFixed(1)}" y2="${height - bottom}" stroke="rgba(120,170,205,.075)"/><text x="${xx.toFixed(1)}" y="${height - 13}" text-anchor="middle" fill="#7895aa" font-size="${size === "compact" && !modal ? 10 : 11}">${label}</text>`;
  }).join("");

  const fractions = size === "compact" && !modal ? [-1, 0, 1] : [-1, -.5, 0, .5, 1];
  const powerTicks = fractions.map((fraction) => {
    const value = peakKw * fraction;
    const yy = zeroY - fraction * (plotH / 2);
    return `<line x1="${left}" y1="${yy.toFixed(1)}" x2="${width - right}" y2="${yy.toFixed(1)}" stroke="rgba(125,179,211,${fraction === 0 ? ".24" : ".07"})"/><text x="${left - 10}" y="${(yy + 4).toFixed(1)}" text-anchor="end" fill="#819caf" font-size="10">${Number(value.toFixed(1))}</text>`;
  }).join("");

  const actualSlot = plotW * (5 * 60 * 1000) / Math.max(1, data.endMs - data.startMs);
  const actualWidth = Math.max(1.4, actualSlot * 0.56);
  const showSourceAttribution = (modal || size === "large") && Boolean(data.attributionRows?.length);
  const actualBars = showSourceAttribution
    ? attributionBars(panel, data.attributionRows, x, powerY, zeroY, actualWidth)
    : (data.actualRows || [])
      .filter((point) => Math.abs(point.w) >= ACTUAL_IDLE_W)
      .map((point) => {
        const xx = x(point.t) - actualWidth / 2;
        const yy = powerY(point.w);
        const rectY = Math.min(yy, zeroY);
        const rectH = Math.max(1, Math.abs(zeroY - yy));
        const color = point.w < 0 ? "#27dfc2" : "#ffa52f";
        const label = point.w < 0 ? t(panel, "actualCharge") : t(panel, "actualDischarge");
        return `<rect x="${xx.toFixed(1)}" y="${rectY.toFixed(1)}" width="${actualWidth.toFixed(1)}" height="${rectH.toFixed(1)}" rx="1.5" fill="${color}" opacity=".92"><title>${panel._escape(`${formatChartTime(panel, point.t, data.chartTime?.timeZone)} · ${label} · ${formatPower(point.w)}`)}</title></rect>`;
      }).join("");

  const past = data.historicalPlanRows || [];
  const historicalPlan = past.map((point, index) => {
    const startT = Math.max(data.startMs, point.t);
    const endT = Math.min(data.nowMs, past[index + 1]?.t ?? data.nowMs);
    if (endT <= startT) return "";
    const xx = x(startT);
    const blockWidth = Math.max(2, x(endT) - xx);
    const yy = powerY(point.w);
    const rectY = Math.min(yy, zeroY);
    const rectH = Math.max(1, Math.abs(zeroY - yy));
    const color = point.w < 0 ? "#43e7ca" : point.w > 0 ? "#ffb354" : "#a7c3cf";
    return `<rect x="${xx.toFixed(1)}" y="${rectY.toFixed(1)}" width="${blockWidth.toFixed(1)}" height="${rectH.toFixed(1)}" rx="2.5" fill="${color}" fill-opacity=".025" stroke="${color}" stroke-opacity=".82" stroke-width="1.15" stroke-dasharray="4 3"><title>${panel._escape(`${formatChartTime(panel, startT, data.chartTime?.timeZone)}–${formatChartTime(panel, endT, data.chartTime?.timeZone)} · ${t(panel, "plan")} · ${formatPower(point.w)}`)}</title></rect>`;
  }).join("");

  const future = data.futurePlanPoints || [];
  const fallback = inferredPlanInterval(future);
  const futurePlan = future.map((point, index) => {
    const nextT = future[index + 1]?.t ?? point.t + fallback;
    const startT = Math.max(point.t, data.nowMs);
    const endT = Math.min(nextT, data.endMs);
    if (endT <= startT) return "";
    const xx = x(startT);
    const blockWidth = Math.max(2, x(endT) - xx - 1);
    const yy = powerY(point.w);
    const rectY = Math.min(yy, zeroY);
    const rectH = Math.max(1, Math.abs(zeroY - yy));
    const color = point.w < 0 ? "#43e7ca" : point.w > 0 ? "#ffb354" : "#a7c3cf";
    return `<rect x="${xx.toFixed(1)}" y="${rectY.toFixed(1)}" width="${blockWidth.toFixed(1)}" height="${rectH.toFixed(1)}" rx="3" fill="${color}" fill-opacity=".085" stroke="${color}" stroke-opacity=".90" stroke-width="1.2" stroke-dasharray="6 4"><title>${panel._escape(`${formatChartTime(panel, startT, data.chartTime?.timeZone)}–${formatChartTime(panel, endT, data.chartTime?.timeZone)} · ${t(panel, "future")} · ${formatPower(point.w)}`)}</title></rect>`;
  }).join("");

  const actualSocPath = linePath(data.actualSocRows || [], x, socY, "pct");
  const actualSoc = actualSocPath
    ? `<path data-series="actual-soc" d="${actualSocPath}" fill="none" stroke="#f472b6" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>`
    : "";
  const actualSocDots = (data.actualSocRows || []).map((point) => (
    `<circle cx="${x(point.t).toFixed(1)}" cy="${socY(point.pct).toFixed(1)}" r="${data.actualSocRows.length === 1 ? 2.8 : 5}" fill="${data.actualSocRows.length === 1 ? "#f472b6" : "transparent"}"><title>${panel._escape(`${formatChartTime(panel, point.t, data.chartTime?.timeZone)} · ${t(panel, "actualSoc")} · ${point.pct.toFixed(1)}%`)}</title></circle>`
  )).join("");

  const wantedSocPoints = desiredSocPoints(data);
  const forecastSocPath = linePath(wantedSocPoints, x, socY, "pct");
  const forecastSoc = forecastSocPath
    ? `<path data-series="forecast-soc" data-history-points="${data.historicalSocWantedRows?.length || 0}" d="${forecastSocPath}" fill="none" stroke="#c4b5fd" stroke-width="2.1" stroke-dasharray="7 5" stroke-linejoin="round" stroke-linecap="round"/>`
    : "";
  const forecastSocDots = wantedSocPoints.map((point) => (
    `<circle cx="${x(point.t).toFixed(1)}" cy="${socY(point.pct).toFixed(1)}" r="${wantedSocPoints.length === 1 ? 2.8 : 5}" fill="${wantedSocPoints.length === 1 ? "#c4b5fd" : "transparent"}"><title>${panel._escape(`${formatChartTime(panel, point.t, data.chartTime?.timeZone)} · ${t(panel, "wantedSoc")} · ${point.pct.toFixed(1)}%`)}</title></circle>`
  )).join("");

  const socFractions = size === "compact" && !modal ? [0, .5, 1] : [0, .25, .5, .75, 1];
  const socTicks = socFractions.map((fraction) => {
    const value = fraction * 100;
    const yy = socY(value);
    return `<text x="${width - right + 9}" y="${(yy + 4).toFixed(1)}" fill="#e69ac6" font-size="9">${value}</text>`;
  }).join("");

  const pricePath = steppedPricePath(data.pricePoints || [], x, priceY, data.endMs);
  const priceLine = pricePath ? `<path d="${pricePath}" fill="none" stroke="#55e8ff" stroke-width="${size === "compact" && !modal ? 2 : 2.5}" stroke-linejoin="round" stroke-linecap="round" filter="url(#epV027PriceGlow)"/>` : "";
  const priceDots = (data.pricePoints || []).map((p) => `<circle cx="${x(p.t).toFixed(1)}" cy="${priceY(p.market).toFixed(1)}" r="5" fill="transparent"><title>${panel._escape(`${formatChartTime(panel, p.t, data.chartTime?.timeZone)} · ${formatPrice(panel, p.market, data.payload?.currency)}`)}</title></circle>`).join("");
  const priceFractions = size === "compact" && !modal ? [0, .5, 1] : [0, .25, .5, .75, 1];
  const priceTicks = range ? priceFractions.map((fraction) => {
    const value = range.minimum + (range.maximum - range.minimum) * fraction;
    const yy = priceY(value);
    return `<text x="${width - right + 47}" y="${(yy + 4).toFixed(1)}" fill="#61dff2" font-size="10">${value.toFixed(2)}</text>`;
  }).join("") : "";

  const nowX = data.nowMs >= data.startMs && data.nowMs < data.endMs ? x(data.nowMs) : null;
  const nowLine = nowX === null ? "" : `<line x1="${nowX.toFixed(1)}" y1="${top}" x2="${nowX.toFixed(1)}" y2="${height - bottom}" stroke="rgba(238,251,255,.28)" stroke-dasharray="4 5"/><text x="${nowX.toFixed(1)}" y="${top - 9}" text-anchor="middle" fill="#c4dae4" font-size="9">${panel._escape(t(panel, "now"))}</text>`;
  const currency = panel._escape(data.payload?.currency || "EUR");
  const titles = size === "compact" && !modal ? "" : `<text x="${left}" y="17" fill="#d9eaf2" font-size="11">${panel._escape(t(panel, "powerAxis"))}</text><text x="${width - right + 9}" y="17" fill="#e69ac6" font-size="10">${panel._escape(t(panel, "socAxis"))}</text><text x="${width - 4}" y="17" text-anchor="end" fill="#62e2f5" font-size="10">${panel._escape(t(panel, "priceAxisShort", { currency }))}</text>`;

  return `<svg viewBox="0 0 ${width} ${height}" width="100%" role="img" aria-label="${panel._escape(chartSubtitle(panel, data.viewRange))}"><defs><filter id="epV027PriceGlow" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="2.1" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter><pattern id="epV051UnknownHatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="5" height="5" fill="#697b8c" fill-opacity=".28"/><line x1="0" y1="0" x2="0" y2="5" stroke="#b7c3ce" stroke-width="1.2"/></pattern><pattern id="${stripePatternId}" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="8" height="8" fill="#79e68c" fill-opacity=".045"/><rect width="2.2" height="8" fill="#a2f2ad" fill-opacity=".24"/></pattern></defs>${titles}${evUnderlays}${grid}${powerTicks}${actualBars}${historicalPlan}${futurePlan}${actualSoc}${forecastSoc}${actualSocDots}${forecastSocDots}${socTicks}${priceLine}${priceDots}${priceTicks}${nowLine}</svg>`;
}

function sourceLine(panel, native, graphValue) {
  return native
    ? `${t(panel, "goodweCounter")} · ${t(panel, "graphEstimate", { value: formatEnergy(graphValue) })}`
    : t(panel, "approximate");
}

function summaryHtml(panel, data, size, modal) {
  const energy = energyComparison(data);
  const planned = planEnergy(data);
  const point = currentPrice(data?.pricePoints || [], data?.nowMs || Date.now());
  const currency = data?.payload?.currency || "EUR";
  const showPlan = modal || size === "large";
  return `<div class="ep-v027-summary ${showPlan ? "with-plan" : ""}">
    <div class="ep-v027-chip charge"><span class="ep-v027-icon">↓</span><div><small>${panel._escape(t(panel, "chargedToday"))}</small><strong>${panel._escape(formatEnergy(energy.charged))}</strong><em>${panel._escape(sourceLine(panel, energy.chargeNative, energy.graph.charged))}</em></div></div>
    <div class="ep-v027-chip discharge"><span class="ep-v027-icon">↑</span><div><small>${panel._escape(t(panel, "dischargedToday"))}</small><strong>${panel._escape(formatEnergy(energy.discharged))}</strong><em>${panel._escape(sourceLine(panel, energy.dischargeNative, energy.graph.discharged))}</em></div></div>
    <div class="ep-v027-chip price"><span class="ep-v027-icon">€</span><div><small>${panel._escape(t(panel, "currentPrice"))}</small><strong>${panel._escape(formatPrice(panel, point?.market, currency))}</strong><em>${panel._escape(data?.payload?.source || "—")}</em></div></div>
    ${showPlan ? `<div class="ep-v027-chip plan-charge"><span class="ep-v027-icon">◇</span><div><small>${panel._escape(t(panel, "plannedCharge"))}</small><strong>${panel._escape(formatEnergy(planned.charged))}</strong><em>${panel._escape(t(panel, "plan"))}</em></div></div><div class="ep-v027-chip plan-discharge"><span class="ep-v027-icon">◇</span><div><small>${panel._escape(t(panel, "plannedDischarge"))}</small><strong>${panel._escape(formatEnergy(planned.discharged))}</strong><em>${panel._escape(t(panel, "plan"))}</em></div></div>` : ""}
  </div>`;
}

function notesHtml(panel, data) {
  const notes = [];
  if (!data?.actualRows?.length) notes.push(t(panel, "noActual"));
  if (!data?.actualSocRows?.length) notes.push(t(panel, "noActualSoc"));
  if (!data?.historicalPlanRows?.length && !data?.futurePlanPoints?.length) notes.push(t(panel, "noPlan"));
  if (!data?.socPlanPoints?.length) notes.push(t(panel, "noForecastSoc"));
  if (!data?.pricePoints?.length) notes.push(data?.payload?.error || t(panel, "noPrice"));
  if (data?.actualRows?.length) notes.push(t(panel, "energySource"));
  if (data?.attributionRows?.length) notes.push(t(panel, "sourceEstimate"));
  if (data?.historicalPlanRows?.length || data?.futurePlanPoints?.length) notes.push(t(panel, "planHistory"));
  if (data?.evProtectionIntervals?.length) notes.push(t(panel, "evHistory"));
  if (data?.actualSocRows?.length || data?.socPlanPoints?.length) notes.push(t(panel, "socSource"));
  const comparison = energyComparison(data);
  if (comparison.chargeDifference > 0.25 || comparison.dischargeDifference > 0.25) notes.push(t(panel, "discrepancy"));
  return notes.map((note) => `<span>${panel._escape(note)}</span>`).join(" · ");
}

function legendHtml(panel, data, size, modal) {
  if (size === "compact") {
    return `<div class="ep-v027-legend compact"><span><i class="actual-combined"></i>${panel._escape(t(panel, "actual"))}</span><span><i class="plan"></i>${panel._escape(t(panel, "plan"))}</span><span><i class="ev-charge-allowed"></i>${panel._escape(t(panel, "evChargeAllowed"))}</span><span><i class="ev-discharge-blocked"></i>${panel._escape(t(panel, "evDischargeBlocked"))}</span><span><i class="actual-soc"></i>${panel._escape(t(panel, "actualSoc"))}</span><span><i class="forecast-soc"></i>${panel._escape(t(panel, "wantedSoc"))}</span><span><i class="price"></i>${panel._escape(t(panel, "marketPrice"))}</span></div>`;
  }
  const sourceLegend = (modal || size === "large") && data?.attributionRows?.length
    ? `<span><i class="grid-battery"></i>${panel._escape(t(panel, "gridToBattery"))}</span><span><i class="solar-battery"></i>${panel._escape(t(panel, "solarToBattery"))}</span><span><i class="unknown-source"></i>${panel._escape(t(panel, "unknownSource"))}</span><span><i class="battery-grid"></i>${panel._escape(t(panel, "batteryToGrid"))}</span><span><i class="solar-grid"></i>${panel._escape(t(panel, "solarToGrid"))}</span>`
    : `<span><i class="actual-charge"></i>${panel._escape(t(panel, "actualCharge"))}</span><span><i class="actual-discharge"></i>${panel._escape(t(panel, "actualDischarge"))}</span>`;
  return `<div class="ep-v027-legend">${sourceLegend}<span><i class="plan"></i>${panel._escape(t(panel, "plan"))}</span><span><i class="ev-charge-allowed"></i>${panel._escape(t(panel, "evChargeAllowed"))}</span><span><i class="ev-discharge-blocked"></i>${panel._escape(t(panel, "evDischargeBlocked"))}</span><span><i class="actual-soc"></i>${panel._escape(t(panel, "actualSoc"))}</span><span><i class="forecast-soc"></i>${panel._escape(t(panel, "wantedSoc"))}</span><span><i class="price"></i>${panel._escape(t(panel, "marketPrice"))}</span></div>`;
}

export function sizeControlHtml(panel, size) {
  const definitions = [["compact", "S", t(panel, "compact")], ["normal", "M", t(panel, "normal")], ["large", "L", t(panel, "large")]];
  return `<div class="ep-v027-size-control" role="group" aria-label="Chart size">${definitions.map(([value, label, title]) => `<button type="button" data-chart-size="${value}" class="${size === value ? "active" : ""}" title="${panel._escape(title)}" aria-pressed="${size === value ? "true" : "false"}">${label}</button>`).join("")}</div>`;
}

export function rangeControlHtml(panel, range) {
  const definitions = [
    ["12h", "12h", t(panel, "range12")],
    ["24h", "24h", t(panel, "range24")],
    ["36h", "36h", t(panel, "range36")],
  ];
  return `<div class="ep-v027-range-control" role="group" aria-label="${panel._escape(t(panel, "rangeControl"))}">${definitions.map(([value, label, title]) => `<button type="button" data-chart-range="${value}" class="${range === value ? "active" : ""}" title="${panel._escape(title)}" aria-pressed="${range === value ? "true" : "false"}">${label}</button>`).join("")}</div>`;
}

export function cardBody(panel, data, size, modal = false) {
  return `<div class="ep-v027-chart size-${size} ${modal ? "modal" : ""}">${chartSvg(panel, data, size, modal)}</div>${legendHtml(panel, data, size, modal)}${summaryHtml(panel, data, size, modal)}<div class="ep-v027-notes">${notesHtml(panel, data)}</div>`;
}

export function ensureStyles(root) {
  if (root.querySelector("#ep-v027-battery-plan-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v027-battery-plan-style";
  style.textContent = `
    .ep-v027-battery-plan-card{min-width:0;padding:17px 18px 14px;border:1px solid rgba(116,198,232,.20);border-radius:22px;background:linear-gradient(150deg,rgba(10,34,63,.93),rgba(5,18,38,.96));box-shadow:0 18px 50px rgba(0,0,0,.18),inset 0 1px 0 rgba(255,255,255,.035);position:relative;overflow:hidden;backdrop-filter:blur(24px);transition:grid-column .22s ease,padding .22s ease,border-radius .22s ease}
    .ep-v027-battery-plan-card.size-compact{grid-column:span 2!important;padding:14px 14px 12px;border-radius:20px}.ep-v027-battery-plan-card.size-normal,.ep-v027-battery-plan-card.size-large{grid-column:1/-1!important}.ep-v027-battery-plan-card.size-large{padding:19px 20px 15px}
    .ep-v027-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.ep-v027-head-actions{display:flex;align-items:center;justify-content:flex-end;flex-wrap:wrap;gap:8px}.ep-v027-kicker{color:#65e6f9;font-size:10px;letter-spacing:.15em;font-weight:850}.ep-v027-subtitle{color:#819caf;font-size:10px;margin-top:4px}
    .ep-v027-size-control{display:flex;align-items:center;padding:3px;border:1px solid rgba(255,255,255,.075);border-radius:999px;background:rgba(1,12,28,.42);box-shadow:inset 0 1px 8px rgba(0,0,0,.20)}.ep-v027-size-control button{width:29px;height:27px;border:0;border-radius:999px;background:transparent;color:#7793a7;font:700 9px -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",sans-serif;cursor:pointer;transition:background .16s ease,color .16s ease,box-shadow .16s ease}.ep-v027-size-control button.active{background:rgba(255,255,255,.13);color:#f0fbff;box-shadow:0 1px 8px rgba(0,0,0,.25),inset 0 1px 0 rgba(255,255,255,.12)}
    .ep-v027-range-control{display:flex;align-items:center;padding:3px;border:1px solid rgba(85,232,255,.14);border-radius:999px;background:rgba(1,12,28,.42);box-shadow:inset 0 1px 8px rgba(0,0,0,.20)}.ep-v027-range-control button{min-width:39px;height:27px;padding:0 8px;border:0;border-radius:999px;background:transparent;color:#7793a7;font:700 9px -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",sans-serif;cursor:pointer;transition:background .16s ease,color .16s ease,box-shadow .16s ease}.ep-v027-range-control button.active{background:rgba(85,232,255,.13);color:#dffaff;box-shadow:0 1px 8px rgba(0,0,0,.25),inset 0 1px 0 rgba(255,255,255,.10)}
    .ep-v027-expand{width:34px;height:34px;display:grid;place-items:center;border-radius:11px;border:1px solid rgba(72,198,235,.22);background:rgba(9,47,74,.50);color:#c3eff8;cursor:pointer;font-size:17px;transition:background .16s ease,border-color .16s ease,transform .16s ease}.ep-v027-expand:hover{background:rgba(12,66,94,.68);border-color:rgba(73,225,248,.42);transform:translateY(-1px)}
    .ep-v027-chart{margin-top:8px;border-radius:15px;background:rgba(1,12,28,.25);overflow:hidden}.ep-v027-chart.size-compact{min-height:160px}.ep-v027-chart.size-normal{min-height:260px}.ep-v027-chart.size-large{min-height:360px}.ep-v027-chart svg{display:block}.ep-v027-empty{min-height:190px;display:grid;place-items:center;color:#7895aa;font-size:10px}
    .ep-v027-legend{display:flex;align-items:center;justify-content:center;flex-wrap:wrap;gap:9px 19px;margin:5px 0 12px;color:#91a9ba;font-size:9px}.ep-v027-legend span{display:flex;align-items:center;gap:7px}.ep-v027-legend i{display:inline-block}.ep-v027-legend i.actual-charge,.ep-v027-legend i.actual-discharge,.ep-v027-legend i.grid-battery,.ep-v027-legend i.solar-battery,.ep-v027-legend i.battery-grid,.ep-v027-legend i.solar-grid,.ep-v027-legend i.unknown-source{width:9px;height:9px;border-radius:3px;background:#27dfc2}.ep-v027-legend i.actual-discharge{background:#ffa52f}.ep-v027-legend i.grid-battery{background:#41b96f}.ep-v027-legend i.solar-battery{background:#d9a928}.ep-v027-legend i.battery-grid{background:#eb6a24}.ep-v027-legend i.solar-grid{background:#f0b52f}.ep-v027-legend i.unknown-source{background:repeating-linear-gradient(45deg,#697b8c 0 2px,#b7c3ce 2px 3px,#697b8c 3px 5px)}.ep-v027-legend i.actual-combined{width:15px;height:9px;border-radius:3px;background:linear-gradient(90deg,#27dfc2 0 50%,#ffa52f 50% 100%)}.ep-v027-legend i.plan{width:18px;height:0;border-top:1px dashed #a8c5d1}.ep-v027-legend i.ev-charge-allowed,.ep-v027-legend i.ev-discharge-blocked{width:16px;height:9px;border:1px solid rgba(140,242,155,.46);border-radius:2px}.ep-v027-legend i.ev-charge-allowed{background:repeating-linear-gradient(135deg,rgba(162,242,173,.42) 0 2px,rgba(121,230,140,.06) 2px 6px)}.ep-v027-legend i.ev-discharge-blocked{background:rgba(121,230,140,.32)}.ep-v027-legend i.actual-soc{width:18px;height:2px;border-radius:999px;background:#f472b6}.ep-v027-legend i.forecast-soc{width:18px;height:0;border-top:2px dashed #c4b5fd}.ep-v027-legend i.price{width:18px;height:2px;border-radius:999px;background:#55e8ff;box-shadow:0 0 8px rgba(85,232,255,.42)}
    .ep-v027-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.ep-v027-summary.with-plan{grid-template-columns:repeat(5,minmax(0,1fr))}.ep-v027-chip{min-width:0;display:flex;align-items:center;gap:10px;padding:10px 11px;border:1px solid rgba(255,255,255,.055);border-radius:13px;background:rgba(255,255,255,.022);box-shadow:inset 0 1px 0 rgba(255,255,255,.025)}.ep-v027-icon{width:29px;height:29px;flex:0 0 29px;display:grid;place-items:center;border-radius:50%;border:1px solid rgba(39,224,193,.62);color:#42ebce;font-size:14px}.ep-v027-chip.discharge .ep-v027-icon{border-color:rgba(255,165,47,.66);color:#ffb34a}.ep-v027-chip.price .ep-v027-icon{border-color:rgba(85,232,255,.62);color:#64e9fb}.ep-v027-chip.plan-charge .ep-v027-icon,.ep-v027-chip.plan-discharge .ep-v027-icon{border-color:rgba(171,205,220,.38);color:#a8c5d1}.ep-v027-chip small{display:block;color:#849dae;font-size:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ep-v027-chip strong{display:block;margin-top:2px;color:#eff9fd;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ep-v027-chip em{display:block;margin-top:2px;color:#607c90;font-size:7px;font-style:normal;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .ep-v027-notes{margin-top:9px;color:#617f94;font-size:8px;line-height:1.5}.ep-v027-footer{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:9px}.ep-v027-footer-actions{display:flex;align-items:center;gap:12px}.ep-v027-footer button{border:0;padding:0;background:transparent;color:#70d5eb;cursor:pointer;font:inherit;font-size:8px}.ep-v027-footer span{color:#607d92;font-size:8px}
    .ep-v027-battery-plan-card.size-compact .ep-v027-subtitle{max-width:340px}.ep-v027-battery-plan-card.size-compact .ep-v027-notes{display:none}.ep-v027-battery-plan-card.size-compact .ep-v027-legend{gap:7px 12px;margin:3px 0 9px}.ep-v027-battery-plan-card.size-compact .ep-v027-summary{grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.ep-v027-battery-plan-card.size-compact .ep-v027-chip{padding:8px;gap:7px}.ep-v027-battery-plan-card.size-compact .ep-v027-icon{width:25px;height:25px;flex-basis:25px}.ep-v027-battery-plan-card.size-compact .ep-v027-chip strong{font-size:12px}.ep-v027-battery-plan-card.size-compact .ep-v027-chip em{display:none}
    @media(max-width:1000px){.ep-v027-battery-plan-card.size-compact{grid-column:1/-1!important}.ep-v027-summary.with-plan{grid-template-columns:repeat(3,minmax(0,1fr))}}
    @media(max-width:720px){.ep-v027-battery-plan-card{padding:14px 13px 12px;border-radius:18px}.ep-v027-head{align-items:flex-start;flex-wrap:wrap}.ep-v027-head-actions{width:100%;justify-content:space-between;gap:6px}.ep-v027-size-control button{width:27px}.ep-v027-range-control button{min-width:38px;padding:0 7px}.ep-v027-summary,.ep-v027-summary.with-plan{grid-template-columns:1fr}.ep-v027-chip strong{font-size:13px}.ep-v027-chart.size-normal{min-height:220px}.ep-v027-chart.size-large{min-height:260px}}
  `;
  root.appendChild(style);
}
