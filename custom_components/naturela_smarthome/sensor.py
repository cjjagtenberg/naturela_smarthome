"""Sensor entities for Naturela BurnerTouch pellet stove."""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfMass, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BURNING_STATUS_CODES,
    CONF_DEVICE_ID,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    STATUS_NAMES,
    STATUS_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)

# Track Status values we've already warned about so we don't spam the log
# every poll cycle (default 30s) with the same unknown code.
_LOGGED_UNKNOWN_STATUS: set = set()


@dataclass
class NaturelaSensorEntityDescription(SensorEntityDescription):
    """Extended description to carry the API field key."""

    api_key: str = ""
    value_multiplier: float = 1.0
    null_as_zero: bool = False  # Treat None/null API value as 0 (e.g. power when stove is off)


SENSORS: tuple[NaturelaSensorEntityDescription, ...] = (
    NaturelaSensorEntityDescription(
        key="temp_boiler",
        api_key="TempBoiler",
        name="Keteltemperatuur",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:thermometer",
    ),
    NaturelaSensorEntityDescription(
        key="temp_dhw",
        api_key="TempDHW",
        name="Warmwatertemperatuur",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:water-thermometer",
    ),
    NaturelaSensorEntityDescription(
        key="temp_fume",
        api_key="TempFume",
        name="Rookgastemperatuur",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:smoke",
    ),
    NaturelaSensorEntityDescription(
        key="set_temp",
        api_key="SetTemp",
        name="Doeltemperatuur",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:target",
    ),
    NaturelaSensorEntityDescription(
        key="power_kw",
        api_key="FPower",
        name="Brandertrap",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fire",
        null_as_zero=True,
    ),
    NaturelaSensorEntityDescription(
        key="fire_level",
        api_key="FireLevel",
        name="Vlamniveau",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fire-circle",
        null_as_zero=True,
    ),
    NaturelaSensorEntityDescription(
        key="fuel_consumed",
        api_key="FuelConsum",
        name="Pelletverbruik totaal",
        native_unit_of_measurement=UnitOfMass.KILOGRAMS,
        device_class=None,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:silo",
    ),
    NaturelaSensorEntityDescription(
        key="output_power",
        api_key="OutputPower",
        name="Thermisch vermogen",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:gauge",
        value_multiplier=0.1,
        null_as_zero=True,
    ),
    NaturelaSensorEntityDescription(
        key="main_fan",
        api_key="MainFan",
        name="Hoofdventilator",
        native_unit_of_measurement="%",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
        null_as_zero=True,
    ),
    NaturelaSensorEntityDescription(
        key="exhaust_fan",
        api_key="ExhaustFan",
        name="Afzuigventilator",
        native_unit_of_measurement="%",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan-chevron-down",
        null_as_zero=True,
    ),
    NaturelaSensorEntityDescription(
        key="power1_threshold",
        api_key="Power1",
        name="Vermogenstrap 1",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer-slow",
    ),
    NaturelaSensorEntityDescription(
        key="power2_threshold",
        api_key="Power2",
        name="Vermogenstrap 2",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer-medium",
    ),
    NaturelaSensorEntityDescription(
        key="power3_threshold",
        api_key="Power3",
        name="Vermogenstrap 3",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:speedometer",
    ),
)


# Sensors whose values must always be finite numbers.  Used to guard against
# the Naturela API returning "NaN", null, or out-of-range values on fields that
# the stove doesn't actually measure (e.g. no DHW boiler connected).
_NUMERIC_KEYS = {
    "temp_boiler",
    "temp_dhw",
    "temp_fume",
    "set_temp",
    "output_power",
    "power_kw",
    "fire_level",
    "fuel_consumed",
    "main_fan",
    "exhaust_fan",
    "power1_threshold",
    "power2_threshold",
    "power3_threshold",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Naturela sensor entities."""
    coordinator = entry.runtime_data.coordinator
    device_id = entry.data.get(CONF_DEVICE_ID, 6548)

    entities: list[SensorEntity] = [
        NaturelaStatusSensor(coordinator, device_id),
    ]
    entities += [
        NaturelaSensor(coordinator, device_id, desc)
        for desc in SENSORS
    ]
    async_add_entities(entities)


class _NaturelaEntityBase(CoordinatorEntity):
    """Shared base for Naturela sensors."""

    def __init__(self, coordinator, device_id: int) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(device_id))},
            "name": "Schuurkachel",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }


class NaturelaStatusSensor(_NaturelaEntityBase, SensorEntity):
    """Human-readable status of the stove.

    Returns one of the labels in STATUS_OPTIONS (ENUM device class) so HA's
    history graph and logbook render nicely with colored bars per state.

    Mapping logic:
      - When status code is in BURNING_STATUS_CODES (2 or 8), derive power
        label from FPower vs Power1/Power2/Power3 thresholds reported by
        the API → returns "Power1" / "Power2" / "Power3" / "PS".
      - Otherwise look up STATUS_NAMES (numeric or string key).
      - Unknown codes return "Unknown" rather than raising or polluting
        history with arbitrary values.
    """

    _attr_icon = "mdi:fire-alert"
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUS_OPTIONS

    def __init__(self, coordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_status"
        self._attr_name = "Status"

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        d = self.coordinator.data
        value = d.get("Status")
        if value is None:
            return None
        # Burning state → derive power-level label from FPower vs thresholds.
        # Matches what the Naturela controller and web portal display.
        if value in BURNING_STATUS_CODES:
            fpower = d.get("FPower") or 0
            p3 = d.get("Power3")
            p2 = d.get("Power2")
            p1 = d.get("Power1")
            if p3 is not None and fpower >= p3:
                return "Power3"
            if p2 is not None and fpower >= p2:
                return "Power2"
            if p1 is not None and fpower >= p1:
                return "Power1"
            # FPower below P1 threshold but burning → PS (Keeping)
            if fpower > 0:
                return "PS"
            # FPower=0 yet status burning → transitional, fall through to STATUS_NAMES
        label = STATUS_NAMES.get(value)
        if label is None:
            # Unknown status — log once per unique value so we can extend
            # STATUS_NAMES later. Critical for catching error states like
            # "No pellets" or "Overheating" with their actual API spelling.
            key = (type(value).__name__, value)
            if key not in _LOGGED_UNKNOWN_STATUS:
                _LOGGED_UNKNOWN_STATUS.add(key)
                _LOGGER.warning(
                    "Naturela: unknown Status value %r (type=%s) — falling back to 'Unknown'. "
                    "Please report so it can be added to STATUS_NAMES.",
                    value, type(value).__name__,
                )
            return "Unknown"
        # Final safety: only return labels that are in the ENUM options list.
        if label not in STATUS_OPTIONS:
            key = ("label", label)
            if key not in _LOGGED_UNKNOWN_STATUS:
                _LOGGED_UNKNOWN_STATUS.add(key)
                _LOGGER.warning(
                    "Naturela: status label %r maps from %r but is not in STATUS_OPTIONS",
                    label, value,
                )
            return "Unknown"
        return label


def _coerce_numeric(value):
    """Convert an API value to a finite float, or return None.

    Guards against:
    - None
    - float('nan') / float('inf')
    - string "NaN", "null", "", etc.
    - any value that can't be converted to a finite float
    """
    if value is None:
        return None
    # Catch actual float NaN/Inf first (isinstance check before str conversion)
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return value
    if isinstance(value, (int, bool)):
        return float(value)
    # String or other — try to convert, treat "NaN"/"Infinity"/"" as missing
    try:
        s = str(value).strip()
        if not s or s.lower() in ("nan", "null", "none", "inf", "-inf", "infinity", "-infinity"):
            return None
        num = float(s)
        if not math.isfinite(num):
            return None
        return num
    except (TypeError, ValueError):
        return None


class NaturelaSensor(_NaturelaEntityBase, SensorEntity):
    """Generic numeric sensor based on a NaturelaSensorEntityDescription."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        device_id: int,
        description: NaturelaSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{description.key}"

    @property
    def native_value(self):
        if not self.coordinator.data:
            return None
        value = self.coordinator.data.get(self.entity_description.api_key)
        if value is None:
            # For sensors where "no data" means 0 (power, fan speed, etc.),
            # return 0 instead of None so the sensor shows 0 instead of "-".
            if self.entity_description.null_as_zero:
                value = 0
            else:
                return None

        multiplier = self.entity_description.value_multiplier

        # All sensors defined here are numeric — coerce to a finite float or None.
        # Home Assistant validates finite values for TEMPERATURE / POWER device
        # classes and will raise errors on NaN / Inf, which shows up as "NaN"
        # on the dashboard.
        if self.entity_description.key in _NUMERIC_KEYS:
            num = _coerce_numeric(value)
            if num is None:
                return None
            if multiplier != 1.0:
                return round(num * multiplier, 2)
            # Preserve integer type for fields that are always whole numbers
            if isinstance(value, int) and not isinstance(value, bool):
                return int(num)
            return num

        # Fallback for any future non-numeric sensors
        if multiplier != 1.0:
            try:
                return round(float(value) * multiplier, 2)
            except (TypeError, ValueError):
                return value
        return value
