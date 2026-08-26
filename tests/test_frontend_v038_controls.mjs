import assert from "node:assert/strict";
import {
  PROFILE_KEYS,
  canonicalProfiles,
} from "../custom_components/gw_energypilot/frontend/gw-energy-pilot-v038-model.js";

const english = canonicalProfiles("en", []);
const dutch = canonicalProfiles("nl", []);
assert.deepEqual(
  english.map((profile) => profile.key),
  [...PROFILE_KEYS, "custom"]
);
assert.deepEqual(
  dutch.map((profile) => profile.key),
  [...PROFILE_KEYS, "custom"]
);
assert.equal(english.length, 5);
assert.equal(dutch.length, 5);
assert.equal(english[3].label, "Battery Saver");
assert.equal(dutch[3].label, "Batterijbesparing");
assert.equal(english[4].label, "Custom");
assert.equal(dutch[4].label, "Aangepast");

class FakeElement {}
globalThis.Element = FakeElement;
globalThis.HTMLElement = FakeElement;

class FakeButton extends FakeElement {
  constructor(mode, visibleText) {
    super();
    this.dataset = { epV038Profile: mode };
    this.textContent = visibleText;
    this.disabled = false;
    this.attributes = new Map();
    this.badgeInserted = false;
  }

  matches(selector) {
    return selector === "button[data-ep-v038-profile]";
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  querySelector() {
    return null;
  }

  insertAdjacentHTML() {
    this.badgeInserted = true;
  }
}

class FakeRoot {
  constructor(buttons) {
    this.buttons = buttons;
    this.listeners = new Map();
  }

  addEventListener(type, listener) {
    this.listeners.set(type, listener);
  }

  querySelectorAll(selector) {
    return selector === "[data-ep-v038-profile]" ? this.buttons : [];
  }

  querySelector() {
    return null;
  }
}

const buttons = [
  new FakeButton("mad_steve", "MAD-STEVE ACTIEF"),
  new FakeButton("gold_rush", "GOUDKOORTS"),
  new FakeButton("balanced", "VOLLEDIG ANDERE ZICHTBARE TEKST"),
  new FakeButton("battery_saver", "BATTERIJBESPARING"),
  new FakeButton("custom", "AANGEPAST"),
];
const root = new FakeRoot(buttons);
const calls = [];
let renders = 0;
const modes = PROFILE_KEYS.map((key) => ({ key }));
const panel = {
  shadowRoot: root,
  _escape(value) {
    return String(value ?? "");
  },
  _queueRender() {
    renders += 1;
  },
  _hass: {
    async callWS(request) {
      calls.push(request);
      return {
        entry_id: "entry-1",
        managed: true,
        mode: request.mode,
        modes,
        current_emhass_values: {},
      };
    },
  },
  __epV038BatterySaver: {
    data: {
      entry_id: "entry-1",
      managed: true,
      mode: "mad_steve",
      modes,
      current_emhass_values: {},
    },
    loading: false,
    busy: false,
    pendingMode: null,
    message: "",
    tone: "",
    error: null,
  },
};

const { installV038DelegatedControls } = await import(
  "../custom_components/gw_energypilot/frontend/gw-energy-pilot-v038-strategy.js"
);
installV038DelegatedControls(panel, root);
installV038DelegatedControls(panel, root);
assert.equal(root.listeners.size, 3);

let prevented = false;
root.listeners.get("click")({
  composedPath: () => [buttons[3]],
  preventDefault: () => {
    prevented = true;
  },
});
await new Promise((resolve) => setTimeout(resolve, 0));

assert.equal(prevented, true);
assert.equal(calls.length, 1);
assert.equal(calls[0].type, "gw_energypilot/battery_saver/set");
assert.equal(calls[0].entry_id, "entry-1");
assert.equal(calls[0].mode, "battery_saver");
assert.equal(renders >= 2, true);
assert.equal(buttons.every((button) => button.disabled === false), true);
assert.deepEqual(
  buttons
    .filter((button) => button.attributes.get("aria-pressed") === "true")
    .map((button) => button.dataset.epV038Profile),
  ["battery_saver"]
);

buttons[1].disabled = true;
root.listeners.get("click")({
  composedPath: () => [buttons[1]],
  preventDefault: () => {},
});
await new Promise((resolve) => setTimeout(resolve, 0));
assert.equal(calls.length, 1);

console.log("v0.38 delegated profile control tests passed");
