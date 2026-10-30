"""Timer buttons (v1.4.0)."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .schedule_entity import NaturelaScheduleEntity

BUTTONS = {
    "start_timer": ("mdi:timer-play", "async_start_timer_from_settings"),
    "start_for_duration": ("mdi:fire-circle", "async_turn_on_for_burn_duration"),
    "off_after_duration": ("mdi:timer-play-outline", "async_turn_off_after_burn_duration"),
    "cancel_schedule": ("mdi:timer-off-outline", "async_cancel"),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    scheduler = hass.data[DOMAIN][entry.entry_id]["scheduler"]
    async_add_entities(
        NaturelaScheduleButton(entry, scheduler, key, icon, method)
        for key, (icon, method) in BUTTONS.items()
    )


class NaturelaScheduleButton(NaturelaScheduleEntity, ButtonEntity):
    """Button that triggers a scheduler action."""

    def __init__(self, entry, scheduler, key: str, icon: str, method: str) -> None:
        super().__init__(entry, scheduler, key)
        self._attr_icon = icon
        self._method = method

    async def async_press(self) -> None:
        await getattr(self._scheduler, self._method)()
