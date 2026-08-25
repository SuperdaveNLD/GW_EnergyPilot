import "./gw-energy-pilot-v035.js?v=0.36-controller2";

const VERSION = "0.36";
const PANEL_NAME = "gw-energypilot-panel";
const CUSTOM_MODE = "custom";

const TEXT = {
  en: {
    kicker: "CHARGING STRATEGY",
    title: "Battery strategy",
    description: "Choose how EnergyPilot should value battery use. A profile change updates EMHASS and immediately builds a fresh plan.",
    custom: "Custom",
    customDescription: "Keep the current EMHASS battery values and tune the main limits manually.",
    active: "ACTIVE",
    applying: "Applying profile and optimizing…",
    applied: "Profile applied · fresh plan published.",
    customTitle: "Custom battery settings",
    customNote: "SOC sliders use the existing Home Assistant entities. Minimum SOC remains synchronized with the GoodWe on-grid battery floor; each completed change triggers a fresh optimization. Advanced EMHASS battery penalties are shown below for transparency and remain managed in EMHASS.",
    minimum: "Minimum SOC",
    maximum: "Maximum SOC",
    deficit: "Low-SOC cost",
    surplus: "High-SOC cost",
    stress: "Power stress",
    chargeWeight: "Charge cost",
    dischargeWeight: "Discharge cost",
    diagnostics: "Low-level controller command is available in Diagnostics.",
  },
  nl: {
    kicker: "LAADSTRATEGIE",
    title: "Batterijstrategie",
    description: "Kies hoe EnergyPilot batterijgebruik moet waarderen. Een profielwijziging past EMHASS aan en bouwt direct een nieuw plan.",
    custom: "Custom",
    customDescription: "Behoud de huidige EMHASS-batterijwaarden en stel de belangrijkste limieten handmatig af.",
    active: "ACTIEF",
    applying: "Profiel toepassen en optimaliseren…",
    applied: "Profiel toegepast · nieuw plan gepubliceerd.",
    customTitle: "Custom batterijinstellingen",
    customNote: "De SOC-sliders gebruiken de bestaande Home Assistant-entiteiten. Minimum SOC blijft gekoppeld aan de GoodWe on-grid ondergrens; iedere afgeronde wijziging start een nieuwe optimalisatie. De overige EMHASS-batterijkosten staan hieronder ter controle en blijven in EMHASS beheerd.",
    minimum: "Minimum SOC",
    maximum: "Maximum SOC",
    deficit: "Kosten lage SOC",
    surplus: "Kosten hoge SOC",
    stress: "Vermogensstress",
    chargeWeight: "Laadkosten",
    dischargeWeight: "Ontlaadkosten",
    diagnostics: "Het technische controllercommando staat in Diagnostiek.",
  },
};

function copy(panel) {
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  const lang = String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
  return TEXT[lang];
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v036-controller-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v036-controller-style";
  style.textContent = `
    .ep-v036-strategy { margin-top:15px; padding-top:14px; border-top:1px solid rgba(81,168,211,.10); }
    .ep-v036-head { display:flex; align-items:flex-start; justify-content:space-between; gap:14px; }
    .ep-v036-kicker { color:#62e5f7; font-size:8px; font-weight:900; letter-spacing:.15em; }
    .ep-v036-title { margin-top:3px; color:#e8f7fc; font-size:14px; font-weight:860; }
    .ep-v036-description { max-width:720px; margin-top:5px; color:#7696aa; font-size:9px; line-height:1.5; }
    .ep-v036-profile-grid { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; margin-top:12px; }
    .ep-v036-profile { position:relative; min-height:78px; padding:10px; border:1px solid rgba(75,164,209,.12); border-radius:11px; color:#a7c3d1; background:rgba(5,27,47,.48); cursor:pointer; text-align:left; }
    .ep-v036-profile:hover { border-color:rgba(55,213,231,.30); background:rgba(7,43,66,.62); }
    .ep-v036-profile.active { border-color:rgba(41,226,181,.46); background:linear-gradient(145deg,rgba(10,82,91,.52),rgba(8,67,52,.47)); box-shadow:inset 0 0 18px rgba(37,220,174,.05); }
    .ep-v036-profile:disabled { opacity:.52; cursor:wait; }
    .ep-v036-profile strong { display:block; color:#e7f7fc; font-size:10px; font-weight:850; }
    .ep-v036-profile small { display:block; margin-top:6px; color:#64869a; font-size:7px; line-height:1.4; }
    .ep-v036-profile.active small { color:#87acab; }
    .ep-v036-badge { position:absolute; top:7px; right:7px; color:#64dfbb; font-size:6px; font-weight:900; letter-spacing:.08em; }
    .ep-v036-message { margin-top:9px; min-height:14px; color:#6f91a4; font-size:8px; }
    .ep-v036-message.ok { color:#72dbb3; }
    .ep-v036-message.error { color:#ef9f98; }
    .ep-v036-custom { margin-top:11px; padding:11px; border:1px solid rgba(67,188,215,.12); border-radius:11px; background:rgba(5,24,42,.38); }
    .ep-v036-custom-head { color:#d8edf5; font-size:10px; font-weight:820; }
    .ep-v036-custom-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin-top:9px; }
    .ep-v036-soc { padding:9px 10px; border:1px solid rgba(76,157,202,.10); border-radius:9px; background:rgba(7,29,50,.43); }
    .ep-v036-soc-label { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:6px; color:#8fa9ba; font-size:8px; }
    .ep-v036-soc-label strong { color:#e5f4fa; font-size:10px; }
    .ep-v036-soc input { width:100%; accent-color:#25ddb6; }
    .ep-v036-custom-values { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:7px; margin-top:9px; }
    .ep-v036-custom-value { padding:8px; border:1px solid rgba(76,157,202,.08); border-radius:8px; background:rgba(7,29,50,.32); min-width:0; }
    .ep-v036-custom-value span { display:block; color:#66879a; font-size:7px; }
    .ep-v036-custom-value strong { display:block; margin-top:3px; color:#bfd6e1; font-size:8px; overflow-wrap:anywhere; }
    .ep-v036-custom-note { margin-top:8px; color:#5f7e91; font-size:7px; line-height:1.45; }
    .ep-v036-diagnostic-note { margin-top:10px; color:#58788d; font-size:8px; }
    @media (max-width:1000px) { .ep-v036-profile-grid { grid-template-columns:repeat(3,minmax(0,1fr)); } .ep-v036-custom-values { grid-template-columns:repeat(3,minmax(0,1fr)); } }
    @media (max-width:650px) { .ep-v036-profile-grid { grid-template-columns:1fr 1fr; } .ep-v036-custom-grid, .ep-v036-custom-values { grid-template-columns:1fr; } }
    @media (max-width:430px) { .ep-v036-profile-grid { grid-template-columns:1fr; } }
  `;
  root.appendChild(style);
}

function batterySaverCache(panel) {
  panel.__epV036BatterySaver = panel.__epV036BatterySaver || {};
  return panel.__epV036BatterySaver;
}

async function loadBatterySaver(panel, force = false) {
  const cache = batterySaverCache(panel);
  if (!panel._hass?.callWS || cache.loading) return;
  if (!force && cache.data) return;
  cache.loading = true;
  try {
    cache.data = await panel._hass.callWS({ type: "gw_energypilot/battery_saver/get" });
    cache.error = null;
  } catch (err) {
    cache.error = err?.message || String(err);
  } finally {
    cache.loading = false;
    panel._queueRender();
  }
}

async function selectProfile(panel, mode) {
  const cache = batterySaverCache(panel);
  if (!panel._hass?.callWS || cache.busy) return;
  if (!cache.data?.entry_id) await loadBatterySaver(panel, true);
  const entryId = cache.data?.entry_id;
  if (!entryId) return;
  const t = copy(panel);
  cache.busy = true;
  cache.message = t.applying;
  cache.tone = "";
  panel._queueRender();
  try {
    cache.data = await panel._hass.callWS({
      type: "gw_energypilot/battery_saver/set",
      entry_id: entryId,
      mode,
    });
    cache.message = t.applied;
    cache.tone = "ok";
  } catch (err) {
    cache.message = err?.message || String(err);
    cache.tone = "error";
  } finally {
    cache.busy = false;
    panel._queueRender();
  }
}

function numberModel(panel, key, fallback) {
  const entityId = panel._entityId?.(key);
  const state = entityId ? panel._state?.(entityId) : null;
  const value = Number(state?.state);
  return { entityId, value: Number.isFinite(value) ? value : fallback };
}

function displayConfigValue(value) {
  if (Array.isArray(value)) return value.map((item) => displayConfigValue(item)).join(", ");
  const number = Number(value);
  return Number.isFinite(number) ? String(Math.round(number * 1000000) / 1000000) : "—";
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
    <div class="ep-v036-custom">
      <div class="ep-v036-custom-head">${panel._escape(t.customTitle)}</div>
      <div class="ep-v036-custom-grid">
        <div class="ep-v036-soc">
          <div class="ep-v036-soc-label"><span>${panel._escape(t.minimum)}</span><strong data-v036-soc-value="min">${Math.round(min.value)}%</strong></div>
          <input data-v036-soc="min" type="range" min="0" max="100" step="1" value="${min.value}" ${min.entityId ? "" : "disabled"}>
        </div>
        <div class="ep-v036-soc">
          <div class="ep-v036-soc-label"><span>${panel._escape(t.maximum)}</span><strong data-v036-soc-value="max">${Math.round(max.value)}%</strong></div>
          <input data-v036-soc="max" type="range" min="0" max="100" step="1" value="${max.value}" ${max.entityId ? "" : "disabled"}>
        </div>
      </div>
      <div class="ep-v036-custom-values">
        ${fields.map(([label, value]) => `<div class="ep-v036-custom-value"><span>${panel._escape(label)}</span><strong>${panel._escape(displayConfigValue(value))}</strong></div>`).join("")}
      </div>
      <div class="ep-v036-custom-note">${panel._escape(t.customNote)}</div>
    </div>`;
}

function bindCustomSoc(panel, wrap) {
  const refs = {
    min: numberModel(panel, "emhass_minimum_soc", 0),
    max: numberModel(panel, "emhass_maximum_soc", 100),
  };
  for (const kind of ["min", "max"]) {
    const slider = wrap.querySelector(`[data-v036-soc="${kind}"]`);
    const label = wrap.querySelector(`[data-v036-soc-value="${kind}"]`);
    const ref = refs[kind];
    if (!slider || !label || !ref.entityId) continue;
    slider.addEventListener("input", () => { label.textContent = `${slider.value}%`; });
    slider.addEventListener("change", async () => {
      slider.disabled = true;
      try {
        await panel._hass.callService("number", "set_value", {
          entity_id: ref.entityId,
          value: Number(slider.value),
        });
      } catch (err) {
        window.alert(`Battery SOC update failed: ${err?.message || err}`);
      } finally {
        slider.disabled = false;
        panel._queueRender();
      }
    });
  }
}

function removeLowLevelCommand(card) {
  for (const metric of card.querySelectorAll(".metric")) {
    const label = metric.querySelector(".metric-label")?.textContent?.trim().toLowerCase();
    if (label === "command" || label === "commando") metric.remove();
  }
}

function installCustomerStrategy(panel, root) {
  const card = root.querySelector(".panel-card.controller");
  if (!card) return;
  removeLowLevelCommand(card);
  if (card.querySelector(".ep-v036-strategy")) return;
  ensureStyles(root);

  const cache = batterySaverCache(panel);
  if (!cache.data && !cache.loading && !cache.error) queueMicrotask(() => loadBatterySaver(panel));
  const data = cache.data;
  const t = copy(panel);
  const activeMode = data?.managed ? data.mode : CUSTOM_MODE;
  const modes = [
    ...(data?.modes || []),
    { key: CUSTOM_MODE, label: t.custom, description: t.customDescription, recommended: false },
  ];

  const wrap = document.createElement("section");
  wrap.className = "ep-v036-strategy";
  wrap.innerHTML = `
    <div class="ep-v036-head">
      <div>
        <div class="ep-v036-kicker">${panel._escape(t.kicker)}</div>
        <div class="ep-v036-title">${panel._escape(t.title)}</div>
        <div class="ep-v036-description">${panel._escape(t.description)}</div>
      </div>
    </div>
    <div class="ep-v036-profile-grid">
      ${modes.map((mode) => `
        <button type="button" class="ep-v036-profile ${activeMode === mode.key ? "active" : ""}" data-v036-mode="${panel._escape(mode.key)}" ${cache.busy || cache.loading ? "disabled" : ""}>
          ${activeMode === mode.key ? `<span class="ep-v036-badge">${panel._escape(t.active)}</span>` : ""}
          <strong>${panel._escape(mode.label)}</strong>
          <small>${panel._escape(mode.description || "")}</small>
        </button>`).join("")}
    </div>
    ${activeMode === CUSTOM_MODE ? customSocHtml(panel, t, data) : ""}
    <div class="ep-v036-message ${cache.tone || ""}">${panel._escape(cache.error || cache.message || "")}</div>
    <div class="ep-v036-diagnostic-note">${panel._escape(t.diagnostics)}</div>`;

  const manualPad = card.querySelector(".ep-v021-manual-pad");
  if (manualPad) card.insertBefore(wrap, manualPad);
  else card.appendChild(wrap);

  wrap.querySelectorAll("[data-v036-mode]").forEach((button) => {
    button.addEventListener("click", () => selectProfile(panel, button.dataset.v036Mode));
  });
  if (activeMode === CUSTOM_MODE) bindCustomSoc(panel, wrap);
}

function updateVersion(root) {
  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);

if (!PanelClass.prototype.__epV036CustomerControllerInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV036CustomerControllerRender() {
    previousRender.call(this);
    const root = this.shadowRoot;
    if (!root) return;
    installCustomerStrategy(this, root);
    updateVersion(root);
  };
  PanelClass.prototype.__epV036CustomerControllerInstalled = true;
}
