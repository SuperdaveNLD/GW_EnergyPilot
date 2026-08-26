import assert from "node:assert/strict";
import {
  canonicalProfiles,
} from "../custom_components/gw_energypilot/frontend/gw-energy-pilot-v038-model.js";
import {
  controllerCopy,
  localizedEmsMode,
  localizeManualMessage,
} from "../custom_components/gw_energypilot/frontend/gw-energy-pilot-v038-i18n.js";

const dutch = controllerCopy("nl-NL");
assert.equal(dutch.windowLabel, "Regelaar");
assert.equal(dutch.kicker, "ENERGYPILOT REGELING");
assert.equal(dutch.manualKicker, "HANDMATIGE EMS-TEST");
assert.equal(dutch.manualTitle, "GoodWe-modi 1–12");
assert.equal(dutch.telemetry, "telemetrie");
assert.equal(controllerCopy("en-US"), null);

const discharge = localizedEmsMode("nl", 12);
assert.equal(discharge.name, "Batterijontlaadvermogen");
assert.match(discharge.tip, /omvormer\/BMS-limieten/);
assert.equal(localizedEmsMode("en", 12).name, "Battery discharge power");

assert.equal(
  localizeManualMessage(
    "nl",
    "Applying mode 12 · Battery discharge power · 15000 W…"
  ),
  "Modus 12 toepassen · Batterijontlaadvermogen · 15000 W…"
);
assert.equal(
  localizeManualMessage(
    "nl",
    "Requested mode 11 · Battery charge power · 12000 W. Waiting for Modbus read-back."
  ),
  "Modus 11 aangevraagd · Batterijlaadvermogen · 12000 W. Wachten op Modbus-teruglezing."
);
assert.equal(
  localizeManualMessage("nl", "Manual mode failed: write timeout"),
  "Handmatige modus mislukt: write timeout"
);

const backendEnglishModes = [
  {
    key: "mad_steve",
    label: "Mad-Steve",
    description: "English backend Mad-Steve description",
  },
  {
    key: "gold_rush",
    label: "Gold Rush",
    description: "English backend Gold Rush description",
  },
  {
    key: "balanced",
    label: "Balanced",
    description: "English backend Balanced description",
  },
  {
    key: "battery_saver",
    label: "Battery Saver",
    description: "English backend Battery Saver description",
  },
];
const localizedProfiles = canonicalProfiles("nl", backendEnglishModes);
assert.equal(localizedProfiles.find((item) => item.key === "balanced").label, "Gebalanceerd");
assert.equal(
  localizedProfiles.find((item) => item.key === "battery_saver").label,
  "Batterijbesparing"
);
assert.doesNotMatch(
  localizedProfiles.find((item) => item.key === "mad_steve").description,
  /English backend/
);
assert.doesNotMatch(
  localizedProfiles.find((item) => item.key === "gold_rush").description,
  /English backend/
);

console.log("v0.38 Dutch controller localization tests passed");
