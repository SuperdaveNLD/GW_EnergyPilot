import "./gw-energy-pilot.js?v=1.3.0-beta.3";

const VERSION = "0.07";
const PANEL_NAME = "gw-energypilot-panel";

const LOGO_MARK = `
<svg viewBox="0 0 100 100" role="img" aria-label="GW EnergyPilot" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="epLogoBg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0c2f56"/>
      <stop offset="1" stop-color="#061327"/>
    </linearGradient>
    <linearGradient id="epLogoGlow" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#20dcff"/>
      <stop offset="0.52" stop-color="#19e1d5"/>
      <stop offset="1" stop-color="#22f59c"/>
    </linearGradient>
    <filter id="epLogoShadow" x="-45%" y="-45%" width="190%" height="190%">
      <feGaussianBlur stdDeviation="2.6" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <rect x="2" y="2" width="96" height="96" rx="24" fill="url(#epLogoBg)" stroke="#15527d" stroke-width="2"/>
  <circle cx="50" cy="50" r="31" fill="none" stroke="#18dfff" stroke-width="5" opacity=".92" filter="url(#epLogoShadow)"/>
  <path d="M58 20 41 47h13l-8 19 23-29H56l8-17Z" fill="#22f59c" filter="url(#epLogoShadow)"/>
  <text x="50" y="68" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="26" font-weight="900" letter-spacing="-2" fill="url(#epLogoGlow)" filter="url(#epLogoShadow)">GW</text>
</svg>`;

const ICONS = {
  house: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 11.3 12 4l9 7.3v8.2a.5.5 0 0 1-.5.5h-5.2v-6.1H8.7V20H3.5a.5.5 0 0 1-.5-.5v-8.2Z"/><path d="M9 20v-6h6v6"/></svg>`,
  solar: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 11h12l2 8H2l2-8Z"/><path d="m6 11-1 8M10 11v8M14 11l1 8M3 15h14M10 19v3M6.5 22h7"/><circle cx="18.5" cy="5.5" r="2.5"/><path d="M18.5 1V0M18.5 11v-1M14.5 5.5h-1M23.5 5.5h-1M15.7 2.7 15 2M22 9l-.7-.7M21.3 2.7 22 2M15 9l.7-.7"/></svg>`,
  grid: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 2 5 20M12 2 7 22M8.5 8h7M6.8 14h10.4M5.4 19h13.2M9 8l6 6M15 8l-6 6"/></svg>`,
  battery: `<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="4" width="10" height="17" rx="2"/><path d="M10 4V2h4v2M9.5 9h5M9.5 13h5M9.5 17h5"/></svg>`,
};

await customElements.whenDefined(PANEL_NAME);

const PanelClass = customElements.get(PANEL_NAME);
const originalRender = PanelClass.prototype._render;
const originalFormatState = PanelClass.prototype._formatState;

function toCelsius(value, unit) {
  if (unit === "°C") return value;
  if (unit === "°F") return (value - 32) * (5 / 9);
  if (unit === "K") return value - 273.15;
  return value;
}

function fromCelsius(value, unit) {
  if (unit === "°C") return value;
  if (unit === "°F") return value * (9 / 5) + 32;
  if (unit === "K") return value + 273.15;
  return value;
}

function localizedNumber(hass, value, digits = 1) {
  const language = hass?.locale?.language || hass?.language || undefined;
  return new Intl.NumberFormat(language, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

function formatTemperatureForHA(hass, stateObj, fallback = "—") {
  if (!stateObj || ["unknown", "unavailable"].includes(stateObj.state)) {
    return fallback;
  }

  const numeric = Number(stateObj.state);
  if (!Number.isFinite(numeric)) {
    return fallback;
  }

  const sourceUnit = stateObj.attributes?.unit_of_measurement || "°C";
  const targetUnit = hass?.config?.unit_system?.temperature || sourceUnit;
  const celsius = toCelsius(numeric, sourceUnit);
  const converted = fromCelsius(celsius, targetUnit);
  return `${localizedNumber(hass, converted, 1)} ${targetUnit}`;
}

PanelClass.prototype._formatState = function energyPilotFormatState(
  stateObj,
  fallback = "—"
) {
  if (stateObj?.attributes?.device_class === "temperature") {
    return formatTemperatureForHA(this._hass, stateObj, fallback);
  }
  return originalFormatState.call(this, stateObj, fallback);
};

function formatPower(panel, value) {
  return panel._formatPower(Number.isFinite(value) ? value : null);
}

function chooseHouseLoad(rawLoad, pv, grid, battery) {
  const calculated =
    Number.isFinite(pv) && Number.isFinite(grid) && Number.isFinite(battery)
      ? pv - grid + battery
      : null;

  if (!Number.isFinite(rawLoad)) {
    return Number.isFinite(calculated) && calculated >= 0 ? calculated : null;
  }

  if (rawLoad < 0 && Number.isFinite(calculated) && calculated >= 0) {
    return calculated;
  }

  if (
    Number.isFinite(calculated) &&
    calculated >= 0 &&
    Math.abs(rawLoad - calculated) > Math.max(1500, Math.abs(calculated) * 0.8)
  ) {
    return calculated;
  }

  return Math.max(0, rawLoad);
}

function flowDirection(value, positiveDirection, negativeDirection) {
  if (!Number.isFinite(value) || Math.abs(value) < 50) {
    return "idle";
  }
  return value > 0 ? positiveDirection : negativeDirection;
}

function nodeHtml(kind, title, value, subtitle = "") {
  return `
    <div class="ep-flow-node ep-flow-${kind}">
      <div class="ep-flow-node-title">${title}</div>
      <div class="ep-flow-icon">${ICONS[kind]}</div>
      <div class="ep-flow-node-value">${value}</div>
      ${subtitle ? `<div class="ep-flow-node-sub">${subtitle}</div>` : ""}
    </div>`;
}

function flowLink(className, direction) {
  return `
    <div class="ep-flow-link ${className} ${direction}">
      <div class="ep-flow-track"></div>
      <div class="ep-flow-arrows"><span>›</span><span>›</span><span>›</span></div>
    </div>`;
}

function buildFlowOverview(panel) {
  const pv = panel._numberByKey("pv_total_power");
  const grid = panel._numberByKey("meter_total_power_fast");
  const battery = panel._numberByKey("battery_power");
  const rawLoad = panel._numberByKey("total_load_power");
  const soc = panel._numberByKey("battery_soc");
  const house = chooseHouseLoad(rawLoad, pv, grid, battery);

  const gridDirection = flowDirection(grid, "outbound", "inbound");
  const batteryDirection = flowDirection(battery, "inbound", "outbound");
  const pvDirection = Number.isFinite(pv) && pv > 50 ? "inbound" : "idle";
  const houseDirection = Number.isFinite(house) && house > 50 ? "outbound" : "idle";

  const gridText =
    !Number.isFinite(grid) || Math.abs(grid) < 50
      ? "Balanced"
      : grid > 0
      ? "Exporting"
      : "Importing";
  const batteryText =
    !Number.isFinite(battery) || Math.abs(battery) < 50
      ? `Holding${Number.isFinite(soc) ? ` · ${Math.round(soc)}%` : ""}`
      : battery < 0
      ? `Charging${Number.isFinite(soc) ? ` · ${Math.round(soc)}%` : ""}`
      : `Discharging${Number.isFinite(soc) ? ` · ${Math.round(soc)}%` : ""}`;

  return `
    <section class="ep-flow-overview" aria-label="Live energy flow overview">
      <div class="ep-flow-heading">
        <div>
          <div class="ep-flow-kicker">LIVE ENERGY FLOW</div>
          <div class="ep-flow-title">Power overview</div>
        </div>
        <div class="ep-flow-live"><span></span>LIVE</div>
      </div>
      <div class="ep-flow-stage">
        ${nodeHtml("house", "HOUSE", formatPower(panel, house), "Total load")}
        ${nodeHtml("solar", "PV", formatPower(panel, pv), "Production")}
        <div class="ep-flow-hub">${LOGO_MARK}</div>
        ${nodeHtml("grid", "GRID", formatPower(panel, grid), gridText)}
        ${nodeHtml("battery", "BATTERY", formatPower(panel, battery), batteryText)}
        ${flowLink("ep-link-pv", pvDirection)}
        ${flowLink("ep-link-grid", gridDirection)}
        ${flowLink("ep-link-house", houseDirection)}
        ${flowLink("ep-link-battery", batteryDirection)}
      </div>
    </section>`;
}

function flowStyles() {
  return `
    .ep-brand-mark {
      width: 62px;
      height: 62px;
      flex: 0 0 62px;
      display: grid;
      place-items: center;
      border-radius: 17px;
      overflow: visible;
      filter: drop-shadow(0 0 18px rgba(25,217,255,.18));
    }
    .ep-brand-mark svg { width: 100%; height: 100%; display: block; }

    .ep-flow-overview {
      width: min(430px, 100%);
      min-height: 300px;
      margin: 0 0 14px;
      padding: 16px 17px 13px;
      border-radius: 20px;
      border: 1px solid rgba(64, 161, 255, .23);
      background:
        radial-gradient(circle at 48% 50%, rgba(26, 221, 255, .09), transparent 35%),
        linear-gradient(145deg, rgba(8, 30, 59, .94), rgba(5, 17, 36, .97));
      box-shadow: 0 14px 44px rgba(0,0,0,.18), inset 0 0 40px rgba(12, 97, 154, .05);
      overflow: hidden;
      position: relative;
    }
    .ep-flow-overview::before {
      content: "";
      position: absolute;
      width: 220px;
      height: 220px;
      left: 105px;
      top: 65px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(24, 238, 175, .08), transparent 68%);
      pointer-events: none;
    }
    .ep-flow-heading {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      position: relative;
      z-index: 2;
    }
    .ep-flow-kicker {
      color: #66e7fb;
      font-size: 10px;
      letter-spacing: .16em;
      font-weight: 850;
    }
    .ep-flow-title {
      color: #eef8ff;
      font-size: 17px;
      font-weight: 760;
      margin-top: 2px;
      letter-spacing: -.015em;
    }
    .ep-flow-live {
      display: flex;
      align-items: center;
      gap: 6px;
      color: #8df7d2;
      font-size: 9px;
      font-weight: 850;
      letter-spacing: .11em;
      padding: 5px 8px;
      border-radius: 999px;
      border: 1px solid rgba(31, 239, 167, .18);
      background: rgba(31, 239, 167, .07);
    }
    .ep-flow-live span {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #20f49d;
      box-shadow: 0 0 10px #20f49d;
      animation: epPulseLive 1.5s ease-in-out infinite;
    }
    .ep-flow-stage {
      width: 100%;
      height: 236px;
      position: relative;
      margin-top: 3px;
    }
    .ep-flow-node {
      position: absolute;
      width: 92px;
      min-height: 68px;
      padding: 7px 7px 6px;
      border: 1px solid rgba(54, 160, 255, .20);
      border-radius: 14px;
      background: linear-gradient(145deg, rgba(13, 39, 72, .88), rgba(7, 23, 47, .94));
      box-shadow: inset 0 0 22px rgba(40, 165, 255, .035);
      text-align: center;
      z-index: 4;
    }
    .ep-flow-house { top: 0; left: 50%; transform: translateX(-50%); }
    .ep-flow-solar { left: 0; top: 50%; transform: translateY(-50%); border-color: rgba(31,239,167,.27); }
    .ep-flow-grid { right: 0; top: 50%; transform: translateY(-50%); }
    .ep-flow-battery { bottom: 0; left: 50%; transform: translateX(-50%); border-color: rgba(31,239,167,.27); }
    .ep-flow-node-title {
      color: #65e7fa;
      font-size: 8px;
      letter-spacing: .14em;
      font-weight: 850;
    }
    .ep-flow-icon { height: 24px; display: grid; place-items: center; margin: 3px auto 2px; }
    .ep-flow-icon svg {
      width: 26px;
      height: 26px;
      fill: none;
      stroke: #1bdcff;
      stroke-width: 1.8;
      stroke-linecap: round;
      stroke-linejoin: round;
      filter: drop-shadow(0 0 6px rgba(27,220,255,.45));
    }
    .ep-flow-solar .ep-flow-icon svg,
    .ep-flow-battery .ep-flow-icon svg {
      stroke: #22f59c;
      filter: drop-shadow(0 0 6px rgba(34,245,156,.42));
    }
    .ep-flow-node-value {
      color: #f5fbff;
      font-size: 13px;
      font-weight: 820;
      line-height: 1.1;
      letter-spacing: -.02em;
    }
    .ep-flow-node-sub {
      color: #8098af;
      font-size: 8px;
      margin-top: 3px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .ep-flow-hub {
      position: absolute;
      left: 50%;
      top: 50%;
      width: 62px;
      height: 62px;
      transform: translate(-50%, -50%);
      border-radius: 50%;
      z-index: 6;
      display: grid;
      place-items: center;
      background: rgba(3, 20, 39, .96);
      box-shadow: 0 0 28px rgba(25, 217, 255, .16), 0 0 42px rgba(34,245,156,.08);
    }
    .ep-flow-hub::before {
      content: "";
      position: absolute;
      inset: -5px;
      border-radius: 50%;
      border: 1px solid rgba(24, 220, 255, .42);
      box-shadow: inset 0 0 13px rgba(24,220,255,.12), 0 0 13px rgba(24,220,255,.14);
      animation: epHubPulse 2.4s ease-in-out infinite;
    }
    .ep-flow-hub svg { width: 52px; height: 52px; border-radius: 50%; }
    .ep-flow-hub svg > rect { rx: 50; ry: 50; }

    .ep-flow-link {
      position: absolute;
      z-index: 2;
      overflow: hidden;
      color: #20dcff;
      opacity: .95;
    }
    .ep-flow-link.idle { opacity: .22; }
    .ep-link-pv, .ep-link-grid {
      height: 18px;
      top: 50%;
      transform: translateY(-50%);
    }
    .ep-link-pv { left: 91px; width: calc(50% - 118px); color: #22f59c; }
    .ep-link-grid { left: calc(50% + 30px); width: calc(50% - 121px); color: #20dcff; }
    .ep-link-house, .ep-link-battery {
      width: 18px;
      left: 50%;
      transform: translateX(-50%);
    }
    .ep-link-house { top: 67px; height: calc(50% - 92px); color: #20dcff; }
    .ep-link-battery { top: calc(50% + 30px); height: calc(50% - 95px); color: #22f59c; }
    .ep-flow-track {
      position: absolute;
      inset: 7px 0 auto;
      height: 4px;
      border-radius: 999px;
      background: currentColor;
      box-shadow: 0 0 10px currentColor, 0 0 18px currentColor;
      opacity: .62;
    }
    .ep-link-house .ep-flow-track,
    .ep-link-battery .ep-flow-track {
      inset: 0 auto 0 7px;
      width: 4px;
      height: auto;
    }
    .ep-flow-arrows {
      position: absolute;
      inset: -2px 0 0;
      display: flex;
      align-items: center;
      justify-content: space-around;
      color: white;
      font-size: 18px;
      font-weight: 900;
      text-shadow: 0 0 9px currentColor;
      animation: epFlowHorizontal .95s linear infinite;
    }
    .ep-flow-link.inbound .ep-flow-arrows { animation-direction: normal; }
    .ep-flow-link.outbound .ep-flow-arrows { animation-direction: reverse; }
    .ep-link-grid.inbound .ep-flow-arrows { animation-direction: reverse; }
    .ep-link-grid.outbound .ep-flow-arrows { animation-direction: normal; }
    .ep-link-house,
    .ep-link-battery { overflow: visible; }
    .ep-link-house .ep-flow-arrows,
    .ep-link-battery .ep-flow-arrows {
      width: 18px;
      height: 100%;
      flex-direction: row;
      transform: rotate(90deg);
      transform-origin: center;
      animation-name: epFlowVertical;
      font-size: 16px;
    }
    .ep-link-house.outbound .ep-flow-arrows { animation-direction: reverse; }
    .ep-link-house.inbound .ep-flow-arrows { animation-direction: normal; }
    .ep-link-battery.outbound .ep-flow-arrows { animation-direction: normal; }
    .ep-link-battery.inbound .ep-flow-arrows { animation-direction: reverse; }
    .ep-flow-link.idle .ep-flow-arrows { animation-play-state: paused; }

    @keyframes epPulseLive {
      0%, 100% { opacity: .45; transform: scale(.82); }
      50% { opacity: 1; transform: scale(1.15); }
    }
    @keyframes epHubPulse {
      0%, 100% { transform: scale(.96); opacity: .55; }
      50% { transform: scale(1.04); opacity: 1; }
    }
    @keyframes epFlowHorizontal {
      from { transform: translateX(-7px); }
      to { transform: translateX(7px); }
    }
    @keyframes epFlowVertical {
      from { transform: rotate(90deg) translateX(-7px); }
      to { transform: rotate(90deg) translateX(7px); }
    }

    @media (max-width: 720px) {
      .ep-brand-mark { width: 48px; height: 48px; flex-basis: 48px; border-radius: 13px; }
      .ep-flow-overview { width: 100%; min-height: 292px; padding: 14px; border-radius: 17px; }
      .ep-flow-stage { height: 230px; }
      .ep-flow-node { width: 84px; }
      .ep-link-pv { left: 83px; width: calc(50% - 110px); }
      .ep-link-grid { left: calc(50% + 30px); width: calc(50% - 113px); }
    }
  `;
}

PanelClass.prototype._render = function energyPilotRenderV007() {
  originalRender.call(this);

  const root = this.shadowRoot;
  if (!root) {
    return;
  }

  // Replace the old image element entirely. This avoids PNG contrast issues,
  // broken static paths and CSP/data-URI differences between HA clients.
  const oldBrandImage = root.querySelector(".brand img");
  if (oldBrandImage) {
    const mark = document.createElement("div");
    mark.className = "ep-brand-mark";
    mark.innerHTML = LOGO_MARK;
    oldBrandImage.replaceWith(mark);
  }

  const versionBadge = root.querySelector(".version");
  if (versionBadge) {
    versionBadge.textContent = `v${VERSION}`;
  }

  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) {
    footerItems[0].textContent = `GW EnergyPilot v${VERSION}`;
  }

  const style = document.createElement("style");
  style.textContent = flowStyles();
  root.appendChild(style);

  const heroGrid = root.querySelector(".hero-grid");
  if (heroGrid) {
    heroGrid.insertAdjacentHTML("beforebegin", buildFlowOverview(this));
  }
};
