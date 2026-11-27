"""Binary sensor entities for Naturela BurnerTouch pellet stove."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICE_ID,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    timer_next_change,
    timer_state,
)


@dataclass
class NaturelaBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Extended description that carries the API field key."""

    api_key: str = ""


BINARY_SENSORS: tuple[NaturelaBinarySensorEntityDescription, ...] = (
    NaturelaBinarySensorEntityDescription(
        key="ch_pump",
        api_key="CHPump",
        name="Central heating pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
    ),
    NaturelaBinarySensorEntityDescription(
        key="dhw_pump",
        api_key="DHWPump",
        name="DHW pump",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pump",
    ),
    NaturelaBinarySensorEntityDescription(
        key="igniter",
        api_key="Igniter",
        name="Igniter active",
        device_class=BinarySensorDeviceClass.HEAT,
        icon="mdi:fire",
    ),
    NaturelaBinarySensorEntityDescription(
        key="cleaner",
        api_key="Cleaner",
        name="Cleaner active",
        device_class=None,
        icon="mdi:broom",
    ),
    NaturelaBinarySensorEntityDescription(
        key="thermostat",
        api_key="Thermostat",
        name="Thermostat",
        device_class=BinarySensorDeviceClass.HEAT,
        icon="mdi:thermostat",
    ),
    NaturelaBinarySensorEntityDescription(
        key="external_stop",
        api_key="ExternalStop",
        name="External stop",
        device_class=BinarySensorDeviceClass.SAFETY,
        icon="mdi:stop-circle",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Naturela binary sensor entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    device_id = entry.data.get(CONF_DEVICE_ID, 6548)
    async_add_entities(
        [
            NaturelaBinarySensor(data["coordinator"], device_id, desc)
            for desc in BINARY_SENSORS
        ]
        + [NaturelaTimerWindowSensor(data["coordinator"], device_id)]
    )


class NaturelaBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """A binary (on/off) sensor for one boolean field from the stove."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        device_id: int,
        description: NaturelaBinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(device_id))},
            "name": "Pellet Stove",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        return bool(self.coordinator.data.get(self.entity_description.api_key))


class NaturelaTimerWindowSensor(CoordinatorEntity, BinarySensorEntity):
    """On while the controller's timer programme allows burning (v1.5.0).

    Follows the controller itself (TimerSFI): "stop" = inside a timer slot that
    ends at next_change; "start"/"delay" = waiting; "off" = timers not in use.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "timer_window"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, device_id: int) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_timer_window"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(device_id))},
            "name": "Pellet Stove",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def is_on(self) -> bool | None:
        state = timer_state(self.coordinator.data)
        if state is None:
            return None
        return state == "stop"

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        return {"timer_state": timer_state(data), "next_change": timer_next_change(data)}
