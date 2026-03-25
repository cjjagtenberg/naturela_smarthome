"""Config flow for Naturela Smarthome."""
from __future__ import annotations
import logging
import voluptuous as vol
from homeassistant import config_entries
from .api import NaturelaAPI, NaturelaAuthError, NaturelaConnectionError
from .const import CONF_DEVICE_ID, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required("username"): str,
    vol.Required("password"): str,
    vol.Required(CONF_DEVICE_ID, default=6548): int,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(int, vol.Range(min=10, max=300)),
})


class NaturelaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial configuration."""
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            api = NaturelaAPI(
                username=user_input["username"],
                password=user_input["password"],
                device_id=user_input.get(CONF_DEVICE_ID, 6548),
            )
            try:
                await api.login()
            except NaturelaAuthError:
                errors["base"] = "invalid_auth"
            except NaturelaConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during config flow")
                errors["base"] = "unknown"
            else:
                await api.close()
                device_id = user_input.get(CONF_DEVICE_ID, 6548)
                await self.async_set_unique_id(f"naturela_{device_id}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Naturela Schuurkachel ({device_id})",
                    data=user_input,
                )
            await api.close()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"url": "https://iot.naturela-bg.com"},
        )
