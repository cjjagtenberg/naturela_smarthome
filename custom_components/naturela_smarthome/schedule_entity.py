"""Shared base for the timer / schedule entities (v1.4.0)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity

from .const import CONF_DEVICE_ID, DOMAIN, MANUFACTURER, MODEL
from .scheduler import NaturelaScheduler


class NaturelaScheduleEntity(Entity):
    """Entity that reflects the scheduler state, linked to the stove device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, scheduler: NaturelaScheduler, key: str) -> None:
        device_id = entry.data.get(CONF_DEVICE_ID, 6548)
        self._scheduler = scheduler
        self._attr_translation_key = key
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(device_id))},
            "name": "Pellet Stove",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self._scheduler.async_add_listener(self.async_write_ha_state)
        )
