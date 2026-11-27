"""Operating mode select: OFF / ON / Timers (v1.5.0).

The climate entity only knows OFF and HEAT (= ON). The Naturela controller
has a third mode, "Timers", in which it follows the timer programme stored
on the controller itself. Without this entity there is no way back to that
mode from Home Assistant once the stove has been switched on or off here.
"""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DEVICE_ID,
    DOMAIN,
    MANUFACTURER,
    MODE_OPTIONS,
    MODEL,
    STATE_OFF,
    build_state,
    get_mode,
)

_LOGGER = logging.getLogger(__name__)

_OPTION_BY_MODE = {mode: option for option, mode in MODE_OPTIONS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the operating mode select."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            NaturelaModeSelect(
                coordinator=data["coordinator"],
                api=data["api"],
                device_id=entry.data.get(CONF_DEVICE_ID, 6548),
            )
        ]
    )


class NaturelaModeSelect(CoordinatorEntity, SelectEntity):
    """Controller operating mode as shown in the Naturela web UI."""

    _attr_has_entity_name = True
    _attr_translation_key = "operating_mode"
    _attr_icon = "mdi:power-settings"
    _attr_options = list(MODE_OPTIONS)

    def __init__(self, coordinator, api, device_id) -> None:
        super().__init__(coordinator)
        self._api = api
        self._attr_unique_id = f"{DOMAIN}_{device_id}_operating_mode"
        # Same identifiers as the climate entity, so it joins that device.
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(device_id))},
            "name": "Pellet Stove",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }
        self._optimistic: str | None = None

    @property
    def _raw_state(self):
        return (self.coordinator.data or {}).get("State")

    @property
    def current_option(self) -> str | None:
        if self._optimistic is not None:
            return self._optimistic
        raw = self._raw_state
        if raw is None:
            return None
        # Unknown values (e.g. mode 1) are reported as None rather than guessed.
        return _OPTION_BY_MODE.get(get_mode(raw))

    @property
    def extra_state_attributes(self) -> dict:
        return {"raw_state": self._raw_state}

    def _handle_coordinator_update(self) -> None:
        # The first poll after a command shows what the controller accepted.
        self._optimistic = None
        super()._handle_coordinator_update()

    async def async_select_option(self, option: str) -> None:
        if option not in MODE_OPTIONS:
            raise HomeAssistantError(f"Unknown operating mode: {option}")
        state = build_state(MODE_OPTIONS[option], self._raw_state or STATE_OFF)
        if not await self._api.set_state(state):
            raise HomeAssistantError(
                f"Naturela cloud rejected mode {option} (state {state})"
            )
        _LOGGER.debug("Operating mode set to %s (state %s)", option, state)
        self._optimistic = option
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
