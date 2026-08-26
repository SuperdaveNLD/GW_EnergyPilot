const DEFAULT_FLOW_THRESHOLD_W = 50;

function finiteNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export function flowAnimationDirections(
  values,
  threshold = DEFAULT_FLOW_THRESHOLD_W
) {
  const pv = finiteNumber(values?.pv);
  const grid = finiteNumber(values?.grid);
  const house = finiteNumber(values?.house);
  const battery = finiteNumber(values?.battery);
  const direction = (value, positive, negative) => {
    if (value === null || Math.abs(value) < threshold) return null;
    return value > 0 ? positive : negative;
  };

  return {
    // Physical dashboard geometry:
    // PV is left of the hub; positive production travels left -> right.
    pv: direction(pv, "normal", "reverse"),
    // Grid is right of the hub. GoodWe positive = export (hub -> grid),
    // negative = import (grid -> hub).
    grid: direction(grid, "normal", "reverse"),
    // House is above the hub. Positive load travels bottom -> top.
    house: direction(house, "reverse", "normal"),
    // Battery is below the hub. Positive = discharge (bottom -> top),
    // negative = charge (top -> bottom).
    battery: direction(battery, "reverse", "normal"),
  };
}

export function relevantStateObjectsChanged(
  previousStates,
  nextStates,
  entityIds
) {
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
