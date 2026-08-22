"""Constants for GW EnergyPilot."""

DOMAIN = "gw_energypilot"
NAME = "GW EnergyPilot"

CONF_SLAVE = "slave"
CONF_P_BATT_ENTITY = "p_batt_entity"
CONF_OPTIM_STATUS_ENTITY = "optim_status_entity"
CONF_OPTIM_REQUIRED_STATE = "optim_required_state"
CONF_ENABLE_EV_COORDINATION = "enable_ev_coordination"
CONF_EV_MODE_ENTITY = "ev_mode_entity"
CONF_EV_POWER_ENTITY = "ev_power_entity"
CONF_MAX_POWER = "max_power"
CONF_DEADBAND = "deadband"
CONF_EV_DEADBAND = "ev_deadband"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 502
DEFAULT_SLAVE = 247
DEFAULT_MAX_POWER = 15000
DEFAULT_DEADBAND = 300
DEFAULT_EV_DEADBAND = 500
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_P_BATT_ENTITY = "sensor.p_batt_forecast"
DEFAULT_OPTIM_STATUS_ENTITY = "sensor.optim_status"
DEFAULT_OPTIM_REQUIRED_STATE = "Optimal"

REGISTER_EMS_MODE = 47511
REGISTER_EMS_POWER = 47512

MODE_AUTO = 1
MODE_BATTERY_HOLD = 8
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
