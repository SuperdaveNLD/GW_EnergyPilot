import assert from "node:assert/strict";
import {
  CUSTOM_MODE,
  flowMotionMap,
  localizedProfile,
  normalizeLanguage,
  resolveHousePower,
} from "../custom_components/gw_energypilot/frontend/gw-energy-pilot-v038-model.js";

assert.equal(CUSTOM_MODE, "custom");
assert.equal(normalizeLanguage("nl-NL"), "nl");
assert.equal(normalizeLanguage("en-GB"), "en");
assert.equal(localizedProfile("nl", { key: "battery_saver" }).label, "Batterijbesparing");
assert.equal(localizedProfile("en", { key: "battery_saver" }).label, "Battery Saver");
assert.equal(localizedProfile("nl", { key: "custom" }).label, "Aangepast");

assert.equal(resolveHousePower(-500, 2000, 500, 0), 1500);
assert.equal(resolveHousePower(null, 2000, 500, -500), 1000);
assert.equal(resolveHousePower(900, 1500, -400, -1200), 900);

assert.deepEqual(
  flowMotionMap({ pv: 1500, grid: -400, house: 900, battery: -1200 }),
  { pv: "right", grid: "left", house: "up", battery: "down" }
);
assert.deepEqual(
  flowMotionMap({ pv: 1500, grid: 400, house: 900, battery: 1200 }),
  { pv: "right", grid: "right", house: "up", battery: "up" }
);
assert.deepEqual(
  flowMotionMap({ pv: 2000, grid: 500, house: -500, battery: 0 }),
  { pv: "right", grid: "right", house: "up", battery: "idle" }
);
assert.deepEqual(
  flowMotionMap({ pv: 0, grid: 0, house: 0, battery: 0 }),
  { pv: "idle", grid: "idle", house: "idle", battery: "idle" }
);

console.log("v0.38 frontend model tests passed");
