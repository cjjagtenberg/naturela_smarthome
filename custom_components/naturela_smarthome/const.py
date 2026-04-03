h"""Constants for the Naturela Smarthome integration."""

DOMAIN = "naturela_smarthome"
MANUFACTURER = "Naturela"
MODEL = "BurnerTouch"

CONF_DEVICE_ID = "device_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 10  # seconds

BASE_URL = "https://iot.naturela-bg.com"
LOGIN_URL = f"{BASE_URL}/account/login"
API_URL = f"{BASE_URL}/api/burnertouch"
SET_STATE_URL = f"{BASE_URL}/api/burnertouch/setState"
SET_TEMP_URL  = f"{BASE_URL}/api/burnertouch/setTemperature"

STATE_OFF = 0
STATE_ON = 128

# Status codes (as reported by the device)
# When Status is 2 or 8 (running), the displayed status is derived from
# FPower vs Power1/Power2/Power3 thresholds -- see sensor.py NaturelaStatusSensor
STATUS_NAMES = {
    0: "Stand-by",
    1: "Ontsteking",
    2: "Ontsteking",
    3: "Ontsteking",  # Igniter=True variant
    4: "Fout",
    5: "Wachten",
    6: "Reinigen",
    7: "Afkoelen",
    8: "Werkt",
    10: "Op temperatuur",
    "Stand by": "Stand-by",
    "Firing": "Ontsteking",
    "keeping": "Op temperatuur",
    "see display": "Zie display",
    "Burning": "Brandt",
    "Power3": "Power 3",
    "Ignition Fail": "Ontstekingsfout",
}
