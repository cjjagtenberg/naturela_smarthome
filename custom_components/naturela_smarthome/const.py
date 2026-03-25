"""Constants for the Naturela Smarthome integration."""

DOMAIN = "naturela_smarthome"
MANUFACTURER = "Naturela"
MODEL = "BurnerTouch"

CONF_DEVICE_ID = "device_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 30

BASE_URL = "https://iot.naturela-bg.com"
LOGIN_URL = BASE_URL + "/account/login"
API_URL = BASE_URL + "/api/burnertouch"
UPDATE_URL = BASE_URL + "/api/device/updatestat"

STATE_OFF = 0
STATE_ON = 1
STATE_TIMERS = 2

STATUS_NAMES = {
    0: "Stand-by",
    1: "Ontsteking",
    2: "Werkt",
    3: "Afkoelen",
    4: "Fout",
    5: "Wachten",
    6: "Reinigen",
}
