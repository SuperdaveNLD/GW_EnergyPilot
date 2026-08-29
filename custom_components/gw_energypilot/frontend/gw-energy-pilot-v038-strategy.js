import {
  CUSTOM_MODE,
  PROFILE_KEYS,
  canonicalProfiles,
  normalizeLanguage,
} from "./gw-energy-pilot-v038-model.js?v=0.46-external-pv1";

const TEXT = {
  en: {
    kicker: "CHARGING STRATEGY",
    title: "Battery strategy",
    description:
      "Choose how EnergyPilot should value battery use. A profile change updates EMHASS and immediately builds a fresh plan.",
    active: "ACTIVE",
    applying: "Applying profile and optimizing…",
    applied: "Profile applied · fresh plan published.",
    loading: "Loading battery profiles…",
    customTitle: "Custom battery settings",
    customNote:
      "SOC sliders use the existing Home Assistant entities. Minimum SOC remains synchronized with the GoodWe on-grid battery floor; each completed change triggers a fresh optimization. Advanced EMHASS battery penalties are shown below for transparency and remain managed in EMHASS.",
    minimum: "Minimum SOC",
    maximum: "Maximum SOC",
    deficit: "Low-SOC cost",
    surplus: "High-SOC cost",
    stress: "Power stress",
    chargeWeight: "Charge cost",
    dischargeWeight: "Discharge cost",
    diagnostics: "Low-level controller command is available in Diagnostics.",
    socError: "Battery SOC update failed",
  },
  nl: {
    kicker: "LAADSTRATEGIE",
    title: "Batterijstrategie",
    description:
      "Kies hoe EnergyPilot batterijgebruik waardeert. Een profielwijziging past EMHASS aan en bouwt direct een nieuw plan.",
    active: "ACTIEF",
    applying: "Profiel toepassen en optimaliseren…",
    applied: "Profiel toegepast · nieuw plan gepubliceerd.",
    loading: "Batterijprofielen laden…",
    customTitle: "Aangepaste batterijinstellingen",
    customNote:
      "De SOC-schuifregelaars gebruiken de bestaande Home Assistant-entiteiten. Minimum SOC blijft gekoppeld aan de GoodWe on-grid ondergrens; iedere afgeronde wijziging start een nieuwe optimalisatie. De overige EMHASS-batterijkosten staan hieronder ter controle en blijven in EMHASS beheerd.",
    minimum: "Minimum SOC",
    maximum: "Maximum SOC",
    deficit: "Kosten lage SOC",
    surplus: "Kosten hoge SOC",
    stress: "Vermogensstress",
    chargeWeight: "Laadkosten",
    dischargeWeight: "Ontlaadkosten",
    diagnostics: "Het technische controllercommando staat in Diagnostiek.",
    socError: "Bijwerken van batterij-SOC mislukt",
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
    cache.data = await panel._hass.callWS({
      type: "gw_energypilot/battery_saver/get",
    });
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
    cache.data = await panel._hass.callWS({
      type: "gw_energypilot/battery_saver/set",
      entry_id: entryId,
      mode,
    });
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

function customSocHtml(panel, t, data) {
  const min = numberModel(panel, "emhass_minimum_soc", 0);
  const max = numberModel(panel, "emhass_maximum_soc", 100);
  const values = data?.current_emhass_values || {};
  const fields = [
    [t.deficit, values.battery_soc_deficit_cost],
    [t.surplus, values.battery_soc_surplus_cost],
    [t.stress, values.battery_stress_cost],
    [t.chargeWeight, values.weight_battery_charge],
    [t.dischargeWeight, values.weight_battery_discharge],
  ];
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
      <div class="ep-v038-custom-values">
        ${fields
          .map(
            ([label, value]) =>
              `<div class="ep-v038-custom-value"><span>${panel._escape(label)}</span><strong>${panel._escape(displayConfigValue(value))}</strong></div>`
          )
          .join("")}
      </div>
      <div class="ep-v038-custom-note">${panel._escape(t.customNote)}</div>
    </div>`;
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
            </button>`
        )
        .join("")}
    </div>
    ${activeMode === CUSTOM_MODE ? customSocHtml(panel, t, cache.data) : ""}
    <div class="ep-v038-message ${panel._escape(cache.tone || "")}">${panel._escape(cache.error || cache.message || (!cache.data || cache.loading ? t.loading : ""))}</div>
    <div class="ep-v038-diagnostic-note">${panel._escape(t.diagnostics)}</div>`;
  wrap.dataset.epV038Signature = signature;
}

export function installV038CustomerStrategy(panel, root, reusableStrategy = null) {
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
