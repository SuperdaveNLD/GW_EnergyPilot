import assert from "node:assert/strict";
import {
  CUSTOM_MODE,
  flowMotionMap,
  flowVisualMap,
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

assert.deepEqual(
  flowVisualMap({ pv: 4800, grid: 1100, house: 2500, battery: -1200 }),
  {
    pv: { direction: "right", status: "active", intensity: "high", power: 4800 },
    grid: { direction: "right", status: "active", intensity: "low", power: 1100 },
    house: { direction: "up", status: "active", intensity: "medium", power: 2500 },
    battery: { direction: "down", status: "active", intensity: "low", power: -1200 },
  }
);
assert.deepEqual(
  flowVisualMap({ pv: null, grid: 49, house: null, battery: -49 }),
  {
    pv: { direction: "idle", status: "unknown", intensity: "none", power: null },
    grid: { direction: "idle", status: "idle", intensity: "none", power: 49 },
    house: { direction: "idle", status: "unknown", intensity: "none", power: null },
    battery: { direction: "idle", status: "idle", intensity: "none", power: -49 },
  }
);
assert.equal(
  flowVisualMap({ pv: 1500, grid: -400, house: 900, battery: 1200 }).grid.direction,
  "left"
);
assert.equal(
  flowVisualMap({ pv: 1500, grid: -400, house: 900, battery: 1200 }).battery.direction,
  "up"
);

console.log("v0.38 frontend model tests passed");
