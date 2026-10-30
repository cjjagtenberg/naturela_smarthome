"""Constants for the Naturela Smarthome integration."""

DOMAIN = "naturela_smarthome"
MANUFACTURER = "Naturela"

CONF_DEVICE_ID = "device_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_CONTROLLER_TYPE = "controller_type"
DEFAULT_SCAN_INTERVAL = 30  # seconds

# Timer / schedule (v1.4.0)
DEFAULT_BURN_DURATION_HOURS = 2.0
MIN_BURN_DURATION_HOURS = 0.5
MAX_BURN_DURATION_HOURS = 12.0
BURN_DURATION_STEP_HOURS = 0.5
DEFAULT_DELAY_HOURS = 0.0
MIN_DELAY_HOURS = 0.0
MAX_DELAY_HOURS = 24.0
DELAY_STEP_HOURS = 0.25

# Controller types — corresponds to the endpoint segment used in
# iot.naturela-bg.com/api/{controller_type} and the URL shown in the
# Naturela web UI (/#/device/{controller_type}/<id>).
CONTROLLER_BURNERTOUCH = "burnertouch"   # NPBC_V6T_2 (BurnerTouch)
CONTROLLER_BURNER = "burner"             # NPBC-V3C-1 and older
DEFAULT_CONTROLLER = CONTROLLER_BURNERTOUCH

CONTROLLER_MODELS = {
    CONTROLLER_BURNERTOUCH: "BurnerTouch (NPBC_V6T_2)",
    CONTROLLER_BURNER: "NPBC-V3C-1",
}
# Back-compat alias used by climate/sensor/binary_sensor device_info.
# Platforms may also call get_model(controller_type) for the precise name.
MODEL = "BurnerTouch"


def get_model(controller_type: str) -> str:
    """Return a human-readable model label for the given controller type."""
    return CONTROLLER_MODELS.get(controller_type, MODEL)


BASE_URL = "https://iot.naturela-bg.com"
LOGIN_URL = f"{BASE_URL}/account/login"


def build_api_urls(controller_type: str) -> tuple[str, str, str]:
    """Return (API_URL, SET_STATE_URL, SET_TEMP_URL) for a controller type."""
    ct = controller_type or DEFAULT_CONTROLLER
    return (
        f"{BASE_URL}/api/{ct}",
        f"{BASE_URL}/api/{ct}/setState",
        f"{BASE_URL}/api/{ct}/setTemperature",
    )


# Back-compat module-level URLs (point at BurnerTouch, the original target).
# New code should call build_api_urls(controller_type) instead.
API_URL, SET_STATE_URL, SET_TEMP_URL = build_api_urls(DEFAULT_CONTROLLER)

# Device state values (confirmed by capturing Naturela web UI XHR requests)
# The web UI sends {"deviceId": "<serial>", "state": 128} for ON
# and {"deviceId": "<serial>", "state": 0} for OFF
STATE_OFF = 0
STATE_ON  = 128

# Status code labels (v1.4.2).
# Literal BurnStatus enum from the Naturela cloud frontend
# (https://iot.naturela-bg.com/scripts/applicationbundle.js, pattern
# `BurnStatus[BurnStatus["LABEL"] = N] = "LABEL";`, captured 2026-05-14).
# No own names or translations: HA shows exactly what Naturela shows.
# Observed start sequence: 1 -> 2 -> 3 -> 4 -> 8; stop: 10 -> 1 -> 0.
STATUS_NAMES = {
    0:  "Standby",
    1:  "Clearing",
    2:  "Charging",
    3:  "Firing",
    4:  "Burning",
    5:  "Keeping",
    6:  "Power1",
    7:  "Power2",
    8:  "Power3",
    9:  "Clearing2",
    10: "StopFiring",
    # Text values returned as strings by some firmware versions
    "Stand by":      "Standby",
    "keeping":       "Keeping",
    "Firing":        "Firing",
    "see display":   "See display",
    "Ignition Fail": "Ignition fail",
    # Error / alarm states (not part of the BurnStatus enum; labels are
    # best-guess and get logged with a WARNING the first time they occur).
    "No pellets":      "No pellets",
    "No Pellets":      "No pellets",
    "No fuel":         "No pellets",
    "Out of fuel":     "No pellets",
    "No pellet":       "No pellets",
    "Empty hopper":    "No pellets",
    "Pellets empty":   "No pellets",
    "Overheating":     "Overheating",
    "Overheat":        "Overheating",
    "Over temperature": "Overheating",
    "Over Temp":       "Overheating",
    "Boiler over temp": "Overheating",
    "OverTemp":        "Overheating",
}

# Power1/2/3 are direct status codes (6/7/8); no derivation from FPower.
# Kept (empty) for backwards compatibility of imports.
BURNING_STATUS_CODES: set = set()

# All possible status labels, used as `options` for the ENUM status sensor.
STATUS_OPTIONS = [
    "Standby",
    "Clearing",
    "Charging",
    "Firing",
    "Burning",
    "Keeping",
    "Power1",
    "Power2",
    "Power3",
    "Clearing2",
    "StopFiring",
    "See display",
    "Ignition fail",
    "No pellets",
    "Overheating",
    "Unknown",
]
