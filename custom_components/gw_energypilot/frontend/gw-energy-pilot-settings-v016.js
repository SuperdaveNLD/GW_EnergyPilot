import "./gw-energy-pilot-v015.js?v=0.47-custom-battery1";

const VERSION = "0.16";
const PANEL_NAME = "gw-energypilot-panel";
const SECTION_ORDER = ["energypilot", "emhass", "pv", "goodwe"];

const PV_COPY = Object.freeze({
  en: Object.freeze({
    title: "PV sources",
    description:
      "Choose which internal and external PV power sources EnergyPilot shows. These values are display-only.",
    note:
      "PV insight only: configured power is shown in the dashboard and is never used by EMS control or EMHASS.",
    internalLabel: "Include internal GoodWe PV",
    internalDescription:
      "Include the existing canonical GoodWe PV total in the dashboard PV total.",
    externalToggleLabel: "Include external PV",
    externalToggleDescription:
      "Enable the four external Home Assistant PV source fields below.",
    externalLabel: "External PV source",
    externalDescription:
      "Choose a Home Assistant power entity with non-negative PV generation in W, kW or MW.",
  }),
  nl: Object.freeze({
    title: "PV-bronnen",
    description:
      "Kies welke interne en externe PV-vermogens EnergyPilot toont. Deze waarden zijn uitsluitend voor inzicht.",
    note:
      "Alleen PV-inzicht: de ingestelde vermogens worden in het dashboard getoond en nooit gebruikt door EMS-regeling of EMHASS.",
    internalLabel: "Interne GoodWe-PV meenemen",
    internalDescription:
      "Neem het bestaande canonieke GoodWe PV-totaal op in het PV-totaal van het dashboard.",
    externalToggleLabel: "Externe PV meenemen",
    externalToggleDescription:
      "Activeer de vier externe Home Assistant PV-bronvelden hieronder.",
    externalLabel: "Externe PV-bron",
    externalDescription:
      "Kies een Home Assistant-vermogensentiteit met niet-negatieve PV-opwek in W, kW of MW.",
  }),
});

function settingsLanguage(panel) {
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function pvCopy(panel) {
  return PV_COPY[settingsLanguage(panel)];
}

function gearIcon() {
  return `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z"/>
      <path d="M19.4 13.5a7.8 7.8 0 0 0 .05-1.5 7.8 7.8 0 0 0-.05-1.5l2-1.55-2-3.45-2.45.95a8.6 8.6 0 0 0-2.6-1.5L14 2.35h-4l-.35 2.6a8.6 8.6 0 0 0-2.6 1.5L4.6 5.5l-2 3.45 2 1.55a7.8 7.8 0 0 0-.05 1.5c0 .5.02 1 .05 1.5l-2 1.55 2 3.45 2.45-.95a8.6 8.6 0 0 0 2.6 1.5L10 21.65h4l.35-2.6a8.6 8.6 0 0 0 2.6-1.5l2.45.95 2-3.45-2-1.55Z"/>
    </svg>`;
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v016-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v016-style";
  style.textContent = `
    .ep-v016-settings-button {
      width: 38px;
      height: 38px;
      display: grid;
      place-items: center;
      border-radius: 12px;
      border: 1px solid rgba(106,192,255,.18);
      color: #9edff4;
      background: rgba(12,38,66,.72);
      cursor: pointer;
      transition: border-color .14s linear, background-color .14s linear;
    }
    .ep-v016-settings-button:hover,
    .ep-v016-settings-button.active {
      border-color: rgba(36,226,255,.45);
      color: #dffcff;
      background: rgba(13,50,86,.94);
    }
    .ep-v016-settings-button svg {
      width: 20px;
      height: 20px;
      fill: none;
      stroke: currentColor;
      stroke-width: 1.7;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    .ep-v016-settings {
      margin-top: 8px;
      min-height: calc(100vh - 126px);
      border: 1px solid rgba(75,174,255,.16);
      border-radius: 20px;
      overflow: hidden;
      background:
        radial-gradient(circle at 94% 0%, rgba(31,239,167,.055), transparent 22rem),
        linear-gradient(145deg, rgba(8,28,53,.86), rgba(4,15,31,.94));
      box-shadow: 0 24px 70px rgba(0,0,0,.18);
    }
    .ep-v016-settings-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 20px 22px;
      border-bottom: 1px solid rgba(91,174,224,.10);
    }
    .ep-v016-settings-kicker {
      color: #62e6fb;
      font-size: 9px;
      font-weight: 850;
      letter-spacing: .16em;
    }
    .ep-v016-settings-head h2 {
      margin: 3px 0 0;
      color: #edf8ff;
      font-size: 24px;
      letter-spacing: -.02em;
    }
    .ep-v016-back {
      min-height: 36px;
      padding: 8px 12px;
      border-radius: 11px;
      border: 1px solid rgba(90,180,235,.18);
      color: #add2e6;
      background: rgba(9,39,67,.54);
      cursor: pointer;
      font-size: 10px;
      font-weight: 800;
    }
    .ep-v016-settings-layout {
      display: grid;
      grid-template-columns: 210px minmax(0,1fr);
      min-height: 620px;
    }
    .ep-v016-settings-nav {
      padding: 18px 14px;
      border-right: 1px solid rgba(91,174,224,.10);
      background: rgba(3,18,36,.28);
    }
    .ep-v016-entry-select {
      width: 100%;
      margin-bottom: 15px;
      padding: 9px 10px;
      border: 1px solid rgba(93,176,229,.16);
      border-radius: 10px;
      color: #dbeef8;
      background: #0a2540;
      font-size: 10px;
      outline: none;
    }
    .ep-v016-tab {
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin: 0 0 6px;
      padding: 11px 12px;
      border: 1px solid transparent;
      border-radius: 11px;
      color: #7897ac;
      background: transparent;
      cursor: pointer;
      text-align: left;
      font-size: 11px;
      font-weight: 850;
      letter-spacing: .05em;
    }
    .ep-v016-tab:hover {
      color: #c5e6f4;
      background: rgba(19,70,102,.30);
    }
    .ep-v016-tab.active {
      color: #e9fcff;
      border-color: rgba(44,217,238,.23);
      background: linear-gradient(135deg, rgba(13,91,126,.48), rgba(11,75,74,.34));
      box-shadow: inset 0 0 16px rgba(44,225,226,.035);
    }
    .ep-v016-tab small {
      color: #4f7189;
      font-size: 8px;
      font-weight: 700;
    }
    .ep-v016-tab.active small { color: #73d9e7; }

    .ep-v016-settings-content {
      padding: 22px clamp(18px,3vw,38px) 30px;
      min-width: 0;
    }
    .ep-v016-section-head {
      margin-bottom: 20px;
    }
    .ep-v016-section-head h3 {
      margin: 0;
      color: #effaff;
      font-size: 21px;
    }
    .ep-v016-section-head p {
      max-width: 720px;
      margin: 6px 0 0;
      color: #7895aa;
      font-size: 11px;
      line-height: 1.55;
    }
    .ep-v016-goodwe-note,
    .ep-v016-emhass-note,
    .ep-v016-pv-note {
      margin: 0 0 16px;
      padding: 10px 12px;
      border: 1px solid rgba(67,196,224,.13);
      border-radius: 11px;
      color: #83a9bd;
      background: rgba(8,43,66,.30);
      font-size: 9px;
      line-height: 1.5;
    }
    .ep-v016-goodwe-note strong,
    .ep-v016-emhass-note strong,
    .ep-v016-pv-note strong { color: #ccecf6; }

    .ep-v016-fields {
      display: grid;
      grid-template-columns: repeat(2,minmax(0,1fr));
      gap: 12px;
    }
    .ep-v016-pv-fields {
      display: grid;
      gap: 12px;
    }
    .ep-v016-external-group {
      min-width: 0;
      padding: 14px;
      border: 1px solid rgba(79,162,211,.13);
      border-radius: 13px;
      background: rgba(7,29,51,.44);
    }
    .ep-v016-external-group.is-enabled {
      border-color: rgba(45,221,239,.22);
      background: rgba(7,32,55,.58);
    }
    .ep-v016-external-group > .ep-v016-field.boolean {
      padding: 0 0 13px;
      border: 0;
      border-bottom: 1px solid rgba(91,174,224,.11);
      border-radius: 0;
      background: transparent;
    }
    .ep-v016-external-inputs {
      display: grid;
      grid-template-columns: repeat(2,minmax(0,1fr));
      gap: 11px 14px;
      padding-top: 13px;
    }
    .ep-v016-external-inputs .ep-v016-field {
      padding: 0;
      border: 0;
      border-radius: 0;
      background: transparent;
    }
    .ep-v016-external-group.is-disabled .ep-v016-external-inputs {
      opacity: .42;
    }
    .ep-v016-field {
      min-width: 0;
      padding: 13px 14px;
      border: 1px solid rgba(79,162,211,.10);
      border-radius: 12px;
      background: rgba(7,29,51,.38);
    }
    .ep-v016-field.boolean {
      display: grid;
      grid-template-columns: minmax(0,1fr) auto;
      align-items: center;
      gap: 14px;
    }
    .ep-v016-field-label {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 7px;
      color: #c8dde9;
      font-size: 10px;
      font-weight: 760;
    }
    .ep-v016-field.boolean .ep-v016-field-label { margin-bottom: 0; }
    .ep-v016-field-label span:last-child {
      color: #628198;
      font-size: 8px;
      font-weight: 600;
    }
    .ep-v016-field-description {
      margin-top: 7px;
      color: #5f7e94;
      font-size: 8px;
      line-height: 1.45;
    }
    .ep-v016-input,
    .ep-v016-readonly {
      width: 100%;
      min-height: 38px;
      box-sizing: border-box;
      padding: 9px 10px;
      border: 1px solid rgba(93,176,229,.16);
      border-radius: 9px;
      color: #e4f4fb;
      background: rgba(4,21,39,.72);
      outline: none;
      font: inherit;
      font-size: 11px;
    }
    .ep-v016-input:focus {
      border-color: rgba(45,221,239,.42);
      box-shadow: 0 0 0 2px rgba(45,221,239,.05);
    }
    .ep-v016-input:disabled {
      color: #668196;
      border-color: rgba(93,176,229,.08);
      background: rgba(4,18,33,.58);
      cursor: not-allowed;
    }
    .ep-v016-readonly {
      display: flex;
      align-items: center;
      color: #8ca8ba;
      background: rgba(7,26,44,.40);
    }
    .ep-v016-switch {
      appearance: none;
      position: relative;
      width: 40px;
      height: 22px;
      border: 0;
      border-radius: 999px;
      background: #294159;
      cursor: pointer;
      transition: background .15s linear;
    }
    .ep-v016-switch::after {
      content: "";
      position: absolute;
      width: 16px;
      height: 16px;
      left: 3px;
      top: 3px;
      border-radius: 50%;
      background: #dce9ef;
      transition: transform .15s linear;
    }
    .ep-v016-switch:checked { background: rgba(27,209,155,.58); }
    .ep-v016-switch:checked::after {
      transform: translateX(18px);
      background: #d8fff1;
      box-shadow: 0 0 11px rgba(30,240,165,.34);
    }

    .ep-v016-actions {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 18px;
      padding-top: 16px;
      border-top: 1px solid rgba(91,174,224,.09);
    }
    .ep-v016-action {
      min-height: 38px;
      padding: 9px 14px;
      border-radius: 10px;
      border: 1px solid rgba(77,176,229,.18);
      color: #b6d7e7;
      background: rgba(9,42,70,.48);
      cursor: pointer;
      font-size: 10px;
      font-weight: 800;
    }
    .ep-v016-action.primary {
      border-color: rgba(42,225,190,.32);
      color: #e5fff8;
      background: linear-gradient(135deg, rgba(16,112,139,.60), rgba(13,126,91,.48));
    }
    .ep-v016-action:disabled { opacity: .45; cursor: wait; }
    .ep-v016-message {
      margin-right: auto;
      color: #78a4b9;
      font-size: 9px;
    }
    .ep-v016-message.ok { color: #68ddb0; }
    .ep-v016-message.error { color: #f0a29c; }
    .ep-v016-loading {
      padding: 70px 20px;
      text-align: center;
      color: #7597ad;
      font-size: 11px;
    }

    @media (max-width: 900px) {
      .ep-v016-settings-layout { grid-template-columns: 1fr; }
      .ep-v016-settings-nav {
        display: flex;
        gap: 7px;
        padding: 12px;
        border-right: 0;
        border-bottom: 1px solid rgba(91,174,224,.10);
        overflow-x: auto;
      }
      .ep-v016-entry-select { width: auto; min-width: 180px; margin: 0 4px 0 0; }
      .ep-v016-tab { width: auto; min-width: 105px; margin: 0; }
    }
    @media (max-width: 650px) {
      .ep-v016-settings { border-radius: 15px; }
      .ep-v016-settings-head { padding: 15px; }
      .ep-v016-settings-head h2 { font-size: 20px; }
      .ep-v016-settings-content { padding: 17px 14px 24px; }
      .ep-v016-fields { grid-template-columns: 1fr; }
      .ep-v016-external-inputs { grid-template-columns: 1fr; }
      .ep-v016-actions { flex-wrap: wrap; }
      .ep-v016-message { width: 100%; margin-bottom: 5px; }
    }
  `;
  root.appendChild(style);
}

function installHassGuard(PanelClass) {
  if (PanelClass.prototype.__epV016HassGuard) return;
  const descriptor = Object.getOwnPropertyDescriptor(PanelClass.prototype, "hass");
  if (!descriptor?.set) return;

  Object.defineProperty(PanelClass.prototype, "hass", {
    configurable: descriptor.configurable,
    enumerable: descriptor.enumerable,
    get() {
      return descriptor.get ? descriptor.get.call(this) : this._hass;
    },
    set(value) {
      if (this.__epV016SettingsOpen) {
        this._hass = value;
        if (!this._registryLoaded && !this._registryLoading) this._loadRegistry();
        return;
      }
      descriptor.set.call(this, value);
    },
  });
  PanelClass.prototype.__epV016HassGuard = true;
}

function hasDrafts(panel) {
  return Object.values(panel.__epV016Draft || {}).some(
    (values) => values && Object.keys(values).length > 0
  );
}

function closeSettings(panel) {
  if (hasDrafts(panel) && !window.confirm("Discard unsaved EnergyPilot settings?")) return;
  panel.__epV016SettingsOpen = false;
  panel.__epV016Draft = {};
  panel.__epV016Message = null;
  panel._queueRender();
}

async function loadSettings(panel, entryId = null) {
  if (!panel._hass?.callWS || panel.__epV016SettingsLoading) return;
  panel.__epV016SettingsLoading = true;
  panel.__epV016SettingsError = null;
  panel._queueRender();
  try {
    const request = { type: "gw_energypilot/settings/get" };
    if (entryId) request.entry_id = entryId;
    panel.__epV016SettingsData = await panel._hass.callWS(request);
    panel.__epV016SelectedEntry = panel.__epV016SettingsData?.entry_id || entryId;
  } catch (err) {
    console.error("GW EnergyPilot: settings load failed", err);
    panel.__epV016SettingsError = err?.message || String(err);
  } finally {
    panel.__epV016SettingsLoading = false;
    panel._queueRender();
  }
}

function installSettingsButton(panel, root) {
  const actions = root.querySelector(".header-actions");
  if (!actions || actions.querySelector(".ep-v016-settings-button")) return;
  if (panel._hass?.user && panel._hass.user.is_admin === false) return;

  const button = document.createElement("button");
  button.type = "button";
  button.className = `ep-v016-settings-button${panel.__epV016SettingsOpen ? " active" : ""}`;
  button.title = "GW EnergyPilot configuration";
  button.setAttribute("aria-label", "Open GW EnergyPilot configuration");
  button.innerHTML = gearIcon();
  actions.prepend(button);

  button.addEventListener("click", () => {
    if (panel.__epV016SettingsOpen) {
      closeSettings(panel);
      return;
    }
    panel.__epV016SettingsOpen = true;
    panel.__epV016SettingsTab = panel.__epV016SettingsTab || "energypilot";
    panel.__epV016Draft = panel.__epV016Draft || {};
    panel.__epV016Message = null;
    panel._queueRender();
    if (!panel.__epV016SettingsData) loadSettings(panel);
  });
}

function fieldValue(panel, sectionId, field) {
  const draft = panel.__epV016Draft?.[sectionId] || {};
  return Object.prototype.hasOwnProperty.call(draft, field.key)
    ? draft[field.key]
    : field.value;
}

function pvFieldPresentation(panel, sectionId, field) {
  if (sectionId !== "pv") return field;
  const copy = pvCopy(panel);
  if (field.key === "enable_internal_pv") {
    return {
      ...field,
      label: copy.internalLabel,
      description: copy.internalDescription,
    };
  }
  if (field.key === "enable_external_pv") {
    return {
      ...field,
      label: copy.externalToggleLabel,
      description: copy.externalToggleDescription,
    };
  }
  const match = String(field.key || "").match(/external_pv_entity_(\d+)/);
  if (!match) return field;
  return {
    ...field,
    label: `${copy.externalLabel} ${match[1]}`,
    description: copy.externalDescription,
  };
}

function powerEntityOptions(panel) {
  const aggregateId = panel._entityId?.("pv_generation_power");
  const supportedUnits = new Set(["W", "kW", "MW", "mW"]);
  return Object.entries(panel?._hass?.states || {})
    .filter(([entityId, state]) => {
      if (entityId === aggregateId) return false;
      const attrs = state?.attributes || {};
      if (attrs.purpose === "display_only" && Array.isArray(attrs.sources)) return false;
      return attrs.device_class === "power" || supportedUnits.has(attrs.unit_of_measurement);
    })
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([entityId, state]) => {
      const friendly = state?.attributes?.friendly_name || entityId;
      return `<option value="${panel._escape(entityId)}" label="${panel._escape(friendly)}"></option>`;
    })
    .join("");
}

function fieldHtml(panel, sectionId, field) {
  field = pvFieldPresentation(panel, sectionId, field);
  const value = fieldValue(panel, sectionId, field);
  const disabled = field.disabled ? " disabled" : "";
  const fieldClass = `ep-v016-field${field.disabled ? " is-disabled" : ""}`;
  const unit = field.unit ? `<span>${panel._escape(field.unit)}</span>` : "<span></span>";
  const description = field.description
    ? `<div class="ep-v016-field-description">${panel._escape(field.description)}</div>`
    : "";
  const label = `<div class="ep-v016-field-label"><span>${panel._escape(field.label)}</span>${unit}</div>`;

  if (field.readonly) {
    return `<div class="${fieldClass}">${label}<div class="ep-v016-readonly">${panel._escape(value ?? "")}</div>${description}</div>`;
  }
  if (field.type === "boolean") {
    return `<label class="ep-v016-field boolean"><div>${label}${description}</div><input class="ep-v016-switch" type="checkbox" data-setting-key="${panel._escape(field.key)}" ${value ? "checked" : ""}></label>`;
  }
  if (field.type === "number") {
    const min = field.min === undefined ? "" : ` min="${field.min}"`;
    const max = field.max === undefined ? "" : ` max="${field.max}"`;
    const step = field.step === undefined ? "" : ` step="${field.step}"`;
    return `<label class="${fieldClass}">${label}<input class="ep-v016-input" type="number" data-setting-key="${panel._escape(field.key)}" value="${panel._escape(value ?? "")}"${min}${max}${step}${disabled}>${description}</label>`;
  }
  if (field.type === "select") {
    const options = (field.options || []).map((option) => {
      const optionValue = String(option?.value ?? option ?? "");
      const optionLabel = String(option?.label ?? optionValue);
      const selected = String(value ?? "") === optionValue ? " selected" : "";
      return `<option value="${panel._escape(optionValue)}"${selected}>${panel._escape(optionLabel)}</option>`;
    }).join("");
    return `<label class="${fieldClass}">${label}<select class="ep-v016-input" data-setting-key="${panel._escape(field.key)}"${disabled}>${options}</select>${description}</label>`;
  }
  if (field.type === "entity") {
    const listId = `ep-v016-${field.key}-entities`;
    return `<label class="${fieldClass}">${label}<input class="ep-v016-input" type="text" data-setting-key="${panel._escape(field.key)}" value="${panel._escape(value ?? "")}" list="${panel._escape(listId)}" placeholder="sensor…" autocomplete="off"${disabled}><datalist id="${panel._escape(listId)}">${powerEntityOptions(panel)}</datalist>${description}</label>`;
  }
  return `<label class="${fieldClass}">${label}<input class="ep-v016-input" type="text" data-setting-key="${panel._escape(field.key)}" value="${panel._escape(value ?? "")}" autocomplete="off"${disabled}>${description}</label>`;
}

function pvFieldsHtml(panel, sectionId, fields) {
  const internal = fields.find((field) => field.key === "enable_internal_pv");
  const externalToggle = fields.find((field) => field.key === "enable_external_pv");
  const externalFields = fields.filter((field) =>
    /^external_pv_entity_\d+$/.test(String(field.key || ""))
  );
  if (!internal || !externalToggle) {
    return fields.map((field) => fieldHtml(panel, sectionId, field)).join("");
  }
  const externalEnabled = Boolean(fieldValue(panel, sectionId, externalToggle));
  const groupedFields = externalFields
    .map((field) => fieldHtml(panel, sectionId, { ...field, disabled: !externalEnabled }))
    .join("");
  return `
    ${fieldHtml(panel, sectionId, internal)}
    <section class="ep-v016-external-group ${externalEnabled ? "is-enabled" : "is-disabled"}" data-pv-external-group aria-disabled="${externalEnabled ? "false" : "true"}">
      ${fieldHtml(panel, sectionId, externalToggle)}
      <div class="ep-v016-external-inputs">${groupedFields}</div>
    </section>`;
}

function syncExternalPvFields(form) {
  const toggle = form?.querySelector('[data-setting-key="enable_external_pv"]');
  const group = form?.querySelector("[data-pv-external-group]");
  if (!toggle || !group) return;
  const enabled = Boolean(toggle.checked);
  group.classList.toggle("is-enabled", enabled);
  group.classList.toggle("is-disabled", !enabled);
  group.setAttribute("aria-disabled", enabled ? "false" : "true");
  group.querySelectorAll('[data-setting-key^="external_pv_entity_"]').forEach((input) => {
    input.disabled = !enabled;
    input.closest(".ep-v016-field")?.classList.toggle("is-disabled", !enabled);
  });
}

function collectValues(form) {
  const values = {};
  form.querySelectorAll("[data-setting-key]").forEach((input) => {
    const key = input.dataset.settingKey;
    if (!key) return;
    if (input.type === "checkbox") values[key] = Boolean(input.checked);
    else if (input.type === "number") values[key] = input.value === "" ? null : Number(input.value);
    else values[key] = input.value;
  });
  return values;
}

async function saveSection(panel, form, sectionId) {
  if (!panel.__epV016SettingsData?.entry_id || panel.__epV016Saving) return;
  const values = collectValues(form);
  panel.__epV016Saving = true;
  panel.__epV016Message = { tone: "", text: sectionId === "goodwe" ? "Validating GoodWe connection…" : "Saving configuration…" };
  panel._queueRender();

  try {
    const result = await panel._hass.callWS({
      type: "gw_energypilot/settings/update",
      entry_id: panel.__epV016SettingsData.entry_id,
      section: sectionId,
      values,
    });
    if (result?.settings) panel.__epV016SettingsData = result.settings;
    panel.__epV016SelectedEntry = panel.__epV016SettingsData?.entry_id;
    if (panel.__epV016Draft) delete panel.__epV016Draft[sectionId];
    panel.__epV016Message = {
      tone: "ok",
      text: result?.require_restart
        ? "Saved. Home Assistant restart required to apply every change."
        : "Saved and EnergyPilot reloaded.",
    };
  } catch (err) {
    console.error("GW EnergyPilot: settings update failed", err);
    panel.__epV016Message = { tone: "error", text: err?.message || String(err) };
  } finally {
    panel.__epV016Saving = false;
    panel._queueRender();
  }
}

function renderSettingsPage(panel, root) {
  if (!panel.__epV016SettingsOpen) return;
  const page = root.querySelector("main.page");
  const topbar = page?.querySelector(".topbar");
  if (!page || !topbar) return;

  [...page.children].forEach((child) => {
    if (child !== topbar) child.hidden = true;
  });

  const shell = document.createElement("section");
  shell.className = "ep-v016-settings";
  shell.hidden = false;

  const data = panel.__epV016SettingsData;
  const tabId = SECTION_ORDER.includes(panel.__epV016SettingsTab)
    ? panel.__epV016SettingsTab
    : "energypilot";
  const section = data?.sections?.[tabId];
  const entries = data?.entries || [];

  const entryPicker = entries.length > 1
    ? `<select class="ep-v016-entry-select" data-entry-picker>${entries.map((entry) => `<option value="${panel._escape(entry.entry_id)}" ${entry.entry_id === data.entry_id ? "selected" : ""}>${panel._escape(entry.title)} · ${panel._escape(entry.state)}</option>`).join("")}</select>`
    : "";

  const tabs = SECTION_ORDER.map((id) => {
    const item = data?.sections?.[id];
    const label = item?.short_title || id.toUpperCase();
    return `<button type="button" class="ep-v016-tab ${id === tabId ? "active" : ""}" data-settings-tab="${id}"><span>${panel._escape(label)}</span><small>›</small></button>`;
  }).join("");

  let content;
  if (panel.__epV016SettingsLoading && !data) {
    content = `<div class="ep-v016-loading">Loading EnergyPilot configuration…</div>`;
  } else if (panel.__epV016SettingsError && !data) {
    content = `<div class="ep-v016-loading">Unable to load configuration: ${panel._escape(panel.__epV016SettingsError)}</div>`;
  } else if (!section) {
    content = `<div class="ep-v016-loading">Configuration is not available yet.</div>`;
  } else {
    const sectionTitle = tabId === "pv" ? pvCopy(panel).title : section.title;
    const sectionDescription = tabId === "pv" ? pvCopy(panel).description : section.description;
    const note = tabId === "goodwe"
      ? `<div class="ep-v016-goodwe-note"><strong>Connection safety:</strong> host, port and unit ID are tested against the inverter before they are saved. A successful change reloads the integration.</div>`
      : tabId === "emhass"
      ? `<div class="ep-v016-emhass-note"><strong>EMHASS:</strong> this page owns EnergyPilot's EMHASS connection, scheduling, output mapping and price-source settings. Live SOC and cost-function controls remain available on the dashboard while they are migrated into this configuration area.</div>`
      : tabId === "pv"
      ? `<div class="ep-v016-pv-note"><strong>PV:</strong> ${panel._escape(pvCopy(panel).note)}</div>`
      : "";
    const sectionFields = section.fields || [];
    const fields = tabId === "pv"
      ? pvFieldsHtml(panel, tabId, sectionFields)
      : sectionFields.map((field) => fieldHtml(panel, tabId, field)).join("");
    const fieldsClass = tabId === "pv" ? "ep-v016-pv-fields" : "ep-v016-fields";
    const message = panel.__epV016Message
      ? `<span class="ep-v016-message ${panel._escape(panel.__epV016Message.tone || "")}">${panel._escape(panel.__epV016Message.text)}</span>`
      : `<span class="ep-v016-message">Changes are stored in the existing Home Assistant config entry.</span>`;

    content = `
      <div class="ep-v016-section-head">
        <h3>${panel._escape(sectionTitle)}</h3>
        <p>${panel._escape(sectionDescription || "")}</p>
      </div>
      ${note}
      <form class="ep-v016-form" data-section="${tabId}">
        <div class="${fieldsClass}">${fields}</div>
        <div class="ep-v016-actions">
          ${message}
          <button type="button" class="ep-v016-action" data-discard ${panel.__epV016Saving ? "disabled" : ""}>Discard changes</button>
          <button type="submit" class="ep-v016-action primary" ${panel.__epV016Saving ? "disabled" : ""}>${panel.__epV016Saving ? "Saving…" : "Save changes"}</button>
        </div>
      </form>`;
  }

  shell.innerHTML = `
    <div class="ep-v016-settings-head">
      <div><div class="ep-v016-settings-kicker">GW ENERGYPILOT</div><h2>Configuration</h2></div>
      <button type="button" class="ep-v016-back">← Dashboard</button>
    </div>
    <div class="ep-v016-settings-layout">
      <nav class="ep-v016-settings-nav" aria-label="EnergyPilot configuration sections">
        ${entryPicker}
        ${tabs}
      </nav>
      <div class="ep-v016-settings-content">${content}</div>
    </div>`;

  topbar.insertAdjacentElement("afterend", shell);

  shell.querySelector(".ep-v016-back")?.addEventListener("click", () => closeSettings(panel));
  shell.querySelectorAll("[data-settings-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      panel.__epV016SettingsTab = button.dataset.settingsTab;
      panel.__epV016Message = null;
      panel._queueRender();
    });
  });
  shell.querySelector("[data-entry-picker]")?.addEventListener("change", (event) => {
    const nextEntry = event.currentTarget.value;
    panel.__epV016Draft = {};
    panel.__epV016Message = null;
    panel.__epV016SettingsData = null;
    loadSettings(panel, nextEntry);
  });

  const form = shell.querySelector(".ep-v016-form");
  if (form) {
    syncExternalPvFields(form);
    form.querySelectorAll("[data-setting-key]").forEach((input) => {
      const remember = () => {
        panel.__epV016Draft = panel.__epV016Draft || {};
        panel.__epV016Draft[tabId] = panel.__epV016Draft[tabId] || {};
        panel.__epV016Draft[tabId][input.dataset.settingKey] =
          input.type === "checkbox" ? Boolean(input.checked) : input.value;
        panel.__epV016Message = null;
      };
      input.addEventListener(input.type === "checkbox" ? "change" : "input", remember);
      if (input.dataset.settingKey === "enable_external_pv") {
        input.addEventListener("change", () => syncExternalPvFields(form));
      }
    });
    form.querySelector("[data-discard]")?.addEventListener("click", () => {
      if (panel.__epV016Draft) delete panel.__epV016Draft[tabId];
      panel.__epV016Message = null;
      panel._queueRender();
    });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      saveSection(panel, form, tabId);
    });
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
installHassGuard(PanelClass);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV016Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  ensureStyles(root);
  installSettingsButton(this, root);
  renderSettingsPage(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION}`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION}`;
};
