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
CONF_MAX_POWER = "max_power"
CONF_DEADBAND = "deadband"
CONF_EV_DEADBAND = "ev_deadband"
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
DEFAULT_EMHASS_OPTIMIZATION_INTERVAL = 60
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
