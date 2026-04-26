"""Constants for the Naturela Smarthome integration."""

DOMAIN = "naturela_smarthome"
MANUFACTURER = "Naturela"
MODEL = "BurnerTouch"

CONF_DEVICE_ID = "device_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 30  # seconds

BASE_URL = "https://iot.naturela-bg.com"
LOGIN_URL = f"{BASE_URL}/account/login"
API_URL = f"{BASE_URL}/api/burnertouch"
SET_STATE_URL = f"{BASE_URL}/api/burnertouch/setState"      # confirmed from web UI
SET_TEMP_URL  = f"{BASE_URL}/api/burnertouch/setTemperature"  # confirmed from web UI

# Device state values (confirmed by capturing Naturela web UI XHR requests)
# The web UI sends {"deviceId": "<serial>", "state": 128} for ON
# and {"deviceId": "<serial>", "state": 0} for OFF
STATE_OFF = 0
STATE_ON = 128

# Status code labels.
# These match LITERALLY what the Naturela controller and iot.naturela-bg.com
# web portal display (confirmed by live observation 2026-04-26).
# Keys can be numeric codes (int) or text strings from the controller.
#
# Note on Status 1: covers three sub-phases on the controller
# ("Cleaning" → "Feeding" → "Ignition") that are not exposed as separate
# API codes. Generic label "Cleaning" is used; for shutdown context the
# same code 1 also represents "Cleaning on stop" (~40s blow-out).
STATUS_NAMES = {
    # Numeric codes
    0:  "Stand-by",
    1:  "Cleaning",          # Cleaning + Feeding + Ignition (start) OR Cleaning on stop
    2:  "Burning",           # rare; sensor.py overrides to Power1/2/3 when FPower set
    3:  "Cool down",         # observed in historical logs
    4:  "Unfolding fire",    # vlamopbouw na ignition (rookgas +5 °C trigger)
    5:  "Suspend",           # PS modulation - water op temperatuur
    6:  "Suspend",           # entering Suspend (P1 modulation just before)
    7:  "Burning shutdown",  # P3 → P2 → P1 ramp (60s each), observed historical
    8:  "Burning",           # main burning state; sensor.py overrides to Power1/2/3
    10: "Cool down",         # observed in historical logs
    # Text values returned as strings by some firmware versions
    "Stand by":     "Stand-by",
    "keeping":      "Extinguishing",
    "Firing":       "Cleaning",
    "see display":  "Zie display",
    "Ignition Fail": "Ignition fail",
    # Error / alarm states (best-guess mappings — verified labels will be
    # captured via the WARNING log in sensor.py the first time they occur).
    "No pellets":       "No pellets",
    "No Pellets":       "No pellets",
    "No fuel":          "No pellets",
    "Out of fuel":      "No pellets",
    "No pellet":        "No pellets",
    "Empty hopper":     "No pellets",
    "Pellets empty":    "No pellets",
    "Overheating":      "Overheating",
    "Overheat":         "Overheating",
    "Over temperature": "Overheating",
    "Over Temp":        "Overheating",
    "Boiler over temp": "Overheating",
    "OverTemp":         "Overheating",
}

# Status codes considered "burning" — sensor.py derives Power1/2/3 from FPower
# vs Power1/Power2/Power3 thresholds for these codes.
BURNING_STATUS_CODES = {2, 8}

# All possible status labels — used as `options` for the ENUM device class
# on the status sensor so that HA's history graph + logbook render nicely.
STATUS_OPTIONS = [
    "Stand-by",
    "Cleaning",
    "Unfolding fire",
    "Burning",
    "PS",        # Keeping - FPower below P1 threshold
    "Power1",
    "Power2",
    "Power3",
    "Suspend",
    "Burning shutdown",
    "Cool down",
    "Extinguishing",
    "Zie display",
    "Ignition fail",
    "No pellets",
    "Overheating",
    "Unknown",
]
