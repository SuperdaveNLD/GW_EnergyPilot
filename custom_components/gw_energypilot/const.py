"""Constants for GW EnergyPilot."""

DOMAIN = "gw_energypilot"
NAME = "GW EnergyPilot"

CONF_SLAVE = "slave"
CONF_USE_GOODWE_SMART_METER = "use_goodwe_smart_meter"
CONF_CONTROL_STRATEGY = "control_strategy"
CONF_P_BATT_ENTITY = "p_batt_entity"
CONF_P_GRID_ENTITY = "p_grid_entity"
CONF_OPTIM_STATUS_ENTITY = "optim_status_entity"
CONF_OPTIM_REQUIRED_STATE = "optim_required_state"
CONF_ENABLE_EV_COORDINATION = "enable_ev_coordination"
CONF_EV_MODE_ENTITY = "ev_mode_entity"
CONF_EV_POWER_ENTITY = "ev_power_entity"
CONF_EV_ONLINE_ENTITY = "ev_online_entity"
CONF_ENABLE_INTERNAL_PV = "enable_internal_pv"
CONF_ENABLE_EXTERNAL_PV = "enable_external_pv"
CONF_EXTERNAL_PV_ENTITY_1 = "external_pv_entity_1"
CONF_EXTERNAL_PV_ENTITY_2 = "external_pv_entity_2"
CONF_EXTERNAL_PV_ENTITY_3 = "external_pv_entity_3"
CONF_EXTERNAL_PV_ENTITY_4 = "external_pv_entity_4"
EXTERNAL_PV_ENTITY_KEYS = (
    CONF_EXTERNAL_PV_ENTITY_1,
    CONF_EXTERNAL_PV_ENTITY_2,
    CONF_EXTERNAL_PV_ENTITY_3,
    CONF_EXTERNAL_PV_ENTITY_4,
)
CONF_MAX_POWER = "max_power"
CONF_DEADBAND = "deadband"
CONF_EV_DEADBAND = "ev_deadband"
CONF_ENABLE_EV_LOAD_BALANCING = "enable_ev_load_balancing"
CONF_GRID_CONNECTION_PROFILE = "grid_connection_profile"
CONF_GRID_CUSTOM_CURRENT = "grid_custom_current"
# Kept as a legacy option key so an EV settings save can remove the former
# manually selected grid-current sensor from existing config entries.
CONF_EV_GRID_CURRENT_ENTITY = "ev_grid_current_entity"
CONF_EV_CHARGER_CURRENT_ENTITY = "ev_charger_current_entity"
CONF_EV_CHARGER_ALLOCATED_CURRENT_ENTITY = "ev_charger_allocated_current_entity"
CONF_EV_CHARGER_PHASES = "ev_charger_phases"
CONF_EV_CHARGER_PHASE = "ev_charger_phase"
CONF_EV_CHARGER_MIN_CURRENT = "ev_charger_min_current"
CONF_EV_CHARGER_MAX_CURRENT = "ev_charger_max_current"
CONF_EV_LOAD_BALANCE_WINDOW = "ev_load_balance_window"
CONF_SCAN_INTERVAL = "scan_interval"

CONTROL_STRATEGY_BATTERY = "battery"
CONTROL_STRATEGY_GRID = "grid"
CONTROL_STRATEGY_HYBRID = "hybrid"
CONTROL_STRATEGIES = {
    CONTROL_STRATEGY_BATTERY,
    CONTROL_STRATEGY_GRID,
    CONTROL_STRATEGY_HYBRID,
}

# Built-in EMHASS orchestration.
CONF_ENABLE_EMHASS_ORCHESTRATOR = "enable_emhass_orchestrator"
CONF_EMHASS_URL = "emhass_url"
CONF_EMHASS_OPTIMIZATION_INTERVAL = "emhass_optimization_interval"
CONF_EMHASS_SOC_FINAL = "emhass_soc_final"
CONF_EMHASS_FALLBACK_LOAD = "emhass_fallback_load"
CONF_USE_NORDPOOL_PRICES = "use_nordpool_prices"
CONF_OPTIMIZE_ON_TOMORROW_PRICES = "optimize_on_tomorrow_prices"
CONF_NORDPOOL_AREA = "nordpool_area"
CONF_NORDPOOL_CURRENCY = "nordpool_currency"
CONF_BUY_PRICE_ADDER = "buy_price_adder"
CONF_SELL_PRICE_DEDUCTION = "sell_price_deduction"
CONF_BATTERY_SAVER_MODE = "battery_saver_mode"

DEFAULT_PORT = 502
DEFAULT_SLAVE = 247
# Existing installations without an explicit strategy retain the legacy
# boolean mapping: False = battery control, True = grid control.
DEFAULT_USE_GOODWE_SMART_METER = False
DEFAULT_CONTROL_STRATEGY = CONTROL_STRATEGY_BATTERY
DEFAULT_MAX_POWER = 15000
DEFAULT_DEADBAND = 300
DEFAULT_EV_DEADBAND = 500
DEFAULT_ENABLE_EV_LOAD_BALANCING = False
DEFAULT_GRID_CONNECTION_PROFILE = "3x25"
DEFAULT_GRID_CUSTOM_CURRENT = 25
DEFAULT_EV_CHARGER_PHASES = 3
DEFAULT_EV_CHARGER_PHASE = "l1"
DEFAULT_EV_CHARGER_MIN_CURRENT = 6
DEFAULT_EV_CHARGER_MAX_CURRENT = 16
DEFAULT_EV_LOAD_BALANCE_WINDOW = 15
EV_LOAD_BALANCE_WINDOW_OPTIONS = (1, 2, 3, 5, 10, 15)
EV_LOAD_BALANCE_HYSTERESIS = 0.5
EV_FEEDBACK_TOLERANCE = 0.25
EV_FEEDBACK_TIMEOUT_SECONDS = 60
EV_CHARGER_PHASE_OPTIONS = ("l1", "l2", "l3")

# Per-phase current limits. Grid-current observation comes directly from the
# GoodWe meter L1/L2/L3 telemetry owned by this config entry.
GRID_CONNECTION_PROFILES = {
    "1x25": (1, 25),
    "1x35": (1, 35),
    "1x40": (1, 40),
    "3x25": (3, 25),
    "3x35": (3, 35),
    "3x40": (3, 40),
    "3x50": (3, 50),
    "3x63": (3, 63),
    "3x80": (3, 80),
}
GRID_CONNECTION_CUSTOM_PROFILES = {"custom_1_phase": 1, "custom_3_phase": 3}
EV_CONNECTIVITY_GRACE_SECONDS = 300
DEFAULT_ENABLE_INTERNAL_PV = True
DEFAULT_ENABLE_EXTERNAL_PV = False
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_P_BATT_ENTITY = "sensor.p_batt_forecast"
DEFAULT_P_GRID_ENTITY = "sensor.p_grid_forecast"
DEFAULT_OPTIM_STATUS_ENTITY = "sensor.optim_status"
DEFAULT_OPTIM_REQUIRED_STATE = "Optimal"

# Kept only for backwards-compatible diagnostics in v0.22+. The old 30-second
# mode-11 grid-neutral feedback loop is no longer scheduled or used when GoodWe
# smart-meter control is enabled; modes 9/10 close the PCC loop inside GoodWe.
GRID_NEUTRAL_CONTROL_INTERVAL_SECONDS = 30

# Existing installations upgrade with the native schedule OFF to avoid running
# alongside a legacy YAML scheduler. Fresh installations suggest ON in the
# config flow.
DEFAULT_ENABLE_EMHASS_ORCHESTRATOR = False
DEFAULT_EMHASS_URL = "http://5b918bf2-emhass:5000"
EMHASS_OPTIMIZATION_INTERVALS = (15, 30, 60)
DEFAULT_EMHASS_OPTIMIZATION_INTERVAL = 15
DEFAULT_EMHASS_SOC_FINAL = 0.10
DEFAULT_EMHASS_FALLBACK_LOAD = 700
DEFAULT_USE_NORDPOOL_PRICES = True
DEFAULT_OPTIMIZE_ON_TOMORROW_PRICES = True
DEFAULT_NORDPOOL_AREA = ""
DEFAULT_NORDPOOL_CURRENCY = "EUR"
DEFAULT_BUY_PRICE_ADDER = 0.0
DEFAULT_SELL_PRICE_DEDUCTION = 0.0248
# Mad-Steve is behavior-compatible with the historic zero-penalty EMHASS setup.
# Existing entries only become Battery Saver-managed after this option is
# explicitly persisted; see orchestrator policy preparation.
DEFAULT_BATTERY_SAVER_MODE = "mad_steve"

REGISTER_EMS_MODE = 47511
REGISTER_EMS_POWER = 47512

MODE_AUTO = 1
MODE_BATTERY_HOLD = 8
MODE_GRID_IMPORT_TARGET = 9
MODE_GRID_EXPORT_TARGET = 10
MODE_CHARGE_BATTERY = 11
MODE_DISCHARGE_BATTERY = 12

MODES_ZERO_POWER = {1, 6, 7, 8}

MODE_NAMES = {
    1: "GoodWe Auto / AI",
    2: "PV-priority charging",
    3: "PV + battery supply",
    4: "Inverter import / AC charging",
    5: "Inverter export power",
    6: "Reserve / Conserve",
    7: "Off-grid",
    8: "Battery Hold",
    9: "Grid import target",
    10: "Grid export target",
    11: "Battery charge power",
    12: "Battery discharge power",
}
