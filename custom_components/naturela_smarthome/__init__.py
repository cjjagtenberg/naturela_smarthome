"""Naturela Smarthome Home Assistant custom integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NaturelaAPI, NaturelaAuthError, NaturelaConnectionError
from .const import CONF_DEVICE_ID, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["climate", "sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Naturela from a config entry."""
    api = NaturelaAPI(
        username=entry.data["username"],
        password=entry.data["password"],
        device_id=entry.data.get(CONF_DEVICE_ID, 6548),
    )
    try:
        await api.login()
    except NaturelaAuthError as exc:
        raise ConfigEntryNotReady(f"Authentication failed: {exc}") from exc
    except NaturelaConnectionError as exc:
        raise ConfigEntryNotReady(f"Cannot connect: {exc}") from exc

    scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    async def _async_update_data() -> dict:
        try:
            data = await api.get_device_data()
            if data is None:
                raise UpdateFailed("Empty response from device")
            return data
        except NaturelaAuthError as exc:
            raise UpdateFailed(f"Authentication error: {exc}") from exc
        except NaturelaConnectionError as exc:
            raise UpdateFailed(f"Connection error: {exc}") from exc

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=_async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["api"].close()
    return unload_ok
