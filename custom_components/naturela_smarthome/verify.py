"""Verify that the stove really follows an on/off command (v1.4.3).

The Naturela cloud can accept a command (HTTP 200) while the stove does not
act on it. After every on/off command sent by Home Assistant this verifier
watches the reported Status:

- OFF: confirmed when the status becomes StopFiring, Clearing, Clearing2 or
  Standby within VERIFY_WINDOW. If the stove is still burning, the command is
  re-sent (with a fresh login) up to OFF_RETRIES times.
- ON: confirmed when the status leaves Standby within VERIFY_WINDOW. No
  automatic retry (a second ignition command is not sent blindly).

When a command is not confirmed, the event `naturela_smarthome_command_failed`
is fired and a persistent notification is created.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import timedelta

from homeassistant.components import persistent_notification
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from .const import DOMAIN, STATE_OFF, STATE_ON, STATUS_NAMES

_LOGGER = logging.getLogger(__name__)

EVENT_COMMAND_FAILED = f"{DOMAIN}_command_failed"
VERIFY_INTERVAL = 30          # seconds between checks
VERIFY_WINDOW = 180           # seconds the stove gets to react
OFF_RETRIES = 2               # extra OFF attempts after the first one

# Codes (int or firmware text) that mean "shutting down or off"
OFF_CONFIRMED = {0, 1, 9, 10, "Stand by"}
# Codes that mean "starting or burning": an OFF command was not followed
BURNING = {2, 3, 4, 5, 6, 7, 8, "Firing", "keeping"}
STANDBY = {0, "Stand by"}


class CommandVerifier:
    """Watches one command at a time; a new command replaces the old check."""

    def __init__(self, hass: HomeAssistant, api, coordinator, entity_id_getter: Callable[[], str | None],
                 on_change: Callable[[], None]) -> None:
        self.hass = hass
        self._api = api
        self._coordinator = coordinator
        self._entity_id = entity_id_getter
        self._on_change = on_change
        self._unsub: CALLBACK_TYPE | None = None
        self._turn_on = False
        self._attempt = 0
        self._deadline = None
        self.state = "idle"          # idle | checking | ok | failed

    @callback
    def cancel(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def start(self, turn_on: bool) -> None:
        self.cancel()
        self._turn_on = turn_on
        self._attempt = 1
        self._deadline = dt_util.utcnow() + timedelta(seconds=VERIFY_WINDOW)
        self._set_state(f"checking 1/{1 if turn_on else 1 + OFF_RETRIES}")
        self._schedule()

    def _set_state(self, state: str) -> None:
        self.state = state
        self._on_change()

    @callback
    def _schedule(self) -> None:
        self._unsub = async_call_later(self.hass, VERIFY_INTERVAL, self._async_check)

    def _status(self):
        data = self._coordinator.data or {}
        return data.get("Status")

    async def _async_check(self, _now=None) -> None:
        self._unsub = None
        await self._coordinator.async_refresh()
        status = self._status()
        label = STATUS_NAMES.get(status, f"Status {status}")

        if self._turn_on and status is not None and status not in STANDBY:
            _LOGGER.info("Turn-on confirmed by stove (status %s)", label)
            self._set_state("ok")
            return
        if not self._turn_on and status in OFF_CONFIRMED:
            _LOGGER.info("Turn-off confirmed by stove (status %s)", label)
            self._set_state("ok")
            return

        if dt_util.utcnow() < self._deadline:
            self._schedule()
            return

        if not self._turn_on and status in BURNING and self._attempt <= OFF_RETRIES:
            self._attempt += 1
            _LOGGER.warning(
                "Stove still burning (status %s) %s s after turn-off; re-sending "
                "turn-off with a fresh login (attempt %s/%s). Last response: %s",
                label, VERIFY_WINDOW, self._attempt, 1 + OFF_RETRIES, self._api.last_command,
            )
            await self._api.force_relogin()
            await self._api.set_state(STATE_OFF)
            self._deadline = dt_util.utcnow() + timedelta(seconds=VERIFY_WINDOW)
            self._set_state(f"checking {self._attempt}/{1 + OFF_RETRIES}")
            self._schedule()
            return

        self._fail(label)

    @callback
    def _fail(self, label: str) -> None:
        command = "on" if self._turn_on else "off"
        _LOGGER.error(
            "Stove did not follow turn-%s command after %s attempt(s); status %s. "
            "Last response: %s", command, self._attempt, label, self._api.last_command,
        )
        self._set_state("failed")
        self.hass.bus.async_fire(
            EVENT_COMMAND_FAILED,
            {
                "entity_id": self._entity_id(),
                "command": command,
                "status": label,
                "attempts": self._attempt,
            },
        )
        persistent_notification.async_create(
            self.hass,
            f"De pelletkachel reageert niet op het {'aan' if self._turn_on else 'uit'}-commando "
            f"(na {self._attempt} poging(en)). Huidige status: {label}.",
            title="Naturela: commando niet uitgevoerd",
            notification_id=f"{DOMAIN}_command_failed",
        )
