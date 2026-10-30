"""Scheduled on / off moments as datetime entities (v1.4.0)."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .schedule_entity import NaturelaScheduleEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    scheduler = hass.data[DOMAIN][entry.entry_id]["scheduler"]
    async_add_entities(
        [
            NaturelaScheduleDateTime(entry, scheduler, "scheduled_on", "mdi:fire"),
            NaturelaScheduleDateTime(entry, scheduler, "scheduled_off", "mdi:fire-off"),
        ]
    )


class NaturelaScheduleDateTime(NaturelaScheduleEntity, DateTimeEntity):
    """Set the moment the stove turns on or off. Empty = nothing planned."""

    def __init__(self, entry, scheduler, key: str, icon: str) -> None:
        super().__init__(entry, scheduler, key)
        self._attr_icon = icon
        self._is_on = key == "scheduled_on"

    @property
    def native_value(self) -> datetime | None:
        return self._scheduler.on_at if self._is_on else self._scheduler.off_at

    async def async_set_value(self, value: datetime) -> None:
        if self._is_on:
            await self._scheduler.async_set_on_at(value)
        else:
            await self._scheduler.async_set_off_at(value)
