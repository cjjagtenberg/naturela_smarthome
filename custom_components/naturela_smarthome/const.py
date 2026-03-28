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

# Status codes and text values (as reported by the device)
# Keys can be numeric codes (int) or text strings from the controller
STATUS_NAMES = {
    # Numerieke codes
    0: "Stand-by",
    1: "Ontsteking",
    2: "Werkt",
    3: "Afkoelen",
    4: "Fout",
    5: "Wachten",
    6: "Reinigen",
    8: "Werkt",  # observed in the field during normal operation
    # Tekst-waarden van de controller (Engels -> Nederlands)
    "Stand by": "Stand-by",
    "Firing": "Ontsteking",
    "keeping": "Op temperatuur",
    "see display": "Zie display",
    "Ignition Fail": "Ontstekingsfout",
    "1": "Vermogen 1",
    "2": "Vermogen 2",
    "3": "Vermogen 3",
}
