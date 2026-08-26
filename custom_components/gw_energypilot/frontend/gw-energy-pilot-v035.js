import "./gw-energy-pilot-v034.js?v=0.35-release1";
import "./gw-energy-pilot-v031-window-controls.js?v=0.35-controls-rewrite1";
import "./gw-energy-pilot-v036-flow-direction.js?v=0.35-flow-direction1";

const VERSION = "0.35";
const PANEL_NAME = "gw-energypilot-panel";
const HASS_RENDER_BATCH_MS = 100;
const DEFAULT_EXTERNAL_ENTITIES = [
  "sensor.p_batt_forecast",
  "sensor.p_grid_forecast",
  "sensor.optim_status",
  "sensor.soc_batt_forecast",
  "sensor.p_load_forecast",
  "sensor.p_pv_forecast",
];
const EXTERNAL_ENTITY_SUFFIXES = [
  ".p_batt_forecast",
  "_p_batt_forecast",
  ".p_grid_forecast",
  "_p_grid_forecast",
  ".optim_status",
  "_optim_status",
  ".soc_batt_forecast",
  "_soc_batt_forecast",
  ".p_load_forecast",
  "_p_load_forecast",
  ".p_pv_forecast",
  "_p_pv_forecast",
];

export function relevantStateObjectsChanged(previousStates, nextStates, entityIds) {
  if (!previousStates || !nextStates) return true;
  for (const entityId of entityIds || []) {
    if (previousStates[entityId] !== nextStates[entityId]) return true;
  }
  return false;
}

export function uiContextSignature(hass) {
  return JSON.stringify({
    language: hass?.locale?.language || hass?.language || "",
    numberFormat: hass?.locale?.number_format || "",
    timeFormat: hass?.locale?.time_format || "",
    dateFormat: hass?.locale?.date_format || "",
    userId: hass?.user?.id || "",
    isAdmin: hass?.user?.is_admin === true,
    darkMode: hass?.themes?.darkMode === true,
    selectedTheme: hass?.selectedTheme?.theme || "",
  });
}

function refreshExternalEntityIds(panel, hass, force = false) {
  const states = hass?.states || {};
  const stateCount = Object.keys(states).length;
  if (
    !force &&
    panel.__epV035ExternalEntityIds &&
    panel.__epV035ObservedStateCount === stateCount
  ) {
    return panel.__epV035ExternalEntityIds;
  }

  const ids = new Set(DEFAULT_EXTERNAL_ENTITIES);
  for (const entityId of Object.keys(states)) {
    if (EXTERNAL_ENTITY_SUFFIXES.some((suffix) => entityId.endsWith(suffix))) {
      ids.add(entityId);
    }
  }
  panel.__epV035ExternalEntityIds = [...ids];
  panel.__epV035ObservedStateCount = stateCount;
  return panel.__epV035ExternalEntityIds;
}

function configuredExternalEntityIds(panel, hass) {
  const ids = new Set();
  const optimizeId = panel._entityId?.("optimize_now");
  const optimizeState = optimizeId ? hass?.states?.[optimizeId] : null;
  const attrs = optimizeState?.attributes || {};
  for (const key of ["p_batt_entity", "p_grid_entity", "optim_status_entity"]) {
    const entityId = attrs[key];
    if (typeof entityId === "string" && entityId.includes(".")) ids.add(entityId);
  }

  const planEntity = panel.__epV027BatteryPlanData?.payload?.battery_plan?.entity_id;
  if (typeof planEntity === "string" && planEntity.includes(".")) ids.add(planEntity);
  return ids;
}

function relevantEntityIds(panel, previousHass, nextHass) {
  const ids = new Set(Object.values(panel._entityMap || {}).filter(Boolean));
  const previousCount = Object.keys(previousHass?.states || {}).length;
  const nextCount = Object.keys(nextHass?.states || {}).length;
  for (const entityId of refreshExternalEntityIds(
    panel,
    nextHass,
    previousCount !== nextCount
  )) {
    ids.add(entityId);
  }
  for (const entityId of configuredExternalEntityIds(panel, previousHass)) ids.add(entityId);
  for (const entityId of configuredExternalEntityIds(panel, nextHass)) ids.add(entityId);
  return ids;
}

function scheduleHassRender(panel) {
  if (panel.__epV035HassRenderTimer) return;
  panel.__epV035HassRenderTimer = window.setTimeout(() => {
    panel.__epV035HassRenderTimer = null;
    panel._queueRender();
  }, HASS_RENDER_BATCH_MS);
}

function installRelevantHassGuard(PanelClass) {
  if (PanelClass.prototype.__epV035RelevantHassGuardInstalled) return;
  const descriptor = Object.getOwnPropertyDescriptor(PanelClass.prototype, "hass");
  if (!descriptor?.set) return;

  Object.defineProperty(PanelClass.prototype, "hass", {
    configurable: descriptor.configurable,
    enumerable: descriptor.enumerable,
    get() {
      return descriptor.get ? descriptor.get.call(this) : this._hass;
    },
    set(value) {
      const previousHass = this._hass;

      // Preserve the original initialization and entity-registry discovery.
      if (!previousHass || !this._registryLoaded) {
        descriptor.set.call(this, value);
        return;
      }

      // Always retain the newest Home Assistant snapshot. Only the expensive
      // full-shadow-DOM rebuild is filtered and batched.
      this._hass = value;

      // Existing settings forms deliberately remain stable while being edited;
      // their own actions request explicit renders when required.
      if (this.__epV016SettingsOpen) return;

      const contextChanged =
        uiContextSignature(previousHass) !== uiContextSignature(value);
      const statesChanged = relevantStateObjectsChanged(
        previousHass.states,
        value?.states,
        relevantEntityIds(this, previousHass, value)
      );
      if (contextChanged || statesChanged) scheduleHassRender(this);
    },
  });
  PanelClass.prototype.__epV035RelevantHassGuardInstalled = true;
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
installRelevantHassGuard(PanelClass);

if (!PanelClass.prototype.__epV035StableRenderInstalled) {
  const previousRender = PanelClass.prototype._render;
  PanelClass.prototype._render = function energyPilotV035StableRender() {
    if (this.__epV035HassRenderTimer) {
      window.clearTimeout(this.__epV035HassRenderTimer);
      this.__epV035HassRenderTimer = null;
    }

    previousRender.call(this);
    const root = this.shadowRoot;
    if (!root) return;

    const versionBadge = root.querySelector(".version");
    if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;

    const footerItems = root.querySelectorAll("footer span");
    if (footerItems.length > 0) {
      footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
    }
  };
  PanelClass.prototype.__epV035StableRenderInstalled = true;
}
