import {
  canonicalProfiles,
  normalizeLanguage,
} from "./gw-energy-pilot-v038-model.js?v=1.1.0-stable1";

const EMS_MODE_TEXT = {
  en: {
    1: ["GoodWe Auto / AI", "Normal GoodWe self-use control. Setpoint is forced to 0 W."],
    2: ["PV-priority charging", "Charge with GoodWe-visible PV first; setpoint is the allowed grid-assist limit."],
    3: ["PV + battery supply", "PV has priority; setpoint is the allowed battery-discharge limit."],
    4: ["Inverter import / AC charging", "Inverter-level grid-import target. Not the same as direct battery charge power."],
    5: ["Inverter export power", "Inverter-level AC export target. Site load is not controlled like mode 10."],
    6: ["Reserve / Conserve", "Reserve battery energy for off-grid use. Setpoint is forced to 0 W."],
    7: ["Off-grid", "Force off-grid operation. Use only when the installation is prepared for it."],
    8: ["Battery Hold", "Battery standby: no active charge or discharge. Setpoint is forced to 0 W."],
    9: ["Grid import target", "Target net import at the GoodWe smart meter/PCC; battery direction may change to hold it."],
    10: ["Grid export target", "Target net export at the GoodWe smart meter/PCC. Use 0 W for a zero-export test."],
    11: ["Battery charge power", "Direct battery charge-power target. PV may contribute; grid can fill the remainder."],
    12: ["Battery discharge power", "Direct battery discharge-power target, bounded by inverter/BMS limits."],
  },
  nl: {
    1: ["GoodWe Auto / AI", "Normale GoodWe-zelfverbruiksregeling. Het setpoint wordt op 0 W gezet."],
    2: ["PV-prioriteit laden", "Laadt eerst met het door GoodWe zichtbare PV-vermogen; het setpoint is de toegestane limiet voor netondersteuning."],
    3: ["PV + batterijvoeding", "PV heeft prioriteit; het setpoint is de toegestane limiet voor batterijontlading."],
    4: ["Omvormerimport / AC-laden", "Doel voor netimport op omvormerniveau. Niet hetzelfde als direct batterijlaadvermogen."],
    5: ["Omvormerexportvermogen", "AC-exportdoel op omvormerniveau. De huislast wordt niet geregeld zoals in modus 10."],
    6: ["Reserve / behoud", "Reserveert batterij-energie voor off-grid gebruik. Het setpoint wordt op 0 W gezet."],
    7: ["Off-grid", "Forceert off-grid bedrijf. Alleen gebruiken als de installatie daarop is voorbereid."],
    8: ["Batterij stand-by", "Batterij stand-by: geen actief laden of ontladen. Het setpoint wordt op 0 W gezet."],
    9: ["Netimportdoel", "Doel voor netto-import bij de GoodWe smart meter/PCC; de batterijrichting kan wijzigen om dit doel vast te houden."],
    10: ["Netexportdoel", "Doel voor netto-export bij de GoodWe smart meter/PCC. Gebruik 0 W voor een nul-exporttest."],
    11: ["Batterijlaadvermogen", "Direct doel voor batterijlaadvermogen. PV kan bijdragen; het net kan de rest aanvullen."],
    12: ["Batterijontlaadvermogen", "Direct doel voor batterijontlaadvermogen, begrensd door omvormer/BMS-limieten."],
  },
};

const NL = Object.freeze({
  windowLabel: "Regelaar",
  kicker: "ENERGYPILOT REGELING",
  title: "Regelaar",
  automaticOn: "Automatisch AAN",
  automaticOff: "Automatisch UIT",
  emsMode: "EMS-modus",
  emsSetpoint: "EMS-setpoint",
  pccTarget: "PCC-doel",
  batteryTarget: "Batterijdoel",
  controlTarget: "Regeldoel",
  safety:
    "Automatische regeling keert na het herladen van de integratie of een herstart van Home Assistant terug naar GoodWe Auto / AI.",
  manualKicker: "HANDMATIGE EMS-TEST",
  manualTitle: "GoodWe-modi 1–12",
  lockedAutomatic: "VERGRENDELD · AUTOMATISCH",
  manualReady: "HANDMATIG GEREED",
  entitiesMissing: "ENTITEITEN ONTBREKEN",
  manualSetpoint: "Handmatig setpoint",
  manualSetpointAria: "Handmatig GoodWe EMS-vermogenssetpoint",
  automaticOwner:
    "Automatische regeling bestuurt de omvormer.",
  automaticOwnerDetail:
    "Bediening is vergrendeld; de actieve modus volgt de live Modbus-teruglezing.",
  manualUnavailable:
    "Handmatige bediening is niet beschikbaar.",
  manualUnavailableDetail:
    "De vereiste Home Assistant-entiteiten ontbreken.",
  live: "Live",
  hoverHint: "Beweeg over een modus voor uitleg.",
  strategy:
    "GoodWe smart meter AAN gebruikt P_grid → 9/10 (modus 1 rond nul). Smart meter UIT gebruikt P_batt → 11/12 (modus 8 rond nul). EV-anti-ontlaadbeveiliging heeft tijdens actief EV-laden voorrang: ontladen wordt geblokkeerd, expliciet batterijladen blijft toegestaan. Handmatige knoppen blijven altijd directe bedieningscommando's.",
  strategyLabel: "Automatische regelstrategie",
  telemetry: "telemetrie",
});

export function dashboardLanguage(panel) {
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return normalizeLanguage(raw);
}

export function localizedEmsMode(language, mode) {
  const lang = normalizeLanguage(language);
  const number = Number(mode);
  const entry = EMS_MODE_TEXT[lang]?.[number] || EMS_MODE_TEXT.en[number];
  if (!entry) return { name: String(mode ?? "—"), tip: "" };
  return { name: entry[0], tip: entry[1] };
}

export function controllerCopy(language) {
  return normalizeLanguage(language) === "nl" ? NL : null;
}

export function localizeManualMessage(language, text) {
  if (normalizeLanguage(language) !== "nl") return String(text || "");
  const source = String(text || "");
  const modeMatch = source.match(/mode\s+(\d+)/i);
  const mode = modeMatch ? Number(modeMatch[1]) : null;
  const modeName = mode ? localizedEmsMode("nl", mode).name : "";
  const power = source.match(/ · (-?\d+(?:\.\d+)? W)/)?.[1] || "";

  if (/^Applying mode\s+/i.test(source) && mode) {
    return `Modus ${mode} toepassen · ${modeName}${power ? ` · ${power}` : ""}…`;
  }
  if (/^Requested mode\s+/i.test(source) && mode) {
    return `Modus ${mode} aangevraagd · ${modeName}${power ? ` · ${power}` : ""}. Wachten op Modbus-teruglezing.`;
  }
  if (/^Manual mode failed:/i.test(source)) {
    return source.replace(/^Manual mode failed:/i, "Handmatige modus mislukt:");
  }
  if (/^Manual power update failed:/i.test(source)) {
    return source.replace(
      /^Manual power update failed:/i,
      "Bijwerken handmatig vermogen mislukt:"
    );
  }
  return source;
}

function metricByLabel(card, labels) {
  for (const metric of card.querySelectorAll(".metric")) {
    const label = metric.querySelector(".metric-label")?.textContent?.trim();
    if (labels.includes(label)) return metric;
  }
  return null;
}

function replaceTrailingButtonText(button, text) {
  if (!button) return;
  const trailing = [...button.childNodes]
    .reverse()
    .find((node) => node.nodeType === 3);
  if (trailing) trailing.textContent = ` ${text}`;
  else button.insertAdjacentText("beforeend", ` ${text}`);
}

function localizeStrategyProfiles(panel, root) {
  const strategy = root.querySelector(".ep-v038-strategy");
  if (!strategy) return;
  const profiles = canonicalProfiles(
    "nl",
    panel.__epV038BatterySaver?.data?.modes || []
  );
  const byKey = new Map(profiles.map((profile) => [profile.key, profile]));
  for (const button of strategy.querySelectorAll("[data-ep-v038-profile]")) {
    const profile = byKey.get(button.dataset.epV038Profile);
    if (!profile) continue;
    const label = button.querySelector("strong");
    const description = button.querySelector("small");
    if (label) label.textContent = profile.label;
    if (description) description.textContent = profile.description;
  }
}

function localizeManualPad(panel, card, t) {
  const pad = card.querySelector(".ep-v021-manual-pad");
  if (!pad) return;

  const automaticOn = panel._stateByKey?.("automatic_control")?.state === "on";
  const controlsReady = Boolean(
    panel._entityId?.("manual_mode") && panel._entityId?.("manual_power")
  );
  const mode = Number(panel._stateByKey?.("ems_mode")?.state);

  const kicker = pad.querySelector(".ep-v021-manual-kicker");
  const title = pad.querySelector(".ep-v021-manual-title");
  const state = pad.querySelector(".ep-v021-manual-state");
  const powerLabel = pad.querySelector(".ep-v021-power-label span");
  const slider = pad.querySelector(".ep-v021-power-slider");
  if (kicker) kicker.textContent = t.manualKicker;
  if (title) title.textContent = t.manualTitle;
  if (state) {
    state.textContent = automaticOn
      ? t.lockedAutomatic
      : controlsReady
        ? t.manualReady
        : t.entitiesMissing;
  }
  if (powerLabel) powerLabel.textContent = t.manualSetpoint;
  if (slider) slider.setAttribute("aria-label", t.manualSetpointAria);

  for (const button of pad.querySelectorAll(".ep-v021-mode-button")) {
    const buttonMode = Number(button.dataset.mode);
    const localized = localizedEmsMode("nl", buttonMode);
    const tip = `${buttonMode} · ${localized.name} — ${localized.tip}`;
    button.dataset.tip = tip;
    button.setAttribute("aria-label", tip);
  }

  const note = pad.querySelector("[data-manual-note]");
  if (!note) return;
  if (automaticOn) {
    note.innerHTML = `<strong>${panel._escape(t.automaticOwner)}</strong> ${panel._escape(t.automaticOwnerDetail)}`;
    return;
  }

  if (!controlsReady) {
    note.innerHTML = `<strong>${panel._escape(t.manualUnavailable)}</strong> ${panel._escape(t.manualUnavailableDetail)}`;
    return;
  }

  const message = panel.__epV021ManualMessage?.text;
  if (message) {
    note.textContent = localizeManualMessage("nl", message);
    return;
  }

  const localized = Number.isFinite(mode) ? localizedEmsMode("nl", mode) : null;
  const actualSetpoint = Number(panel._stateByKey?.("ems_setpoint")?.state);
  note.innerHTML = `<strong>${panel._escape(t.live)}:</strong> modus ${panel._escape(Number.isFinite(mode) ? mode : "—")}${localized ? ` · ${panel._escape(localized.name)}` : ""} · ${panel._escape(Number.isFinite(actualSetpoint) ? `${Math.round(actualSetpoint)} W` : "—")}. ${panel._escape(t.hoverHint)}`;
}

function localizeControllerMetrics(panel, card, t) {
  const modeState = panel._stateByKey?.("ems_mode");
  const mode = Number(modeState?.state);
  const modeMetric = metricByLabel(card, ["EMS mode", "EMS-modus"]);
  if (modeMetric) {
    const label = modeMetric.querySelector(".metric-label");
    const value = modeMetric.querySelector(".metric-value");
    if (label) label.textContent = t.emsMode;
    if (value) {
      const stateText = modeState?.state || "—";
      const localized = Number.isFinite(mode)
        ? localizedEmsMode("nl", mode).name
        : modeState?.attributes?.mode_name || "Onbekend";
      value.textContent = `${stateText} · ${localized}`;
    }
  }

  const setpointMetric = metricByLabel(card, ["EMS setpoint", "EMS-setpoint"]);
  const setpointLabel = setpointMetric?.querySelector(".metric-label");
  if (setpointLabel) setpointLabel.textContent = t.emsSetpoint;

  const targetMetric = metricByLabel(card, [
    "EnergyPilot target",
    "PCC target",
    "Battery target",
    "Control target",
    "PCC-doel",
    "Batterijdoel",
    "Regeldoel",
  ]);
  const targetLabel = targetMetric?.querySelector(".metric-label");
  if (targetLabel) {
    const command = String(panel._stateByKey?.("control_command")?.state || "");
    targetLabel.textContent = command.startsWith("grid_") || command === "goodwe_auto"
      ? t.pccTarget
      : command.startsWith("battery_") || command.startsWith("ev_")
        ? t.batteryTarget
        : t.controlTarget;
  }
}

export function localizeV038Controller(panel, root) {
  if (!root || dashboardLanguage(panel) !== "nl") return;
  const card = root.querySelector(".panel-card.controller");
  if (!card) return;
  const t = NL;

  const windowLabel = card.querySelector(".ep-v031-card-windowlabel");
  const kicker = card.querySelector(".section-title-row .card-kicker");
  const title = card.querySelector(".section-title-row h2");
  const autoButton = card.querySelector("#auto-toggle");
  const automaticOn = panel._stateByKey?.("automatic_control")?.state === "on";
  const safety = card.querySelector(".safety-note");
  const refresh = card.querySelector(".ep-v013-refresh");

  if (windowLabel) windowLabel.textContent = t.windowLabel;
  if (kicker) kicker.textContent = t.kicker;
  if (title) title.textContent = t.title;
  replaceTrailingButtonText(autoButton, automaticOn ? t.automaticOn : t.automaticOff);
  if (safety) safety.textContent = t.safety;
  if (refresh) {
    refresh.textContent = String(refresh.textContent || "").replace(
      /^telemetry\b/i,
      t.telemetry
    );
  }

  localizeControllerMetrics(panel, card, t);
  localizeStrategyProfiles(panel, root);
  localizeManualPad(panel, card, t);

  const strategyNote = card.querySelector(".ep-v022-strategy-note");
  if (strategyNote?.dataset.epReleasePresentationOwner !== "v048-hybrid") {
    strategyNote.innerHTML = `<strong>${panel._escape(t.strategyLabel)}:</strong> ${panel._escape(t.strategy)}`;
  }
}
