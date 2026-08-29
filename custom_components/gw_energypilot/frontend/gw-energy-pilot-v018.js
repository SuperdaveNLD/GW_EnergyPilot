import "./gw-energy-pilot-v017.js?v=0.45-pv-soc1";

const VERSION = "0.18";
const PANEL_NAME = "gw-energypilot-panel";

const BETA_SOC_FIELDS = [
  {
    key: "battery_discharge_depth_on_grid",
    register: 45356,
    label: "On-grid minimum SOC",
    detail: "Raw G20 register value. Upstream GoodWe maps this to 100 - on-grid DoD.",
  },
  {
    key: "battery_discharge_depth_off_grid",
    register: 45358,
    label: "Off-grid minimum SOC",
    detail: "Raw G20 off-grid SOC floor candidate. Change independently during field validation.",
  },
];

function ensureBetaSocStyles(root) {
  if (root.querySelector("#ep-v018-beta-soc-style")) return;
  const style = document.createElement("style");
  style.id = "ep-v018-beta-soc-style";
  style.textContent = `
    .ep-v018-beta-soc {
      margin-top: 18px;
      padding: 16px;
      border: 1px solid rgba(255,190,72,.20);
      border-radius: 14px;
      background: linear-gradient(145deg, rgba(52,38,9,.28), rgba(9,31,49,.42));
    }
    .ep-v018-beta-soc-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 14px;
      margin-bottom: 12px;
    }
    .ep-v018-beta-soc-kicker {
      color: #f0bd65;
      font-size: 8px;
      font-weight: 900;
      letter-spacing: .14em;
    }
    .ep-v018-beta-soc h4 {
      margin: 4px 0 0;
      color: #edf8ff;
      font-size: 16px;
    }
    .ep-v018-beta-soc-copy {
      max-width: 760px;
      margin: 7px 0 0;
      color: #7895aa;
      font-size: 9px;
      line-height: 1.55;
    }
    .ep-v018-beta-badge {
      flex: 0 0 auto;
      padding: 5px 8px;
      border: 1px solid rgba(245,184,74,.28);
      border-radius: 999px;
      color: #efc77d;
      background: rgba(86,58,13,.24);
      font-size: 8px;
      font-weight: 900;
      letter-spacing: .08em;
    }
    .ep-v018-beta-grid {
      display: grid;
      grid-template-columns: repeat(2,minmax(0,1fr));
      gap: 10px;
    }
    .ep-v018-beta-card {
      padding: 12px;
      border: 1px solid rgba(94,166,205,.11);
      border-radius: 11px;
      background: rgba(4,22,39,.58);
    }
    .ep-v018-beta-label {
      display: flex;
      justify-content: space-between;
      gap: 8px;
      color: #d2e6ef;
      font-size: 10px;
      font-weight: 800;
    }
    .ep-v018-beta-label small {
      color: #67869b;
      font-size: 8px;
      font-weight: 700;
    }
    .ep-v018-beta-detail {
      min-height: 28px;
      margin: 6px 0 9px;
      color: #617f93;
      font-size: 8px;
      line-height: 1.45;
    }
    .ep-v018-beta-control {
      display: grid;
      grid-template-columns: minmax(0,1fr) auto;
      gap: 7px;
    }
    .ep-v018-beta-input {
      min-width: 0;
      min-height: 38px;
      box-sizing: border-box;
      padding: 8px 10px;
      border: 1px solid rgba(96,179,224,.17);
      border-radius: 9px;
      color: #effbff;
      background: rgba(3,17,31,.80);
      outline: none;
      font-size: 11px;
    }
    .ep-v018-beta-input:focus { border-color: rgba(55,218,232,.42); }
    .ep-v018-beta-write,
    .ep-v018-beta-refresh {
      min-height: 38px;
      padding: 8px 11px;
      border: 1px solid rgba(236,182,78,.24);
      border-radius: 9px;
      color: #f3d8a3;
      background: rgba(78,52,12,.32);
      cursor: pointer;
      font-size: 9px;
      font-weight: 850;
    }
    .ep-v018-beta-write:disabled,
    .ep-v018-beta-refresh:disabled { opacity: .42; cursor: wait; }
    .ep-v018-beta-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-top: 11px;
      color: #6f8da1;
      font-size: 8px;
      line-height: 1.45;
    }
    .ep-v018-beta-message.ok { color: #67dcae; }
    .ep-v018-beta-message.error { color: #ef9d96; }
    @media (max-width: 720px) {
      .ep-v018-beta-grid { grid-template-columns: 1fr; }
      .ep-v018-beta-soc-head,
      .ep-v018-beta-footer { flex-direction: column; align-items: stretch; }
    }
  `;
  root.appendChild(style);
}

function betaSnapshotV018(panel) {
  const optimizeId = panel._entityId("optimize_now");
  const attrs = (optimizeId ? panel._state(optimizeId)?.attributes : null) || {};
  const fields = [
    ["On-grid minimum SOC 45356 %", attrs.battery_discharge_depth_on_grid_45356],
    ["Off-grid minimum SOC 45358 %", attrs.battery_discharge_depth_off_grid_45358],
    ["SOC protection candidate 47500", attrs.battery_soc_protection_47500],
    ["Extended grid export candidate 36104 kWh", attrs.meter_total_energy_export_extended_candidate],
    ["Extended grid import candidate 36120 kWh", attrs.meter_total_energy_import_extended_candidate],
    ["Legacy grid export 36015 kWh", attrs.meter_total_energy_export],
    ["Legacy grid import 36017 kWh", attrs.meter_total_energy_import],
    ["Battery SOC", attrs.battery_soc],
    ["EMS mode 47511", attrs.ems_mode],
    ["EMS setpoint 47512", attrs.ems_setpoint],
  ];
  return [
    `GW EnergyPilot v${VERSION} beta G20 diagnostics`,
    "45356/45358: manual field-test settings with write + read-back verification.",
    "47500/36104/36120: read-only Beta diagnostics; no Beta value is an Automatic Control target.",
    ...fields.map(([label, value]) => `${label}: ${value ?? "—"}`),
  ].join("\n");
}

function alignBetaDiagnostics(panel, root) {
  const labels = {
    "soc-on-grid": "BETA · On-grid minimum SOC 45356",
    "soc-off-grid": "BETA · Off-grid minimum SOC 45358",
  };
  for (const [marker, label] of Object.entries(labels)) {
    const rowLabel = root.querySelector(`[data-v016-beta="${marker}"] span`);
    if (rowLabel) rowLabel.textContent = label;
  }

  const note = root.querySelector(".ep-v016-beta-note");
  if (note) {
    note.textContent = "BETA: 45356/45358 are manual v0.18 minimum-SOC field-test settings with verified read-back. 47500, 36104 and 36120 remain read-only. No Beta value is an Automatic Control target.";
  }

  const oldCopy = root.querySelector(".ep-v016-copy");
  if (!oldCopy || oldCopy.dataset.v018Copy === "1") return;

  const button = oldCopy.cloneNode(true);
  button.dataset.v018Copy = "1";
  button.textContent = "Copy beta diagnostics";
  oldCopy.replaceWith(button);
  button.addEventListener("click", async () => {
    const text = betaSnapshotV018(panel);
    try {
      await navigator.clipboard.writeText(text);
      const previous = button.textContent;
      button.textContent = "Copied";
      setTimeout(() => { button.textContent = previous; }, 1200);
    } catch (_err) {
      window.prompt("Copy EnergyPilot beta diagnostics", text);
    }
  });
}

async function loadBetaSoc(panel, entryId, force = false) {
  if (!panel._hass?.callWS || !entryId || panel.__epV018BetaLoading) return;
  if (!force && panel.__epV018BetaLoadedEntry === entryId && panel.__epV018BetaData) return;
  panel.__epV018BetaLoading = true;
  panel.__epV018BetaMessage = null;
  panel._queueRender();
  try {
    panel.__epV018BetaData = await panel._hass.callWS({
      type: "gw_energypilot/beta_soc/get",
      entry_id: entryId,
    });
    panel.__epV018BetaLoadedEntry = entryId;
  } catch (err) {
    panel.__epV018BetaMessage = { tone: "error", text: err?.message || String(err) };
  } finally {
    panel.__epV018BetaLoading = false;
    panel._queueRender();
  }
}

async function writeBetaSoc(panel, entryId, field, input) {
  if (panel.__epV018BetaSaving || !entryId) return;
  const value = Number(input.value);
  if (!Number.isInteger(value) || value < 0 || value > 100) {
    panel.__epV018BetaMessage = {
      tone: "error",
      text: "Use a whole minimum-SOC value from 0 to 100%.",
    };
    panel._queueRender();
    return;
  }

  const current = panel.__epV018BetaData?.values?.[field.key];
  if (current === value) {
    panel.__epV018BetaMessage = { tone: "ok", text: `${field.label} is already ${value}%.` };
    panel._queueRender();
    return;
  }

  const confirmed = window.confirm(
    `Write ${value}% directly to GoodWe Beta register ${field.register} (${field.label})?\n\n` +
    "EnergyPilot will write only this one register and verify the value by reading it back."
  );
  if (!confirmed) return;

  panel.__epV018BetaSaving = field.key;
  panel.__epV018BetaMessage = {
    tone: "",
    text: `Writing register ${field.register} and verifying read-back…`,
  };
  panel._queueRender();

  try {
    const result = await panel._hass.callWS({
      type: "gw_energypilot/beta_soc/set",
      entry_id: entryId,
      key: field.key,
      value,
    });
    panel.__epV018BetaData = result;
    panel.__epV018BetaLoadedEntry = entryId;
    panel.__epV018BetaMessage = {
      tone: "ok",
      text: result.changed
        ? `${field.label}: ${result.previous}% → ${result.readback}% (read-back verified).`
        : `${field.label} remains ${result.readback}%.`,
    };
  } catch (err) {
    panel.__epV018BetaMessage = { tone: "error", text: err?.message || String(err) };
  } finally {
    panel.__epV018BetaSaving = null;
    panel._queueRender();
  }
}

function renderBetaSocSettings(panel, root) {
  if (!panel.__epV016SettingsOpen || panel.__epV016SettingsTab !== "goodwe") return;

  const entryId = panel.__epV016SettingsData?.entry_id;
  const content = root.querySelector(".ep-v016-settings-content");
  const form = content?.querySelector(".ep-v016-form[data-section='goodwe']");
  if (!entryId || !content || !form || content.querySelector(".ep-v018-beta-soc")) return;

  ensureBetaSocStyles(root);
  if (panel.__epV018BetaLoadedEntry !== entryId && !panel.__epV018BetaLoading) {
    loadBetaSoc(panel, entryId);
  }

  const data = panel.__epV018BetaLoadedEntry === entryId ? panel.__epV018BetaData : null;
  const cards = BETA_SOC_FIELDS.map((field) => {
    const value = data?.values?.[field.key];
    const available = data?.available?.[field.key] === true;
    const busy = Boolean(panel.__epV018BetaSaving);
    return `
      <div class="ep-v018-beta-card">
        <div class="ep-v018-beta-label">
          <span>${panel._escape(field.label)}</span>
          <small>register ${field.register}</small>
        </div>
        <div class="ep-v018-beta-detail">${panel._escape(field.detail)}</div>
        <div class="ep-v018-beta-control">
          <input
            class="ep-v018-beta-input"
            type="number"
            min="0"
            max="100"
            step="1"
            value="${panel._escape(value ?? "")}"
            data-beta-soc-input="${panel._escape(field.key)}"
            ${!available || busy ? "disabled" : ""}
            aria-label="${panel._escape(field.label)}">
          <button
            type="button"
            class="ep-v018-beta-write"
            data-beta-soc-write="${panel._escape(field.key)}"
            ${!available || busy ? "disabled" : ""}>
            ${panel.__epV018BetaSaving === field.key ? "Verifying…" : "Write + verify"}
          </button>
        </div>
      </div>`;
  }).join("");

  const message = panel.__epV018BetaMessage
    ? `<span class="ep-v018-beta-message ${panel._escape(panel.__epV018BetaMessage.tone || "")}">${panel._escape(panel.__epV018BetaMessage.text)}</span>`
    : `<span class="ep-v018-beta-message">Change one register at a time. 47500 remains read-only while its G20 meaning is unresolved.</span>`;

  const beta = document.createElement("section");
  beta.className = "ep-v018-beta-soc";
  beta.innerHTML = `
    <div class="ep-v018-beta-soc-head">
      <div>
        <div class="ep-v018-beta-soc-kicker">G20 FIELD TEST · DIRECT INVERTER SETTING</div>
        <h4>Battery minimum SOC limits</h4>
        <p class="ep-v018-beta-soc-copy">
          These controls write the inverter itself; they are not stored in the Home Assistant config entry.
          Register 45356 is now treated as the raw on-grid minimum SOC floor (equivalent DoD = 100 − value),
          matching current upstream GoodWe handling and the observed 10% G20 discharge stop. Register 45358 is
          the off-grid counterpart. Both remain Beta until this hardware test is completed.
        </p>
      </div>
      <span class="ep-v018-beta-badge">BETA WRITE TEST</span>
    </div>
    <div class="ep-v018-beta-grid">${cards}</div>
    <div class="ep-v018-beta-footer">
      ${message}
      <button type="button" class="ep-v018-beta-refresh" ${panel.__epV018BetaLoading || panel.__epV018BetaSaving ? "disabled" : ""}>
        ${panel.__epV018BetaLoading ? "Refreshing…" : "Refresh values"}
      </button>
    </div>`;

  form.insertAdjacentElement("afterend", beta);

  beta.querySelectorAll("[data-beta-soc-write]").forEach((button) => {
    button.addEventListener("click", () => {
      const field = BETA_SOC_FIELDS.find((item) => item.key === button.dataset.betaSocWrite);
      const input = beta.querySelector(`[data-beta-soc-input="${button.dataset.betaSocWrite}"]`);
      if (field && input) writeBetaSoc(panel, entryId, field, input);
    });
  });
  beta.querySelector(".ep-v018-beta-refresh")?.addEventListener("click", () => {
    loadBetaSoc(panel, entryId, true);
  });

  const connectionNote = content.querySelector(".ep-v016-goodwe-note");
  if (connectionNote && !connectionNote.dataset.v018BetaNote) {
    connectionNote.dataset.v018BetaNote = "1";
    connectionNote.innerHTML += " <strong>G20 field test:</strong> battery minimum-SOC register controls are shown below and are written independently from connection settings.";
  }
}

await customElements.whenDefined(PANEL_NAME);
const PanelClass = customElements.get(PANEL_NAME);
const previousRender = PanelClass.prototype._render;

PanelClass.prototype._render = function energyPilotV018Render() {
  previousRender.call(this);
  const root = this.shadowRoot;
  if (!root) return;

  alignBetaDiagnostics(this, root);
  renderBetaSocSettings(this, root);

  const versionBadge = root.querySelector(".version");
  if (versionBadge) versionBadge.textContent = `v${VERSION} BETA`;
  const footerItems = root.querySelectorAll("footer span");
  if (footerItems.length > 0) footerItems[0].textContent = `GW EnergyPilot v${VERSION} · BETA`;
};
