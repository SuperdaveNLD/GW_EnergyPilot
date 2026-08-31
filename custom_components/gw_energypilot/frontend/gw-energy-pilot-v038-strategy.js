import {
  CUSTOM_MODE,
  PROFILE_KEYS,
  canonicalProfiles,
  normalizeLanguage,
} from "./gw-energy-pilot-v038-model.js?v=1.1.1-stable1";

const TEXT = {
  en: {
    kicker: "CHARGING STRATEGY",
    title: "Battery strategy",
    description:
      "Choose how EnergyPilot should value battery use. A profile change updates EMHASS and immediately builds a fresh plan.",
    active: "ACTIVE",
    applying: "Applying profile and optimizing…",
    applied: "Profile applied · fresh plan published.",
    savingCustom: "Saving custom values and optimizing…",
    savedCustom: "Custom values saved · fresh plan published.",
    saveCustom: "Save and optimize",
    loading: "Loading battery profiles…",
    customTitle: "Custom battery settings",
    managedTitle: "Managed profile limits",
    hardRange: "Hard SOC range",
    comfortRange: "Comfort zone",
    lowCost: "Low-SOC cost",
    highCost: "High-SOC cost",
    stressCost: "Power stress",
    antiChurn: "Charge/discharge anti-churn",
    customNote:
      "SOC sliders use the existing Home Assistant entities. Minimum SOC remains synchronized with the GoodWe on-grid battery floor. Enter non-negative custom EMHASS costs below, then save once to build a fresh plan.",
    minimum: "Minimum SOC",
    maximum: "Maximum SOC",
    deficit: "Low-SOC cost",
    surplus: "High-SOC cost",
    stress: "Power stress",
    chargeWeight: "Charge cost",
    dischargeWeight: "Discharge cost",
    diagnostics: "Low-level controller command is available in Diagnostics.",
    socError: "Battery SOC update failed",
    customError: "Custom values could not be saved",
    singleBatteryOnly: "Custom value editing is available for one EMHASS battery.",
  },
  nl: {
    kicker: "LAADSTRATEGIE",
    title: "Batterijstrategie",
    description:
      "Kies hoe EnergyPilot batterijgebruik waardeert. Een profielwijziging past EMHASS aan en bouwt direct een nieuw plan.",
    active: "ACTIEF",
    applying: "Profiel toepassen en optimaliseren…",
    applied: "Profiel toegepast · nieuw plan gepubliceerd.",
    savingCustom: "Aangepaste waarden opslaan en optimaliseren…",
    savedCustom: "Aangepaste waarden opgeslagen · nieuw plan gepubliceerd.",
    saveCustom: "Opslaan en optimaliseren",
    loading: "Batterijprofielen laden…",
    customTitle: "Aangepaste batterijinstellingen",
    managedTitle: "Vaste profielgrenzen",
    hardRange: "Harde SOC-range",
    comfortRange: "Comfortzone",
    lowCost: "Kosten lage SOC",
    highCost: "Kosten hoge SOC",
    stressCost: "Vermogensstress",
    antiChurn: "Anti-pendel laden/ontladen",
    customNote:
      "De SOC-schuifregelaars gebruiken de bestaande Home Assistant-entiteiten. Minimum SOC blijft gekoppeld aan de GoodWe on-grid ondergrens. Vul hieronder niet-negatieve aangepaste EMHASS-kosten in en sla ze één keer op om een nieuw plan te maken.",
    minimum: "Minimum SOC",
    maximum: "Maximum SOC",
    deficit: "Kosten lage SOC",
    surplus: "Kosten hoge SOC",
    stress: "Vermogensstress",
    chargeWeight: "Laadkosten",
    dischargeWeight: "Ontlaadkosten",
    diagnostics: "Het technische controllercommando staat in Diagnostiek.",
    socError: "Bijwerken van batterij-SOC mislukt",
    customError: "Aangepaste waarden konden niet worden opgeslagen",
    singleBatteryOnly: "Aangepaste waarden kunnen voor één EMHASS-batterij worden bewerkt.",
  },
};

function language(panel) {
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return normalizeLanguage(raw);
}

function copy(panel) {
  return TEXT[language(panel)] || TEXT.en;
}

function batterySaverCache(panel) {
  panel.__epV038BatterySaver = panel.__epV038BatterySaver || {
    data: null,
    loading: false,
    busy: false,
    pendingMode: null,
    message: "",
    tone: "",
    error: null,
  };
  return panel.__epV038BatterySaver;
}

function shareBatterySaverData(panel, data) {
  panel.__epV031BSData = data;
  const cache = batterySaverCache(panel);
  cache.data = data;
  return data;
}

function requestStrategyRefresh(panel) {
  if (
    panel.__epV041StableRuntime &&
    typeof panel.__epV041RefreshStrategy === "function"
  ) {
    panel.__epV041RefreshStrategy();
    return;
  }
  panel._queueRender();
}

async function loadBatterySaver(panel, force = false) {
  const cache = batterySaverCache(panel);
  if (!panel._hass?.callWS || cache.loading || cache.busy) return;
  if (!force && cache.data) return;
  cache.loading = true;
  cache.error = null;
  requestStrategyRefresh(panel);
  try {
    shareBatterySaverData(panel, await panel._hass.callWS({
      type: "gw_energypilot/battery_saver/get",
    }));
  } catch (err) {
    cache.error = err?.message || String(err);
  } finally {
    cache.loading = false;
    requestStrategyRefresh(panel);
  }
}

function activeProfileMode(cache) {
  if (cache.pendingMode) return cache.pendingMode;
  if (!cache.data) return null;
  return cache.data.managed ? cache.data.mode : CUSTOM_MODE;
}

function numberModel(panel, key, fallback) {
  const entityId = panel._entityId?.(key);
  const state = entityId ? panel._state?.(entityId) : null;
  const value = Number(state?.state);
  return { entityId, value: Number.isFinite(value) ? value : fallback };
}

function stableConfigEntries(values) {
  return Object.entries(values || {}).sort(([left], [right]) =>
    left.localeCompare(right)
  );
}

function strategySignature(panel, cache) {
  const min = numberModel(panel, "emhass_minimum_soc", 0);
  const max = numberModel(panel, "emhass_maximum_soc", 100);
  return JSON.stringify({
    language: language(panel),
    activeMode: activeProfileMode(cache),
    busy: Boolean(cache.busy),
    loading: Boolean(cache.loading),
    error: cache.error || "",
    message: cache.message || "",
    tone: cache.tone || "",
    modes: PROFILE_KEYS,
    min: min.value,
    max: max.value,
    values: stableConfigEntries(cache.data?.current_emhass_values),
  });
}

function updateStrategyVisualState(panel, commitSignature = false) {
  const root = panel.shadowRoot;
  if (!root) return;
  const cache = batterySaverCache(panel);
  const activeMode = activeProfileMode(cache);
  const t = copy(panel);
  for (const button of root.querySelectorAll("[data-ep-v038-profile]")) {
    const active = button.dataset.epV038Profile === activeMode;
    button.setAttribute("aria-pressed", active ? "true" : "false");
    button.disabled = Boolean(cache.busy || cache.loading || !cache.data);
    const badge = button.querySelector(".ep-v038-badge");
    if (active && !badge) {
      button.insertAdjacentHTML(
        "afterbegin",
        `<span class="ep-v038-badge">${panel._escape(t.active)}</span>`
      );
    } else if (!active && badge) {
      badge.remove();
    }
  }
  const message = root.querySelector(".ep-v038-message");
  if (message) {
    message.className = `ep-v038-message ${cache.tone || ""}`;
    message.textContent =
      cache.error || cache.message || (!cache.data ? t.loading : "");
  }
  if (commitSignature) {
    const strategy = root.querySelector(".ep-v038-strategy");
    if (strategy) {
      strategy.dataset.epV038Signature = strategySignature(panel, cache);
    }
  }
}

async function selectProfile(panel, mode) {
  const cache = batterySaverCache(panel);
  if (!panel._hass?.callWS || cache.busy || cache.loading) return;
  if (!cache.data?.entry_id) await loadBatterySaver(panel, true);
  const entryId = cache.data?.entry_id;
  if (!entryId || cache.busy || cache.loading) return;

  const t = copy(panel);
  cache.busy = true;
  cache.pendingMode = mode;
  cache.message = t.applying;
  cache.tone = "";
  cache.error = null;
  requestStrategyRefresh(panel);

  try {
    shareBatterySaverData(panel, await panel._hass.callWS({
      type: "gw_energypilot/battery_saver/set",
      entry_id: entryId,
      mode,
    }));
    cache.message = t.applied;
    cache.tone = "ok";
  } catch (err) {
    cache.error = err?.message || String(err);
    cache.message = "";
    cache.tone = "error";
  } finally {
    cache.busy = false;
    cache.pendingMode = null;
    requestStrategyRefresh(panel);
  }
}

function displayConfigValue(value) {
  if (Array.isArray(value)) {
    return value.map((item) => displayConfigValue(item)).join(", ");
  }
  const number = Number(value);
  return Number.isFinite(number)
    ? String(Math.round(number * 1000000) / 1000000)
    : "—";
}

function inputConfigValue(value) {
  const raw = Array.isArray(value) ? value[0] : value;
  if (raw === null || raw === undefined || raw === "") return "";
  const number = Number(raw);
  return Number.isFinite(number) && number >= 0 ? displayConfigValue(number) : "";
}

function percent(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${number}%` : "—";
}

function managedProfileHtml(panel, t, mode) {
  if (!mode) return "";
  const hard = `${percent(mode.minimum_soc_pct)} – ${percent(mode.maximum_soc_pct)}`;
  const comfort = `${percent(mode.deficit_threshold_pct)} – ${percent(mode.surplus_threshold_pct)}`;
  return `
    <div class="ep-v038-managed">
      <div class="ep-v038-custom-head">${panel._escape(t.managedTitle)}</div>
      <div class="ep-v038-managed-grid">
        <span>${panel._escape(t.hardRange)} <strong>${panel._escape(hard)}</strong></span>
        <span>${panel._escape(t.comfortRange)} <strong>${panel._escape(comfort)}</strong></span>
        <span>${panel._escape(t.lowCost)} <strong>${panel._escape(percent(mode.deficit_cost_factor_pct))}</strong></span>
        <span>${panel._escape(t.highCost)} <strong>${panel._escape(percent(mode.surplus_cost_factor_pct))}</strong></span>
        <span>${panel._escape(t.stressCost)} <strong>${panel._escape(percent(mode.stress_cost_factor_pct))}</strong></span>
        <span>${panel._escape(t.antiChurn)} <strong>${panel._escape(percent(mode.anti_churn_cost_factor_pct))}</strong></span>
      </div>
    </div>`;
}

function customSocHtml(panel, t, data, busy) {
  const min = numberModel(panel, "emhass_minimum_soc", 0);
  const max = numberModel(panel, "emhass_maximum_soc", 100);
  const values = data?.current_emhass_values || {};
  const fields = [
    ["battery_soc_deficit_cost", t.deficit, values.battery_soc_deficit_cost],
    ["battery_soc_surplus_cost", t.surplus, values.battery_soc_surplus_cost],
    ["battery_stress_cost", t.stress, values.battery_stress_cost],
    ["weight_battery_charge", t.chargeWeight, values.weight_battery_charge],
    ["weight_battery_discharge", t.dischargeWeight, values.weight_battery_discharge],
  ];
  const editable = data?.battery_count === 1;
  return `
    <div class="ep-v038-custom">
      <div class="ep-v038-custom-head">${panel._escape(t.customTitle)}</div>
      <div class="ep-v038-custom-grid">
        <div class="ep-v038-soc">
          <div class="ep-v038-soc-label"><span>${panel._escape(t.minimum)}</span><strong data-ep-v038-soc-value="min">${Math.round(min.value)}%</strong></div>
          <input data-ep-v038-soc="min" type="range" min="0" max="100" step="1" value="${min.value}" ${min.entityId ? "" : "disabled"}>
        </div>
        <div class="ep-v038-soc">
          <div class="ep-v038-soc-label"><span>${panel._escape(t.maximum)}</span><strong data-ep-v038-soc-value="max">${Math.round(max.value)}%</strong></div>
          <input data-ep-v038-soc="max" type="range" min="0" max="100" step="1" value="${max.value}" ${max.entityId ? "" : "disabled"}>
        </div>
      </div>
      <form data-ep-v038-custom-form>
        <div class="ep-v038-custom-values">
          ${fields
            .map(
              ([key, label, value]) => `
                <label class="ep-v038-custom-value">
                  <span>${panel._escape(label)}</span>
                  <input type="number" inputmode="decimal" min="0" step="0.000001" required
                    data-ep-v038-custom-value="${panel._escape(key)}"
                    value="${panel._escape(inputConfigValue(value))}"
                    ${busy || !editable ? "disabled" : ""}>
                </label>`
            )
            .join("")}
        </div>
        <div class="ep-v038-custom-actions">
          <button type="submit" class="ep-v038-custom-save" ${busy || !editable ? "disabled" : ""}>${panel._escape(busy ? t.savingCustom : t.saveCustom)}</button>
        </div>
      </form>
      <div class="ep-v038-custom-note">${panel._escape(editable ? t.customNote : t.singleBatteryOnly)}</div>
    </div>`;
}

async function saveCustomValues(panel, form) {
  const cache = batterySaverCache(panel);
  if (!panel._hass?.callWS || cache.busy || cache.loading || !form) return;
  const entryId = cache.data?.entry_id;
  if (!entryId) return;

  const values = {};
  for (const input of form.querySelectorAll("[data-ep-v038-custom-value]")) {
    const value = Number(input.value);
    if (!Number.isFinite(value) || value < 0) {
      input.reportValidity?.();
      return;
    }
    values[input.dataset.epV038CustomValue] = value;
  }

  const t = copy(panel);
  cache.busy = true;
  cache.message = t.savingCustom;
  cache.tone = "";
  cache.error = null;
  requestStrategyRefresh(panel);
  try {
    shareBatterySaverData(panel, await panel._hass.callWS({
      type: "gw_energypilot/battery_saver/custom_set",
      entry_id: entryId,
      values,
    }));
    cache.message = t.savedCustom;
    cache.tone = "ok";
  } catch (err) {
    cache.error = `${t.customError}: ${err?.message || String(err)}`;
    cache.message = "";
    cache.tone = "error";
  } finally {
    cache.busy = false;
    requestStrategyRefresh(panel);
  }
}

async function updateSoc(panel, input) {
  if (!input || input.disabled) return;
  const kind = input.dataset.epV038Soc;
  const key = kind === "min" ? "emhass_minimum_soc" : "emhass_maximum_soc";
  const ref = numberModel(panel, key, kind === "min" ? 0 : 100);
  if (!ref.entityId) return;
  const requestedValue = Number(input.value);
  input.dataset.epSocDraft = String(requestedValue);
  input.disabled = true;
  try {
    await panel._hass.callService("number", "set_value", {
      entity_id: ref.entityId,
      value: requestedValue,
    });
  } catch (err) {
    delete input.dataset.epSocDraft;
    const t = copy(panel);
    window.alert(`${t.socError}: ${err?.message || err}`);
  } finally {
    input.disabled = false;
    requestStrategyRefresh(panel);
  }
}

function eventElement(event, selector) {
  for (const node of event.composedPath()) {
    if (node instanceof Element && node.matches(selector)) return node;
  }
  return null;
}

export function installV038DelegatedControls(panel, root) {
  if (panel.__epControlSurfaceArchitecture) return;
  if (panel.__epV038DelegatedControlsInstalled) return;
  panel.__epV038DelegatedControlsInstalled = true;

  root.addEventListener(
    "click",
    (event) => {
      const button = eventElement(event, "button[data-ep-v038-profile]");
      if (!button || button.disabled) return;
      event.preventDefault();
      void selectProfile(panel, button.dataset.epV038Profile);
    },
    true
  );

  root.addEventListener(
    "submit",
    (event) => {
      const form = eventElement(event, "form[data-ep-v038-custom-form]");
      if (!form) return;
      event.preventDefault();
      void saveCustomValues(panel, form);
    },
    true
  );

  root.addEventListener(
    "input",
    (event) => {
      const input = eventElement(event, "input[data-ep-v038-soc]");
      if (!input) return;
      input.dataset.epSocDraft = input.value;
      const label = root.querySelector(
        `[data-ep-v038-soc-value="${input.dataset.epV038Soc}"]`
      );
      if (label) label.textContent = `${input.value}%`;
    },
    true
  );

  root.addEventListener(
    "change",
    (event) => {
      const input = eventElement(event, "input[data-ep-v038-soc]");
      if (input) void updateSoc(panel, input);
    },
    true
  );
}

function removeLowLevelCommand(card) {
  for (const metric of card.querySelectorAll(".metric")) {
    const label = metric
      .querySelector(".metric-label")
      ?.textContent?.trim()
      .toLowerCase();
    if (label === "command" || label === "commando") metric.remove();
  }
}

function renderCustomerStrategy(panel, wrap, cache) {
  const signature = strategySignature(panel, cache);
  if (wrap.dataset.epV038Signature === signature) return;

  const t = copy(panel);
  const activeMode = activeProfileMode(cache);
  const modes = canonicalProfiles(language(panel), cache.data?.modes || []);
  const activeProfile = modes.find((mode) => mode.key === activeMode);
  const controlsDisabled = Boolean(cache.busy || cache.loading || !cache.data);

  wrap.innerHTML = `
    <div>
      <div class="ep-v038-kicker">${panel._escape(t.kicker)}</div>
      <div class="ep-v038-title">${panel._escape(t.title)}</div>
      <div class="ep-v038-description">${panel._escape(t.description)}</div>
    </div>
    <div class="ep-v038-profile-grid" role="group" aria-label="${panel._escape(t.title)}">
      ${modes
        .map(
          (mode) => `
            <button type="button" class="ep-v038-profile" data-ep-v038-profile="${panel._escape(mode.key)}" aria-pressed="${activeMode === mode.key ? "true" : "false"}" ${controlsDisabled ? "disabled" : ""}>
              ${activeMode === mode.key ? `<span class="ep-v038-badge">${panel._escape(t.active)}</span>` : ""}
              <strong>${panel._escape(mode.label)}</strong>
              <small>${panel._escape(mode.description)}</small>
              ${mode.key === CUSTOM_MODE ? "" : `<span class="ep-v038-profile-range">SOC ${panel._escape(percent(mode.minimum_soc_pct))} – ${panel._escape(percent(mode.maximum_soc_pct))}</span>`}
            </button>`
        )
        .join("")}
    </div>
    ${activeMode === CUSTOM_MODE ? customSocHtml(panel, t, cache.data, cache.busy) : managedProfileHtml(panel, t, activeProfile)}
    <div class="ep-v038-message ${panel._escape(cache.tone || "")}">${panel._escape(cache.error || cache.message || (!cache.data || cache.loading ? t.loading : ""))}</div>
    <div class="ep-v038-diagnostic-note">${panel._escape(t.diagnostics)}</div>`;
  wrap.dataset.epV038Signature = signature;
}

export function installV038CustomerStrategy(panel, root, reusableStrategy = null) {
  if (panel.__epControlSurfaceArchitecture) return null;
  const card = root.querySelector(".panel-card.controller");
  if (!card) return null;
  removeLowLevelCommand(card);

  const cache = batterySaverCache(panel);
  if (!cache.data && !cache.loading && !cache.error) {
    queueMicrotask(() => loadBatterySaver(panel));
  }

  const wrap =
    reusableStrategy instanceof HTMLElement
      ? reusableStrategy
      : root.querySelector(".ep-v038-strategy") || document.createElement("section");
  wrap.className = "ep-v038-strategy";
  wrap.setAttribute("translate", "no");
  renderCustomerStrategy(panel, wrap, cache);

  const manualPad = card.querySelector(".ep-v021-manual-pad");
  if (manualPad) card.insertBefore(wrap, manualPad);
  else card.appendChild(wrap);

  panel.__epV041RefreshStrategy = () => {
    const currentRoot = panel.shadowRoot;
    const currentWrap = currentRoot?.querySelector(".ep-v038-strategy");
    if (!currentWrap) return;
    renderCustomerStrategy(panel, currentWrap, batterySaverCache(panel));
    updateStrategyVisualState(panel, true);
    panel.__epV041FreezeMotion?.();
  };
  return wrap;
}
