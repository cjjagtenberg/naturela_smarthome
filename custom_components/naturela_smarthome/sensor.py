"""Sensor entities for Naturela BurnerTouch pellet stove."""
from __future__ import annotations

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

from .const import CONF_DEVICE_ID, DOMAIN, MANUFACTURER, MODEL, STATUS_NAMES


@dataclass
class NaturelaSensorEntityDescription(SensorEntityDescription):
    """Extended description to carry the API field key."""

    api_key: str = ""
    value_multiplier: float = 1.0


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
    ),
    NaturelaSensorEntityDescription(
        key="fire_level",
        api_key="FireLevel",
        name="Vlamniveau",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fire-circle",
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
    ),
    NaturelaSensorEntityDescription(
        key="main_fan",
        api_key="MainFan",
        name="Hoofdventilator",
        native_unit_of_measurement="%",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan",
    ),
    NaturelaSensorEntityDescription(
        key="exhaust_fan",
        api_key="ExhaustFan",
        name="Afzuigventilator",
        native_unit_of_measurement="%",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:fan-chevron-down",
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Naturela sensor entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    device_id = entry.data.get(CONF_DEVICE_ID, 6548)

    entities: list[SensorEntity] = [
        NaturelaStatusSensor(data["coordinator"], device_id),
    ]
    entities += [
        NaturelaSensor(data["coordinator"], device_id, desc)
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
    """Human-readable status (Stand-by / Power1 / Power2 / Power3 ...)."""

    _attr_icon = "mdi:fire-alert"
    _attr_has_entity_name = True

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
        if value in (2, 8):
            if d.get("Igniter"):
                return "Ontsteking"
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
        return STATUS_NAMES.get(value, str(value))


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
            return None
        multiplier = self.entity_description.value_multiplier
        if multiplier != 1.0:
            try:
                return round(float(value) * multiplier, 2)
            except (TypeError, ValueError):
                return value
        return value
