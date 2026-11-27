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

# Operating mode (v1.5.0).
# The "State" byte packs two fields, as decoded by the Naturela web UI
# (applicationbundle.js, BurnerStatus / BurnerTouchStatus):
#   onOffState = (State >> 6) & 3   -> 0 = OFF, 2 = ON, 3 = Timers
#   fuelState  =  State       & 3   -> fuel selection, must be preserved
# The web UI writes it back as (onOffState << 6) | fuelState.
MODE_OFF = 0
MODE_ON = 2
MODE_TIMERS = 3
MODE_SHIFT = 6
MODE_MASK = 0b11
FUEL_MASK = 0b11

MODE_OPTIONS = {
    "off": MODE_OFF,
    "on": MODE_ON,
    "timers": MODE_TIMERS,
}


def get_mode(state) -> int:
    """Return the onOffState field of a raw State value (0 if unknown)."""
    try:
        return (int(state) >> MODE_SHIFT) & MODE_MASK
    except (TypeError, ValueError):
        return MODE_OFF


def build_state(mode: int, current_state=0) -> int:
    """Compose a State value for setState, keeping the current fuel bits."""
    try:
        fuel = int(current_state) & FUEL_MASK
    except (TypeError, ValueError):
        fuel = 0
    return ((mode & MODE_MASK) << MODE_SHIFT) | fuel

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


# Controller timer programme (v1.5.0).
# The cloud object carries the controller's own ON/OFF timers in the field
# "Alarms" (the web UI shows them under User settings -> Timers). Begin/End are
# controller-local wall-clock times with a misleading "Z" suffix. DaysEnabled
# is a bitmask, Monday = 1 ... Sunday = 64 (SmartHome.Days in the web UI).
# TimerSFI / TimerNDate drive the "Timers: Stop: 14:00" line on the status
# page: TimerN enum 0 = off, 1 = Start, 2 = Stop, 3 = Delay. "Stop" means the
# stove is inside a timer slot that ends at TimerNDate; "Start" means it waits
# for the next slot.
TIMER_STATES = {0: "off", 1: "start", 2: "stop", 3: "delay"}
DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _hhmm(value) -> str | None:
    if not isinstance(value, str) or len(value) < 16:
        return None
    return value[11:16]


def parse_timers(data: dict | None) -> list[dict]:
    """Return the controller timers as a list of plain dicts."""
    timers = []
    for item in (data or {}).get("Alarms") or []:
        if not isinstance(item, dict) or "Begin" not in item:
            continue
        mask = int(item.get("DaysEnabled") or 0)
        timers.append(
            {
                "enabled": bool(item.get("Enabled")),
                "begin": _hhmm(item.get("Begin")),
                "end": _hhmm(item.get("End")),
                "days": [d for i, d in enumerate(DAY_NAMES) if mask & (1 << i)],
            }
        )
    return timers


def timer_state(data: dict | None) -> str | None:
    """off / start / stop / delay, or None if the field is missing."""
    raw = (data or {}).get("TimerSFI")
    if raw is None:
        return None
    try:
        return TIMER_STATES.get(int(raw))
    except (TypeError, ValueError):
        return None


def timer_next_change(data: dict | None) -> str | None:
    """HH:MM of the next timer change (controller-local time)."""
    return _hhmm((data or {}).get("TimerNDate"))
