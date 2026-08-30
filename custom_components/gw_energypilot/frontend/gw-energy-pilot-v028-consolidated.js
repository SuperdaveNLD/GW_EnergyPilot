import "./gw-energy-pilot-v028-window-controls.js?v=1.0.1-beta1";

const PANEL_NAME = "gw-energypilot-panel";

function language(panel) {
  const raw = panel?._hass?.locale?.language || panel?._hass?.language || "en";
  return String(raw).toLowerCase().split(/[-_]/)[0] === "nl" ? "nl" : "en";
}

function copy(panel) {
  return language(panel) === "nl"
    ? {
        defaults: "Aanbevolen standaardwaarden herstellen",
        defaultsLoaded: "Aanbevolen EMHASS-standaardwaarden zijn ingevuld. Controleer ze en sla daarna op.",
        sync: "Noodzakelijke config synchroniseren",
        checking: "EMHASS-config controleren…",
        synced: "EMHASS-config is gesynchroniseerd",
        changes: "wijzigingen nodig",
        confirm: "De noodzakelijke EnergyPilot-koppelingen naar EMHASS config.json schrijven? Overige EMHASS-instellingen blijven behouden.",
        done: "EMHASS-configuratie is gesynchroniseerd. Voer een nieuwe optimalisatie uit voordat Automatische regeling wordt ingeschakeld.",
      }
    : {
        defaults: "Restore recommended defaults",
        defaultsLoaded: "Recommended EMHASS defaults loaded. Review them, then save to apply.",
        sync: "Synchronize required config",
        checking: "Checking EMHASS config…",
        synced: "EMHASS config is synchronized",
        changes: "change(s) required",
        confirm: "Write the required EnergyPilot mappings to EMHASS config.json? Unrelated EMHASS settings will be preserved.",
        done: "EMHASS configuration synchronized. Run a fresh optimization before enabling Automatic Control.",
      };
}

function ensureStyles(root) {
  if (root.querySelector("#ep-v028-consolidated-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v028-consolidated-style";
  style.textContent = `
    /* The v0.13 geometry-specific keyframes are authoritative. Never reverse
       them again in a later semantic layer. */
    .ep-flow-link .ep-v011-particles span { animation-direction: normal !important; }
    .ep-v028-sync-tools { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-right:auto; }
    .ep-v028-sync-state { font-size:8px; color:#7899ad; }
    .ep-v028-sync-state.ok { color:#72d9b2; }
    .ep-v028-sync-state.warn { color:#e7b66f; }
  `;
  root.appendChild(style);
}

function state(panel) {
  if (!panel.__epV028Sync) {
    panel.__epV028Sync = { entryId: null, data: null, loading: false, applying: false, error: null };
  }
  return panel.__epV028Sync;
}

async function loadSync(panel, force = false) {
  const entryId = panel.__epV016SettingsData?.entry_id;
  const current = state(panel);
  if (!panel._hass?.callWS || !entryId || current.loading || current.applying) return;
  if (!force && current.entryId === entryId && current.data) return;
  current.entryId = entryId;
  current.loading = true;
  current.error = null;
  panel._queueRender();
  try {
    current.data = await panel._hass.callWS({ type: "gw_energypilot/emhass_sync/get", entry_id: entryId });
  } catch (err) {
    current.error = err?.message || String(err);
  } finally {
    current.loading = false;
    panel._queueRender();
  }
}

function restoreDefaults(panel, form) {
  const defaults = state(panel).data?.recommended_options || {};
  panel.__epV016Draft = panel.__epV016Draft || {};
  panel.__epV016Draft.emhass = panel.__epV016Draft.emhass || {};
  form.querySelectorAll("[data-setting-key]").forEach((input) => {
    const key = input.dataset.settingKey;
    if (key && Object.prototype.hasOwnProperty.call(defaults, key)) {
      panel.__epV016Draft.emhass[key] = defaults[key];
    }
  });
  panel.__epV016Message = { tone: "", text: copy(panel).defaultsLoaded };
  panel._queueRender();
}

async function applySync(panel) {
  const entryId = panel.__epV016SettingsData?.entry_id;
  const current = state(panel);
  if (!panel._hass?.callWS || !entryId || current.applying) return;
  if (!window.confirm(copy(panel).confirm)) return;
  current.applying = true;
  current.error = null;
  panel._queueRender();
  try {
    current.data = await panel._hass.callWS({ type: "gw_energypilot/emhass_sync/apply", entry_id: entryId });
    panel.__epV016Message = { tone: "", text: copy(panel).done };
  } catch (err) {
    current.error = err?.message || String(err);
    panel.__epV016Message = { tone: "error", text: current.error };
  } finally {
    current.applying = false;
    panel._queueRender();
  }
}

function installSyncTools(panel, root) {
  if (!panel.__epV016SettingsOpen || panel.__epV016SettingsTab !== "emhass") return;
  const form = root.querySelector('.ep-v016-form[data-section="emhass"]');
  const actions = form?.querySelector(".ep-v016-actions");
  if (!form || !actions || actions.querySelector(".ep-v028-sync-tools")) return;

  const current = state(panel);
  if (!current.data && !current.loading) queueMicrotask(() => loadSync(panel));

  const holder = document.createElement("div");
  holder.className = "ep-v028-sync-tools";
  const defaults = document.createElement("button");
  defaults.type = "button";
  defaults.className = "ep-v016-action";
  defaults.textContent = copy(panel).defaults;
  defaults.disabled = !current.data?.recommended_options || current.loading || current.applying;
  defaults.addEventListener("click", () => restoreDefaults(panel, form));

  const sync = document.createElement("button");
  sync.type = "button";
  sync.className = "ep-v016-action";
  sync.textContent = copy(panel).sync;
  sync.disabled = current.loading || current.applying || !current.data?.available;
  sync.addEventListener("click", () => applySync(panel));

  const status = document.createElement("span");
  status.className = `ep-v028-sync-state ${current.data?.synchronized ? "ok" : current.data?.changes?.length ? "warn" : ""}`;
  status.textContent = current.loading
    ? copy(panel).checking
    : current.error
      ? current.error
      : current.data?.synchronized
        ? copy(panel).synced
        : current.data?.changes?.length
          ? `${current.data.changes.length} ${copy(panel).changes}`
          : "";

  holder.append(defaults, sync, status);
  actions.prepend(holder);
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV028ConsolidatedRender() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;
  ensureStyles(root);
  installSyncTools(this, root);
};
