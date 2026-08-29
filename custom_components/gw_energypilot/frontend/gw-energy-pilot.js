const DOMAIN = "gw_energypilot";
const VERSION = "0.05";
const STATIC_BASE = "/gw_energypilot_static";

const POWER_KEYS = [
  "pv_total_power",
  "total_load_power",
  "battery_power",
  "meter_total_power_fast",
  "total_inverter_power",
  "ac_active_power",
  "ems_setpoint",
  "target_power",
];

class GWEnergyPilotPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._panel = null;
    this._narrow = false;
    this._route = null;
    this._entityMap = {};
    this._registryLoaded = false;
    this._registryLoading = false;
    this._renderQueued = false;
  }

  set hass(value) {
    this._hass = value;
    if (!this._registryLoaded && !this._registryLoading) {
      this._loadRegistry();
    }
    this._queueRender();
  }

  get hass() {
    return this._hass;
  }

  set panel(value) {
    this._panel = value;
    this._queueRender();
  }

  get panel() {
    return this._panel;
  }

  set narrow(value) {
    this._narrow = Boolean(value);
    this._queueRender();
  }

  get narrow() {
    return this._narrow;
  }

  set route(value) {
    this._route = value;
  }

  get route() {
    return this._route;
  }

  connectedCallback() {
    this._queueRender();
  }

  async _loadRegistry() {
    if (!this._hass?.callWS) {
      return;
    }
    this._registryLoading = true;
    try {
      const entries = await this._hass.callWS({
        type: "config/entity_registry/list",
      });
      const relevant = entries.filter((entry) => entry.platform === DOMAIN);
      const map = {};
      for (const entry of relevant) {
        const configEntryId = entry.config_entry_id || "";
        const uniqueId = entry.unique_id || "";
        if (!configEntryId || !uniqueId.startsWith(`${configEntryId}_`)) {
          continue;
        }
        const key = uniqueId.slice(configEntryId.length + 1);
        map[key] = entry.entity_id;
      }
      this._entityMap = map;
      this._registryLoaded = true;
    } catch (err) {
      console.error("GW EnergyPilot: failed to load entity registry", err);
    } finally {
      this._registryLoading = false;
      this._queueRender();
    }
  }

  _queueRender() {
    if (this._renderQueued) {
      return;
    }
    this._renderQueued = true;
    requestAnimationFrame(() => {
      this._renderQueued = false;
      this._render();
    });
  }

  _entityId(key) {
    return this._entityMap[key] || null;
  }

  _stateByKey(key) {
    const entityId = this._entityId(key);
    return entityId ? this._hass?.states?.[entityId] : null;
  }

  _state(entityId) {
    return entityId ? this._hass?.states?.[entityId] : null;
  }

  _numberByKey(key, fallback = null) {
    return this._numberState(this._stateByKey(key), fallback);
  }

  _numberState(stateObj, fallback = null) {
    if (!stateObj) {
      return fallback;
    }
    const value = Number(stateObj.state);
    return Number.isFinite(value) ? value : fallback;
  }

  _textByKey(key, fallback = "—") {
    const stateObj = this._stateByKey(key);
    if (!stateObj || ["unknown", "unavailable"].includes(stateObj.state)) {
      return fallback;
    }
    return stateObj.state;
  }

  _findState(candidates) {
    for (const entityId of candidates) {
      if (this._hass?.states?.[entityId]) {
        return this._hass.states[entityId];
      }
    }
    return null;
  }

  _findStateBySuffix(suffixes) {
    const states = this._hass?.states || {};
    for (const suffix of suffixes) {
      const match = Object.entries(states).find(([entityId]) =>
        entityId.endsWith(suffix)
      );
      if (match) {
        return match[1];
      }
    }
    return null;
  }

  _formatPower(value) {
    if (!Number.isFinite(value)) {
      return "—";
    }
    const abs = Math.abs(value);
    if (abs >= 1000) {
      return `${(value / 1000).toFixed(abs >= 10000 ? 1 : 2)} kW`;
    }
    return `${Math.round(value)} W`;
  }

  _formatNumber(value, decimals = 1, unit = "") {
    if (!Number.isFinite(value)) {
      return "—";
    }
    return `${value.toFixed(decimals)}${unit ? ` ${unit}` : ""}`;
  }

  _formatState(stateObj, fallback = "—") {
    if (!stateObj || ["unknown", "unavailable"].includes(stateObj.state)) {
      return fallback;
    }
    if (typeof this._hass?.formatEntityState === "function") {
      try {
        return this._hass.formatEntityState(stateObj);
      } catch (_err) {
        // Fall back to raw Home Assistant state below.
      }
    }
    const unit = stateObj.attributes?.unit_of_measurement || "";
    return `${stateObj.state}${unit ? ` ${unit}` : ""}`;
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _flowLabel(value, positiveLabel, negativeLabel, idleLabel = "Idle") {
    if (!Number.isFinite(value) || Math.abs(value) < 50) {
      return idleLabel;
    }
    return value > 0 ? positiveLabel : negativeLabel;
  }

  _batteryMode(power) {
    if (!Number.isFinite(power) || Math.abs(power) < 50) {
      return { label: "Holding", css: "hold" };
    }
    return power < 0
      ? { label: "Charging", css: "charge" }
      : { label: "Discharging", css: "discharge" };
  }

  _gridMode(power) {
    if (!Number.isFinite(power) || Math.abs(power) < 50) {
      return { label: "Balanced", css: "hold" };
    }
    // GoodWe smart-meter convention validated on the ETA test system:
    // positive = export, negative = import.
    return power > 0
      ? { label: "Exporting", css: "export" }
      : { label: "Importing", css: "import" };
  }

  async _toggleAutomatic() {
    const entityId = this._entityId("automatic_control");
    const stateObj = entityId ? this._state(entityId) : null;
    if (!entityId || !stateObj) {
      return;
    }
    const turningOn = stateObj.state !== "on";
    if (
      turningOn &&
      !window.confirm(
        "Enable GW EnergyPilot automatic control?\n\nOnly continue when EMHASS is fully configured, optimization is successful, publish-data is working and the selected P_batt sensor is valid."
      )
    ) {
      return;
    }
    await this._hass.callService(
      "switch",
      turningOn ? "turn_on" : "turn_off",
      { entity_id: entityId }
    );
  }

  _metric(label, value, sub = "") {
    return `
      <div class="metric">
        <div class="metric-label">${this._escape(label)}</div>
        <div class="metric-value">${this._escape(value)}</div>
        ${sub ? `<div class="metric-sub">${this._escape(sub)}</div>` : ""}
      </div>`;
  }

  _render() {
    if (!this.shadowRoot) {
      return;
    }

    const internalPv = this._numberByKey("pv_total_power");
    const pvGenerationState = this._stateByKey("pv_generation_power");
    const pv = pvGenerationState
      ? this._numberState(pvGenerationState, null)
      : internalPv;
    const pvGenerationAttributes = pvGenerationState?.attributes || {};
    const pvSources = Array.isArray(pvGenerationAttributes.sources)
      ? pvGenerationAttributes.sources
      : [];
    const configuredExternalPv = Number(
      pvGenerationAttributes.configured_external_sources || 0
    );
    const useConfiguredPvBreakdown = Boolean(
      pvGenerationState &&
      (configuredExternalPv > 0 || pvGenerationAttributes.internal_enabled === false)
    );
    const load = this._numberByKey("total_load_power");
    const battery = this._numberByKey("battery_power");
    const grid = this._numberByKey("meter_total_power_fast");
    const soc = this._numberByKey("battery_soc");
    const soh = this._numberByKey("battery_soh");
    const inverter = this._numberByKey("total_inverter_power");
    const acActive = this._numberByKey("ac_active_power");

    const pv1 = this._numberByKey("pv1_power");
    const pv2 = this._numberByKey("pv2_power");
    const pv3 = this._numberByKey("pv3_power");
    const pv4 = this._numberByKey("pv4_power");

    const batteryVoltage = this._stateByKey("battery_voltage");
    const batteryCurrent = this._stateByKey("battery_current");
    const batteryTemp = this._stateByKey("battery_max_cell_temperature");
    const bmsTemp = this._stateByKey("bms_package_temperature");
    const inverterTemp = this._stateByKey("inverter_radiator_temperature");
    const maxCharge = this._stateByKey("bms_max_charge_current");
    const maxDischarge = this._stateByKey("bms_max_discharge_current");

    const l1 = this._numberByKey("meter_l1_active_power");
    const l2 = this._numberByKey("meter_l2_active_power");
    const l3 = this._numberByKey("meter_l3_active_power");
    const l1v = this._stateByKey("meter_l1_voltage");
    const l2v = this._stateByKey("meter_l2_voltage");
    const l3v = this._stateByKey("meter_l3_voltage");
    const l1a = this._stateByKey("meter_l1_current");
    const l2a = this._stateByKey("meter_l2_current");
    const l3a = this._stateByKey("meter_l3_current");

    const emsModeState = this._stateByKey("ems_mode");
    const emsMode = emsModeState?.state || "—";
    const emsModeName = emsModeState?.attributes?.mode_name || "Unknown";
    const emsSetpoint = this._numberByKey("ems_setpoint");
    const targetPower = this._numberByKey("target_power");
    const command = this._textByKey("control_command");

    const autoEntity = this._entityId("automatic_control");
    const autoState = autoEntity ? this._state(autoEntity) : null;
    const automaticOn = autoState?.state === "on";

    const pBattState =
      this._findState(["sensor.p_batt_forecast"]) ||
      this._findStateBySuffix([".p_batt_forecast", "_p_batt_forecast"]);
    const optimState =
      this._findState(["sensor.optim_status"]) ||
      this._findStateBySuffix([".optim_status", "_optim_status"]);
    const socForecast =
      this._findState(["sensor.soc_batt_forecast"]) ||
      this._findStateBySuffix([".soc_batt_forecast", "_soc_batt_forecast"]);
    const loadForecast =
      this._findState(["sensor.p_load_forecast"]) ||
      this._findStateBySuffix([".p_load_forecast", "_p_load_forecast"]);
    const pvForecast =
      this._findState(["sensor.p_pv_forecast"]) ||
      this._findStateBySuffix([".p_pv_forecast", "_p_pv_forecast"]);

    const pBatt = this._numberState(pBattState);
    const batteryMode = this._batteryMode(battery);
    const gridMode = this._gridMode(grid);
    const optimText = optimState?.state || "Not detected";
    const optimOk = String(optimText).toLowerCase() === "optimal";

    const socClamped = Number.isFinite(soc) ? Math.min(100, Math.max(0, soc)) : 0;
    const pv4Visible = Number.isFinite(pv4) && Math.abs(pv4) > 20;
    const pvBreakdown = useConfiguredPvBreakdown
      ? pvSources.length > 0
        ? pvSources.map((source, index) => {
            const powerValue = Number(source?.power_w);
            const power = source?.power_w !== null &&
              source?.power_w !== undefined &&
              Number.isFinite(powerValue)
              ? powerValue
              : null;
            const sourceDetail = source?.kind === "internal"
              ? "Internal GoodWe telemetry"
              : source?.entity_id || "External PV entity";
            return `<div class="metric" data-pv-source-index="${index}">
              <div class="metric-label">${this._escape(source?.name || `PV ${index + 1}`)}</div>
              <div class="metric-value">${this._escape(this._formatPower(power))}</div>
              <div class="metric-sub">${this._escape(sourceDetail)}</div>
            </div>`;
          }).join("")
        : `<div class="metric" data-pv-empty>
            <div class="metric-label">PV sources</div>
            <div class="metric-value">—</div>
            <div class="metric-sub">No sources configured</div>
          </div>`
      : `
          ${this._metric("PV1", this._formatPower(pv1))}
          ${this._metric("PV2", this._formatPower(pv2))}
          ${this._metric("PV3", this._formatPower(pv3))}
          ${pv4Visible ? this._metric("PV4", this._formatPower(pv4)) : ""}`;

    const statusClass = automaticOn ? "active" : "inactive";
    const statusText = automaticOn ? "AUTO ACTIVE" : "GOODWE AUTO";

    const registryMessage = !this._registryLoaded
      ? `<div class="notice info">Discovering GW EnergyPilot entities…</div>`
      : Object.keys(this._entityMap).length === 0
      ? `<div class="notice warning">No GW EnergyPilot entities found. Reload the integration or Home Assistant.</div>`
      : "";

    const emhassNotice = !pBattState
      ? `<div class="notice warning"><strong>EMHASS output not detected.</strong> Automatic control should remain off until a valid P_batt forecast is published.</div>`
      : !Number.isFinite(pBatt)
      ? `<div class="notice warning"><strong>EMHASS P_batt is not numeric.</strong> Check optimization and publish-data.</div>`
      : "";

    this.shadowRoot.innerHTML = `
      <style>${this._styles()}</style>
      <main class="page ${this._narrow ? "narrow" : ""}">
        <header class="topbar">
          <div class="brand">
            <img src="${STATIC_BASE}/logo.png" alt="GW EnergyPilot" />
            <div>
              <div class="eyebrow">GOODWE ETA ENERGY MANAGEMENT</div>
              <h1>GW EnergyPilot</h1>
            </div>
          </div>
          <div class="header-actions">
            <span class="status ${statusClass}"><span class="dot"></span>${statusText}</span>
            <span class="version">v${VERSION}</span>
          </div>
        </header>

        ${registryMessage}
        ${emhassNotice}

        <section class="hero-grid">
          <article class="energy-card solar">
            <div class="card-kicker">SOLAR</div>
            <div class="hero-value">${this._escape(this._formatPower(pv))}</div>
            <div class="hero-sub">Current PV production</div>
            <div class="mini-grid">
              ${pvBreakdown}
            </div>
          </article>

          <article class="energy-card home">
            <div class="card-kicker">HOME</div>
            <div class="hero-value">${this._escape(this._formatPower(load))}</div>
            <div class="hero-sub">GoodWe total load</div>
            <div class="balance-row">
              <span>Inverter</span><strong>${this._escape(this._formatPower(inverter))}</strong>
            </div>
            <div class="balance-row">
              <span>AC active</span><strong>${this._escape(this._formatPower(acActive))}</strong>
            </div>
          </article>

          <article class="energy-card grid">
            <div class="card-topline">
              <div class="card-kicker">GRID</div>
              <span class="pill ${gridMode.css}">${gridMode.label}</span>
            </div>
            <div class="hero-value">${this._escape(this._formatPower(grid))}</div>
            <div class="hero-sub">GoodWe smart meter fast total</div>
            <div class="phase-grid">
              ${this._metric("L1", this._formatPower(l1), `${this._formatState(l1v)} · ${this._formatState(l1a)}`)}
              ${this._metric("L2", this._formatPower(l2), `${this._formatState(l2v)} · ${this._formatState(l2a)}`)}
              ${this._metric("L3", this._formatPower(l3), `${this._formatState(l3v)} · ${this._formatState(l3a)}`)}
            </div>
          </article>

          <article class="energy-card battery">
            <div class="card-topline">
              <div class="card-kicker">BATTERY</div>
              <span class="pill ${batteryMode.css}">${batteryMode.label}</span>
            </div>
            <div class="battery-head">
              <div>
                <div class="soc">${Number.isFinite(soc) ? `${Math.round(soc)}%` : "—"}</div>
                <div class="hero-sub">State of charge</div>
              </div>
              <div class="battery-power">${this._escape(this._formatPower(battery))}</div>
            </div>
            <div class="soc-track"><div class="soc-fill" style="width:${socClamped}%"></div></div>
            <div class="mini-grid battery-details">
              ${this._metric("SOH", Number.isFinite(soh) ? `${Math.round(soh)}%` : "—")}
              ${this._metric("Voltage", this._formatState(batteryVoltage))}
              ${this._metric("Current", this._formatState(batteryCurrent))}
              ${this._metric("Max cell temp", this._formatState(batteryTemp))}
            </div>
          </article>
        </section>

        <section class="secondary-grid">
          <article class="panel-card controller">
            <div class="section-title-row">
              <div>
                <div class="card-kicker">ENERGYPILOT CONTROL</div>
                <h2>Controller</h2>
              </div>
              <button class="auto-button ${automaticOn ? "on" : "off"}" id="auto-toggle" ${!autoEntity ? "disabled" : ""}>
                <span class="switch-track"><span class="switch-knob"></span></span>
                ${automaticOn ? "Automatic ON" : "Automatic OFF"}
              </button>
            </div>
            <div class="control-grid">
              ${this._metric("EMS mode", `${emsMode} · ${emsModeName}`)}
              ${this._metric("EMS setpoint", this._formatPower(emsSetpoint))}
              ${this._metric("EnergyPilot target", this._formatPower(targetPower))}
              ${this._metric("Command", command)}
            </div>
            <div class="safety-note">Automatic control returns to GoodWe Auto / AI after an integration reload or Home Assistant restart.</div>
          </article>

          <article class="panel-card emhass">
            <div class="section-title-row">
              <div>
                <div class="card-kicker">OPTIMIZER</div>
                <h2>EMHASS</h2>
              </div>
              <span class="status ${optimOk ? "active" : "inactive"}"><span class="dot"></span>${this._escape(optimText)}</span>
            </div>
            <div class="emhass-target">
              <span>P_batt target</span>
              <strong>${this._escape(this._formatPower(pBatt))}</strong>
            </div>
            <div class="control-grid">
              ${this._metric("SOC forecast", this._formatState(socForecast))}
              ${this._metric("Load forecast", this._formatState(loadForecast))}
              ${this._metric("PV forecast", this._formatState(pvForecast))}
              ${this._metric("Mapping", Number.isFinite(pBatt) ? (pBatt < -50 ? "Mode 11 · Charge" : pBatt > 50 ? "Mode 12 · Discharge" : "Mode 8 · Hold") : "Waiting")}
            </div>
          </article>

          <article class="panel-card thermal">
            <div class="card-kicker">THERMAL & LIMITS</div>
            <h2>System health</h2>
            <div class="control-grid">
              ${this._metric("Inverter radiator", this._formatState(inverterTemp))}
              ${this._metric("BMS package", this._formatState(bmsTemp))}
              ${this._metric("Battery max cell", this._formatState(batteryTemp))}
              ${this._metric("BMS max charge", this._formatState(maxCharge))}
              ${this._metric("BMS max discharge", this._formatState(maxDischarge))}
            </div>
          </article>
        </section>

        <footer>
          <span>GW EnergyPilot v${VERSION}</span>
          <span>Local Modbus TCP · GoodWe ETA</span>
        </footer>
      </main>`;

    const toggle = this.shadowRoot.getElementById("auto-toggle");
    if (toggle) {
      toggle.addEventListener("click", () => this._toggleAutomatic());
    }
  }

  _styles() {
    return `
      :host {
        display: block;
        min-height: 100%;
        color: #eef7ff;
        background:
          radial-gradient(circle at 14% 0%, rgba(0, 222, 255, .12), transparent 28rem),
          radial-gradient(circle at 90% 8%, rgba(0, 255, 156, .08), transparent 30rem),
          #061126;
        --ep-cyan: #19d9ff;
        --ep-green: #18efa3;
        --ep-blue: #0b3e78;
        --ep-card: rgba(9, 25, 52, .88);
        --ep-card-2: rgba(12, 34, 67, .82);
        --ep-border: rgba(122, 192, 255, .14);
        --ep-muted: #91a7bd;
        --ep-text: #eef7ff;
        font-family: var(--paper-font-body1_-_font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
      }
      * { box-sizing: border-box; }
      .page {
        max-width: 1560px;
        margin: 0 auto;
        padding: calc(22px + env(safe-area-inset-top)) calc(24px + env(safe-area-inset-right)) calc(28px + env(safe-area-inset-bottom)) calc(24px + env(safe-area-inset-left));
      }
      .topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 20px;
        margin-bottom: 20px;
      }
      .brand { display: flex; align-items: center; gap: 15px; min-width: 0; }
      .brand img { width: 62px; height: 62px; border-radius: 16px; box-shadow: 0 12px 34px rgba(0, 217, 255, .13); }
      h1, h2, p { margin: 0; }
      h1 { font-size: clamp(26px, 3.1vw, 39px); line-height: 1; letter-spacing: -.035em; }
      h2 { font-size: 22px; margin-top: 3px; letter-spacing: -.02em; }
      .eyebrow, .card-kicker { font-size: 11px; letter-spacing: .16em; color: #6fdff2; font-weight: 800; }
      .header-actions { display: flex; align-items: center; gap: 10px; }
      .version { color: var(--ep-muted); font-size: 12px; border: 1px solid var(--ep-border); border-radius: 999px; padding: 7px 9px; }
      .status { display: inline-flex; align-items: center; gap: 7px; padding: 7px 11px; border-radius: 999px; font-size: 11px; letter-spacing: .08em; font-weight: 800; white-space: nowrap; }
      .status.active { color: #dffff4; background: rgba(24, 239, 163, .11); border: 1px solid rgba(24, 239, 163, .25); }
      .status.inactive { color: #c4d2df; background: rgba(145, 167, 189, .09); border: 1px solid rgba(145, 167, 189, .17); }
      .dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; box-shadow: 0 0 12px currentColor; }
      .notice { margin: 0 0 16px; padding: 12px 14px; border-radius: 12px; font-size: 13px; }
      .notice.warning { color: #ffd9aa; background: rgba(255, 166, 66, .10); border: 1px solid rgba(255, 166, 66, .20); }
      .notice.info { color: #c8f5ff; background: rgba(25, 217, 255, .08); border: 1px solid rgba(25, 217, 255, .18); }
      .hero-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
      .energy-card, .panel-card {
        position: relative;
        overflow: hidden;
        background: linear-gradient(145deg, var(--ep-card), rgba(7, 20, 42, .95));
        border: 1px solid var(--ep-border);
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 14px 44px rgba(0, 0, 0, .16);
      }
      .energy-card::after { content: ""; position: absolute; inset: auto -40px -60px auto; width: 150px; height: 150px; border-radius: 50%; filter: blur(2px); opacity: .08; pointer-events: none; }
      .solar::after { background: var(--ep-cyan); }
      .battery::after { background: var(--ep-green); }
      .grid::after { background: #7fa8ff; }
      .home::after { background: #b56dff; }
      .hero-value { font-size: clamp(31px, 3vw, 48px); font-weight: 790; margin: 9px 0 2px; letter-spacing: -.045em; }
      .hero-sub, .metric-sub, .safety-note { color: var(--ep-muted); }
      .hero-sub { font-size: 13px; }
      .card-topline, .section-title-row, .battery-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
      .mini-grid, .control-grid, .phase-grid { display: grid; gap: 9px; margin-top: 17px; }
      .mini-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .phase-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      .control-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .metric { min-width: 0; padding: 10px 11px; background: rgba(255,255,255,.025); border: 1px solid rgba(255,255,255,.045); border-radius: 12px; }
      .metric-label { color: var(--ep-muted); font-size: 11px; margin-bottom: 4px; }
      .metric-value { font-size: 15px; font-weight: 720; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .metric-sub { font-size: 10px; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .balance-row { display: flex; justify-content: space-between; gap: 10px; padding-top: 11px; margin-top: 11px; border-top: 1px solid rgba(255,255,255,.06); color: var(--ep-muted); font-size: 13px; }
      .balance-row strong { color: var(--ep-text); }
      .pill { font-size: 10px; font-weight: 850; letter-spacing: .05em; padding: 6px 9px; border-radius: 999px; }
      .pill.charge, .pill.export { color: #bfffea; background: rgba(24,239,163,.11); border: 1px solid rgba(24,239,163,.22); }
      .pill.discharge, .pill.import { color: #cceeff; background: rgba(25,217,255,.10); border: 1px solid rgba(25,217,255,.20); }
      .pill.hold { color: #cbd7e1; background: rgba(145,167,189,.08); border: 1px solid rgba(145,167,189,.16); }
      .soc { font-size: 48px; line-height: 1; font-weight: 820; letter-spacing: -.05em; }
      .battery-power { color: var(--ep-green); font-size: 22px; font-weight: 780; }
      .soc-track { height: 10px; margin-top: 16px; background: rgba(255,255,255,.07); border-radius: 999px; overflow: hidden; }
      .soc-fill { height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--ep-cyan), var(--ep-green)); box-shadow: 0 0 18px rgba(24,239,163,.25); }
      .secondary-grid { display: grid; grid-template-columns: 1.3fr 1.1fr .9fr; gap: 14px; margin-top: 14px; }
      .panel-card { min-height: 230px; }
      .auto-button { appearance: none; border: 0; border-radius: 999px; display: flex; align-items: center; gap: 9px; padding: 8px 11px 8px 8px; font-weight: 800; font-size: 11px; cursor: pointer; color: #dbe7f2; background: rgba(255,255,255,.05); }
      .auto-button:disabled { opacity: .45; cursor: not-allowed; }
      .auto-button.on { color: #dffff4; background: rgba(24,239,163,.10); }
      .switch-track { position: relative; width: 31px; height: 18px; border-radius: 999px; background: #33455a; display: inline-block; }
      .switch-knob { position: absolute; width: 14px; height: 14px; border-radius: 50%; top: 2px; left: 2px; background: #e8f2f8; transition: transform .18s ease; }
      .auto-button.on .switch-track { background: rgba(24,239,163,.45); }
      .auto-button.on .switch-knob { transform: translateX(13px); background: #cffff0; }
      .safety-note { font-size: 11px; margin-top: 13px; line-height: 1.45; }
      .emhass-target { display: flex; align-items: end; justify-content: space-between; gap: 15px; padding: 17px 0 4px; }
      .emhass-target span { color: var(--ep-muted); font-size: 12px; }
      .emhass-target strong { font-size: 31px; color: var(--ep-cyan); letter-spacing: -.035em; }
      footer { display: flex; justify-content: space-between; gap: 14px; color: #607890; font-size: 10px; margin-top: 17px; padding: 0 4px; }
      @media (max-width: 1180px) {
        .hero-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .secondary-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .thermal { grid-column: 1 / -1; }
      }
      @media (max-width: 720px) {
        .page { padding-left: calc(12px + env(safe-area-inset-left)); padding-right: calc(12px + env(safe-area-inset-right)); }
        .topbar { align-items: flex-start; }
        .brand img { width: 48px; height: 48px; border-radius: 13px; }
        .eyebrow { font-size: 9px; }
        .header-actions { flex-direction: column; align-items: flex-end; }
        .hero-grid, .secondary-grid { grid-template-columns: 1fr; }
        .thermal { grid-column: auto; }
        .phase-grid { grid-template-columns: 1fr; }
        .section-title-row { align-items: flex-start; }
        .control-grid { grid-template-columns: 1fr 1fr; }
        .energy-card, .panel-card { border-radius: 17px; padding: 16px; }
      }
      @media (max-width: 460px) {
        .control-grid, .mini-grid { grid-template-columns: 1fr; }
        .battery-details { grid-template-columns: 1fr 1fr; }
        .topbar { gap: 8px; }
        .version { display: none; }
      }
    `;
  }
}

if (!customElements.get("gw-energypilot-panel")) {
  customElements.define("gw-energypilot-panel", GWEnergyPilotPanel);
}
