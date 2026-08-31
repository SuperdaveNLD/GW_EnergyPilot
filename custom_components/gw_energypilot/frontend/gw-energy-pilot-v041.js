import "./gw-energy-pilot-v039.js?v=1.0.1-beta4";
import {
  FLOW_THRESHOLD_W,
  flowVisualMap,
  resolveHousePower,
} from "./gw-energy-pilot-v038-model.js?v=1.0.1-beta4";
import {
  dashboardLanguage,
  localizedEmsMode,
  localizeV038Controller,
} from "./gw-energy-pilot-v038-i18n.js?v=1.0.1-beta4";
import { loadChartData } from "./gw-energy-pilot-v027-battery-plan-data.js?v=1.0.1-beta4";
import { refreshBatteryPlanCard } from "./gw-energy-pilot-v027-battery-plan-core.js?v=1.0.1-beta4";

const VERSION = "0.41";
const PANEL_NAME = "gw-energypilot-panel";
const MOTION_STYLE_ID = "ep-v041-no-motion";
const GLOBAL_MOTION_STYLE_ID = "ep-v041-global-no-motion";
const LIVE_PATCH_DELAY_MS = 40;
const PLAN_PATCH_DELAY_MS = 220;
const BATTERY_QUICK_ACTION_COMMANDS = Object.freeze({
  max_export: "manual_max_export",
  battery_pause: "manual_battery_hold",
  max_charge: "manual_max_charge",
});
const EMHASS_COST_FUNCTIONS = Object.freeze({
  profit: Object.freeze({ label: "Profit", legacyKey: "emhass_costfun_profit" }),
  cost: Object.freeze({ label: "Cost", legacyKey: "emhass_costfun_cost" }),
  "self-consumption": Object.freeze({
    label: "Self-consumption",
    legacyKey: "emhass_costfun_self_consumption",
  }),
});

const COPY = Object.freeze({
  en: Object.freeze({
    autoActive: "AUTO ACTIVE",
    goodweAuto: "GOODWE AUTO",
    automaticOn: "Automatic ON",
    automaticOff: "Automatic OFF",
    balanced: "Balanced",
    importing: "Importing",
    exporting: "Exporting",
    holding: "Holding",
    charging: "Charging",
    discharging: "Discharging",
    totalLoad: "Total load",
    production: "Production",
    waiting: "Waiting",
    modeCharge: "Mode 11 · Charge",
    modeDischarge: "Mode 12 · Discharge",
    modeHold: "Mode 8 · Hold",
    locked: "LOCKED · AUTOMATIC",
    manualReady: "MANUAL READY",
    entitiesMissing: "ENTITIES MISSING",
    automaticOwner: "Automatic Control owns the inverter.",
    automaticOwnerDetail: "Manual controls are hidden; the active mode continues to follow live Modbus read-back.",
    manualUnavailable: "Manual controls are unavailable.",
    manualUnavailableDetail: "The required Home Assistant entities are missing.",
    live: "Live",
    hoverHint: "Hover a mode for its meaning.",
    today: "Today",
    yesterday: "Yesterday",
    motionDisabled: "Disabled in v0.41 for stable desktop and mobile operation",
    flowUnknown: "power unavailable",
    flowIdle: "idle below 50 W",
    flowLow: "low relative flow",
    flowMedium: "medium relative flow",
    flowHigh: "high relative flow",
    pvToSystem: "PV to system",
    gridToSystem: "Grid to system",
    systemToGrid: "System to grid",
    systemToHouse: "System to house",
    batteryToSystem: "Battery to system",
    systemToBattery: "System to battery",
    pvSources: "PV sources",
    noPvSources: "No sources configured",
    internalPvTelemetry: "Internal GoodWe telemetry",
    externalPvEntity: "External PV entity",
    connectivityTitle: "System status",
    connectivityOk: "ALL OK",
    connectivityIssue: "ISSUE",
    connectivityChecking: "CHECKING",
    modbus: "Modbus",
    evCharger: "EV charger",
    evCoordination: "EV coordination",
    online: "Online",
    unreachable: "Unknown / unreachable",
    checkingStatus: "Waiting for first poll",
    refreshEvery: "refresh every",
    notConfigured: "Online check not configured",
    active: "Active",
    offByUser: "Off by user",
    temporarilyPaused: "Temporarily paused",
    pausesIn: "pauses in",
    resumesIn: "resumes in",
    lastEmsSetpointUpdate: "Last update",
    evBlockingTitle: "EV CHARGING · ANTI-DISCHARGE ACTIVE",
    evBlockingDetail: "Home battery discharge is blocked · Mode 8 Battery Hold",
    evChargeAllowedTitle: "EV CHARGING · BATTERY CHARGE ALLOWED",
    evChargeAllowedDetail: "The home battery is following the active charging plan",
    evWaitingTitle: "EV CHARGING STOPPED · FRESH PLAN REQUIRED",
    evWaitingDetail: "Battery Hold remains active while EnergyPilot waits for a fresh EMHASS plan",
    evPendingTitle: "EV CHARGING · PROTECTION EVALUATING",
    evPendingDetail: "EnergyPilot is determining the safe home-battery direction",
  }),
  nl: Object.freeze({
    autoActive: "AUTO ACTIEF",
    goodweAuto: "GOODWE AUTO",
    automaticOn: "Automatisch AAN",
    automaticOff: "Automatisch UIT",
    balanced: "In balans",
    importing: "Importeren",
    exporting: "Exporteren",
    holding: "Stand-by",
    charging: "Laden",
    discharging: "Ontladen",
    totalLoad: "Totale belasting",
    production: "Productie",
    waiting: "Wachten",
    modeCharge: "Modus 11 · Laden",
    modeDischarge: "Modus 12 · Ontladen",
    modeHold: "Modus 8 · Stand-by",
    locked: "VERGRENDELD · AUTOMATISCH",
    manualReady: "HANDMATIG GEREED",
    entitiesMissing: "ENTITEITEN ONTBREKEN",
    automaticOwner: "Automatische regeling bestuurt de omvormer.",
    automaticOwnerDetail: "Handmatige bediening is verborgen; de actieve modus volgt de live Modbus-teruglezing.",
    manualUnavailable: "Handmatige bediening is niet beschikbaar.",
    manualUnavailableDetail: "De vereiste Home Assistant-entiteiten ontbreken.",
    live: "Live",
    hoverHint: "Beweeg over een modus voor uitleg.",
    today: "Vandaag",
    yesterday: "Gisteren",
    motionDisabled: "Uitgeschakeld in v0.41 voor stabiele werking op desktop en mobiel",
    flowUnknown: "vermogen niet beschikbaar",
    flowIdle: "inactief onder 50 W",
    flowLow: "lage relatieve stroom",
    flowMedium: "gemiddelde relatieve stroom",
    flowHigh: "hoge relatieve stroom",
    pvToSystem: "PV naar systeem",
    gridToSystem: "Net naar systeem",
    systemToGrid: "Systeem naar net",
    systemToHouse: "Systeem naar woning",
    batteryToSystem: "Batterij naar systeem",
    systemToBattery: "Systeem naar batterij",
    pvSources: "PV-bronnen",
    noPvSources: "Geen bronnen geconfigureerd",
    internalPvTelemetry: "Interne GoodWe-telemetrie",
    externalPvEntity: "Externe PV-entiteit",
    connectivityTitle: "Systeemstatus",
    connectivityOk: "ALLES OK",
    connectivityIssue: "STORING",
    connectivityChecking: "CONTROLEREN",
    modbus: "Modbus",
    evCharger: "Laadpaal",
    evCoordination: "EV-regeling",
    online: "Online",
    unreachable: "Onbekend / niet bereikbaar",
    checkingStatus: "Wachten op eerste poll",
    refreshEvery: "verversing iedere",
    notConfigured: "Onlinecontrole niet ingesteld",
    active: "Actief",
    offByUser: "Uit door gebruiker",
    temporarilyPaused: "Tijdelijk gepauzeerd",
    pausesIn: "pauzeert over",
    resumesIn: "hervat over",
    lastEmsSetpointUpdate: "Laatste update",
    evBlockingTitle: "EV LAADT · ONTLAADBEVEILIGING ACTIEF",
    evBlockingDetail: "Ontladen van de thuisaccu is geblokkeerd · Modus 8 Battery Hold",
    evChargeAllowedTitle: "EV LAADT · THUISACCU LADEN TOEGESTAAN",
    evChargeAllowedDetail: "De thuisaccu volgt het actieve laadplan",
    evWaitingTitle: "EV-LADEN GESTOPT · NIEUW PLAN NODIG",
    evWaitingDetail: "Battery Hold blijft actief terwijl EnergyPilot op een nieuw EMHASS-plan wacht",
    evPendingTitle: "EV LAADT · BEVEILIGING WORDT BEOORDEELD",
    evPendingDetail: "EnergyPilot bepaalt de veilige richting voor de thuisaccu",
  }),
});

const NO_MOTION_CSS = `
  :host,
  :host *,
  :host *::before,
  :host *::after {
    animation: none !important;
    transition: none !important;
    scroll-behavior: auto !important;
  }
  :host {
    overflow-anchor: auto !important;
  }
  :host button,
  :host a,
  :host label,
  :host input,
  :host select,
  :host textarea,
  :host [role="button"],
  :host [tabindex] {
    touch-action: manipulation;
  }
  :host .ep-layout-menu {
    max-height: calc(100dvh - 104px) !important;
    overscroll-behavior: contain;
    touch-action: pan-y;
    -webkit-overflow-scrolling: touch;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
  }
  :host .ep-v041-motion-disabled {
    opacity: .58;
  }
  :host .ep-v041-motion-disabled input {
    cursor: not-allowed !important;
  }
  :host main .ep-battery-actions .ep-battery-action[data-action="resume_auto"]:not(.active),
  :host main .ep-battery-actions .ep-battery-action[data-action="resume_auto"]:hover:not(:disabled):not(.active) {
    border-color: rgba(82, 175, 233, .18) !important;
    background: rgba(6, 31, 55, .48) !important;
    color: #a9c4d8 !important;
    box-shadow: none !important;
    transform: none !important;
  }
  :host .ep-flow-link::after,
  :host .ep-flow-arrows,
  :host .ep-flow-live span,
  :host .ep-flow-hub::after,
  :host .ep-v011-particles span {
    display: none !important;
  }
  :host .ep-flow-link[data-ep-v041-flow-status] {
    --ep-v041-pipe-size: 4px;
    --ep-v041-pipe-opacity: .86;
    opacity: 1;
    overflow: visible;
  }
  :host .ep-flow-link[data-ep-v041-flow-intensity="low"] {
    --ep-v041-pipe-size: 3px;
    --ep-v041-pipe-opacity: .72;
  }
  :host .ep-flow-link[data-ep-v041-flow-intensity="medium"] {
    --ep-v041-pipe-size: 4px;
    --ep-v041-pipe-opacity: .86;
  }
  :host .ep-flow-link[data-ep-v041-flow-intensity="high"] {
    --ep-v041-pipe-size: 5px;
    --ep-v041-pipe-opacity: 1;
  }
  :host .ep-flow-link[data-ep-v041-flow-status="idle"],
  :host .ep-flow-link[data-ep-v041-flow-status="unknown"] {
    --ep-v041-pipe-size: 2px;
    color: #71879a;
  }
  :host .ep-flow-link[data-ep-v041-flow-status="idle"] {
    --ep-v041-pipe-opacity: .34;
  }
  :host .ep-flow-link[data-ep-v041-flow-status="unknown"] {
    --ep-v041-pipe-opacity: .52;
  }
  :host .ep-flow-link[data-ep-v041-flow-status] .ep-flow-track {
    inset: auto 0;
    top: 50%;
    width: auto;
    height: var(--ep-v041-pipe-size);
    transform: translateY(-50%);
    background: currentColor;
    border-radius: 999px;
    box-shadow: 0 0 0 1px rgba(3, 17, 32, .82), 0 0 7px currentColor;
    opacity: var(--ep-v041-pipe-opacity);
  }
  :host .ep-link-house[data-ep-v041-flow-status] .ep-flow-track,
  :host .ep-link-battery[data-ep-v041-flow-status] .ep-flow-track {
    inset: 0 auto;
    left: 50%;
    width: var(--ep-v041-pipe-size);
    height: auto;
    transform: translateX(-50%);
  }
  :host .ep-flow-link[data-ep-v038-motion="right"] .ep-flow-track {
    -webkit-mask-image: linear-gradient(to right, rgba(0,0,0,.35), #000 58%, #000);
    mask-image: linear-gradient(to right, rgba(0,0,0,.35), #000 58%, #000);
  }
  :host .ep-flow-link[data-ep-v038-motion="left"] .ep-flow-track {
    -webkit-mask-image: linear-gradient(to left, rgba(0,0,0,.35), #000 58%, #000);
    mask-image: linear-gradient(to left, rgba(0,0,0,.35), #000 58%, #000);
  }
  :host .ep-flow-link[data-ep-v038-motion="down"] .ep-flow-track {
    -webkit-mask-image: linear-gradient(to bottom, rgba(0,0,0,.35), #000 58%, #000);
    mask-image: linear-gradient(to bottom, rgba(0,0,0,.35), #000 58%, #000);
  }
  :host .ep-flow-link[data-ep-v038-motion="up"] .ep-flow-track {
    -webkit-mask-image: linear-gradient(to top, rgba(0,0,0,.35), #000 58%, #000);
    mask-image: linear-gradient(to top, rgba(0,0,0,.35), #000 58%, #000);
  }
  :host .ep-flow-link[data-ep-v041-flow-status="idle"] .ep-flow-track,
  :host .ep-flow-link[data-ep-v041-flow-status="unknown"] .ep-flow-track {
    -webkit-mask-image: none;
    mask-image: none;
    box-shadow: 0 0 0 1px rgba(3, 17, 32, .72);
  }
  :host .ep-flow-link[data-ep-v041-flow-status="unknown"] .ep-flow-track {
    background: repeating-linear-gradient(90deg,currentColor 0 5px,transparent 5px 9px);
  }
  :host .ep-link-house[data-ep-v041-flow-status="unknown"] .ep-flow-track,
  :host .ep-link-battery[data-ep-v041-flow-status="unknown"] .ep-flow-track {
    background: repeating-linear-gradient(180deg,currentColor 0 5px,transparent 5px 9px);
  }
  :host .ep-v041-flow-arrow,
  :host .ep-v041-flow-state {
    position: absolute;
    left: 50%;
    top: 50%;
    z-index: 7;
    display: none;
    min-width: 0;
    min-height: 0;
    padding: 0;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    border: 0;
    background: currentColor;
    color: currentColor;
    font-size: 0;
    line-height: 0;
    transform: translate(-50%, -50%);
    pointer-events: none;
  }
  :host .ep-v041-flow-arrow {
    width: 22px;
    height: 12px;
    -webkit-clip-path: polygon(0 34%, 66% 34%, 66% 0, 100% 50%, 66% 100%, 66% 66%, 0 66%);
    clip-path: polygon(0 34%, 66% 34%, 66% 0, 100% 50%, 66% 100%, 66% 66%, 0 66%);
  }
  :host .ep-flow-link[data-ep-v038-motion="left"] .ep-v041-flow-arrow {
    transform: translate(-50%, -50%) rotate(180deg);
  }
  :host .ep-flow-link[data-ep-v038-motion="down"] .ep-v041-flow-arrow {
    transform: translate(-50%, -50%) rotate(90deg);
  }
  :host .ep-flow-link[data-ep-v038-motion="up"] .ep-v041-flow-arrow {
    transform: translate(-50%, -50%) rotate(-90deg);
  }
  :host .ep-flow-link[data-ep-v041-flow-status="active"] .ep-v041-flow-arrow,
  :host .ep-flow-link[data-ep-v041-flow-status="idle"] .ep-v041-flow-state,
  :host .ep-flow-link[data-ep-v041-flow-status="unknown"] .ep-v041-flow-state {
    display: flex;
  }
  :host .ep-flow-link[data-ep-v041-flow-intensity="medium"] .ep-v041-flow-arrow {
    width: 24px;
    height: 13px;
  }
  :host .ep-flow-link[data-ep-v041-flow-intensity="high"] .ep-v041-flow-arrow {
    width: 26px;
    height: 14px;
  }
  :host .ep-flow-link[data-ep-v041-flow-status="idle"] .ep-v041-flow-state {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    opacity: .72;
  }
  :host .ep-flow-link[data-ep-v041-flow-status="unknown"] .ep-v041-flow-state {
    width: 18px;
    height: 18px;
    border: 1px dashed currentColor;
    border-radius: 5px;
    background: #071a2e;
    font-size: 11px;
    line-height: 1;
  }
  :host .ep-flow-hub {
    box-shadow: 0 0 0 1px rgba(25, 217, 255, .20), 0 0 20px rgba(25, 217, 255, .12) !important;
  }
  :host .ep-flow-hub::before {
    inset: -3px !important;
    border-color: rgba(24, 220, 255, .30) !important;
    box-shadow: none !important;
    opacity: .68;
  }
  :host .ep-v034-flow-tight .ep-v041-flow-arrow {
    width: 18px;
    height: 10px;
  }
  :host .ep-connectivity-wrap {
    position: relative;
    display: inline-flex;
  }
  :host .ep-connectivity-status {
    appearance: none;
    display: inline-flex;
    align-items: center;
    gap: 7px;
    min-height: 31px;
    padding: 7px 11px;
    border: 1px solid rgba(145, 167, 189, .17);
    border-radius: 999px;
    color: #c4d2df;
    background: rgba(145, 167, 189, .09);
    font: inherit;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: .08em;
    white-space: nowrap;
    cursor: pointer;
  }
  :host .ep-connectivity-status.ok {
    color: #dffff4;
    border-color: rgba(24, 239, 163, .25);
    background: rgba(24, 239, 163, .11);
  }
  :host .ep-connectivity-status.issue {
    color: #ffd1cc;
    border-color: rgba(241, 101, 89, .36);
    background: rgba(149, 43, 36, .25);
  }
  :host .ep-connectivity-dot {
    width: 7px;
    height: 7px;
    flex: 0 0 7px;
    border-radius: 50%;
    background: currentColor;
    box-shadow: 0 0 12px currentColor;
  }
  :host .ep-connectivity-popover {
    position: absolute;
    z-index: 100;
    top: calc(100% + 8px);
    right: 0;
    display: none;
    width: min(310px, calc(100vw - 28px));
    padding: 11px;
    border: 1px solid rgba(86, 174, 218, .20);
    border-radius: 13px;
    color: #dcecf5;
    background: #081d34;
    box-shadow: 0 16px 38px rgba(0, 0, 0, .34);
    text-align: left;
    pointer-events: auto;
  }
  :host .ep-connectivity-wrap.open .ep-connectivity-popover,
  :host .ep-connectivity-wrap:focus-within .ep-connectivity-popover {
    display: block;
  }
  @media (hover: hover) and (pointer: fine) {
    :host .ep-connectivity-wrap:hover .ep-connectivity-popover {
      display: block;
    }
  }
  :host .ep-connectivity-popover-title {
    margin: 0 0 6px;
    color: #f0f9fd;
    font-size: 10px;
    font-weight: 850;
  }
  :host .ep-connectivity-row {
    display: grid;
    grid-template-columns: 9px minmax(0, 1fr);
    gap: 8px;
    padding: 6px 2px;
    border-top: 1px solid rgba(102, 165, 199, .09);
  }
  :host .ep-connectivity-row:first-of-type { border-top: 0; }
  :host .ep-connectivity-row-marker {
    width: 7px;
    height: 7px;
    margin-top: 3px;
    border-radius: 50%;
    background: #7891a1;
  }
  :host .ep-connectivity-row.good .ep-connectivity-row-marker { background: #55dfaa; }
  :host .ep-connectivity-row.bad .ep-connectivity-row-marker { background: #f1786d; }
  :host .ep-connectivity-row strong {
    display: block;
    color: #d8e9f1;
    font-size: 9px;
  }
  :host .ep-connectivity-row span:last-child {
    display: block;
    margin-top: 2px;
    color: #86a4b5;
    font-size: 8px;
    line-height: 1.35;
  }
  :host .ep-v041-ev-protection[hidden] {
    display: none !important;
  }
  :host .ep-v041-ev-protection {
    display: grid;
    grid-template-columns: 42px minmax(0, 1fr);
    align-items: center;
    gap: 12px;
    margin-top: 14px;
    padding: 13px 14px;
    box-sizing: border-box;
    border: 1px solid rgba(42, 219, 236, .38);
    border-radius: 13px;
    color: #dffcff;
    background: linear-gradient(135deg, rgba(11, 74, 91, .72), rgba(8, 42, 64, .78));
  }
  :host .ep-v041-ev-protection[data-state="allowing_charge"] {
    border-color: rgba(46, 225, 165, .34);
    background: linear-gradient(135deg, rgba(10, 78, 70, .66), rgba(8, 42, 61, .78));
  }
  :host .ep-v041-ev-protection[data-state="waiting_for_fresh_plan"] {
    border-color: rgba(255, 180, 79, .40);
    background: linear-gradient(135deg, rgba(91, 57, 16, .62), rgba(48, 37, 34, .78));
  }
  :host .ep-v041-ev-icon {
    width: 42px;
    height: 42px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
    border: 1px solid rgba(115, 241, 249, .48);
    border-radius: 12px 12px 16px 16px;
    color: #92f7fb;
    background: rgba(7, 29, 49, .72);
    font-size: 11px;
    font-weight: 900;
    letter-spacing: .06em;
  }
  :host .ep-v041-ev-protection[data-state="allowing_charge"] .ep-v041-ev-icon {
    border-color: rgba(105, 246, 199, .45);
    color: #9ff9d8;
  }
  :host .ep-v041-ev-protection[data-state="waiting_for_fresh_plan"] .ep-v041-ev-icon {
    border-color: rgba(255, 199, 116, .48);
    color: #ffd398;
  }
  :host .ep-v041-ev-copy {
    min-width: 0;
  }
  :host .ep-v041-ev-title {
    color: inherit;
    font-size: 11px;
    font-weight: 900;
    letter-spacing: .075em;
    line-height: 1.3;
  }
  :host .ep-v041-ev-detail {
    margin-top: 4px;
    color: #a8cbd5;
    font-size: 11px;
    line-height: 1.4;
  }
  @media (max-width: 720px) {
    :host .ep-layout-menu {
      top: calc(74px + env(safe-area-inset-top)) !important;
      right: calc(14px + env(safe-area-inset-right)) !important;
      left: calc(14px + env(safe-area-inset-left)) !important;
      width: auto !important;
      max-height: calc(100dvh - 94px - env(safe-area-inset-top) - env(safe-area-inset-bottom)) !important;
    }
    :host .ep-v041-ev-protection {
      grid-template-columns: 38px minmax(0, 1fr);
      gap: 10px;
      padding: 12px;
    }
    :host .ep-v041-ev-icon {
      width: 38px;
      height: 38px;
    }
  }
`;

const GLOBAL_NO_MOTION_CSS = `
  .ep-v027-backdrop,
  .ep-v027-backdrop *,
  .ep-v027-backdrop *::before,
  .ep-v027-backdrop *::after,
  .ep-v026-bp-backdrop,
  .ep-v026-bp-backdrop *,
  .ep-v026-bp-backdrop *::before,
  .ep-v026-bp-backdrop *::after,
  .ep13-backdrop,
  .ep13-backdrop *,
  .ep13-backdrop *::before,
  .ep13-backdrop *::after {
    animation: none !important;
    transition: none !important;
    scroll-behavior: auto !important;
  }
  .ep-v027-backdrop,
  .ep-v026-bp-backdrop,
  .ep13-backdrop {
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
  }
`;

function language(panel) {
  return dashboardLanguage(panel) === "nl" ? "nl" : "en";
}

function copy(panel) {
  return COPY[language(panel)];
}

function finite(panel, key) {
  const value = panel._numberByKey?.(key, null);
  return Number.isFinite(value) ? value : null;
}

function formatTimestamp(panel, value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  const locale = panel?._hass?.locale?.language || panel?._hass?.language || undefined;
  return new Intl.DateTimeFormat(locale, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

function pvGenerationSnapshot(panel) {
  const state = panel._stateByKey?.("pv_generation_power");
  if (!state) {
    return {
      state: null,
      power: finite(panel, "pv_total_power"),
      sources: [],
      configuredExternal: 0,
      internalEnabled: true,
    };
  }
  const attrs = state.attributes || {};
  return {
    state,
    power: finiteValue(state.state),
    sources: Array.isArray(attrs.sources) ? attrs.sources : [],
    configuredExternal: Number(attrs.configured_external_sources || 0),
    internalEnabled: attrs.internal_enabled !== false,
  };
}

function patchPvSourceMetrics(panel, solar, snapshot) {
  if (!solar) return;
  const t = copy(panel);
  for (const metric of solar.querySelectorAll("[data-pv-source-index]")) {
    const index = Number(metric.dataset.pvSourceIndex);
    const source = snapshot.sources[index];
    if (!source) continue;
    setText(metric, ".metric-label", source.name || `PV ${index + 1}`);
    setText(metric, ".metric-value", panel._formatPower(finiteValue(source.power_w)));
    setText(
      metric,
      ".metric-sub",
      source.kind === "internal"
        ? t.internalPvTelemetry
        : source.entity_id || t.externalPvEntity
    );
  }
  const empty = solar.querySelector("[data-pv-empty]");
  setText(empty, ".metric-label", t.pvSources);
  setText(empty, ".metric-sub", t.noPvSources);
}

function finiteValue(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function normalize(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replaceAll("‑", "-")
    .replaceAll("–", "-")
    .replaceAll("—", "-")
    .replace(/\s+/g, " ");
}

function setText(root, selector, value) {
  const node = root?.querySelector(selector);
  if (node && node.textContent !== String(value)) node.textContent = String(value);
  return node;
}

function setStrong(root, selector, value) {
  const row = root?.querySelector(selector);
  const node = row?.querySelector("strong") || row;
  if (node && node.textContent !== String(value)) node.textContent = String(value);
}

function setStatus(node, active, text) {
  if (!node) return;
  node.classList.toggle("active", active);
  node.classList.toggle("inactive", !active);
  let dot = node.querySelector(".dot");
  if (!dot) {
    dot = document.createElement("span");
    dot.className = "dot";
    node.prepend(dot);
  }
  const trailing = [...node.childNodes].find((child) => child.nodeType === 3);
  if (trailing) trailing.textContent = text;
  else node.append(document.createTextNode(text));
}

function formatConnectivityDuration(seconds) {
  const value = Math.max(0, Math.round(Number(seconds) || 0));
  const minutes = Math.floor(value / 60);
  const remainder = value % 60;
  return minutes > 0 ? `${minutes}m ${String(remainder).padStart(2, "0")}s` : `${remainder}s`;
}

function ensureConnectivityStatus(panel, root) {
  const actions = root?.querySelector(".header-actions");
  if (!actions || actions.querySelector(".ep-connectivity-wrap")) return;
  const wrap = document.createElement("div");
  wrap.className = "ep-connectivity-wrap";
  wrap.innerHTML = `
    <button type="button" class="ep-connectivity-status checking" aria-expanded="false" aria-controls="ep-connectivity-popover">
      <span class="ep-connectivity-dot" aria-hidden="true"></span>
      <span class="ep-connectivity-label"></span>
    </button>
    <div class="ep-connectivity-popover" id="ep-connectivity-popover" role="tooltip">
      <div class="ep-connectivity-popover-title"></div>
      ${["modbus", "ev", "coordination"].map((key) => `
        <div class="ep-connectivity-row" data-connectivity-row="${key}">
          <span class="ep-connectivity-row-marker" aria-hidden="true"></span>
          <div><strong></strong><span></span></div>
        </div>`).join("")}
    </div>`;
  const version = actions.querySelector(".version");
  actions.insertBefore(wrap, version || null);
  const button = wrap.querySelector(".ep-connectivity-status");
  button?.addEventListener("click", () => {
    const open = !wrap.classList.contains("open");
    wrap.classList.toggle("open", open);
    button.setAttribute("aria-expanded", open ? "true" : "false");
  });
  button?.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    wrap.classList.remove("open");
    button.setAttribute("aria-expanded", "false");
    button.focus();
  });
}

function patchConnectivityRow(root, key, tone, label, detail) {
  const row = root.querySelector(`[data-connectivity-row="${key}"]`);
  if (!row) return;
  row.classList.remove("good", "bad", "neutral");
  row.classList.add(tone);
  setText(row, "strong", label);
  setText(row, "span:last-child", detail);
}

function patchConnectivityStatus(panel, root) {
  const wrap = root.querySelector(".ep-connectivity-wrap");
  const button = wrap?.querySelector(".ep-connectivity-status");
  if (!wrap || !button) return;
  const t = copy(panel);
  const state = panel._stateByKey?.("connectivity_status");
  const attrs = state?.attributes || {};
  const status = String(state?.state || "checking");
  const label = status === "all_ok"
    ? t.connectivityOk
    : status === "issue" ? t.connectivityIssue : t.connectivityChecking;
  button.classList.remove("ok", "issue", "checking");
  button.classList.add(status === "all_ok" ? "ok" : status === "issue" ? "issue" : "checking");
  setText(button, ".ep-connectivity-label", label);
  button.setAttribute("aria-label", `${t.connectivityTitle}: ${label}`);
  setText(wrap, ".ep-connectivity-popover-title", t.connectivityTitle);

  const modbus = String(attrs.modbus_status || "checking");
  const refresh = finiteValue(attrs.refresh_seconds);
  patchConnectivityRow(
    root,
    "modbus",
    modbus === "online" ? "good" : modbus === "unreachable" ? "bad" : "neutral",
    t.modbus,
    modbus === "online"
      ? `${t.online}${refresh === null ? "" : ` · ${t.refreshEvery} ${Math.round(refresh)}s`}`
      : modbus === "unreachable" ? t.unreachable : t.checkingStatus
  );

  const ev = String(attrs.ev_status || "not_configured");
  patchConnectivityRow(
    root,
    "ev",
    ev === "online" ? "good" : ev === "unreachable" ? "bad" : "neutral",
    t.evCharger,
    ev === "online" ? t.online : ev === "unreachable" ? t.unreachable : t.notConfigured
  );

  const requested = attrs.ev_coordination_requested === true;
  const effective = attrs.ev_coordination_effective === true;
  const transition = String(attrs.ev_transition || "");
  const remaining = finiteValue(attrs.ev_transition_remaining_seconds);
  let coordinationDetail = !requested
    ? t.offByUser
    : effective ? t.active : t.temporarilyPaused;
  if (transition === "suspend_pending" && remaining !== null) {
    coordinationDetail = `${t.active} · ${t.pausesIn} ${formatConnectivityDuration(remaining)}`;
  } else if (transition === "resume_pending" && remaining !== null) {
    coordinationDetail = `${t.temporarilyPaused} · ${t.resumesIn} ${formatConnectivityDuration(remaining)}`;
  }
  patchConnectivityRow(
    root,
    "coordination",
    !requested ? "neutral" : effective ? "good" : "bad",
    t.evCoordination,
    coordinationDetail
  );
}

function replaceTrailingButtonText(button, text) {
  if (!button) return;
  const trailing = [...button.childNodes]
    .reverse()
    .find((node) => node.nodeType === 3);
  if (trailing) trailing.textContent = ` ${text}`;
  else button.append(document.createTextNode(` ${text}`));
}

function metricByLabels(card, labels) {
  if (!card) return null;
  const wanted = new Set(labels.map(normalize));
  for (const metric of card.querySelectorAll(".metric")) {
    const label = normalize(metric.querySelector(".metric-label")?.textContent);
    if (wanted.has(label)) return metric;
  }
  return null;
}

function patchMetric(card, labels, value, sub = undefined) {
  const metric = metricByLabels(card, labels);
  if (!metric) return;
  const valueNode = metric.querySelector(".metric-value");
  if (valueNode && valueNode.textContent !== String(value)) {
    valueNode.textContent = String(value);
  }
  if (sub !== undefined) {
    const subNode = metric.querySelector(".metric-sub");
    if (subNode && subNode.textContent !== String(sub)) subNode.textContent = String(sub);
  }
}

function patchBalanceRows(card, panel, load, inverter, acActive) {
  const pvSnapshot = pvGenerationSnapshot(panel);
  const pv = pvSnapshot.power;
  const grid = finite(panel, "meter_total_power_fast");
  const battery = finite(panel, "battery_power");
  const balance =
    [pv, grid, battery].every(Number.isFinite) ? pv - grid + battery : null;
  for (const row of card?.querySelectorAll(".balance-row") || []) {
    const label = normalize(row.querySelector("span")?.textContent);
    const value = row.querySelector("strong");
    if (!value) continue;
    let next = null;
    if (label.includes("inverter") || label.includes("omvormer")) next = inverter;
    else if (label.includes("ac active") || label.includes("ac actief")) next = acActive;
    else if (label.includes("phase sum") || label.includes("fasesom") || label.includes("som belasting fasen")) next = load;
    else if (label.includes("system power balance") || label.includes("systeemvermogensbalans")) next = balance;
    if (next !== null) value.textContent = panel._formatPower(next);
  }
}

function gridPresentation(panel, power) {
  const t = copy(panel);
  if (!Number.isFinite(power) || Math.abs(power) < FLOW_THRESHOLD_W) {
    return { css: "hold", text: t.balanced };
  }
  return power > 0
    ? { css: "export", text: t.exporting }
    : { css: "import", text: t.importing };
}

function batteryPresentation(panel, power) {
  const t = copy(panel);
  if (!Number.isFinite(power) || Math.abs(power) < FLOW_THRESHOLD_W) {
    return { css: "hold", text: t.holding };
  }
  return power > 0
    ? { css: "discharge", text: t.discharging }
    : { css: "charge", text: t.charging };
}

function patchPill(card, presentation) {
  const pill = card?.querySelector(".pill");
  if (!pill) return;
  pill.classList.remove("hold", "import", "export", "charge", "discharge");
  pill.classList.add(presentation.css);
  pill.textContent = presentation.text;
}

function externalState(panel, exact, suffixes) {
  return panel._findState?.(exact) || panel._findStateBySuffix?.(suffixes) || null;
}

function formatEnergy(value) {
  const number = finiteValue(value);
  return number === null ? "—" : `${number.toFixed(number >= 10 ? 1 : 2)} kWh`;
}

function formatPercent(value, decimals = 1) {
  const number = finiteValue(value);
  return number === null ? "—" : `${number.toFixed(decimals)}%`;
}

function formatDecimal(value, decimals = 4) {
  const number = finiteValue(value);
  return number === null ? "—" : number.toFixed(decimals);
}

const FLOW_ARROWS = Object.freeze({
  right: "→",
  left: "←",
  up: "↑",
  down: "↓",
});

function ensureStaticFlowNodes(link) {
  let arrow = link.querySelector(".ep-v041-flow-arrow");
  if (!arrow) {
    arrow = document.createElement("span");
    arrow.className = "ep-v041-flow-arrow";
    arrow.setAttribute("aria-hidden", "true");
    link.appendChild(arrow);
  }
  let state = link.querySelector(".ep-v041-flow-state");
  if (!state) {
    state = document.createElement("span");
    state.className = "ep-v041-flow-state";
    state.setAttribute("aria-hidden", "true");
    link.appendChild(state);
  }
  return { arrow, state };
}

function flowDirectionText(panel, key, direction) {
  const t = copy(panel);
  if (key === "pv") return t.pvToSystem;
  if (key === "house") return t.systemToHouse;
  if (key === "grid") return direction === "left" ? t.gridToSystem : t.systemToGrid;
  return direction === "up" ? t.batteryToSystem : t.systemToBattery;
}

function flowSourceText(panel, key) {
  return {
    pv: "PV",
    grid: language(panel) === "nl" ? "Net" : "Grid",
    house: language(panel) === "nl" ? "Woning" : "House",
    battery: language(panel) === "nl" ? "Batterij" : "Battery",
  }[key];
}

function patchStaticFlowLink(panel, link, key, presentation) {
  const { arrow, state } = ensureStaticFlowNodes(link);
  const t = copy(panel);
  link.dataset.epV038Motion = presentation.direction;
  link.dataset.epV041FlowStatus = presentation.status;
  link.dataset.epV041FlowIntensity = presentation.intensity;
  arrow.textContent = FLOW_ARROWS[presentation.direction] || "";
  state.textContent = presentation.status === "unknown" ? "?" : "•";

  let label;
  if (presentation.status === "unknown") {
    label = `${flowSourceText(panel, key)} · ${t.flowUnknown}`;
  } else if (presentation.status === "idle") {
    label = `${flowSourceText(panel, key)} · ${t.flowIdle}`;
  } else {
    const intensity = {
      low: t.flowLow,
      medium: t.flowMedium,
      high: t.flowHigh,
    }[presentation.intensity];
    label =
      `${flowDirectionText(panel, key, presentation.direction)} · ` +
      `${panel._formatPower(Math.abs(presentation.power))} · ${intensity}`;
  }
  link.setAttribute("role", "img");
  link.setAttribute("aria-label", label);
  link.title = label;
}

function patchFlow(panel, root, pv, load, grid, battery, soc) {
  const house = resolveHousePower(load, pv, grid, battery);
  const visual = flowVisualMap({ pv, house, grid, battery }, FLOW_THRESHOLD_W);
  const t = copy(panel);
  const gridMode = gridPresentation(panel, grid);
  const batteryMode = batteryPresentation(panel, battery);

  setText(root, ".ep-flow-house .ep-flow-node-value", panel._formatPower(house));
  setText(root, ".ep-flow-solar .ep-flow-node-value", panel._formatPower(pv));
  setText(root, ".ep-flow-grid .ep-flow-node-value", panel._formatPower(grid));
  setText(root, ".ep-flow-battery .ep-flow-node-value", panel._formatPower(battery));
  setText(root, ".ep-flow-house .ep-flow-node-sub", t.totalLoad);
  setText(root, ".ep-flow-solar .ep-flow-node-sub", t.production);
  setText(root, ".ep-flow-grid .ep-flow-node-sub", gridMode.text);
  setText(
    root,
    ".ep-flow-battery .ep-flow-node-sub",
    `${batteryMode.text}${Number.isFinite(soc) ? ` · ${Math.round(soc)}%` : ""}`
  );

  const semantic = {
    pv: !Number.isFinite(pv) || pv <= FLOW_THRESHOLD_W ? "idle" : "inbound",
    grid: !Number.isFinite(grid) || Math.abs(grid) < FLOW_THRESHOLD_W
      ? "idle"
      : grid > 0 ? "outbound" : "inbound",
    house: !Number.isFinite(house) || house <= FLOW_THRESHOLD_W ? "idle" : "outbound",
    battery: !Number.isFinite(battery) || Math.abs(battery) < FLOW_THRESHOLD_W
      ? "idle"
      : battery > 0 ? "inbound" : "outbound",
  };
  for (const [key, selector] of Object.entries({
    pv: ".ep-link-pv",
    grid: ".ep-link-grid",
    house: ".ep-link-house",
    battery: ".ep-link-battery",
  })) {
    const link = root.querySelector(selector);
    if (!link) continue;
    link.classList.remove("idle", "inbound", "outbound");
    link.classList.add(semantic[key]);
    patchStaticFlowLink(panel, link, key, visual[key]);
  }
}

function installEvProtectionBanner(root) {
  const card = root?.querySelector(".panel-card.controller");
  if (!card || card.querySelector(".ep-v041-ev-protection")) return;

  const banner = document.createElement("aside");
  banner.className = "ep-v041-ev-protection";
  banner.hidden = true;
  banner.setAttribute("role", "status");
  banner.setAttribute("aria-live", "polite");
  banner.setAttribute("aria-atomic", "true");

  const icon = document.createElement("span");
  icon.className = "ep-v041-ev-icon";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = "EV";

  const text = document.createElement("span");
  text.className = "ep-v041-ev-copy";
  const title = document.createElement("span");
  title.className = "ep-v041-ev-title";
  const detail = document.createElement("span");
  detail.className = "ep-v041-ev-detail";
  title.style.display = "block";
  detail.style.display = "block";
  text.append(title, detail);
  banner.append(icon, text);

  const safetyNote = card.querySelector(".safety-note");
  if (safetyNote) safetyNote.before(banner);
  else card.appendChild(banner);
}

function evProtectionState(panel) {
  const commandState = panel._stateByKey?.("control_command");
  const explicit = String(commandState?.attributes?.ev_protection_state || "");
  if (explicit) return explicit;
  const command = String(commandState?.state || "");
  if (command === "ev_anti_discharge_hold") return "blocking_discharge";
  if (command === "waiting_for_ev_stop_optimization") return "waiting_for_fresh_plan";
  if ([
    "ev_battery_charge",
    "ev_charge_allowed",
    "ev_charge_fallback",
    "ev_grid_import_charge",
  ].includes(command)) return "allowing_charge";
  return "inactive";
}

function patchEvProtectionBanner(panel, root) {
  const banner = root.querySelector(".ep-v041-ev-protection");
  if (!banner) return;
  const state = evProtectionState(panel);
  const t = copy(panel);
  const presentation = {
    blocking_discharge: [t.evBlockingTitle, t.evBlockingDetail],
    allowing_charge: [t.evChargeAllowedTitle, t.evChargeAllowedDetail],
    waiting_for_fresh_plan: [t.evWaitingTitle, t.evWaitingDetail],
    active_pending: [t.evPendingTitle, t.evPendingDetail],
  }[state];

  banner.hidden = !presentation;
  if (!presentation) {
    delete banner.dataset.state;
    return;
  }
  banner.dataset.state = state;
  const title = banner.querySelector(".ep-v041-ev-title");
  const detail = banner.querySelector(".ep-v041-ev-detail");
  if (title) title.textContent = presentation[0];
  if (detail) detail.textContent = presentation[1];
}

function patchController(panel, root, automaticOn) {
  const card = root.querySelector(".panel-card.controller");
  if (!card) return;
  const t = copy(panel);
  const button = card.querySelector("#auto-toggle");
  if (button) {
    button.classList.toggle("on", automaticOn);
    button.classList.toggle("off", !automaticOn);
    button.setAttribute("aria-pressed", automaticOn ? "true" : "false");
    replaceTrailingButtonText(button, automaticOn ? t.automaticOn : t.automaticOff);
  }

  const modeState = panel._stateByKey?.("ems_mode");
  const mode = Number(modeState?.state);
  const modeName = Number.isFinite(mode)
    ? localizedEmsMode(language(panel), mode).name
    : modeState?.attributes?.mode_name || "—";
  patchMetric(card, ["EMS mode", "EMS-modus"], `${modeState?.state || "—"} · ${modeName}`);
  const commandAttrs = panel._stateByKey?.("control_command")?.attributes || {};
  patchMetric(
    card,
    ["EMS setpoint", "EMS-setpoint"],
    panel._formatPower(finite(panel, "ems_setpoint")),
    `${t.lastEmsSetpointUpdate}: ${formatTimestamp(
      panel,
      commandAttrs.last_ems_setpoint_updated_at
    )}`
  );
  patchMetric(
    card,
    ["EnergyPilot target", "PCC target", "Battery target", "Control target", "PCC-doel", "Batterijdoel", "Regeldoel", "Accudoel"],
    panel._formatPower(finite(panel, "target_power"))
  );
  patchMetric(card, ["Command", "Commando"], panel._textByKey?.("control_command") || "—");

  const manual = card.querySelector(".ep-v021-manual-pad");
  if (manual) {
    button?.setAttribute("aria-controls", manual.id);
    const controlsReady = Boolean(panel._entityId?.("manual_mode") && panel._entityId?.("manual_power"));
    const busy = Boolean(panel.__epV021ManualBusy);
    const compact = automaticOn || !controlsReady;
    const wasCompact = manual.classList.contains("compact");
    if (compact && !wasCompact && manual.contains(root.activeElement)) {
      button?.focus({ preventScroll: true });
    }
    manual.classList.toggle("locked", compact);
    manual.classList.toggle("compact", compact);
    const modeGrid = manual.querySelector(".ep-v021-mode-grid");
    const powerRow = manual.querySelector(".ep-v021-power-row");
    if (modeGrid) modeGrid.hidden = compact;
    if (powerRow) powerRow.hidden = compact;
    const state = manual.querySelector(".ep-v021-manual-state");
    if (state) state.textContent = automaticOn ? t.locked : controlsReady ? t.manualReady : t.entitiesMissing;
    for (const modeButton of manual.querySelectorAll(".ep-v021-mode-button")) {
      const active = Number(modeButton.dataset.mode) === mode;
      const pending = Number(modeButton.dataset.mode) === panel.__epV021ManualBusy;
      modeButton.classList.toggle("active", active);
      modeButton.classList.toggle("pending", pending);
      modeButton.disabled = automaticOn || !controlsReady || busy;
      modeButton.setAttribute("aria-disabled", modeButton.disabled ? "true" : "false");
    }
    const slider = manual.querySelector(".ep-v021-power-slider");
    const powerState = panel._stateByKey?.("manual_power");
    const power = finiteValue(powerState?.state);
    if (slider) {
      slider.disabled = automaticOn || !controlsReady || busy;
      if (
        Number.isFinite(power) &&
        root.activeElement !== slider &&
        !panel.__epV021ManualPowerDirty
      ) {
        slider.value = String(power);
      }
    }
    const powerLabel = manual.querySelector(".ep-v021-power-label strong");
    if (powerLabel && Number.isFinite(power) && !panel.__epV021ManualPowerDirty) {
      powerLabel.textContent = `${Math.round(power)} W`;
    }
    const note = manual.querySelector("[data-manual-note]");
    if (note) {
      // Automatic ownership supersedes feedback from an earlier manual command.
      // Drop that stale message so releasing ownership starts from current live
      // read-back instead of presenting a command that is no longer active.
      if (automaticOn && panel.__epV021ManualMessage) {
        panel.__epV021ManualMessage = null;
      }
      const message = panel.__epV021ManualMessage;
      note.classList.remove("ok", "error");
      if (message?.tone) note.classList.add(message.tone);
      if (automaticOn) {
        note.innerHTML = `<strong>${panel._escape(t.automaticOwner)}</strong> ${panel._escape(t.automaticOwnerDetail)}`;
      } else if (message?.text) {
        note.textContent = message.text;
      } else if (!controlsReady) {
        note.innerHTML = `<strong>${panel._escape(t.manualUnavailable)}</strong> ${panel._escape(t.manualUnavailableDetail)}`;
      } else {
        const actualSetpoint = finite(panel, "ems_setpoint");
        note.innerHTML = `<strong>${panel._escape(t.live)}:</strong> ${panel._escape(modeName)} · ${panel._escape(Number.isFinite(actualSetpoint) ? `${Math.round(actualSetpoint)} W` : "—")}. ${panel._escape(t.hoverHint)}`;
      }
    }
  }

  localizeV038Controller(panel, root);
  patchEvProtectionBanner(panel, root);
}

function patchBatteryQuickActions(panel, root, automaticOn) {
  const selectedAction = automaticOn
    ? "resume_auto"
    : Object.entries(BATTERY_QUICK_ACTION_COMMANDS).find(
      ([, command]) => panel._textByKey?.("control_command", "") === command
    )?.[0] || null;

  for (const button of root.querySelectorAll(".ep-battery-action[data-action]")) {
    const active = button.dataset.action === selectedAction;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  }
}

function activeCostFunctionRaw(panel) {
  const state = panel._stateByKey?.("emhass_cost_function");
  if (!state || ["unknown", "unavailable"].includes(state.state)) return null;
  const attribute = state.attributes?.emhass_costfun;
  if (attribute && EMHASS_COST_FUNCTIONS[attribute]) return String(attribute);
  const option = normalize(state.state);
  return Object.entries(EMHASS_COST_FUNCTIONS).find(
    ([, definition]) => normalize(definition.label) === option
  )?.[0] || null;
}

function patchCostFunctionSelector(panel, root) {
  const wrap = root.querySelector(".ep-v016-costfun");
  if (!wrap) return;
  const activeRaw = activeCostFunctionRaw(panel);
  const activeDefinition = activeRaw ? EMHASS_COST_FUNCTIONS[activeRaw] : null;
  const busyRaw = panel.__epV016CostfunBusy || null;
  const busyDefinition = busyRaw ? EMHASS_COST_FUNCTIONS[busyRaw] : null;
  wrap.setAttribute("aria-busy", busyRaw ? "true" : "false");
  const activeLabel = wrap.querySelector(".ep-v016-costfun-active");
  if (activeLabel) {
    activeLabel.classList.toggle("pending", Boolean(busyRaw) || !activeDefinition);
    activeLabel.textContent = busyRaw
      ? `Applying · ${busyDefinition?.label || busyRaw}…`
      : activeDefinition
        ? `Active · ${activeDefinition.label}`
        : "Reading active strategy…";
  }

  const selectEntityId = panel._entityId?.("emhass_cost_function");
  for (const button of wrap.querySelectorAll(".ep-v016-costfun-button[data-costfun]")) {
    const raw = button.dataset.costfun;
    const definition = EMHASS_COST_FUNCTIONS[raw];
    if (!definition) continue;
    const active = raw === activeRaw;
    const available = Boolean(
      selectEntityId || panel._entityId?.(definition.legacyKey)
    );
    const label = button.dataset.costfunLabel || definition.label;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
    button.disabled = Boolean(busyRaw) || !available;
    const nextText = busyRaw === raw
      ? "Applying…"
      : `${active ? "✓ " : ""}${label}`;
    if (button.textContent !== nextText) button.textContent = nextText;
    button.title = active
      ? `${label} is the active EMHASS cost function`
      : `Set EMHASS costfun to ${raw} and run a fresh optimization`;
  }
}

function socLimitValue(panel, kind) {
  const key = kind === "min" ? "emhass_minimum_soc" : "emhass_maximum_soc";
  const entityValue = finite(panel, key);
  if (Number.isFinite(entityValue)) return entityValue;

  // The SOC NumberEntities initialize asynchronously and can remain unknown
  // after a transient startup read failure. Keep the presentation usable from
  // sources that already follow the same ownership contract: GoodWe 45356 is
  // canonical for Minimum SOC, while the periodically refreshed EMHASS config
  // diagnostics are canonical for Maximum SOC.
  const fallback = kind === "min"
    ? optimizeAttributes(panel).battery_discharge_depth_on_grid_45356
    : diagnosticConfigAttributes(panel).emhass_maximum_soc_pct;
  const value = finiteValue(fallback);
  return value !== null && value >= 0 && value <= 100 ? value : null;
}

function patchEmhass(panel, root) {
  const card = root.querySelector(".panel-card.emhass");
  if (!card) return;
  patchCostFunctionSelector(panel, root);
  const t = copy(panel);
  const pBattState = externalState(
    panel,
    ["sensor.p_batt_forecast"],
    [".p_batt_forecast", "_p_batt_forecast"]
  );
  const optimState = externalState(
    panel,
    ["sensor.optim_status"],
    [".optim_status", "_optim_status"]
  );
  const socForecast = externalState(
    panel,
    ["sensor.soc_batt_forecast"],
    [".soc_batt_forecast", "_soc_batt_forecast"]
  );
  const loadForecast = externalState(
    panel,
    ["sensor.p_load_forecast"],
    [".p_load_forecast", "_p_load_forecast"]
  );
  const pvForecast = externalState(
    panel,
    ["sensor.p_pv_forecast"],
    [".p_pv_forecast", "_p_pv_forecast"]
  );
  const pBatt = panel._numberState?.(pBattState, null);
  const optimText = optimState?.state || "Not detected";
  setStatus(card.querySelector(".section-title-row .status"), normalize(optimText) === "optimal", optimText);
  setText(card, ".emhass-target strong", panel._formatPower(pBatt));
  patchMetric(card, ["SOC forecast", "SOC-voorspelling", "SOC-prognose"], panel._formatState(socForecast));
  patchMetric(card, ["Load forecast", "Belastingsvoorspelling", "Verbruiksprognose"], panel._formatState(loadForecast));
  patchMetric(card, ["PV forecast", "PV-voorspelling", "PV-prognose"], panel._formatState(pvForecast));
  const attrs = optimizeAttributes(panel);
  const expectedMode = finiteValue(attrs.controller_expected_mode);
  const expectedTarget = finiteValue(attrs.controller_target_power);
  const command = String(attrs.controller_command || "");
  let mapping;
  if (
    attrs.controller_enabled === true &&
    expectedMode !== null &&
    !command.startsWith("waiting_")
  ) {
    const prefix = language(panel) === "nl" ? "Modus" : "Mode";
    const name = localizedEmsMode(language(panel), expectedMode).name;
    const setpoint = expectedTarget !== null && expectedTarget !== 0
      ? ` · ${panel._formatPower(Math.abs(expectedTarget))}`
      : "";
    mapping = `${prefix} ${expectedMode} · ${name}${setpoint}`;
  } else if (attrs.controller_enabled === false || command.startsWith("waiting_")) {
    mapping = t.waiting;
  } else {
    // Compatibility fallback for an older backend that does not expose the
    // canonical controller decision attributes yet.
    mapping = !Number.isFinite(pBatt)
      ? t.waiting
      : pBatt < -FLOW_THRESHOLD_W
        ? t.modeCharge
        : pBatt > FLOW_THRESHOLD_W
          ? t.modeDischarge
          : t.modeHold;
  }
  patchMetric(card, ["Mapping", "Toewijzing", "Aansturing"], mapping);

  for (const input of card.querySelectorAll("input[data-soc-slider]")) {
    const kind = input.dataset.socSlider;
    const value = socLimitValue(panel, kind);
    if (!Number.isFinite(value)) continue;
    const draft = finiteValue(input.dataset.epSocDraft);
    const acknowledged = Number.isFinite(draft) && value === draft;
    if (acknowledged) delete input.dataset.epSocDraft;
    const displayValue = Number.isFinite(draft) && !acknowledged
      ? draft
      : root.activeElement === input
        ? finiteValue(input.value) ?? value
        : value;
    input.value = String(displayValue);
    const label = card.querySelector(`[data-soc-value="${kind}"]`);
    if (label) label.textContent = `${Math.round(displayValue)}%`;
  }
}

function patchStrategy(panel, root) {
  const strategy = root.querySelector(".ep-v038-strategy");
  if (!strategy) return;
  for (const input of strategy.querySelectorAll("input[data-ep-v038-soc]")) {
    const kind = input.dataset.epV038Soc;
    const value = socLimitValue(panel, kind);
    if (!Number.isFinite(value)) continue;
    const draft = finiteValue(input.dataset.epSocDraft);
    const acknowledged = Number.isFinite(draft) && value === draft;
    if (acknowledged) delete input.dataset.epSocDraft;
    const displayValue = Number.isFinite(draft) && !acknowledged
      ? draft
      : root.activeElement === input
        ? finiteValue(input.value) ?? value
        : value;
    input.value = String(displayValue);
    const label = strategy.querySelector(`[data-ep-v038-soc-value="${kind}"]`);
    if (label) label.textContent = `${Math.round(displayValue)}%`;
  }
}

function patchAccountingDay(day, label, imported, exported) {
  if (!day) return;
  const strong = day.querySelector("strong");
  if (strong) strong.textContent = label;
  let valueNode = [...day.childNodes]
    .reverse()
    .find((node) => node.nodeType === Node.TEXT_NODE);
  if (!valueNode) {
    day.append(document.createElement("br"));
    valueNode = document.createTextNode("");
    day.append(valueNode);
  }
  valueNode.textContent = `↓ ${formatEnergy(imported)} · ↑ ${formatEnergy(exported)}`;
}

function patchGridAccounting(panel, gridCard) {
  const imported = panel._stateByKey?.("grid_energy_imported_today");
  const exported = panel._stateByKey?.("grid_energy_exported_today");
  const days = gridCard?.querySelectorAll(".ep-v013-grid-day") || [];
  if (!imported || !exported || days.length < 2) return;
  const t = copy(panel);
  patchAccountingDay(days[0], t.today, imported.state, exported.state);
  patchAccountingDay(
    days[1],
    t.yesterday,
    imported.attributes?.last_period,
    exported.attributes?.last_period
  );
}

function optimizeAttributes(panel) {
  const entityId = panel._entityId?.("optimize_now");
  return (entityId ? panel._state?.(entityId)?.attributes : null) || {};
}

function diagnosticConfigAttributes(panel) {
  return panel._stateByKey?.("emhass_cost_function")?.attributes || {};
}

function validatedPercent(percentValue, rawValue) {
  const percent = finiteValue(percentValue);
  if (percent !== null) return formatPercent(percent);
  const raw = finiteValue(rawValue);
  return raw === null ? "—" : `invalid raw ${raw}`;
}

function diagnosticValue(panel, label, attrs, configAttrs) {
  const key = normalize(label);
  const power = (value) => panel._formatPower(finiteValue(value));
  const text = (value) => value === null || value === undefined || value === "" ? "—" : String(value);

  if (key.includes("current battery soc")) return formatPercent(attrs.battery_soc);
  if (key.includes("last energypilot optimization soc init") || key.includes("last optimization soc init")) {
    const value = finiteValue(attrs.soc_init);
    return formatPercent(value === null ? null : value * 100);
  }
  if (key.includes("configured energypilot final soc target")) {
    const value = finiteValue(attrs.configured_runtime_soc_final);
    return formatPercent(value === null ? null : value * 100);
  }
  if (key.includes("last successful energypilot runtime final soc") || key.includes("runtime final soc target")) {
    const value = finiteValue(attrs.runtime_soc_final);
    return formatPercent(value === null ? null : value * 100);
  }
  if (key === "emhass minimum soc") {
    return formatPercent(
      finite(panel, "emhass_minimum_soc") ?? configAttrs.emhass_minimum_soc_pct
    );
  }
  if (key.includes("emhass config target soc")) {
    return validatedPercent(
      configAttrs.emhass_config_target_soc_pct,
      configAttrs.emhass_config_target_soc_raw
    );
  }
  if (key.includes("emhass deficit threshold")) {
    return validatedPercent(
      configAttrs.emhass_soc_deficit_threshold_pct,
      configAttrs.emhass_soc_deficit_threshold_raw
    );
  }
  if (key.includes("emhass deficit cost")) {
    return `${formatDecimal(configAttrs.emhass_soc_deficit_cost)} currency/kWh/h`;
  }
  if (key.includes("goodwe on-grid minimum soc")) {
    return formatPercent(attrs.battery_discharge_depth_on_grid_45356);
  }
  if (key.includes("ems mode")) {
    return attrs.ems_mode === null || attrs.ems_mode === undefined
      ? "—"
      : `${attrs.ems_mode} · ${attrs.ems_mode_name || "Unknown"}`;
  }
  if (key.includes("last ems setpoint update") || key.includes("laatste ems-setpointupdate")) {
    return formatTimestamp(panel, attrs.last_ems_setpoint_updated_at);
  }
  if (key.includes("ems setpoint")) return power(attrs.ems_setpoint);
  if (key.includes("app / work")) return text(attrs.app_work_mode_47000);
  if (key.includes("work mode")) return text(attrs.work_mode_35187);
  if (key.includes("operation mode")) return text(attrs.operation_mode_35188);
  if (key.includes("grid mode")) return text(attrs.grid_mode_35136);
  if (key.includes("house load") || key.includes("goodwe load")) return power(attrs.house_load_register_35172);
  if (key.includes("load phase sum")) return power(attrs.house_load_phase_sum);
  if (key.includes("power-balance") || key.includes("system power balance")) {
    return power(attrs.system_balance_power ?? attrs.house_load_power_balance);
  }
  if (key.includes("meter fast total") || key.includes("grid meter fast total")) return power(attrs.meter_total_power_fast);
  if (key.includes("inverter active")) return power(attrs.ac_active_power);
  if (key.includes("inverter power") || key.includes("inverter total")) return power(attrs.total_inverter_power);
  if (key === "battery power") return power(attrs.battery_power);
  if (key === "battery soc") return formatPercent(attrs.battery_soc);
  if (key === "battery soh") return formatPercent(attrs.battery_soh, 0);
  if (key.includes("battery charged lifetime")) return formatEnergy(attrs.battery_charge_energy_total);
  if (key.includes("battery discharged lifetime")) return formatEnergy(attrs.battery_discharge_energy_total);
  if (key.includes("battery charged today")) return formatEnergy(attrs.battery_charge_energy_today);
  if (key.includes("battery discharged today")) return formatEnergy(attrs.battery_discharge_energy_today);
  if (key.includes("grid energy imported total")) return formatEnergy(attrs.meter_total_energy_import);
  if (key.includes("grid energy exported total")) return formatEnergy(attrs.meter_total_energy_export);
  if (key.includes("automatic control")) return attrs.controller_enabled ? "ON" : "OFF";
  if (key === "command" || key.includes("controller command")) return text(attrs.controller_command);
  if (key.includes("controller target")) return power(attrs.controller_target_power);
  if (key.includes("expected ems mode")) return text(attrs.controller_expected_mode);
  if (key.includes("maximum power")) return power(attrs.controller_max_power);
  if (key.includes("goodwe auto deadband")) return power(attrs.controller_goodwe_auto_deadband);
  if (key.includes("deadband")) return power(attrs.controller_deadband);
  if (key === "p_batt") return power(attrs.p_batt_value);
  if (key.includes("p_batt entity")) return text(attrs.p_batt_entity);
  if (key === "p_grid") return power(attrs.p_grid_value);
  if (key.includes("p_grid entity")) return text(attrs.p_grid_entity);
  if (key.includes("optim status entity") || key.includes("optimization status entity")) return text(attrs.optim_status_entity);
  if (key.includes("optim status") || key === "optimization status") return text(attrs.optim_status_value);
  if (key === "soc init") {
    const value = finiteValue(attrs.soc_init);
    return formatPercent(value === null ? null : value * 100);
  }
  if (key.includes("orchestrator")) return text(attrs.orchestrator_status);
  if (key.includes("last trigger") || key.includes("last reason")) return text(attrs.last_reason);
  if (key.includes("telemetry refresh")) return text(attrs.telemetry_refresh_seconds);
  if (key.includes("optimization interval")) return text(attrs.optimization_interval_minutes);
  if (key.includes("emhass health")) return text(attrs.emhass_health);
  if (key.includes("emhass version")) return text(attrs.emhass_version);
  if (key.includes("price source")) return text(attrs.price_runtime_source);
  if (key.includes("price entity")) return text(attrs.price_entity);
  if (key.includes("price area")) return text(attrs.price_area);
  if (key.includes("price points")) return text(attrs.price_points);
  if (key.includes("load forecast source")) return text(attrs.load_forecast_source);
  if (key.includes("load forecast points")) return text(attrs.load_forecast_points);
  if (key.includes("optimize http")) return text(attrs.optimize_http_status);
  if (key.includes("publish http")) return text(attrs.publish_http_status);
  if (key.includes("last error")) return text(attrs.last_error);
  return null;
}

function patchDiagnostics(panel, root) {
  const card = root.querySelector(".panel-card.diagnostics");
  if (!card) return;
  const attrs = optimizeAttributes(panel);
  const configAttrs = diagnosticConfigAttributes(panel);
  for (const row of card.querySelectorAll(".ep-v011-diag-row")) {
    const label = row.querySelector("span")?.textContent || "";
    const value = diagnosticValue(panel, label, attrs, configAttrs);
    const valueNode = row.querySelector("strong");
    if (value !== null && valueNode && valueNode.textContent !== value) {
      valueNode.textContent = value;
    }
  }
}

function buildDiagnosticSnapshot(root) {
  const lines = ["GW EnergyPilot diagnostics"];
  for (const row of root.querySelectorAll(".panel-card.diagnostics .ep-v011-diag-row")) {
    const label = row.querySelector("span")?.textContent?.trim();
    const value = row.querySelector("strong")?.textContent?.trim();
    if (label) lines.push(`${label}: ${value || "—"}`);
  }
  return lines.join("\n");
}

function installFreshDiagnosticsCopy(panel, root) {
  const previous = root.querySelector(".panel-card.diagnostics .ep-v011-copy");
  if (!previous || previous.dataset.epV041Fresh === "1") return;
  const copyButton = previous.cloneNode(true);
  copyButton.dataset.epV041Fresh = "1";
  previous.replaceWith(copyButton);
  copyButton.addEventListener("click", async () => {
    patchDiagnostics(panel, root);
    const text = buildDiagnosticSnapshot(root);
    try {
      await navigator.clipboard.writeText(text);
      const original = copyButton.textContent;
      copyButton.textContent = language(panel) === "nl" ? "Gekopieerd" : "Copied";
      globalThis.setTimeout(() => { copyButton.textContent = original; }, 1200);
    } catch (_err) {
      window.prompt("Copy GW EnergyPilot diagnostics", text);
    }
  });
}

function patchMotionMenu(panel, root) {
  const input = root.querySelector('[data-ep-setting="animations"]');
  if (!input) return;
  input.checked = false;
  input.disabled = true;
  input.setAttribute("aria-disabled", "true");
  const row = input.closest(".ep-menu-row");
  row?.classList.add("ep-v041-motion-disabled");
  const detail = row?.querySelector("small");
  if (detail) detail.textContent = copy(panel).motionDisabled;
}

function patchLiveDom(panel) {
  const root = panel.shadowRoot;
  const main = root?.querySelector("main");
  if (!main) return;
  main.dataset.epV041StableDom = "1";
  const pvSnapshot = pvGenerationSnapshot(panel);
  const pv = pvSnapshot.power;
  const load = finite(panel, "total_load_power");
  const grid = finite(panel, "meter_total_power_fast");
  const battery = finite(panel, "battery_power");
  const soc = finite(panel, "battery_soc");
  const soh = finite(panel, "battery_soh");
  const inverter = finite(panel, "total_inverter_power");
  const acActive = finite(panel, "ac_active_power");
  const automaticOn = panel._stateByKey?.("automatic_control")?.state === "on";
  const t = copy(panel);

  const headerStatus = root.querySelector("header .status");
  setStatus(headerStatus, automaticOn, automaticOn ? t.autoActive : t.goodweAuto);
  patchConnectivityStatus(panel, root);

  const solar = root.querySelector(".energy-card.solar");
  setText(solar, ".hero-value", panel._formatPower(pv));
  if (pvSnapshot.configuredExternal > 0 || !pvSnapshot.internalEnabled) {
    patchPvSourceMetrics(panel, solar, pvSnapshot);
  } else {
    patchMetric(solar, ["PV1"], panel._formatPower(finite(panel, "pv1_power")));
    patchMetric(solar, ["PV2"], panel._formatPower(finite(panel, "pv2_power")));
    patchMetric(solar, ["PV3"], panel._formatPower(finite(panel, "pv3_power")));
    patchMetric(solar, ["PV4"], panel._formatPower(finite(panel, "pv4_power")));
  }

  const home = root.querySelector(".energy-card.home");
  setText(home, ".hero-value", panel._formatPower(load));
  patchBalanceRows(home, panel, load, inverter, acActive);

  const gridCard = root.querySelector(".energy-card.grid");
  setText(gridCard, ".hero-value", panel._formatPower(Number.isFinite(grid) ? Math.abs(grid) : null));
  patchPill(gridCard, gridPresentation(panel, grid));
  for (const [phase, key, voltage, current] of [
    ["L1", "meter_l1_active_power", "meter_l1_voltage", "meter_l1_current"],
    ["L2", "meter_l2_active_power", "meter_l2_voltage", "meter_l2_current"],
    ["L3", "meter_l3_active_power", "meter_l3_voltage", "meter_l3_current"],
  ]) {
    patchMetric(
      gridCard,
      [phase],
      panel._formatPower(finite(panel, key)),
      `${panel._formatState(panel._stateByKey?.(voltage))} · ${panel._formatState(panel._stateByKey?.(current))}`
    );
  }
  patchGridAccounting(panel, gridCard);

  const batteryCard = root.querySelector(".energy-card.battery");
  patchPill(batteryCard, batteryPresentation(panel, battery));
  setText(batteryCard, ".soc", Number.isFinite(soc) ? `${Math.round(soc)}%` : "—");
  setText(batteryCard, ".battery-power", panel._formatPower(battery));
  const fill = batteryCard?.querySelector(".soc-fill");
  if (fill) fill.style.width = `${Number.isFinite(soc) ? Math.min(100, Math.max(0, soc)) : 0}%`;
  patchMetric(batteryCard, ["SOH"], Number.isFinite(soh) ? `${Math.round(soh)}%` : "—");
  patchMetric(batteryCard, ["Voltage", "Spanning"], panel._formatState(panel._stateByKey?.("battery_voltage")));
  patchMetric(batteryCard, ["Current", "Stroom"], panel._formatState(panel._stateByKey?.("battery_current")));
  patchMetric(batteryCard, ["Max cell temp", "Maximale celtemperatuur"], panel._formatState(panel._stateByKey?.("battery_max_cell_temperature")));

  patchBatteryQuickActions(panel, root, automaticOn);
  patchController(panel, root, automaticOn);
  patchEmhass(panel, root);
  patchStrategy(panel, root);
  patchFlow(panel, root, pv, load, grid, battery, soc);
  patchDiagnostics(panel, root);
  patchMotionMenu(panel, root);

  const thermal = root.querySelector(".panel-card.thermal");
  patchMetric(thermal, ["Inverter radiator", "Omvormerradiator"], panel._formatState(panel._stateByKey?.("inverter_radiator_temperature")));
  patchMetric(thermal, ["BMS package", "BMS-pakket"], panel._formatState(panel._stateByKey?.("bms_package_temperature")));
  patchMetric(thermal, ["Battery max cell", "Maximale batterijcel"], panel._formatState(panel._stateByKey?.("battery_max_cell_temperature")));
  patchMetric(thermal, ["BMS max charge", "BMS max laden"], panel._formatState(panel._stateByKey?.("bms_max_charge_current")));
  patchMetric(thermal, ["BMS max discharge", "BMS max ontladen"], panel._formatState(panel._stateByKey?.("bms_max_discharge_current")));
}

function ensureNoMotionStyle(root) {
  if (!root || root.querySelector(`#${MOTION_STYLE_ID}`)) return;
  const style = document.createElement("style");
  style.id = MOTION_STYLE_ID;
  style.textContent = NO_MOTION_CSS;
  root.appendChild(style);
}

function ensureGlobalNoMotionStyle() {
  if (!globalThis.document || document.getElementById(GLOBAL_MOTION_STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = GLOBAL_MOTION_STYLE_ID;
  style.textContent = GLOBAL_NO_MOTION_CSS;
  document.head.appendChild(style);
}

function contextSignature(hass) {
  const locale = hass?.locale || {};
  const user = hass?.user || {};
  const themes = hass?.themes || {};
  return JSON.stringify({
    language: locale.language || hass?.language || "en",
    numberFormat: locale.number_format || "",
    timeFormat: locale.time_format || "",
    userId: user.id || "",
    admin: Boolean(user.is_admin),
    darkMode: Boolean(themes.darkMode),
    theme: themes.theme || "",
  });
}

function structureSignature(panel) {
  const pBattState = externalState(
    panel,
    ["sensor.p_batt_forecast"],
    [".p_batt_forecast", "_p_batt_forecast"]
  );
  const pBatt = panel._numberState?.(pBattState, null);
  const pv4 = finite(panel, "pv4_power");
  const entityMap = Object.entries(panel._entityMap || {})
    .sort(([left], [right]) => left.localeCompare(right));
  const pvSnapshot = pvGenerationSnapshot(panel);
  const pvSourceTopology = pvSnapshot.sources.map((source) => ({
    sourceKey: source?.source_key || "",
    kind: source?.kind || "",
    name: source?.name || "",
    entityId: source?.entity_id || "",
  }));
  return JSON.stringify({
    registryLoaded: Boolean(panel._registryLoaded),
    entityMap,
    pBattState: Boolean(pBattState),
    pBattNumeric: Number.isFinite(pBatt),
    pv4Visible: Number.isFinite(pv4) && Math.abs(pv4) > 20,
    pvInternalEnabled: pvSnapshot.internalEnabled,
    pvConfiguredExternal: pvSnapshot.configuredExternal,
    pvSourceTopology,
  });
}

function planSignature(panel, hass = panel?._hass) {
  const optimizeId = panel?._entityId?.("optimize_now");
  const attrs = optimizeId ? hass?.states?.[optimizeId]?.attributes || {} : {};
  const entityId = typeof attrs.p_batt_entity === "string"
    ? attrs.p_batt_entity
    : "sensor.p_batt_forecast";
  const planState = hass?.states?.[entityId] || null;
  return JSON.stringify({
    revision: attrs.plan_revision ?? null,
    entityId,
    lastUpdated: planState?.last_updated || planState?.last_changed || "",
  });
}

function executionHistorySignature(panel, hass = panel?._hass) {
  const entityId = panel?._entityId?.("control_command");
  const state = entityId ? hass?.states?.[entityId] : null;
  return JSON.stringify({
    entityId: entityId || null,
    revision: state?.attributes?.execution_history_revision ?? null,
  });
}

function scheduleLivePatch(panel) {
  if (panel.__epV041LivePatchTimer) return;
  panel.__epV041LivePatchTimer = globalThis.setTimeout(() => {
    panel.__epV041LivePatchTimer = null;
    patchLiveDom(panel);
  }, LIVE_PATCH_DELAY_MS);
}

function schedulePlanRefresh(panel, backendForce = true) {
  panel.__epV041PlanPatchBackendForce = Boolean(
    panel.__epV041PlanPatchBackendForce || backendForce
  );
  if (panel.__epV041PlanPatchTimer) return;
  panel.__epV041PlanPatchTimer = globalThis.setTimeout(() => {
    panel.__epV041PlanPatchTimer = null;
    const forceBackend = Boolean(panel.__epV041PlanPatchBackendForce);
    panel.__epV041PlanPatchBackendForce = false;
    void loadChartData(panel, true, forceBackend).catch((err) => {
      console.error("GW EnergyPilot: v0.41 battery plan refresh failed", err);
    });
  }, PLAN_PATCH_DELAY_MS);
}

function plainJsonEqual(left, right) {
  if (Object.is(left, right)) return true;
  if (!left || !right || typeof left !== "object" || typeof right !== "object") {
    return false;
  }
  if (Array.isArray(left) || Array.isArray(right)) {
    return Array.isArray(left) && Array.isArray(right) &&
      left.length === right.length &&
      left.every((value, index) => plainJsonEqual(value, right[index]));
  }

  const leftPrototype = Object.getPrototypeOf(left);
  const rightPrototype = Object.getPrototypeOf(right);
  if (
    ![Object.prototype, null].includes(leftPrototype) ||
    ![Object.prototype, null].includes(rightPrototype)
  ) {
    return false;
  }
  const leftKeys = Object.keys(left);
  const rightKeys = Object.keys(right);
  return leftKeys.length === rightKeys.length && leftKeys.every(
    (key) => Object.prototype.hasOwnProperty.call(right, key) &&
      plainJsonEqual(left[key], right[key])
  );
}

function installStableHostProperty(
  PanelClass,
  propertyName,
  normalize,
  equal = Object.is
) {
  const descriptor = Object.getOwnPropertyDescriptor(PanelClass.prototype, propertyName);
  if (!descriptor?.set) return;

  Object.defineProperty(PanelClass.prototype, propertyName, {
    configurable: descriptor.configurable,
    enumerable: descriptor.enumerable,
    get() {
      return descriptor.get ? descriptor.get.call(this) : this[`_${propertyName}`];
    },
    set(value) {
      const next = normalize(value);
      const current = descriptor.get
        ? descriptor.get.call(this)
        : this[`_${propertyName}`];
      if (equal(current, next)) return;
      descriptor.set.call(this, next);
    },
  });
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (PanelClass && !PanelClass.prototype.__epV041Installed) {
  // Home Assistant assigns hass, narrow, route and panel during host updates.
  // The inherited narrow/panel setters queue a complete ShadowRoot render even
  // when their values are unchanged. Keep those assignments idempotent so a
  // pressed control remains connected until native click; real layout/config
  // changes still delegate to the inherited structural-render path.
  installStableHostProperty(PanelClass, "narrow", Boolean);
  installStableHostProperty(PanelClass, "panel", (value) => value, plainJsonEqual);

  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV041StructuralRender(...args) {
    // v0.41 keeps the interaction node alive for normal telemetry. The legacy
    // v0.38 press guard and delayed mobile scroll restoration are therefore
    // explicitly bypassed only in this release path.
    this.__epV041StableRuntime = true;
    this.__epV038InteractionGuardInstalled = true;
    const result = previousRender.apply(this, args);
    ensureNoMotionStyle(this.shadowRoot);
    ensureGlobalNoMotionStyle();
    installEvProtectionBanner(this.shadowRoot);
    this.__epV041RefreshLiveDom = () => {
      ensureNoMotionStyle(this.shadowRoot);
      patchLiveDom(this);
    };
    this.__epV041RefreshBatteryPlan = () => {
      refreshBatteryPlanCard(this);
      ensureNoMotionStyle(this.shadowRoot);
      patchLiveDom(this);
    };
    const root = this.shadowRoot;
    ensureConnectivityStatus(this, root);
    const versionBadge = root?.querySelector(".version");
    if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
    const footerItems = root?.querySelectorAll("footer span") || [];
    if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
    this.__epV041ContextSignature = contextSignature(this._hass);
    this.__epV041StructureSignature = structureSignature(this);
    this.__epV041PlanSignature = planSignature(this);
    this.__epV041ExecutionHistorySignature = executionHistorySignature(this);
    installFreshDiagnosticsCopy(this, root);
    patchLiveDom(this);
    return result;
  };

  const descriptor = Object.getOwnPropertyDescriptor(PanelClass.prototype, "hass");
  if (descriptor?.set) {
    Object.defineProperty(PanelClass.prototype, "hass", {
      configurable: descriptor.configurable,
      enumerable: descriptor.enumerable,
      get() {
        return descriptor.get ? descriptor.get.call(this) : this._hass;
      },
      set(value) {
        const previous = this._hass;
        if (!previous || !this._registryLoaded) {
          descriptor.set.call(this, value);
          return;
        }

        this._hass = value;
        if (this.__epV038HassRenderTimer) {
          globalThis.clearTimeout(this.__epV038HassRenderTimer);
          this.__epV038HassRenderTimer = null;
        }

        const nextPlanSignature = planSignature(this, value);
        const planChanged = nextPlanSignature !== this.__epV041PlanSignature;
        if (planChanged) {
          this.__epV041PlanSignature = nextPlanSignature;
          schedulePlanRefresh(this);
        }
        const nextExecutionHistorySignature = executionHistorySignature(this, value);
        if (nextExecutionHistorySignature !== this.__epV041ExecutionHistorySignature) {
          this.__epV041ExecutionHistorySignature = nextExecutionHistorySignature;
          if (!planChanged) schedulePlanRefresh(this, false);
        }

        if (this.__epV016SettingsOpen) {
          scheduleLivePatch(this);
          return;
        }

        const context = contextSignature(value);
        const structure = structureSignature(this);
        if (
          context !== this.__epV041ContextSignature ||
          structure !== this.__epV041StructureSignature
        ) {
          this._queueRender();
          return;
        }
        scheduleLivePatch(this);
      },
    });
  }

  PanelClass.prototype.__epV041Installed = true;
}
