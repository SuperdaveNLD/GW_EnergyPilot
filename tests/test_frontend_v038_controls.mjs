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
assert.equal(english.length, 6);
assert.equal(dutch.length, 6);
assert.equal(english[2].label, "Chargegasm");
assert.equal(dutch[2].label, "Chargegasm");
assert.equal(english[4].label, "Battery Saver");
assert.equal(dutch[4].label, "Batterijbesparing");
assert.equal(english[5].label, "Custom");
assert.equal(dutch[5].label, "Aangepast");

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

class FakeInput extends FakeElement {
  constructor(key, value) {
    super();
    this.dataset = { epV038CustomValue: key };
    this.value = String(value);
  }
}

class FakeForm extends FakeElement {
  constructor(inputs) {
    super();
    this.inputs = inputs;
  }

  matches(selector) {
    return selector === "form[data-ep-v038-custom-form]";
  }

  querySelectorAll(selector) {
    return selector === "[data-ep-v038-custom-value]" ? this.inputs : [];
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
  new FakeButton("chargegasm", "CHARGEGASM"),
  new FakeButton("balanced", "VOLLEDIG ANDERE ZICHTBARE TEKST"),
  new FakeButton("battery_saver", "BATTERIJBESPARING"),
  new FakeButton("custom", "AANGEPAST"),
];
const root = new FakeRoot(buttons);
const calls = [];
let renders = 0;
let targetedRefreshes = 0;
const modes = PROFILE_KEYS.map((key) => ({ key }));
const panel = {
  shadowRoot: root,
  __epV041StableRuntime: true,
  _escape(value) {
    return String(value ?? "");
  },
  _queueRender() {
    renders += 1;
  },
  __epV041RefreshStrategy() {
    targetedRefreshes += 1;
    const cache = this.__epV038BatterySaver;
    const activeMode = cache.pendingMode || cache.data?.mode || null;
    for (const button of buttons) {
      button.disabled = Boolean(cache.busy || cache.loading || !cache.data);
      button.setAttribute(
        "aria-pressed",
        button.dataset.epV038Profile === activeMode ? "true" : "false"
      );
    }
  },
  _hass: {
    async callWS(request) {
      calls.push(request);
      if (request.type === "gw_energypilot/battery_saver/custom_set") {
        return {
          entry_id: "entry-1",
          managed: false,
          mode: null,
          modes,
          battery_count: 1,
          current_emhass_values: request.values,
        };
      }
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
assert.equal(root.listeners.size, 4);

let prevented = false;
root.listeners.get("click")({
  composedPath: () => [buttons[4]],
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
assert.equal(targetedRefreshes >= 2, true);
assert.equal(renders, 0);
assert.equal(buttons.every((button) => button.disabled === false), true);
assert.deepEqual(
  buttons
    .filter((button) => button.attributes.get("aria-pressed") === "true")
    .map((button) => button.dataset.epV038Profile),
  ["battery_saver"]
);

// Older v0.38-v0.40 entrypoints retain their full-render fallback. The fake
// panel cannot rebuild the DOM, so this branch validates the queued render and
// service request rather than duplicating the real renderer in the unit test.
panel.__epV041StableRuntime = false;
root.listeners.get("click")({
  composedPath: () => [buttons[3]],
  preventDefault: () => {},
});
await new Promise((resolve) => setTimeout(resolve, 0));
assert.equal(calls.length, 2);
assert.equal(calls[1].mode, "balanced");
assert.equal(renders >= 2, true);

buttons[1].disabled = true;
root.listeners.get("click")({
  composedPath: () => [buttons[1]],
  preventDefault: () => {},
});
await new Promise((resolve) => setTimeout(resolve, 0));
assert.equal(calls.length, 2);

panel.__epV041StableRuntime = true;
panel.__epV038BatterySaver.data = {
  ...panel.__epV038BatterySaver.data,
  managed: false,
  mode: null,
  battery_count: 1,
};
const customInputs = [
  new FakeInput("battery_soc_deficit_cost", 0.001111),
  new FakeInput("battery_soc_surplus_cost", 0.002222),
  new FakeInput("battery_stress_cost", 0.003333),
  new FakeInput("weight_battery_charge", 0.004444),
  new FakeInput("weight_battery_discharge", 0.005555),
];
const customForm = new FakeForm(customInputs);
let submitPrevented = false;
root.listeners.get("submit")({
  composedPath: () => [customForm],
  preventDefault: () => {
    submitPrevented = true;
  },
});
await new Promise((resolve) => setTimeout(resolve, 0));
assert.equal(submitPrevented, true);
assert.equal(calls.length, 3);
assert.equal(calls[2].type, "gw_energypilot/battery_saver/custom_set");
assert.equal(calls[2].entry_id, "entry-1");
assert.deepEqual(calls[2].values, {
  battery_soc_deficit_cost: 0.001111,
  battery_soc_surplus_cost: 0.002222,
  battery_stress_cost: 0.003333,
  weight_battery_charge: 0.004444,
  weight_battery_discharge: 0.005555,
});
assert.equal(panel.__epV038BatterySaver.data.managed, false);

console.log("v0.38 delegated profile control tests passed");
