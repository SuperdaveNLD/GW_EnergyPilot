import {
  LitElement,
  html,
  nothing,
} from "./vendor/lit-3.3.3.js?v=1.3.0-beta.3";
import {
  CUSTOM_MODE,
  canonicalProfiles,
  normalizeLanguage,
} from "./gw-energy-pilot-v038-model.js?v=1.3.0-beta.3";
import { localizedEmsMode } from "./gw-energy-pilot-v038-i18n.js?v=1.3.0-beta.3";

const ACK_TIMEOUT_MS = 15_000;
const TRACE_LIMIT = 6_000;
const RUNNING_STATES = new Set([
  "preparing",
  "reading_history",
  "getting_prices",
  "optimizing",
  "publishing",
  "waiting_for_output",
]);

const QUICK_ACTIONS = Object.freeze([
  Object.freeze({
    key: "max_export",
    command: "manual_max_export",
    en: "Max export",
    nl: "Max export",
  }),
  Object.freeze({
    key: "battery_pause",
    command: "manual_battery_hold",
    en: "Pause",
    nl: "Pauze",
  }),
  Object.freeze({
    key: "max_charge",
    command: "manual_max_charge",
    en: "Max charge",
    nl: "Max laden",
  }),
  Object.freeze({
    key: "resume_auto",
    command: null,
    en: "AUTO",
    nl: "AUTO",
  }),
]);

const COST_FUNCTIONS = Object.freeze([
  Object.freeze({
    raw: "profit",
    option: "Profit",
    label: "Profit",
    legacyKey: "emhass_costfun_profit",
  }),
  Object.freeze({
    raw: "cost",
    option: "Cost",
    label: "Cost",
    legacyKey: "emhass_costfun_cost",
  }),
  Object.freeze({
    raw: "self-consumption",
    option: "Self-consumption",
    label: "Self-consumption",
    legacyKey: "emhass_costfun_self_consumption",
  }),
]);

const MANUAL_MODES = Object.freeze([
  [1, "AUTO", "1: GoodWe Auto / AI", true],
  [2, "PV+", "2: PV-priority charging", false],
  [3, "PV-", "3: PV + battery supply", false],
  [4, "IMP", "4: Inverter import / AC charging", false],
  [5, "EXP", "5: Inverter export power", false],
  [6, "RSV", "6: Reserve / Conserve", true],
  [7, "OFF", "7: Off-grid", true],
  [8, "HOLD", "8: Battery Hold", true],
  [9, "BUY", "9: Grid import target", false],
  [10, "SELL", "10: Grid export target", false],
  [11, "CHG", "11: Battery charge power", false],
  [12, "DIS", "12: Battery discharge power", false],
].map(([mode, tag, option, zeroPower]) =>
  Object.freeze({ mode, tag, option, zeroPower })
));

const COPY = Object.freeze({
  en: Object.freeze({
    surface: "EnergyPilot control surface",
    surfaceDetail: "Permanent controls · confirmed Home Assistant state",
    battery: "Battery actions",
    batteryPending: "Request sent · waiting for confirmed ownership…",
    automatic: "Automatic Control",
    automaticOn: "AUTO ACTIVE",
    automaticOff: "AUTO INACTIVE",
    unavailable: "Unavailable",
    confirmAutomatic:
      "Enable GW EnergyPilot automatic control?\n\nOnly continue when EMHASS is fully configured, optimization is successful, publish-data is working and the selected plan sensors are valid.",
    emhass: "EMHASS optimization strategy",
    emhassCompact: "EMHASS",
    batteryStrategy: "Battery strategy",
    batteryCompact: "BATTERY",
    profilesLoading: "Loading battery profiles…",
    custom: "Custom battery values",
    saveCustom: "Save and optimize",
    minimumSoc: "Minimum SOC",
    maximumSoc: "Maximum SOC",
    optimize: "Optimize now",
    optimizing: "Optimizing…",
    active: "Active",
    live: "live",
    lowSocCost: "Low-SOC cost",
    highSocCost: "High-SOC cost",
    powerStress: "Power stress",
    chargeCost: "Charge cost",
    dischargeCost: "Discharge cost",
    managedTitle: "Managed profile limits",
    hardRange: "Hard SOC range",
    comfortRange: "Comfort zone",
    lowCost: "Low-SOC cost",
    highCost: "High-SOC cost",
    stressCost: "Power stress",
    antiChurn: "Charge/discharge anti-churn",
    manual: "Manual EMS controls",
    manualLocked: "Automatic Control owns the inverter. Manual controls are locked.",
    manualReady: "Manual ownership · live GoodWe read-back",
    manualPower: "Manual setpoint",
    confirmOffgrid:
      "Force GoodWe off-grid mode?\n\nMode 7 can materially change inverter operating topology. Continue only if this installation is prepared for off-grid operation.",
    pending: "Pending backend confirmation…",
    acknowledged: "Confirmed by backend.",
    noAcknowledgement: "No matching backend confirmation was received in time.",
    requestFailed: "Request failed",
  }),
  nl: Object.freeze({
    surface: "EnergyPilot-bediening",
    surfaceDetail: "Permanente controls · bevestigde Home Assistant-status",
    battery: "Batterijacties",
    batteryPending: "Opdracht verzonden · wachten op bevestigd eigenaarschap…",
    automatic: "Automatische bediening",
    automaticOn: "AUTO ACTIEF",
    automaticOff: "AUTO INACTIEF",
    unavailable: "Niet beschikbaar",
    confirmAutomatic:
      "GW EnergyPilot automatisch inschakelen?\n\nGa alleen verder als EMHASS volledig is geconfigureerd, de optimalisatie slaagt, publish-data werkt en de gekozen plansensoren geldig zijn.",
    emhass: "EMHASS-optimalisatiestrategie",
    emhassCompact: "EMHASS",
    batteryStrategy: "Batterijstrategie",
    batteryCompact: "BATTERIJ",
    profilesLoading: "Batterijprofielen laden…",
    custom: "Aangepaste batterijwaarden",
    saveCustom: "Opslaan en optimaliseren",
    minimumSoc: "Minimum-SOC",
    maximumSoc: "Maximum-SOC",
    optimize: "Nu optimaliseren",
    optimizing: "Optimaliseren…",
    active: "Actief",
    live: "actueel",
    lowSocCost: "Lage-SOC-kosten",
    highSocCost: "Hoge-SOC-kosten",
    powerStress: "Vermogensbelasting",
    chargeCost: "Laadkosten",
    dischargeCost: "Ontlaadkosten",
    managedTitle: "Vaste profielgrenzen",
    hardRange: "Harde SOC-range",
    comfortRange: "Comfortzone",
    lowCost: "Kosten lage SOC",
    highCost: "Kosten hoge SOC",
    stressCost: "Vermogensstress",
    antiChurn: "Anti-pendel laden/ontladen",
    manual: "Handmatige EMS-bediening",
    manualLocked: "Automatische bediening beheert de omvormer. Handmatige controls zijn vergrendeld.",
    manualReady: "Handmatig eigenaarschap · actuele GoodWe-teruglezing",
    manualPower: "Handmatig setpoint",
    confirmOffgrid:
      "GoodWe off-grid forceren?\n\nModus 7 kan de bedrijfstopologie ingrijpend wijzigen. Ga alleen verder als de installatie hiervoor is voorbereid.",
    pending: "Wachten op backendbevestiging…",
    acknowledged: "Door de backend bevestigd.",
    noAcknowledgement: "Er kwam niet tijdig een overeenkomende backendbevestiging.",
    requestFailed: "Opdracht mislukt",
  }),
});

const HYBRID_NOTE = Object.freeze({
  en: Object.freeze({
    title: "Automatic control strategy:",
    label: "Hybrid control",
    description: "Uses the Battery Hold deadband on P_batt for mode 8 first. Outside it, P_grid uses mode 1 inside the separate GoodWe Auto deadband and modes 9/10 outside it, with the full grid target as setpoint.",
    safety: "EV anti-discharge protection remains active as a safety override.",
  }),
  nl: Object.freeze({
    title: "Automatische regelstrategie:",
    label: "Hybride regeling",
    description: "Gebruikt eerst de Battery Hold-deadband op P_batt voor modus 8. Daarbuiten gebruikt P_grid modus 1 binnen de aparte GoodWe Auto-deadband en modi 9/10 erbuiten, met het volledige netdoel als setpoint.",
    safety: "EV-ontlaadbeveiliging blijft actief als veiligheidsoverride.",
  }),
});

const CONTROL_SURFACE_CSS = `
  ep-control-surface,
  ep-battery-actions,
  ep-automatic-control,
  ep-emhass-strategy,
  ep-battery-strategy,
  ep-optimize-action,
  ep-manual-ems-controls { display:block; min-width:0; }
  ep-control-surface { align-self:start; position:relative; z-index:80; }
  .ep-control-surface {
    margin:0; padding:14px; border-radius:20px;
    border:1px solid rgba(74,190,229,.22);
    background:linear-gradient(145deg,rgba(5,30,54,.96),rgba(4,18,35,.98));
    color:#e6f7ff; touch-action:pan-y; overflow:visible;
  }
  .ep-control-surface *, .ep-control-surface *::before, .ep-control-surface *::after {
    box-sizing:border-box;
  }
  .ep-control-surface [hidden] { display:none!important; }
  .ep-control-surface *::before, .ep-control-surface *::after { pointer-events: none; }
  .ep-control-surface-head { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:10px; }
  .ep-control-surface-kicker { color:#64e5f5; font-size:10px; font-weight:900; letter-spacing:.12em; text-transform:uppercase; }
  .ep-control-surface-detail {
    position:absolute; width:1px; height:1px; padding:0; margin:-1px;
    overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0;
  }
  .ep-control-surface-grid { display:grid; grid-template-columns:1fr; gap:9px; touch-action:pan-y; }
  .ep-control-selectors { display:grid; grid-template-columns:1fr; gap:8px; }
  .ep-control-group { height:auto; min-width:0; padding:0; border:0; border-radius:0; background:transparent; }
  .ep-control-group.wide { grid-column:auto; }
  .ep-control-surface .ep-v016-costfun,
  .ep-control-surface .ep-v038-strategy {
    margin:0; padding:0; border:0; background:transparent;
  }
  .ep-control-title { margin:0 0 8px; color:#dff6ff; font-size:12px; font-weight:850; }
  .ep-control-status { margin-top:7px; color:#829db0; font-size:10px; line-height:1.4; }
  .ep-control-status:empty { display:none; }
  .ep-control-status.error { color:#ff9e96; }
  .ep-control-status.ok { color:#79e4b8; }
  .ep-control-actions { display:grid; gap:8px; }
  .ep-control-surface .ep-battery-actions {
    grid-template-columns:repeat(2,minmax(0,1fr)); margin:0;
  }
  .ep-v016-costfun-actions, .ep-v038-profile-grid { grid-template-columns:1fr; }
  .ep-v021-mode-grid { grid-template-columns:repeat(6,minmax(44px,1fr)); }
  .ep-control-surface button {
    appearance:none; min-width:44px; min-height:44px; padding:9px 10px;
    border:1px solid rgba(74,187,226,.24); border-radius:11px;
    background:rgba(8,43,69,.78); color:#c7e4ef; font:800 11px/1.2 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",sans-serif;
    cursor:pointer; touch-action:manipulation; -webkit-tap-highlight-color:rgba(59,226,205,.18);
  }
  .ep-control-surface button:active:not(:disabled) { background:rgba(19,83,103,.92); border-color:rgba(59,226,205,.70); }
  .ep-control-surface button:focus-visible { outline:3px solid #71e8ff; outline-offset:3px; }
  .ep-control-surface button:disabled { opacity:.44; cursor:not-allowed; }
  .ep-control-surface button[aria-pressed="true"] { border-color:#34e4b0; background:rgba(12,94,86,.74); color:#effff9; box-shadow:inset 0 0 0 1px rgba(52,228,176,.24); }
  .ep-control-surface .ep-battery-action:not([aria-pressed="true"]) {
    border-color:rgba(74,187,226,.24)!important;
    background:rgba(8,43,69,.78)!important;
    background-image:none!important;
    color:#c7e4ef!important;
    box-shadow:none!important;
  }
  .ep-control-surface button[data-pending="true"] { border-color:#6adff4; color:#dcfbff; }
  .ep-automatic-control-button { width:100%; display:flex; align-items:center; justify-content:center; gap:9px; }
  .ep-automatic-indicator { width:10px; height:10px; border-radius:50%; background:#637c8f; pointer-events:none; }
  button[aria-pressed="true"] .ep-automatic-indicator { background:#34e4b0; }
  .ep-automatic-compact { position:relative; }
  .ep-automatic-compact .ep-control-title,
  .ep-battery-quick .ep-control-title,
  .ep-optimize-compact .ep-control-title {
    position:absolute; width:1px; height:1px; padding:0; margin:-1px;
    overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; border:0;
  }
  .ep-automatic-compact .ep-control-status { max-width:150px; text-align:right; }
  .ep-automatic-compact .ep-automatic-control-button {
    width:auto; min-width:128px; border-radius:999px; padding-inline:13px;
  }
  .ep-compact-selector { position:relative; min-width:0; }
  .ep-compact-selector > summary,
  .ep-manual-disclosure > summary {
    min-height:44px; display:flex; align-items:center; justify-content:space-between; gap:9px;
    padding:9px 11px; border:1px solid rgba(74,187,226,.24); border-radius:11px;
    background:rgba(8,43,69,.78); color:#c7e4ef; cursor:pointer;
    font:800 11px/1.2 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI",sans-serif;
    list-style:none; touch-action:manipulation; -webkit-tap-highlight-color:rgba(59,226,205,.18);
  }
  .ep-compact-selector > summary::-webkit-details-marker,
  .ep-manual-disclosure > summary::-webkit-details-marker { display:none; }
  .ep-compact-selector > summary:focus-visible,
  .ep-manual-disclosure > summary:focus-visible { outline:3px solid #71e8ff; outline-offset:3px; }
  .ep-compact-selector-label { min-width:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .ep-compact-selector-label strong { color:#eafaff; letter-spacing:.06em; }
  .ep-compact-chevron { flex:0 0 auto; color:#7894a8; font-size:14px; }
  .ep-compact-selector-menu {
    position:absolute; z-index:30; top:calc(100% + 5px); left:0; right:0;
    padding:8px; border:1px solid rgba(74,190,229,.28); border-radius:12px;
    background:#061c31; box-shadow:0 16px 38px rgba(0,0,0,.42);
  }
  .ep-compact-selector:not([open]) > .ep-compact-selector-menu,
  .ep-manual-disclosure:not([open]) > .ep-manual-body { display:none; }
  .ep-v038-profile { position:relative; text-align:left; }
  .ep-v038-profile strong, .ep-v038-profile small { display:block; pointer-events:none; }
  .ep-v038-profile small { margin-top:4px; color:#7894a8; font-size:9px; font-weight:600; }
  .ep-v038-custom { margin-top:10px; padding-top:10px; border-top:1px solid rgba(78,174,214,.14); }
  .ep-v038-custom[hidden] { display:none; }
  .ep-v038-managed { margin-top:10px; padding-top:10px; border-top:1px solid rgba(78,174,214,.14); }
  .ep-v038-managed-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:7px 12px; margin-top:7px; }
  .ep-v038-managed-grid span { color:#9db8c8; font-size:10px; }
  .ep-v038-managed-grid strong { color:#eafaff; }
  .ep-v038-custom-grid, .ep-v038-custom-values { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:9px; }
  .ep-v038-custom label, .ep-v021-power-label { display:grid; gap:5px; color:#9db8c8; font-size:10px; }
  .ep-v038-custom input[type="number"] { min-height:44px; width:100%; padding:8px 10px; border:1px solid rgba(80,177,218,.22); border-radius:10px; background:#061c31; color:#eafaff; }
  .ep-v038-custom input[type="range"], .ep-v021-power-slider { width:100%; min-height:44px; touch-action:pan-y; accent-color:#34e4b0; }
  .ep-v038-custom-actions { margin-top:9px; display:flex; justify-content:flex-end; }
  .ep-v021-power-row { margin-top:10px; display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:end; gap:10px; }
  .ep-v021-mode-button { padding:7px 4px!important; }
  .ep-v021-mode-button strong, .ep-v021-mode-button small { display:block; pointer-events:none; }
  .ep-v021-mode-button small { margin-top:3px; color:#7894a8; font-size:8px; }
  .ep-manual-readback { color:#7894a8; font-size:10px; white-space:normal; overflow-wrap:anywhere; text-align:right; }
  .ep-optimize-now { width:100%; border-color:rgba(52,228,176,.42)!important; }
  .ep-manual-disclosure { min-width:0; }
  .ep-manual-summary-copy { min-width:0; }
  .ep-manual-summary-copy strong,
  .ep-manual-summary-copy small { display:block; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .ep-manual-summary-copy small { margin-top:3px; color:#7894a8; font-size:9px; font-weight:600; }
  .ep-manual-disclosure[data-locked="true"] > summary { cursor:default; opacity:.82; }
  .ep-manual-disclosure[data-locked="true"] > .ep-manual-body { display:none; }
  .ep-manual-body { padding-top:9px; }
  .ep-control-surface .ep-v022-strategy-note {
    position:absolute!important; width:1px!important; height:1px!important; padding:0!important;
    margin:-1px!important; overflow:hidden!important; clip:rect(0,0,0,0)!important;
    white-space:nowrap!important; border:0!important;
  }
  @media(max-width:820px) {
    .ep-v021-mode-grid { grid-template-columns:repeat(4,minmax(44px,1fr)); }
  }
  @media(max-width:520px) {
    .ep-control-surface { padding:12px; }
    .ep-control-surface-head { align-items:flex-start; }
    .ep-automatic-compact .ep-automatic-control-button { min-width:112px; padding-inline:10px; }
    .ep-compact-selector-menu { position:static; margin-top:6px; }
    .ep-v038-custom-grid, .ep-v038-custom-values { grid-template-columns:1fr; }
  }
`;

function textFor(model) {
  return COPY[model?.language] || COPY.en;
}

function finite(value, fallback = null) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function safeState(panel, key) {
  const entityId = panel?._entityId?.(key) || null;
  const state = entityId ? panel?._state?.(entityId) || null : null;
  return Object.freeze({
    entityId,
    state,
    value: state && !["unknown", "unavailable"].includes(state.state)
      ? state.state
      : null,
    available: Boolean(entityId && state && state.state !== "unavailable"),
  });
}

function rawCostFunction(ref) {
  if (!ref?.state || ["unknown", "unavailable"].includes(ref.state.state)) return null;
  const attribute = ref.state.attributes?.emhass_costfun;
  if (attribute && COST_FUNCTIONS.some((item) => item.raw === String(attribute))) {
    return String(attribute);
  }
  return COST_FUNCTIONS.find((item) => item.option === ref.state.state)?.raw || null;
}

function freezeModel(value) {
  if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
  for (const item of Object.values(value)) freezeModel(item);
  return Object.freeze(value);
}

function profileValues(data) {
  const values = data?.current_emhass_values || {};
  const first = (value, fallback = 0) => {
    const raw = Array.isArray(value) ? value[0] : value;
    return finite(raw, fallback);
  };
  return {
    battery_soc_deficit_cost: first(values.battery_soc_deficit_cost),
    battery_soc_surplus_cost: first(values.battery_soc_surplus_cost),
    battery_stress_cost: first(values.battery_stress_cost),
    weight_battery_charge: first(values.weight_battery_charge),
    weight_battery_discharge: first(values.weight_battery_discharge),
  };
}

function profilePercent(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${number}%` : "—";
}

export function buildControlSurfaceModel(panel, gateway = controlGateway(panel)) {
  const language = normalizeLanguage(
    panel?._hass?.locale?.language || panel?._hass?.language || "en"
  );
  const automatic = safeState(panel, "automatic_control");
  const command = safeState(panel, "control_command");
  const costFunction = safeState(panel, "emhass_cost_function");
  const optimize = safeState(panel, "optimize_now");
  const manualMode = safeState(panel, "manual_mode");
  const emsMode = safeState(panel, "ems_mode");
  const manualPower = safeState(panel, "manual_power");
  const emsSetpoint = safeState(panel, "ems_setpoint");
  const minimumSoc = safeState(panel, "emhass_minimum_soc");
  const maximumSoc = safeState(panel, "emhass_maximum_soc");
  const controlStrategy = safeState(panel, "control_strategy");
  const automaticState = ["on", "off"].includes(automatic.value)
    ? automatic.value
    : null;
  const profileData = gateway.profileData;
  const optimizeStatus = String(optimize.state?.attributes?.orchestrator_status || "");
  const manualMax = Math.max(0, finite(manualPower.state?.attributes?.max, 15_000));
  const manualStep = Math.max(1, finite(manualPower.state?.attributes?.step, 100));

  return freezeModel({
    language,
    narrow: Boolean(panel?.narrow),
    strategy: {
      value: controlStrategy.value,
      note: HYBRID_NOTE[language] || HYBRID_NOTE.en,
    },
    battery: {
      language,
      automaticState,
      command: command.value,
      available: Object.fromEntries(
        QUICK_ACTIONS.map((definition) => [
          definition.key,
          safeState(panel, definition.key).available,
        ])
      ),
    },
    automatic: {
      language,
      state: automaticState,
      available: automatic.available,
    },
    emhass: {
      language,
      currentRaw: rawCostFunction(costFunction),
      available: Object.fromEntries(
        COST_FUNCTIONS.map((definition) => [
          definition.raw,
          Boolean(
            costFunction.available || safeState(panel, definition.legacyKey).available
          ),
        ])
      ),
    },
    profiles: {
      language,
      data: profileData,
      loading: gateway.profileLoading,
      error: gateway.profileError,
      revision: gateway.profileRevision,
      managed: Boolean(profileData?.managed),
      activeMode: profileData
        ? profileData.managed ? profileData.mode : CUSTOM_MODE
        : null,
      modes: canonicalProfiles(language, profileData?.modes || []),
      editable: profileData?.battery_count === 1,
      values: profileValues(profileData),
      minimumSoc: finite(minimumSoc.value, 0),
      maximumSoc: finite(maximumSoc.value, 100),
      minimumSocAvailable: minimumSoc.available,
      maximumSocAvailable: maximumSoc.available,
    },
    optimize: {
      language,
      available: optimize.available,
      running: RUNNING_STATES.has(optimizeStatus),
      status: optimizeStatus,
      planRevision: finite(optimize.state?.attributes?.plan_revision, null),
    },
    manual: {
      language,
      automaticState,
      available: Boolean(manualMode.available && manualPower.available),
      mode: finite(emsMode.value, null),
      power: Math.min(manualMax, Math.max(0, finite(manualPower.value, 0))),
      max: manualMax,
      step: manualStep,
      actualSetpoint: finite(emsSetpoint.value, null),
    },
  });
}

class EpAcknowledgedControl extends LitElement {
  static properties = {
    model: { attribute: false },
    actions: { attribute: false },
    phase: { state: true },
    pendingKey: { state: true },
    feedback: { state: true },
    feedbackTone: { state: true },
  };

  constructor() {
    super();
    this.model = Object.freeze({});
    this.actions = Object.freeze({});
    this.phase = "idle";
    this.pendingKey = null;
    this.feedback = "";
    this.feedbackTone = "";
    this._request = null;
  }

  createRenderRoot() {
    return this;
  }

  willUpdate(changed) {
    if (changed.has("model")) this._checkAcknowledgement();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._request?.timer) globalThis.clearTimeout(this._request.timer);
  }

  _beginRequest(key, invoke, acknowledge, pendingText, onAcknowledge = null) {
    if (this.phase === "pending") return;
    const activeElement = this.getRootNode()?.activeElement;
    this._focusAfterRequest = activeElement instanceof HTMLElement && this.contains(activeElement)
      ? activeElement
      : null;
    const token = Symbol(key);
    this.phase = "pending";
    this.pendingKey = key;
    this.feedback = pendingText;
    this.feedbackTone = "";
    this._request = {
      token,
      key,
      acknowledge,
      onAcknowledge,
      callDone: false,
      acknowledgementSeen: false,
      timer: globalThis.setTimeout(() => {
        if (this._request?.token !== token) return;
        this._failRequest(textFor(this.model).noAcknowledgement);
      }, globalThis.__epControlTestMode === true
        ? Math.max(50, finite(globalThis.__epControlAckTimeoutMs, ACK_TIMEOUT_MS))
        : ACK_TIMEOUT_MS),
    };

    Promise.resolve()
      .then(invoke)
      .then(() => {
        if (this._request?.token !== token) return;
        this._request.callDone = true;
        this._checkAcknowledgement();
      })
      .catch((error) => {
        if (this._request?.token !== token) return;
        this._failRequest(
          `${textFor(this.model).requestFailed}: ${error?.message || String(error)}`
        );
      });
  }

  _checkAcknowledgement() {
    const request = this._request;
    if (!request || this.phase !== "pending") return;
    try {
      request.acknowledgementSeen = Boolean(
        request.acknowledgementSeen || request.acknowledge(this.model)
      );
    } catch (_error) {
      request.acknowledgementSeen = false;
    }
    if (!request.callDone || !request.acknowledgementSeen) return;
    if (request.timer) globalThis.clearTimeout(request.timer);
    request.onAcknowledge?.();
    this._request = null;
    this.phase = "acknowledged";
    this.pendingKey = null;
    this.feedback = textFor(this.model).acknowledged;
    this.feedbackTone = "ok";
    this._restoreRequestFocus();
  }

  _failRequest(message) {
    if (this._request?.timer) globalThis.clearTimeout(this._request.timer);
    this._request = null;
    this.phase = "error";
    this.pendingKey = null;
    this.feedback = message;
    this.feedbackTone = "error";
    this._restoreRequestFocus();
  }

  _restoreRequestFocus() {
    const target = this._focusAfterRequest;
    this._focusAfterRequest = null;
    if (!(target instanceof HTMLElement)) return;
    void this.updateComplete.then(() => {
      if (!target.isConnected) return;
      try {
        target.focus({ preventScroll: true });
      } catch (_error) {
        target.focus();
      }
    });
  }

  _status(defaultText = "", defaultTone = "") {
    return html`<div class="ep-control-status ${this.feedbackTone || defaultTone}" aria-live="polite">${this.feedback || defaultText}</div>`;
  }
}

class EpBatteryActions extends EpAcknowledgedControl {
  _selected() {
    if (this.model.automaticState === "on") return "resume_auto";
    if (this.model.automaticState !== "off") return null;
    return QUICK_ACTIONS.find((item) => item.command === this.model.command)?.key || null;
  }

  _activate(definition) {
    const copy = textFor(this.model);
    this._beginRequest(
      definition.key,
      () => this.actions.pressBatteryAction(definition.key),
      (next) => definition.key === "resume_auto"
        ? next.automaticState === "on"
        : next.automaticState === "off" && next.command === definition.command,
      copy.batteryPending
    );
  }

  render() {
    const copy = textFor(this.model);
    const selected = this._selected();
    const busy = this.phase === "pending";
    return html`
      <section class="ep-control-group ep-battery-quick" aria-busy=${busy ? "true" : "false"}>
        <h2 class="ep-control-title">${copy.battery}</h2>
        <div class="ep-control-actions ep-battery-actions" role="group" aria-label=${copy.battery}>
          ${QUICK_ACTIONS.map((definition) => html`
            <button type="button"
              class=${`ep-battery-action${selected === definition.key ? " active" : ""}`}
              data-action=${definition.key}
              data-control-id=${`battery:${definition.key}`}
              data-pending=${this.pendingKey === definition.key ? "true" : "false"}
              aria-pressed=${selected === definition.key ? "true" : "false"}
              ?disabled=${busy || !this.model.available?.[definition.key]}
              @click=${() => this._activate(definition)}>
              ${this.pendingKey === definition.key ? copy.pending : definition[copy === COPY.nl ? "nl" : "en"]}
            </button>
          `)}
        </div>
        ${this._status()}
      </section>`;
  }
}

class EpAutomaticControl extends EpAcknowledgedControl {
  _toggle() {
    const copy = textFor(this.model);
    const turningOn = this.model.state !== "on";
    if (turningOn && !globalThis.confirm(copy.confirmAutomatic)) return;
    this._beginRequest(
      turningOn ? "on" : "off",
      () => this.actions.setAutomatic(turningOn),
      (next) => next.state === (turningOn ? "on" : "off"),
      copy.pending
    );
  }

  render() {
    const copy = textFor(this.model);
    const confirmedOn = this.model.state === "on";
    const known = ["on", "off"].includes(this.model.state);
    const busy = this.phase === "pending";
    return html`
      <section class="ep-control-group ep-automatic-compact" aria-busy=${busy ? "true" : "false"}>
        <h2 class="ep-control-title">${copy.automatic}</h2>
        <button type="button" id="auto-toggle"
          class="ep-automatic-control-button"
          data-control-id="automatic-control"
          data-pending=${busy ? "true" : "false"}
          aria-pressed=${confirmedOn ? "true" : "false"}
          ?disabled=${busy || !this.model.available || !known}
          @click=${this._toggle}>
          <span class="ep-automatic-indicator" aria-hidden="true"></span>
          ${known ? confirmedOn ? copy.automaticOn : copy.automaticOff : copy.unavailable}
        </button>
        ${this._status()}
      </section>`;
  }
}

class EpEmhassStrategy extends EpAcknowledgedControl {
  _select(definition) {
    const copy = textFor(this.model);
    if (definition.raw === this.model.currentRaw) return;
    this._beginRequest(
      definition.raw,
      () => this.actions.setCostFunction(definition.raw),
      (next) => next.currentRaw === definition.raw,
      copy.pending
    );
  }

  render() {
    const copy = textFor(this.model);
    const busy = this.phase === "pending";
    const active = COST_FUNCTIONS.find(
      (definition) => definition.raw === this.model.currentRaw
    );
    return html`
      <section class="ep-control-group ep-v016-costfun" aria-busy=${busy ? "true" : "false"}>
        <details class="ep-compact-selector">
          <summary data-control-id="emhass-selector"
            aria-label=${`${copy.emhass}: ${active?.label || copy.unavailable}`}>
            <span class="ep-compact-selector-label"><strong>${copy.emhassCompact}</strong> · ${active?.label || copy.unavailable}</span>
            <span class="ep-compact-chevron" aria-hidden="true">⌄</span>
          </summary>
          <div class="ep-compact-selector-menu">
            <h2 class="ep-control-title">${copy.emhass}</h2>
            <div class="ep-control-actions ep-v016-costfun-actions" role="group" aria-label=${copy.emhass}>
              ${COST_FUNCTIONS.map((definition) => html`
                <button type="button"
                  class=${`ep-v016-costfun-button${this.model.currentRaw === definition.raw ? " active" : ""}`}
                  data-costfun=${definition.raw}
                  data-control-id=${`emhass:${definition.raw}`}
                  data-pending=${this.pendingKey === definition.raw ? "true" : "false"}
                  aria-pressed=${this.model.currentRaw === definition.raw ? "true" : "false"}
                  ?disabled=${busy || !this.model.available?.[definition.raw]}
                  @click=${() => this._select(definition)}>
                  ${this.pendingKey === definition.raw ? copy.pending : definition.label}
                </button>
              `)}
            </div>
            ${this._status(this.model.currentRaw ? `${copy.active} · ${this.model.currentRaw}` : copy.unavailable)}
          </div>
        </details>
      </section>`;
  }
}

class EpBatteryStrategy extends EpAcknowledgedControl {
  static properties = {
    ...EpAcknowledgedControl.properties,
    customDraft: { state: true },
    customDirty: { state: true },
    minimumDraft: { state: true },
    maximumDraft: { state: true },
  };

  constructor() {
    super();
    this.customDraft = {};
    this.customDirty = false;
    this.minimumDraft = null;
    this.maximumDraft = null;
  }

  willUpdate(changed) {
    super.willUpdate(changed);
    if (!changed.has("model")) return;
    if (!this.customDirty && this.phase !== "pending") {
      this.customDraft = { ...(this.model.values || {}) };
    }
    if (this.phase !== "pending") {
      this.minimumDraft = finite(this.model.minimumSoc, 0);
      this.maximumDraft = finite(this.model.maximumSoc, 100);
    }
  }

  _select(mode) {
    const copy = textFor(this.model);
    if (mode === this.model.activeMode && this.model.managed) return;
    this._beginRequest(
      `profile:${mode}`,
      () => this.actions.setBatteryProfile(mode),
      (next) => next.activeMode === mode &&
        (mode === CUSTOM_MODE ? !next.managed : next.managed),
      copy.pending
    );
  }

  _customInput(key, event) {
    this.customDraft = { ...this.customDraft, [key]: event.currentTarget.value };
    this.customDirty = true;
  }

  _saveCustom() {
    const values = {};
    for (const [key, raw] of Object.entries(this.customDraft || {})) {
      const value = Number(raw);
      if (!Number.isFinite(value) || value < 0) return;
      values[key] = value;
    }
    const before = finite(this.model.revision, 0);
    const copy = textFor(this.model);
    this._beginRequest(
      "custom",
      () => this.actions.saveCustomBatteryValues(values),
      (next) => next.activeMode === CUSTOM_MODE && finite(next.revision, 0) > before,
      copy.pending,
      () => { this.customDirty = false; }
    );
  }

  _setSoc(kind, value) {
    const requested = Number(value);
    const copy = textFor(this.model);
    this._beginRequest(
      `soc:${kind}`,
      () => this.actions.setSocLimit(kind, requested),
      (next) => finite(kind === "minimum" ? next.minimumSoc : next.maximumSoc) === requested,
      copy.pending
    );
  }

  render() {
    const copy = textFor(this.model);
    const busy = this.phase === "pending";
    const values = this.customDraft || this.model.values || {};
    const activeProfile = (this.model.modes || []).find(
      (mode) => mode.key === this.model.activeMode
    );
    const fields = [
      ["battery_soc_deficit_cost", copy.lowSocCost],
      ["battery_soc_surplus_cost", copy.highSocCost],
      ["battery_stress_cost", copy.powerStress],
      ["weight_battery_charge", copy.chargeCost],
      ["weight_battery_discharge", copy.dischargeCost],
    ];
    return html`
      <section class="ep-control-group wide ep-v038-strategy" aria-busy=${busy ? "true" : "false"}>
        <details class="ep-compact-selector">
          <summary data-control-id="battery-selector"
            aria-label=${`${copy.batteryStrategy}: ${activeProfile?.label || copy.unavailable}`}>
            <span class="ep-compact-selector-label"><strong>${copy.batteryCompact}</strong> · ${activeProfile?.label || copy.unavailable}</span>
            <span class="ep-compact-chevron" aria-hidden="true">⌄</span>
          </summary>
          <div class="ep-compact-selector-menu">
            <h2 class="ep-control-title">${copy.batteryStrategy}</h2>
            <div class="ep-control-actions ep-v038-profile-grid" role="group" aria-label=${copy.batteryStrategy}>
              ${(this.model.modes || []).map((mode) => html`
                <button type="button" class="ep-v038-profile"
                  data-ep-v038-profile=${mode.key}
                  data-control-id=${`profile:${mode.key}`}
                  data-pending=${this.pendingKey === `profile:${mode.key}` ? "true" : "false"}
                  aria-pressed=${this.model.activeMode === mode.key &&
                    (mode.key === CUSTOM_MODE ? !this.model.managed : this.model.managed)
                    ? "true"
                    : "false"}
                  ?disabled=${busy || this.model.loading || !this.model.data}
                  @click=${() => this._select(mode.key)}>
                  <strong>${mode.label}</strong><small>${mode.description}</small>
                </button>
              `)}
            </div>
            <div class="ep-v038-custom" ?hidden=${this.model.activeMode !== CUSTOM_MODE}>
              <div class="ep-control-title">${copy.custom}</div>
              <div class="ep-v038-custom-grid">
                <label>${copy.minimumSoc}
                  <input type="range" min="0" max="100" step="1"
                    data-control-id="profile:minimum-soc"
                    .value=${String(this.minimumDraft ?? this.model.minimumSoc ?? 0)}
                    ?disabled=${busy || !this.model.minimumSocAvailable}
                    @input=${(event) => { this.minimumDraft = Number(event.currentTarget.value); }}
                    @change=${(event) => this._setSoc("minimum", event.currentTarget.value)}>
                </label>
                <label>${copy.maximumSoc}
                  <input type="range" min="0" max="100" step="1"
                    data-control-id="profile:maximum-soc"
                    .value=${String(this.maximumDraft ?? this.model.maximumSoc ?? 100)}
                    ?disabled=${busy || !this.model.maximumSocAvailable}
                    @input=${(event) => { this.maximumDraft = Number(event.currentTarget.value); }}
                    @change=${(event) => this._setSoc("maximum", event.currentTarget.value)}>
                </label>
              </div>
              <div>
                <div class="ep-v038-custom-values">
                  ${fields.map(([key, label]) => html`
                    <label>${label}
                      <input type="number" inputmode="decimal" min="0" step="0.000001" required
                        data-control-id=${`profile:custom:${key}`}
                        .value=${String(values[key] ?? "")}
                        ?disabled=${busy || !this.model.editable}
                        @input=${(event) => this._customInput(key, event)}>
                    </label>
                  `)}
                </div>
                <div class="ep-v038-custom-actions">
                  <button type="button" class="ep-v038-custom-save"
                    data-control-id="profile:custom-save"
                    data-pending=${this.pendingKey === "custom" ? "true" : "false"}
                    ?disabled=${busy || !this.model.editable}
                    @click=${this._saveCustom}>${copy.saveCustom}</button>
                </div>
              </div>
            </div>
            ${this.model.managed && activeProfile ? html`
              <div class="ep-v038-managed">
                <div class="ep-control-title">${copy.managedTitle}</div>
                <div class="ep-v038-managed-grid">
                  <span>${copy.hardRange} <strong>${profilePercent(activeProfile.minimum_soc_pct)} – ${profilePercent(activeProfile.maximum_soc_pct)}</strong></span>
                  <span>${copy.comfortRange} <strong>${profilePercent(activeProfile.deficit_threshold_pct)} – ${profilePercent(activeProfile.surplus_threshold_pct)}</strong></span>
                  <span>${copy.lowCost} <strong>${profilePercent(activeProfile.deficit_cost_factor_pct)}</strong></span>
                  <span>${copy.highCost} <strong>${profilePercent(activeProfile.surplus_cost_factor_pct)}</strong></span>
                  <span>${copy.stressCost} <strong>${profilePercent(activeProfile.stress_cost_factor_pct)}</strong></span>
                  <span>${copy.antiChurn} <strong>${profilePercent(activeProfile.anti_churn_cost_factor_pct)}</strong></span>
                </div>
              </div>
            ` : nothing}
            ${this._status(
              this.model.loading ? copy.profilesLoading : this.model.error || "",
              this.model.error ? "error" : ""
            )}
          </div>
        </details>
      </section>`;
  }
}

class EpOptimizeAction extends EpAcknowledgedControl {
  _optimize() {
    const before = this.model.planRevision;
    const copy = textFor(this.model);
    this._beginRequest(
      "optimize",
      () => this.actions.optimizeNow(),
      (next) => Number.isFinite(next.planRevision) && next.planRevision !== before,
      copy.optimizing
    );
  }

  render() {
    const copy = textFor(this.model);
    const busy = this.phase === "pending" || this.model.running;
    const status = String(this.model.status || "").trim();
    const idleStatus = ["idle", "ready"].includes(status.toLowerCase());
    return html`
      <section class="ep-control-group ep-optimize-compact" aria-busy=${busy ? "true" : "false"}>
        <h2 class="ep-control-title">${copy.optimize}</h2>
        <button type="button" class="ep-optimize-now"
          data-control-id="optimize-now"
          data-pending=${this.phase === "pending" ? "true" : "false"}
          aria-busy=${busy ? "true" : "false"}
          ?disabled=${busy || !this.model.available}
          @click=${this._optimize}>${busy ? copy.optimizing : copy.optimize}</button>
        ${this._status(idleStatus ? "" : status)}
      </section>`;
  }
}

class EpManualEmsControls extends EpAcknowledgedControl {
  static properties = {
    ...EpAcknowledgedControl.properties,
    powerDraft: { state: true },
    powerDirty: { state: true },
  };

  constructor() {
    super();
    this.powerDraft = 0;
    this.powerDirty = false;
  }

  willUpdate(changed) {
    super.willUpdate(changed);
    if (changed.has("model") && !this.powerDirty && this.phase !== "pending") {
      this.powerDraft = finite(this.model.power, 0);
    }
  }

  _selectMode(definition) {
    if (definition.mode === 7 && !globalThis.confirm(textFor(this.model).confirmOffgrid)) return;
    const copy = textFor(this.model);
    const power = definition.zeroPower ? 0 : Number(this.powerDraft);
    this._beginRequest(
      `mode:${definition.mode}`,
      () => this.actions.setManualMode(definition.mode, power),
      (next) => next.automaticState === "off" && next.mode === definition.mode,
      copy.pending,
      () => { this.powerDirty = false; }
    );
  }

  _powerInput(event) {
    this.powerDraft = Number(event.currentTarget.value);
    this.powerDirty = true;
  }

  _savePower(event) {
    const requested = Number(event.currentTarget.value);
    const copy = textFor(this.model);
    this._beginRequest(
      "manual-power",
      () => this.actions.setManualPower(requested),
      (next) => finite(next.power) === requested,
      copy.pending,
      () => { this.powerDirty = false; }
    );
  }

  render() {
    const copy = textFor(this.model);
    const automaticOn = this.model.automaticState === "on";
    const busy = this.phase === "pending";
    const locked = busy || automaticOn || !this.model.available;
    return html`
      <section class=${`ep-control-group wide ep-v021-manual-pad${automaticOn ? " compact" : ""}`} aria-busy=${busy ? "true" : "false"}>
        <details class="ep-manual-disclosure" data-locked=${automaticOn ? "true" : "false"}>
          <summary data-control-id="manual-selector"
            aria-disabled=${automaticOn ? "true" : "false"}
            @click=${(event) => { if (automaticOn) event.preventDefault(); }}>
            <span class="ep-manual-summary-copy">
              <strong>${copy.manual}</strong>
              <small data-manual-note>${automaticOn ? copy.manualLocked : copy.manualReady}</small>
            </span>
            <span class="ep-compact-chevron" aria-hidden="true">⌄</span>
          </summary>
          <div class="ep-manual-body">
            <div class="ep-control-actions ep-v021-mode-grid" role="group" aria-label=${copy.manual}
              ?hidden=${automaticOn} aria-hidden=${automaticOn ? "true" : "false"}>
              ${MANUAL_MODES.map((definition) => {
                const localized = localizedEmsMode(this.model.language, definition.mode);
                const label = `${definition.mode} · ${localized.name}${localized.tip ? ` — ${localized.tip}` : ""}`;
                return html`
                <button type="button" class="ep-v021-mode-button"
                  data-mode=${definition.mode}
                  data-control-id=${`manual-mode:${definition.mode}`}
                  data-pending=${this.pendingKey === `mode:${definition.mode}` ? "true" : "false"}
                  aria-label=${label} title=${label}
                  aria-pressed=${!automaticOn && this.model.mode === definition.mode ? "true" : "false"}
                  ?disabled=${locked}
                  @click=${() => this._selectMode(definition)}>
                  <strong>${definition.mode}</strong><small>${definition.tag}</small>
                </button>`;
              })}
            </div>
            <div class="ep-v021-power-row" ?hidden=${automaticOn} aria-hidden=${automaticOn ? "true" : "false"}>
              <label class="ep-v021-power-label">${copy.manualPower}
                <input type="range" class="ep-v021-power-slider"
                  min="0" .max=${String(this.model.max || 0)} .step=${String(this.model.step || 1)}
                  .value=${String(this.powerDraft)}
                  data-control-id="manual-power"
                  ?disabled=${locked}
                  @input=${this._powerInput}
                  @change=${this._savePower}>
              </label>
              <span class="ep-manual-readback">${Math.round(this.powerDraft)} W · ${copy.live} ${Number.isFinite(this.model.actualSetpoint) ? `${Math.round(this.model.actualSetpoint)} W` : "—"}</span>
            </div>
            ${this._status()}
          </div>
        </details>
      </section>`;
  }
}

class EpControlSurface extends LitElement {
  static properties = {
    model: { attribute: false },
    actions: { attribute: false },
  };

  constructor() {
    super();
    this.model = freezeModel({ language: "en" });
    this.actions = Object.freeze({});
  }

  createRenderRoot() {
    return this;
  }

  _collapseOtherDisclosures(event) {
    const path = event.composedPath();
    const summary = path.find(
      (node) => node instanceof HTMLElement && node.tagName === "SUMMARY"
    );
    const selected = summary?.parentElement;
    if (selected instanceof HTMLDetailsElement) {
      for (const disclosure of this.querySelectorAll("details[open]")) {
        if (disclosure !== selected) disclosure.open = false;
      }
      return;
    }
    const option = path.find(
      (node) => node instanceof HTMLButtonElement &&
        node.closest(".ep-compact-selector-menu")
    );
    option?.closest("details")?.removeAttribute("open");
  }

  render() {
    const copy = textFor(this.model);
    return html`
      <style>${CONTROL_SURFACE_CSS}</style>
      <section class="ep-control-surface" data-ep-permanent-control-surface="1"
        aria-label=${copy.surface} @click=${this._collapseOtherDisclosures}>
        <div class="ep-control-surface-head">
          <div><div class="ep-control-surface-kicker">${copy.surface}</div><div class="ep-control-surface-detail">${copy.surfaceDetail}</div></div>
          <ep-automatic-control .model=${this.model.automatic} .actions=${this.actions}></ep-automatic-control>
        </div>
        <div class="ep-control-surface-grid">
          <ep-battery-actions .model=${this.model.battery} .actions=${this.actions}></ep-battery-actions>
          <div class="ep-control-selectors">
            <ep-emhass-strategy .model=${this.model.emhass} .actions=${this.actions}></ep-emhass-strategy>
            <ep-battery-strategy .model=${this.model.profiles} .actions=${this.actions}></ep-battery-strategy>
          </div>
          <ep-optimize-action .model=${this.model.optimize} .actions=${this.actions}></ep-optimize-action>
          <ep-manual-ems-controls .model=${this.model.manual} .actions=${this.actions}></ep-manual-ems-controls>
        </div>
        <p class="section-note ep-v022-strategy-note"
          data-ep-v048-presentation-key=${`${this.model.language}:hybrid`}
          ?hidden=${this.model.strategy?.value !== "hybrid"}>
          <strong>${this.model.strategy?.note?.title || ""}</strong>
          ${this.model.strategy?.note?.label || ""} · ${this.model.strategy?.note?.description || ""}
          ${this.model.strategy?.note?.safety || ""}
        </p>
      </section>`;
  }
}

const gateways = new WeakMap();
const traces = new WeakMap();
const nodeIdentities = new WeakMap();
let nextNodeIdentity = 1;

function nodeIdentity(node) {
  if (!(node instanceof Node)) return null;
  if (!nodeIdentities.has(node)) nodeIdentities.set(node, nextNodeIdentity++);
  return nodeIdentities.get(node);
}

function traceState(panel) {
  if (!traces.has(panel)) traces.set(panel, { enabled: true, events: [], sequence: 0 });
  return traces.get(panel);
}

export function recordControlTrace(panel, type, details = {}) {
  if (!panel) return;
  const state = traceState(panel);
  if (!state.enabled) return;
  const surface = panel.__epPermanentControlSurface || null;
  state.events.push(Object.freeze({
    sequence: ++state.sequence,
    at: new Date().toISOString(),
    monotonicMs: globalThis.performance?.now?.() ?? null,
    type,
    surfaceIdentity: nodeIdentity(surface),
    surfaceConnected: Boolean(surface?.isConnected),
    ...details,
  }));
  if (state.events.length > TRACE_LIMIT) state.events.splice(0, state.events.length - TRACE_LIMIT);
}

function installTraceApi(panel) {
  const api = {
    enable: () => { traceState(panel).enabled = true; },
    disable: () => { traceState(panel).enabled = false; },
    clear: () => { traceState(panel).events.length = 0; },
    snapshot: () => traceState(panel).events.map((event) => ({ ...event })),
    json: () => JSON.stringify(traceState(panel).events, null, 2),
  };
  panel.controlTrace = api;
  globalThis.__epControlTrace = api;
  globalThis.__epRecordEnergyPilotControlTrace = recordControlTrace;
}

function installPassiveEventTrace(panel, surface) {
  if (surface.__epPassiveTraceInstalled) return;
  surface.__epPassiveTraceInstalled = true;
  for (const eventName of ["pointerdown", "pointermove", "pointerup", "pointercancel", "click"]) {
    surface.addEventListener(eventName, (event) => {
      const control = event.composedPath().find(
        (node) => node instanceof Element && node.hasAttribute?.("data-control-id")
      );
      if (!control) return;
      recordControlTrace(panel, eventName, {
        controlId: control.getAttribute("data-control-id"),
        nodeIdentity: nodeIdentity(control),
        isConnected: control.isConnected,
        pointerId: event.pointerId ?? null,
        pointerType: event.pointerType || null,
        clientX: event.clientX ?? null,
        clientY: event.clientY ?? null,
        defaultPrevented: event.defaultPrevented,
      });
    }, { capture: true, passive: true });
  }
}

class ControlGateway {
  constructor(panel) {
    this.panel = panel;
    this.profileData = null;
    this.profileLoading = false;
    this.profileError = "";
    this.profileRevision = 0;
    this.actions = Object.freeze({
      pressBatteryAction: (key) => this.pressBatteryAction(key),
      setAutomatic: (enabled) => this.setAutomatic(enabled),
      setCostFunction: (raw) => this.setCostFunction(raw),
      setBatteryProfile: (mode) => this.setBatteryProfile(mode),
      saveCustomBatteryValues: (values) => this.saveCustomBatteryValues(values),
      setSocLimit: (kind, value) => this.setSocLimit(kind, value),
      optimizeNow: () => this.optimizeNow(),
      setManualMode: (mode, power) => this.setManualMode(mode, power),
      setManualPower: (power) => this.setManualPower(power),
    });
  }

  refresh(reason = "gateway") {
    refreshEnergyPilotControlSurface(this.panel, reason);
  }

  async callService(controlId, domain, service, data) {
    recordControlTrace(this.panel, "servicecall-start", { controlId, domain, service, data: { ...data } });
    try {
      const result = await this.panel._hass.callService(domain, service, data);
      recordControlTrace(this.panel, "servicecall-end", { controlId, domain, service });
      return result;
    } catch (error) {
      recordControlTrace(this.panel, "servicecall-error", {
        controlId,
        domain,
        service,
        error: error?.message || String(error),
      });
      throw error;
    }
  }

  async callWs(controlId, message) {
    recordControlTrace(this.panel, "servicecall-start", { controlId, websocketType: message.type });
    try {
      const result = await this.panel._hass.callWS(message);
      recordControlTrace(this.panel, "servicecall-end", { controlId, websocketType: message.type });
      return result;
    } catch (error) {
      recordControlTrace(this.panel, "servicecall-error", {
        controlId,
        websocketType: message.type,
        error: error?.message || String(error),
      });
      throw error;
    }
  }

  async ensureProfiles(force = false, throwOnError = false) {
    if (this.profileLoading || (!force && this.profileData)) return;
    this.profileLoading = true;
    this.profileError = "";
    this.refresh("profiles-loading");
    try {
      this.profileData = await this.callWs("profile:load", {
        type: "gw_energypilot/battery_saver/get",
      });
      this.profileRevision += 1;
    } catch (error) {
      this.profileError = error?.message || String(error);
      if (throwOnError) throw error;
    } finally {
      this.profileLoading = false;
      this.refresh("profiles-loaded");
    }
  }

  async pressBatteryAction(key) {
    const entityId = this.panel._entityId?.(key);
    if (!entityId) throw new Error(`${key} entity is unavailable`);
    return this.callService(`battery:${key}`, "button", "press", { entity_id: entityId });
  }

  async setAutomatic(enabled) {
    const entityId = this.panel._entityId?.("automatic_control");
    if (!entityId) throw new Error("Automatic Control entity is unavailable");
    return this.callService(
      "automatic-control",
      "switch",
      enabled ? "turn_on" : "turn_off",
      { entity_id: entityId }
    );
  }

  async setCostFunction(raw) {
    const definition = COST_FUNCTIONS.find((item) => item.raw === raw);
    if (!definition) throw new Error(`Unsupported cost function: ${raw}`);
    const selectEntityId = this.panel._entityId?.("emhass_cost_function");
    if (selectEntityId) {
      return this.callService(`emhass:${raw}`, "select", "select_option", {
        entity_id: selectEntityId,
        option: definition.option,
      });
    }
    const legacyId = this.panel._entityId?.(definition.legacyKey);
    if (!legacyId) throw new Error("EMHASS strategy entity is unavailable");
    return this.callService(`emhass:${raw}`, "button", "press", { entity_id: legacyId });
  }

  async setBatteryProfile(mode) {
    if (!this.profileData?.entry_id) await this.ensureProfiles(true, true);
    const entryId = this.profileData?.entry_id;
    if (!entryId) throw new Error("Battery profile entry is unavailable");
    this.profileData = await this.callWs(`profile:${mode}`, {
      type: "gw_energypilot/battery_saver/set",
      entry_id: entryId,
      mode,
    });
    this.profileRevision += 1;
    this.refresh("profile-confirmed");
  }

  async saveCustomBatteryValues(values) {
    const entryId = this.profileData?.entry_id;
    if (!entryId) throw new Error("Battery profile entry is unavailable");
    this.profileData = await this.callWs("profile:custom-save", {
      type: "gw_energypilot/battery_saver/custom_set",
      entry_id: entryId,
      values,
    });
    this.profileRevision += 1;
    this.refresh("custom-profile-confirmed");
  }

  async setSocLimit(kind, value) {
    const key = kind === "minimum" ? "emhass_minimum_soc" : "emhass_maximum_soc";
    const entityId = this.panel._entityId?.(key);
    if (!entityId) throw new Error(`${key} entity is unavailable`);
    return this.callService(`profile:${kind}-soc`, "number", "set_value", {
      entity_id: entityId,
      value,
    });
  }

  async optimizeNow() {
    const entityId = this.panel._entityId?.("optimize_now");
    if (!entityId) throw new Error("Optimize entity is unavailable");
    return this.callService("optimize-now", "button", "press", { entity_id: entityId });
  }

  async setManualPower(power) {
    const entityId = this.panel._entityId?.("manual_power");
    if (!entityId) throw new Error("Manual power entity is unavailable");
    return this.callService("manual-power", "number", "set_value", {
      entity_id: entityId,
      value: power,
    });
  }

  async setManualMode(mode, _power) {
    const definition = MANUAL_MODES.find((item) => item.mode === Number(mode));
    const entityId = this.panel._entityId?.("manual_mode");
    if (!definition || !entityId) throw new Error("Manual mode entity is unavailable");
    return this.callService(`manual-mode:${mode}`, "select", "select_option", {
      entity_id: entityId,
      option: definition.option,
    });
  }
}

function controlGateway(panel) {
  if (!gateways.has(panel)) gateways.set(panel, new ControlGateway(panel));
  return gateways.get(panel);
}

export function mountEnergyPilotControlSurface(panel, root = panel?.shadowRoot) {
  if (!panel || !root) return null;
  panel.__epControlSurfaceArchitecture = true;
  installTraceApi(panel);
  let surface = panel.__epPermanentControlSurface;
  if (!(surface instanceof HTMLElement)) {
    surface = document.createElement("ep-control-surface");
    panel.__epPermanentControlSurface = surface;
  }
  const newlyMounted = !surface.isConnected;
  if (newlyMounted) {
    const anchor = root.querySelector("[data-ep-control-anchor]");
    const main = root.querySelector("main");
    if (anchor) anchor.replaceWith(surface);
    else if (main) main.insertBefore(surface, main.children[1] || null);
  }
  if (newlyMounted) panel.__epV008PlaceControlSurface?.(surface);
  surface.hidden = false;
  const gateway = controlGateway(panel);
  surface.actions = gateway.actions;
  surface.model = buildControlSurfaceModel(panel, gateway);
  installPassiveEventTrace(panel, surface);
  recordControlTrace(panel, "surface-mounted", {
    nodeIdentity: nodeIdentity(surface),
    isConnected: surface.isConnected,
  });
  void gateway.ensureProfiles();
  return surface;
}

export function refreshEnergyPilotControlSurface(panel, reason = "hass-state-publication") {
  const surface = panel?.__epPermanentControlSurface;
  if (!(surface instanceof HTMLElement)) return null;
  const gateway = controlGateway(panel);
  surface.model = buildControlSurfaceModel(panel, gateway);
  recordControlTrace(panel, reason === "hass-state-publication" ? "hass-state-publication" : reason, {
    nodeIdentity: nodeIdentity(surface),
    isConnected: surface.isConnected,
  });
  return surface;
}

export function patchNarrowControlSurface(panel, narrow) {
  panel._narrow = Boolean(narrow);
  panel.shadowRoot?.querySelector("main")?.classList.toggle("narrow", Boolean(narrow));
  refreshEnergyPilotControlSurface(panel, "narrow-property-update");
}

for (const [name, constructor] of [
  ["ep-battery-actions", EpBatteryActions],
  ["ep-automatic-control", EpAutomaticControl],
  ["ep-emhass-strategy", EpEmhassStrategy],
  ["ep-battery-strategy", EpBatteryStrategy],
  ["ep-optimize-action", EpOptimizeAction],
  ["ep-manual-ems-controls", EpManualEmsControls],
  ["ep-control-surface", EpControlSurface],
]) {
  if (!customElements.get(name)) customElements.define(name, constructor);
}

void nothing;
