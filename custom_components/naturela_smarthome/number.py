"""Burn duration number entity (v1.4.0)."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BURN_DURATION_STEP_HOURS,
    DELAY_STEP_HOURS,
    DOMAIN,
    MAX_BURN_DURATION_HOURS,
    MAX_DELAY_HOURS,
    MIN_BURN_DURATION_HOURS,
    MIN_DELAY_HOURS,
)
from .schedule_entity import NaturelaScheduleEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    scheduler = hass.data[DOMAIN][entry.entry_id]["scheduler"]
    async_add_entities(
        [
            NaturelaBurnDuration(entry, scheduler, "burn_duration"),
            NaturelaDelay(entry, scheduler, "delay"),
        ]
    )


class NaturelaBurnDuration(NaturelaScheduleEntity, NumberEntity):
    """How long the stove burns when started with the timer buttons."""

    _attr_icon = "mdi:timer-cog-outline"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = MIN_BURN_DURATION_HOURS
    _attr_native_max_value = MAX_BURN_DURATION_HOURS
    _attr_native_step = BURN_DURATION_STEP_HOURS
    _attr_native_unit_of_measurement = UnitOfTime.HOURS

    @property
    def native_value(self) -> float:
        return self._scheduler.duration_hours

    async def async_set_native_value(self, value: float) -> None:
        await self._scheduler.async_set_duration(value)


class NaturelaDelay(NaturelaScheduleEntity, NumberEntity):
    """How long to wait before the stove turns on (Start timer button)."""

    _attr_icon = "mdi:timer-sand"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = MIN_DELAY_HOURS
    _attr_native_max_value = MAX_DELAY_HOURS
    _attr_native_step = DELAY_STEP_HOURS
    _attr_native_unit_of_measurement = UnitOfTime.HOURS

    @property
    def native_value(self) -> float:
        return self._scheduler.delay_hours

    async def async_set_native_value(self, value: float) -> None:
        await self._scheduler.async_set_delay(value)
