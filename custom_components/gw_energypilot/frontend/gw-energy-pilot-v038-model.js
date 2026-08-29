export const CUSTOM_MODE = "custom";
export const FLOW_THRESHOLD_W = 50;
export const PROFILE_KEYS = Object.freeze([
  "mad_steve",
  "gold_rush",
  "balanced",
  "battery_saver",
]);

const PROFILE_TEXT = {
  en: {
    mad_steve: {
      label: "Mad-Steve",
      description:
        "Maximum economic freedom up to 100% SOC with anti-churn protection and no extra SOC or power-stress penalty.",
    },
    gold_rush: {
      label: "Gold Rush",
      description:
        "Profit first with a 96% hard maximum, anti-churn protection and light power stress.",
    },
    balanced: {
      label: "Balanced",
      description:
        "Balances trading value and battery preservation with a 95% hard maximum and moderate power stress.",
    },
    battery_saver: {
      label: "Battery Saver",
      description:
        "Uses a 90% hard maximum and the strongest low-SOC and high-power preservation penalties.",
    },
    custom: {
      label: "Custom",
      description:
        "Keep the current EMHASS battery values and tune the main limits manually.",
    },
  },
  nl: {
    mad_steve: {
      label: "Mad-Steve",
      description:
        "Maximale economische vrijheid tot 100% SOC, met anti-churnbescherming en zonder extra SOC- of vermogensstraf.",
    },
    gold_rush: {
      label: "Gold Rush",
      description:
        "Winst voorop met een harde bovengrens van 96%, anti-churnbescherming en lichte vermogensstress.",
    },
    balanced: {
      label: "Gebalanceerd",
      description:
        "Balanceert handelswaarde en batterijbehoud met een harde bovengrens van 95% en gematigde vermogensstress.",
    },
    battery_saver: {
      label: "Batterijbesparing",
      description:
        "Gebruikt een harde bovengrens van 90% en de sterkste bescherming tegen lage SOC en hoog vermogen.",
    },
    custom: {
      label: "Aangepast",
      description:
        "Behoud de huidige EMHASS-batterijwaarden en stel de belangrijkste limieten handmatig af.",
    },
  },
};

export function normalizeLanguage(value) {
  return String(value || "en").toLowerCase().split(/[-_]/)[0] === "nl"
    ? "nl"
    : "en";
}

export function localizedProfile(language, mode) {
  const key = typeof mode === "string" ? mode : mode?.key;
  const source = typeof mode === "object" && mode ? mode : {};
  const localized = PROFILE_TEXT[normalizeLanguage(language)]?.[key];
  return {
    key,
    label: localized?.label || source.label || String(key || ""),
    description: localized?.description || source.description || "",
  };
}

export function canonicalProfiles(language, modes = []) {
  const backendModes = new Map(
    modes.filter((mode) => mode?.key).map((mode) => [mode.key, mode])
  );
  return [
    ...PROFILE_KEYS.map((key) =>
      localizedProfile(language, backendModes.get(key) || { key })
    ),
    localizedProfile(language, { key: CUSTOM_MODE }),
  ];
}

function finite(value) {
  const number = Number(value);
  return value !== null && value !== undefined && Number.isFinite(number)
    ? number
    : null;
}

export function resolveHousePower(rawLoad, pv, grid, battery) {
  const load = finite(rawLoad);
  const pvPower = finite(pv);
  const gridPower = finite(grid);
  const batteryPower = finite(battery);
  const calculated =
    pvPower !== null && gridPower !== null && batteryPower !== null
      ? pvPower - gridPower + batteryPower
      : null;

  if (load === null) {
    return calculated !== null && calculated >= 0 ? calculated : null;
  }
  if (load < 0 && calculated !== null && calculated >= 0) {
    return calculated;
  }
  if (
    calculated !== null &&
    calculated >= 0 &&
    Math.abs(load - calculated) > Math.max(1500, Math.abs(calculated) * 0.8)
  ) {
    return calculated;
  }
  return Math.max(0, load);
}

export function flowMotionMap(values, threshold = FLOW_THRESHOLD_W) {
  const pv = finite(values?.pv);
  const grid = finite(values?.grid);
  const battery = finite(values?.battery);
  const house = resolveHousePower(values?.house, pv, grid, battery);

  return {
    // PV node is left of the hub; production moves right.
    pv: pv !== null && pv > threshold ? "right" : "idle",

    // GoodWe meter: positive export moves right from hub to grid; negative
    // import moves left from grid to hub.
    grid:
      grid === null || Math.abs(grid) < threshold
        ? "idle"
        : grid > 0
          ? "right"
          : "left",

    // House is above the hub. Positive house load is supplied upward.
    house:
      house === null || Math.abs(house) < threshold
        ? "idle"
        : house > 0
          ? "up"
          : "down",

    // GoodWe battery: positive discharge moves up to the hub; negative charge
    // moves down from the hub to the battery.
    battery:
      battery === null || Math.abs(battery) < threshold
        ? "idle"
        : battery > 0
          ? "up"
          : "down",
  };
}

export function flowVisualMap(values, threshold = FLOW_THRESHOLD_W) {
  const pv = finite(values?.pv);
  const grid = finite(values?.grid);
  const battery = finite(values?.battery);
  const house = resolveHousePower(values?.house, pv, grid, battery);
  const direction = flowMotionMap({ pv, grid, battery, house }, threshold);
  const powers = { pv, grid, house, battery };
  const activeMaximum = Math.max(
    0,
    ...Object.entries(powers)
      .filter(([key, power]) => power !== null && direction[key] !== "idle")
      .map(([, power]) => Math.abs(power))
  );

  return Object.fromEntries(
    Object.entries(powers).map(([key, power]) => {
      if (power === null) {
        return [key, {
          direction: "idle",
          status: "unknown",
          intensity: "none",
          power: null,
        }];
      }
      if (direction[key] === "idle") {
        return [key, {
          direction: "idle",
          status: "idle",
          intensity: "none",
          power,
        }];
      }

      const relative = activeMaximum > 0 ? Math.abs(power) / activeMaximum : 0;
      return [key, {
        direction: direction[key],
        status: "active",
        intensity: relative >= 0.75 ? "high" : relative >= 0.35 ? "medium" : "low",
        power,
      }];
    })
  );
}
