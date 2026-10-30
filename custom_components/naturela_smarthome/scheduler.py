"""Timer and schedule for the Naturela pellet stove.

One scheduler per config entry. It keeps two optional moments:
  - on_at  : turn the stove on at this moment
  - off_at : turn the stove off at this moment
plus a configurable burn duration (hours) used by the buttons.

The schedule is persisted with HA's Store so it survives a restart.
Moments that passed while HA was down are discarded (logged), never
executed late.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_BURN_DURATION_HOURS,
    DOMAIN,
    MAX_BURN_DURATION_HOURS,
    MAX_DELAY_HOURS,
    MIN_BURN_DURATION_HOURS,
    MIN_DELAY_HOURS,
    DEFAULT_DELAY_HOURS,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1

# Callable(turn_on: bool) -> Awaitable[None], provided by the climate entity
StoveHandler = Callable[[bool], Awaitable[None]]


class NaturelaScheduler:
    """Keeps and executes the on/off schedule for one stove."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.schedule.{entry_id}"
        )
        self.on_at: datetime | None = None
        self.off_at: datetime | None = None
        self.duration_hours: float = DEFAULT_BURN_DURATION_HOURS
        self.delay_hours: float = DEFAULT_DELAY_HOURS
        self._unsub_on: CALLBACK_TYPE | None = None
        self._unsub_off: CALLBACK_TYPE | None = None
        self._listeners: list[CALLBACK_TYPE] = []
        self._handler: StoveHandler | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_load(self) -> None:
        """Load the persisted schedule and re-arm future moments."""
        data = await self._store.async_load() or {}
        now = dt_util.utcnow()
        changed = False

        duration = data.get("duration_hours")
        if isinstance(duration, (int, float)):
            self.duration_hours = self._clamp_duration(float(duration))
        delay = data.get("delay_hours")
        if isinstance(delay, (int, float)):
            self.delay_hours = self._clamp_delay(float(delay))

        for key in ("on_at", "off_at"):
            raw = data.get(key)
            if not raw:
                continue
            moment = dt_util.parse_datetime(raw)
            if moment is None:
                changed = True
                continue
            moment = dt_util.as_utc(moment)
            if moment <= now:
                _LOGGER.warning(
                    "Scheduled %s at %s passed while Home Assistant was not "
                    "running; discarded, not executed",
                    "turn-on" if key == "on_at" else "turn-off",
                    dt_util.as_local(moment).isoformat(),
                )
                changed = True
                continue
            setattr(self, key, moment)

        self._arm()
        if changed:
            await self._async_save()

    @callback
    def async_unload(self) -> None:
        """Cancel timers (schedule stays persisted)."""
        self._disarm()
        self._handler = None

    @callback
    def attach_handler(self, handler: StoveHandler | None) -> None:
        """Register the function that actually switches the stove."""
        self._handler = handler

    @callback
    def async_add_listener(self, update_callback: CALLBACK_TYPE) -> CALLBACK_TYPE:
        """Listen for schedule changes. Returns a remove function."""
        self._listeners.append(update_callback)

        @callback
        def _remove() -> None:
            if update_callback in self._listeners:
                self._listeners.remove(update_callback)

        return _remove

    # ------------------------------------------------------------------
    # Public API (used by services, buttons, datetime and number entities)
    # ------------------------------------------------------------------

    async def async_set_on_at(self, moment: datetime) -> None:
        moment = self._validate_future(moment)
        if self.off_at is not None and self.off_at <= moment:
            raise ServiceValidationError(
                "Turn-on time must be before the scheduled turn-off time "
                f"({dt_util.as_local(self.off_at).strftime('%Y-%m-%d %H:%M')})"
            )
        self.on_at = moment
        await self._async_changed()

    async def async_set_off_at(self, moment: datetime) -> None:
        moment = self._validate_future(moment)
        if self.on_at is not None and moment <= self.on_at:
            raise ServiceValidationError(
                "Turn-off time must be after the scheduled turn-on time "
                f"({dt_util.as_local(self.on_at).strftime('%Y-%m-%d %H:%M')})"
            )
        self.off_at = moment
        await self._async_changed()

    async def async_turn_off_in(self, duration: timedelta) -> None:
        if duration.total_seconds() <= 0:
            raise ServiceValidationError("Duration must be greater than zero")
        self.off_at = dt_util.utcnow() + duration
        await self._async_changed()

    async def async_turn_on_for(self, duration: timedelta) -> None:
        if duration.total_seconds() <= 0:
            raise ServiceValidationError("Duration must be greater than zero")
        self.on_at = None
        self.off_at = dt_util.utcnow() + duration
        await self._async_changed()
        await self._async_switch(True)

    async def async_start_timer(self, delay: timedelta, duration: timedelta) -> None:
        """Turn on after `delay`, then off again after `duration`.

        A zero delay turns the stove on immediately.
        """
        if duration.total_seconds() <= 0:
            raise ServiceValidationError("Duration must be greater than zero")
        if delay.total_seconds() < 0:
            raise ServiceValidationError("Delay cannot be negative")
        if delay.total_seconds() == 0:
            await self.async_turn_on_for(duration)
            return
        self.on_at = dt_util.utcnow() + delay
        self.off_at = self.on_at + duration
        await self._async_changed()

    async def async_start_timer_from_settings(self) -> None:
        await self.async_start_timer(
            timedelta(hours=self.delay_hours), timedelta(hours=self.duration_hours)
        )

    async def async_set_delay(self, hours: float) -> None:
        self.delay_hours = self._clamp_delay(hours)
        await self._async_changed()

    async def async_turn_on_for_burn_duration(self) -> None:
        await self.async_turn_on_for(timedelta(hours=self.duration_hours))

    async def async_turn_off_after_burn_duration(self) -> None:
        await self.async_turn_off_in(timedelta(hours=self.duration_hours))

    async def async_cancel(self) -> None:
        self.on_at = None
        self.off_at = None
        await self._async_changed()

    async def async_set_duration(self, hours: float) -> None:
        self.duration_hours = self._clamp_duration(hours)
        await self._async_changed()

    async def async_manual_off(self) -> None:
        """Stove switched off by the user via HA.

        The pending turn-off is dropped, unless a turn-on is still planned
        (then the turn-off belongs to that future burn session).
        """
        if self.off_at is not None and self.on_at is None:
            self.off_at = None
            await self._async_changed()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _clamp_duration(hours: float) -> float:
        return max(MIN_BURN_DURATION_HOURS, min(MAX_BURN_DURATION_HOURS, hours))

    @staticmethod
    def _clamp_delay(hours: float) -> float:
        return max(MIN_DELAY_HOURS, min(MAX_DELAY_HOURS, hours))

    @staticmethod
    def _validate_future(moment: datetime) -> datetime:
        # Naive datetimes are interpreted in HA's configured time zone
        moment = dt_util.as_utc(moment)
        if moment <= dt_util.utcnow():
            raise ServiceValidationError("The chosen time is in the past")
        return moment

    async def _async_changed(self) -> None:
        self._arm()
        await self._async_save()
        for update_callback in list(self._listeners):
            update_callback()

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "on_at": self.on_at.isoformat() if self.on_at else None,
                "off_at": self.off_at.isoformat() if self.off_at else None,
                "duration_hours": self.duration_hours,
                "delay_hours": self.delay_hours,
            }
        )

    @callback
    def _disarm(self) -> None:
        if self._unsub_on:
            self._unsub_on()
            self._unsub_on = None
        if self._unsub_off:
            self._unsub_off()
            self._unsub_off = None

    @callback
    def _arm(self) -> None:
        self._disarm()
        if self.on_at is not None:
            self._unsub_on = async_track_point_in_utc_time(
                self.hass, self._async_fire_on, self.on_at
            )
        if self.off_at is not None:
            self._unsub_off = async_track_point_in_utc_time(
                self.hass, self._async_fire_off, self.off_at
            )

    async def _async_fire_on(self, _now: datetime) -> None:
        self._unsub_on = None
        self.on_at = None
        _LOGGER.info("Schedule: turning stove on")
        await self._async_save()
        self._notify()
        await self._async_switch(True)

    async def _async_fire_off(self, _now: datetime) -> None:
        self._unsub_off = None
        self.off_at = None
        _LOGGER.info("Schedule: turning stove off")
        await self._async_save()
        self._notify()
        await self._async_switch(False)

    @callback
    def _notify(self) -> None:
        for update_callback in list(self._listeners):
            update_callback()

    async def _async_switch(self, turn_on: bool) -> None:
        if self._handler is None:
            _LOGGER.error(
                "Schedule: cannot turn stove %s, climate entity not available",
                "on" if turn_on else "off",
            )
            return
        await self._handler(turn_on)
