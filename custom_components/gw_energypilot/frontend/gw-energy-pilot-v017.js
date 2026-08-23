import "./gw-energy-pilot-v016.js?v=0.16-beta-g20-1";

const VERSION = "0.17";
const PANEL_NAME = "gw-energypilot-panel";
const SECTION_ORDER = ["energypilot", "emhass", "goodwe"];

function gearIcon() {
  return `
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z"/>
      <path d="M19.4 13.5a7.8 7.8 0 0 0 .05-1.5 7.8 7.8 0 0 0-.05-1.5l2-1.55-2-3.45-2.45.95a8.6 8.6 0 0 0-2.6-1.5L14 2.35h-4l-.35 2.6a8.6 8.6 0 0 0-2.6 1.5L4.6 5.5l-2 3.45 2 1.55a7.8 7.8 0 0 0-.05 1.5c0 .5.02 1 .05 1.5l-2 1.55 2 3.45 2.45-.95a8.6 8.6 0 0 0 2.6 1.5L10 21.65h4l.35-2.6a8.6 8.6 0 0 0 2.6-1.5l2.45.95 2-3.45-2-1.55Z"/>
    </svg>`;
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v017-settings-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v017-settings-style";
  style.textContent = `
    .ep-v017-settings-button {
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
    .ep-v017-settings-button:hover,
    .ep-v017-settings-button.active {
      border-color: rgba(36,226,255,.45);
      color: #dffcff;
      background: rgba(13,50,86,.94);
    }
    .ep-v017-settings-button svg {
      width: 20px;
      height: 20px;
      fill: none;
      stroke: currentColor;
      stroke-width: 1.7;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .ep-v017-settings {
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
    .ep-v017-settings-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 20px 22px;
      border-bottom: 1px solid rgba(91,174,224,.10);
    }
    .ep-v017-settings-kicker {
      color: #62e6fb;
      font-size: 9px;
      font-weight: 850;
      letter-spacing: .16em;
    }
    .ep-v017-settings-head h2 {
      margin: 3px 0 0;
      color: #edf8ff;
      font-size: 24px;
    }
    .ep-v017-back,
    .ep-v017-action {
      min-height: 36px;
      padding: 8px 12px;
      border-radius: 10px;
      border: 1px solid rgba(90,180,235,.18);
      color: #add2e6;
      background: rgba(9,39,67,.54);
      cursor: pointer;
      font-size: 10px;
      font-weight: 800;
    }
    .ep-v017-settings-layout {
      display: grid;
      grid-template-columns: 210px minmax(0,1fr);
      min-height: 620px;
    }
    .ep-v017-settings-nav {
      padding: 18px 14px;
      border-right: 1px solid rgba(91,174,224,.10);
      background: rgba(3,18,36,.28);
    }
    .ep-v017-entry-select,
    .ep-v017-input {
      width: 100%;
      box-sizing: border-box;
      min-height: 38px;
      padding: 9px 10px;
      border: 1px solid rgba(93,176,229,.16);
      border-radius: 9px;
      color: #e4f4fb;
      background: rgba(4,21,39,.72);
      outline: none;
      font: inherit;
      font-size: 11px;
    }
    .ep-v017-entry-select {
      margin-bottom: 15px;
      background: #0a2540;
      font-size: 10px;
    }
    .ep-v017-input:focus {
      border-color: rgba(45,221,239,.42);
      box-shadow: 0 0 0 2px rgba(45,221,239,.05);
    }
    .ep-v017-tab {
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
    .ep-v017-tab:hover {
      color: #c5e6f4;
      background: rgba(19,70,102,.30);
    }
    .ep-v017-tab.active {
      color: #e9fcff;
      border-color: rgba(44,217,238,.23);
      background: linear-gradient(135deg, rgba(13,91,126,.48), rgba(11,75,74,.34));
    }
    .ep-v017-tab small { color: #4f7189; font-size: 8px; }
    .ep-v017-settings-content {
      padding: 22px clamp(18px,3vw,38px) 30px;
      min-width: 0;
    }
    .ep-v017-section-head { margin-bottom: 20px; }
    .ep-v017-section-head h3 {
      margin: 0;
      color: #effaff;
      font-size: 21px;
    }
    .ep-v017-section-head p {
      max-width: 720px;
      margin: 6px 0 0;
      color: #7895aa;
      font-size: 11px;
      line-height: 1.55;
    }
    .ep-v017-note {
      margin: 0 0 16px;
      padding: 10px 12px;
      border: 1px solid rgba(67,196,224,.13);
      border-radius: 11px;
      color: #83a9bd;
      background: rgba(8,43,66,.30);
      font-size: 9px;
      line-height: 1.5;
    }
    .ep-v017-note strong { color: #ccecf6; }
    .ep-v017-fields {
      display: grid;
      grid-template-columns: repeat(2,minmax(0,1fr));
      gap: 12px;
    }
    .ep-v017-field {
      min-width: 0;
      padding: 13px 14px;
      border: 1px solid rgba(79,162,211,.10);
      border-radius: 12px;
      background: rgba(7,29,51,.38);
    }
    .ep-v017-field.boolean {
      display: grid;
      grid-template-columns: minmax(0,1fr) auto;
      align-items: center;
      gap: 14px;
    }
    .ep-v017-field-label {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 10px;
      margin-bottom: 7px;
      color: #c8dde9;
      font-size: 10px;
      font-weight: 760;
    }
    .ep-v017-field.boolean .ep-v017-field-label { margin-bottom: 0; }
    .ep-v017-field-label span:last-child {
      color: #628198;
      font-size: 8px;
      font-weight: 600;
    }
    .ep-v017-field-description {
      margin-top: 7px;
      color: #5f7e94;
      font-size: 8px;
      line-height: 1.45;
    }
    .ep-v017-readonly {
      min-height: 38px;
      display: flex;
      align-items: center;
      box-sizing: border-box;
      padding: 9px 10px;
      border: 1px solid rgba(93,176,229,.10);
      border-radius: 9px;
      color: #8ca8ba;
      background: rgba(7,26,44,.40);
      font-size: 11px;
    }
    .ep-v017-switch {
      appearance: none;
      position: relative;
      width: 40px;
      height: 22px;
      border: 0;
      border-radius: 999px;
      background: #294159;
      cursor: pointer;
    }
    .ep-v017-switch::after {
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
    .ep-v017-switch:checked { background: rgba(27,209,155,.58); }
    .ep-v017-switch:checked::after {
      transform: translateX(18px);
      background: #d8fff1;
    }
    .ep-v017-actions {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 18px;
      padding-top: 16px;
      border-top: 1px solid rgba(91,174,224,.09);
    }
    .ep-v017-action.primary {
      border-color: rgba(42,225,190,.32);
      color: #e5fff8;
      background: linear-gradient(135deg, rgba(16,112,139,.60), rgba(13,126,91,.48));
    }
    .ep-v017-action:disabled { opacity: .45; cursor: wait; }
    .ep-v017-message {
      margin-right: auto;
      color: #78a4b9;
      font-size: 9px;
    }
    .ep-v017-message.ok { color: #68ddb0; }
    .ep-v017-message.error { color: #f0a29c; }
    .ep-v017-loading {
      padding: 70px 20px;
      text-align: center;
      color: #7597ad;
      font-size: 11px;
    }
    @media (max-width: 900px) {
      .ep-v017-settings-layout { grid-template-columns: 1fr; }
      .ep-v017-settings-nav {
        display: flex;
        gap: 7px;
        padding: 12px;
        border-right: 0;
        border-bottom: 1px solid rgba(91,174,224,.10);
        overflow-x: auto;
      }
      .ep-v017-entry-select { width: auto; min-width: 180px; margin: 0 4px 0 0; }
      .ep-v017-tab { width: auto; min-width: 105px; margin: 0; }
    }
    @media (max-width: 650px) {
      .ep-v017-settings { border-radius: 15px; }
      .ep-v017-settings-head { padding: 15px; }
      .ep-v017-settings-head h2 { font-size: 20px; }
      .ep-v017-settings-content { padding: 17px 14px 24px; }
      .ep-v017-fields { grid-template-columns: 1fr; }
      .ep-v017-actions { flex-wrap: wrap; }
      .ep-v017-message { width: 100%; margin-bottom: 5px; }
    }
  `;
  root.appendChild(style);
}

function installHassGuard(PanelClass) {
  if (PanelClass.prototype.__epV017HassGuard) return;
  const descriptor = Object.getOwnPropertyDescriptor(PanelClass.prototype, "hass");
  if (!descriptor?.set) return;

  Object.defineProperty(PanelClass.prototype, "hass", {
    configurable: descriptor.configurable,
    enumerable: descriptor.enumerable,
    get() {
      return descriptor.get ? descriptor.get.call(this) : this._hass;
    },
    set(value) {
      if (this.__epV017SettingsOpen) {
        this._hass = value;
        if (!this._registryLoaded && !this._registryLoading) this._loadRegistry();
        return;
      }
      descriptor.set.call(this, value);
    },
  });
  PanelClass.prototype.__epV017HassGuard = true;
}

function hasDrafts(panel) {
  return Object.values(panel.__epV017Draft || {}).some(
    (values) => values && Object.keys(values).length > 0
  );
}

function closeSettings(panel) {
  if (hasDrafts(panel) && !window.confirm("Discard unsaved EnergyPilot settings?")) return;
  panel.__epV017SettingsOpen = false;
  panel.__epV017Draft = {};
  panel.__epV017Message = null;
  panel._queueRender();
}

async function loadSettings(panel, entryId = null) {
  if (!panel._hass?.callWS || panel.__epV017SettingsLoading) return;
  panel.__epV017SettingsLoading = true;
  panel.__epV017SettingsError = null;
  panel._queueRender();
  try {
    const request = { type: "gw_energypilot/settings/get" };
    if (entryId) request.entry_id = entryId;
    panel.__epV017SettingsData = await panel._hass.callWS(request);
  } catch (err) {
    console.error("GW EnergyPilot: settings load failed", err);
    panel.__epV017SettingsError = err?.message || String(err);
  } finally {
    panel.__epV017SettingsLoading = false;
    panel._queueRender();
  }
}

function installSettingsButton(panel, root) {
  const actions = root.querySelector(".header-actions");
  if (!actions || actions.querySelector(".ep-v017-settings-button")) return;
  if (panel._hass?.user && panel._hass.user.is_admin === false) return;

  const button = document.createElement("button");
  button.type = "button";
  button.className = `ep-v017-settings-button${panel.__epV017SettingsOpen ? " active" : ""}`;
  button.title = "GW EnergyPilot configuration";
  button.setAttribute("aria-label", "Open GW EnergyPilot configuration");
  button.innerHTML = gearIcon();

  const layoutButton = actions.querySelector(".ep-layout-button");
  if (layoutButton) layoutButton.insertAdjacentElement("afterend", button);
  else actions.prepend(button);

  button.addEventListener("click", () => {
    if (panel.__epV017SettingsOpen) {
      closeSettings(panel);
      return;
    }
    panel.__epV008MenuOpen = false;
    panel.__epV017SettingsOpen = true;
    panel.__epV017SettingsTab = panel.__epV017SettingsTab || "energypilot";
    panel.__epV017Draft = panel.__epV017Draft || {};
    panel.__epV017Message = null;
    panel._queueRender();
    if (!panel.__epV017SettingsData) loadSettings(panel);
  });
}

function fieldValue(panel, sectionId, field) {
  const draft = panel.__epV017Draft?.[sectionId] || {};
  return Object.prototype.hasOwnProperty.call(draft, field.key)
    ? draft[field.key]
    : field.value;
}

function fieldHtml(panel, sectionId, field) {
  const value = fieldValue(panel, sectionId, field);
  const unit = field.unit ? `<span>${panel._escape(field.unit)}</span>` : "<span></span>";
  const description = field.description
    ? `<div class="ep-v017-field-description">${panel._escape(field.description)}</div>`
    : "";
  const label = `<div class="ep-v017-field-label"><span>${panel._escape(field.label)}</span>${unit}</div>`;

  if (field.readonly) {
    return `<div class="ep-v017-field">${label}<div class="ep-v017-readonly">${panel._escape(value ?? "")}</div>${description}</div>`;
  }
  if (field.type === "boolean") {
    return `<label class="ep-v017-field boolean"><div>${label}${description}</div><input class="ep-v017-switch" type="checkbox" data-setting-key="${panel._escape(field.key)}" ${value ? "checked" : ""}></label>`;
  }
  if (field.type === "number") {
    const min = field.min === undefined ? "" : ` min="${field.min}"`;
    const max = field.max === undefined ? "" : ` max="${field.max}"`;
    const step = field.step === undefined ? "" : ` step="${field.step}"`;
    return `<label class="ep-v017-field">${label}<input class="ep-v017-input" type="number" data-setting-key="${panel._escape(field.key)}" value="${panel._escape(value ?? "")}"${min}${max}${step}>${description}</label>`;
  }
  return `<label class="ep-v017-field">${label}<input class="ep-v017-input" type="text" data-setting-key="${panel._escape(field.key)}" value="${panel._escape(value ?? "")}" autocomplete="off">${description}</label>`;
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
  const entryId = panel.__epV017SettingsData?.entry_id;
  if (!entryId || panel.__epV017Saving) return;

  panel.__epV017Saving = true;
  panel.__epV017Message = {
    tone: "",
    text: sectionId === "goodwe" ? "Validating GoodWe connection…" : "Saving configuration…",
  };
  panel._queueRender();

  try {
    const result = await panel._hass.callWS({
      type: "gw_energypilot/settings/update",
      entry_id: entryId,
      section: sectionId,
      values: collectValues(form),
    });
    if (result?.settings) panel.__epV017SettingsData = result.settings;
    if (panel.__epV017Draft) delete panel.__epV017Draft[sectionId];
    panel.__epV017Message = {
      tone: "ok",
      text: result?.require_restart
        ? "Saved. Home Assistant restart required to apply every change."
        : "Saved and EnergyPilot reloaded.",
    };
  } catch (err) {
    console.error("GW EnergyPilot: settings update failed", err);
    panel.__epV017Message = { tone: "error", text: err?.message || String(err) };
  } finally {
    panel.__epV017Saving = false;
    panel._queueRender();
  }
}

function renderSettingsPage(panel, root) {
  if (!panel.__epV017SettingsOpen) return;
  const page = root.querySelector("main.page");
  const topbar = page?.querySelector(".topbar");
  if (!page || !topbar) return;

  const layoutButton = topbar.querySelector(".ep-layout-button");
  if (layoutButton) layoutButton.hidden = true;

  [...page.children].forEach((child) => {
    if (child !== topbar) child.hidden = true;
  });

  const shell = document.createElement("section");
  shell.className = "ep-v017-settings";
  shell.hidden = false;

  const data = panel.__epV017SettingsData;
  const tabId = SECTION_ORDER.includes(panel.__epV017SettingsTab)
    ? panel.__epV017SettingsTab
    : "energypilot";
  const section = data?.sections?.[tabId];
  const entries = data?.entries || [];

  const entryPicker = entries.length > 1
    ? `<select class="ep-v017-entry-select" data-entry-picker>${entries.map((entry) => `<option value="${panel._escape(entry.entry_id)}" ${entry.entry_id === data.entry_id ? "selected" : ""}>${panel._escape(entry.title)} · ${panel._escape(entry.state)}</option>`).join("")}</select>`
    : "";

  const tabs = SECTION_ORDER.map((id) => {
    const item = data?.sections?.[id];
    const label = item?.short_title || id.toUpperCase();
    return `<button type="button" class="ep-v017-tab ${id === tabId ? "active" : ""}" data-settings-tab="${id}"><span>${panel._escape(label)}</span><small>›</small></button>`;
  }).join("");

  let content;
  if (panel.__epV017SettingsLoading && !data) {
    content = `<div class="ep-v017-loading">Loading EnergyPilot configuration…</div>`;
  } else if (panel.__epV017SettingsError && !data) {
    content = `<div class="ep-v017-loading">Unable to load configuration: ${panel._escape(panel.__epV017SettingsError)}</div>`;
  } else if (!section) {
    content = `<div class="ep-v017-loading">Configuration is not available yet.</div>`;
  } else {
    const note = tabId === "goodwe"
      ? `<div class="ep-v017-note"><strong>Connection safety:</strong> host, port and unit ID are tested against the inverter before saving. The Home Assistant device identity remains stable when the connection address changes.</div>`
      : tabId === "emhass"
      ? `<div class="ep-v017-note"><strong>EMHASS:</strong> this page owns EnergyPilot's connection, scheduling, output mapping and price-source settings. Live min/max SOC and cost-function controls still use their existing EMHASS config.json path.</div>`
      : "";
    const fields = (section.fields || []).map((field) => fieldHtml(panel, tabId, field)).join("");
    const message = panel.__epV017Message
      ? `<span class="ep-v017-message ${panel._escape(panel.__epV017Message.tone || "")}">${panel._escape(panel.__epV017Message.text)}</span>`
      : `<span class="ep-v017-message">Changes use the existing Home Assistant config entry.</span>`;

    content = `
      <div class="ep-v017-section-head">
        <h3>${panel._escape(section.title)}</h3>
        <p>${panel._escape(section.description || "")}</p>
      </div>
      ${note}
      <form class="ep-v017-form" data-section="${tabId}">
        <div class="ep-v017-fields">${fields}</div>
        <div class="ep-v017-actions">
          ${message}
          <button type="button" class="ep-v017-action" data-discard ${panel.__epV017Saving ? "disabled" : ""}>Discard changes</button>
          <button type="submit" class="ep-v017-action primary" ${panel.__epV017Saving ? "disabled" : ""}>${panel.__epV017Saving ? "Saving…" : "Save changes"}</button>
        </div>
      </form>`;
  }

  shell.innerHTML = `
    <div class="ep-v017-settings-head">
      <div><div class="ep-v017-settings-kicker">GW ENERGYPILOT</div><h2>Configuration</h2></div>
      <button type="button" class="ep-v017-back">← Dashboard</button>
    </div>
    <div class="ep-v017-settings-layout">
      <nav class="ep-v017-settings-nav" aria-label="EnergyPilot configuration sections">
        ${entryPicker}
        ${tabs}
      </nav>
      <div class="ep-v017-settings-content">${content}</div>
    </div>`;

  topbar.insertAdjacentElement("afterend", shell);

  shell.querySelector(".ep-v017-back")?.addEventListener("click", () => closeSettings(panel));
  shell.querySelectorAll("[data-settings-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      panel.__epV017SettingsTab = button.dataset.settingsTab;
      panel.__epV017Message = null;
      panel._queueRender();
    });
  });
  shell.querySelector("[data-entry-picker]")?.addEventListener("change", (event) => {
    if (hasDrafts(panel) && !window.confirm("Discard unsaved settings and switch EnergyPilot entry?")) {
      event.currentTarget.value = data.entry_id;
      return;
    }
    panel.__epV017Draft = {};
    panel.__epV017Message = null;
    panel.__epV017SettingsData = null;
    loadSettings(panel, event.currentTarget.value);
  });

  const form = shell.querySelector(".ep-v017-form");
  if (!form) return;

  form.querySelectorAll("[data-setting-key]").forEach((input) => {
    const remember = () => {
      panel.__epV017Draft = panel.__epV017Draft || {};
      panel.__epV017Draft[tabId] = panel.__epV017Draft[tabId] || {};
      panel.__epV017Draft[tabId][input.dataset.settingKey] =
        input.type === "checkbox" ? Boolean(input.checked) : input.value;
      panel.__epV017Message = null;
    };
    input.addEventListener(input.type === "checkbox" ? "change" : "input", remember);
  });

  form.querySelector("[data-discard]")?.addEventListener("click", () => {
    if (panel.__epV017Draft) delete panel.__epV017Draft[tabId];
    panel.__epV017Message = null;
    panel._queueRender();
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    saveSection(panel, form, tabId);
  });
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
installHassGuard(PanelClass);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV017Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  ensureStyles(root);
  installSettingsButton(this, root);
  renderSettingsPage(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
};
