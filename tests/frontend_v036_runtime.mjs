import test from "node:test";
import assert from "node:assert/strict";

import {
  flowAnimationDirections,
  relevantStateObjectsChanged,
  uiContextSignature,
} from "../custom_components/gw_energypilot/frontend/gw-energy-pilot-v036-runtime.js";

test("flow directions match the rendered dashboard geometry", () => {
  assert.deepEqual(
    flowAnimationDirections({ pv: 3200, grid: 900, house: 1200, battery: 1800 }),
    { pv: "normal", grid: "normal", house: "reverse", battery: "reverse" }
  );
  assert.deepEqual(
    flowAnimationDirections({ pv: 3200, grid: -900, house: 1200, battery: -1800 }),
    { pv: "normal", grid: "reverse", house: "reverse", battery: "normal" }
  );
});

test("flow directions become idle inside the threshold", () => {
  assert.deepEqual(
    flowAnimationDirections({ pv: 49, grid: -49, house: 0, battery: null }),
    { pv: null, grid: null, house: null, battery: null }
  );
});

test("unrelated Home Assistant state objects do not request a render", () => {
  const relevant = { state: "123" };
  const previous = {
    "sensor.gw_power": relevant,
    "sensor.unrelated": { state: "old" },
  };
  const next = {
    "sensor.gw_power": relevant,
    "sensor.unrelated": { state: "new" },
  };
  assert.equal(
    relevantStateObjectsChanged(previous, next, ["sensor.gw_power"]),
    false
  );
});

test("a relevant Home Assistant state replacement requests a render", () => {
  const previous = { "sensor.gw_power": { state: "123" } };
  const next = { "sensor.gw_power": { state: "124" } };
  assert.equal(
    relevantStateObjectsChanged(previous, next, ["sensor.gw_power"]),
    true
  );
});

test("UI context comparison uses stable primitive values", () => {
  const first = {
    locale: { language: "nl", number_format: "comma_decimal" },
    user: { id: "abc", is_admin: true },
    themes: { darkMode: true },
    selectedTheme: { theme: "default" },
  };
  const equivalent = {
    locale: { language: "nl", number_format: "comma_decimal" },
    user: { id: "abc", is_admin: true },
    themes: { darkMode: true },
    selectedTheme: { theme: "default" },
  };
  assert.equal(uiContextSignature(first), uiContextSignature(equivalent));
});
