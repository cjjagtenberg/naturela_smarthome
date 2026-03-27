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

# Device state values
DEVICE_STATE_OFF = 0
DEVICE_STATE_ON = 128

# Status codes
STATUS_NAMES = {
    0: "Stand-by",
    1: "Ontsteking",
    2: "Werkt",
    3: "Afkoelen",
    4: "Fout",
    5: "Wachten",
    6: "Reinigen",
    8: "Werkt",
}
