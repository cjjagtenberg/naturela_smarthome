"""Naturela Smarthome API client."""
from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

from .const import API_URL, LOGIN_URL, UPDATE_URL

_LOGGER = logging.getLogger(__name__)


class NaturelaAuthError(Exception):
    """Raised when authentication fails."""


class NaturelaConnectionError(Exception):
    """Raised when connection to the API fails."""


class NaturelaAPI:
    """Client for the Naturela Smarthome cloud API."""

    def __init__(self, username: str, password: str, device_id: int) -> None:
        self._username = username
        self._password = password
        self._device_id = device_id
        self._session: aiohttp.ClientSession | None = None
        self._logged_in = False

    async def _get_session(self) -> aiohttp.ClientSession:
        """Return or create an aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def login(self) -> bool:
        """Log in and store session cookie (CSRF-token aware)."""
        session = await self._get_session()
        try:
            async with session.get(LOGIN_URL) as resp:
                html = await resp.text()
            csrf_token = _extract_csrf_token(html)
            form_data = {
                "Email": self._username,
                "Password": self._password,
                "rememberMe": "true",
                "__RequestVerificationToken": csrf_token,
            }
            async with session.post(LOGIN_URL, data=form_data, allow_redirects=True) as resp:
                final_url = str(resp.url)
                self._logged_in = "login" not in final_url.lower()
                if not self._logged_in:
                    raise NaturelaAuthError(f"Login failed - ended up at {final_url}")
                return True
        except NaturelaAuthError:
            raise
        except Exception as exc:
            raise NaturelaConnectionError(f"Login request failed: {exc}") from exc

    async def get_device_data(self) -> dict[str, Any] | None:
        """Poll device status and return parsed data dict."""
        if not self._logged_in:
            await self.login()
        session = await self._get_session()
        url = f"{API_URL}/{self._device_id}"
        try:
            async with session.get(url) as resp:
                if resp.status == 401:
                    self._logged_in = False
                    await self.login()
                    async with session.get(url) as resp2:
                        raw = await resp2.json(content_type=None)
                else:
                    raw = await resp.json(content_type=None)
            object_json = raw.get("objectJson")
            if not object_json:
                return None
            return json.loads(object_json)
        except (NaturelaAuthError, NaturelaConnectionError):
            raise
        except Exception as exc:
            raise NaturelaConnectionError(f"Failed to fetch device data: {exc}") from exc

    async def set_state(self, state: int) -> bool:
        """Set device state. 0=OFF, 1=ON, 2=Timers."""
        return await self._post_command({"deviceId": self._device_id, "state": state})

    async def set_temperature(self, temperature: float) -> bool:
        """Set target boiler temperature."""
        return await self._post_command({"deviceId": self._device_id, "temperature": int(temperature)})

    async def _post_command(self, payload: dict) -> bool:
        """POST a command to the update endpoint."""
        if not self._logged_in:
            await self.login()
        session = await self._get_session()
        try:
            async with session.post(UPDATE_URL, json=payload, headers={"Content-Type": "application/json"}) as resp:
                return resp.status == 200
        except Exception as exc:
            _LOGGER.error("Command request failed: %s", exc)
            return False

    async def close(self) -> None:
        """Close the underlying aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None


def _extract_csrf_token(html: str) -> str:
    """Extract the ASP.NET CSRF token from the login page HTML."""
    marker = 'name="__RequestVerificationToken"'
    idx = html.find(marker)
    if idx == -1:
        return ""
    value_marker = 'value="'
    vi = html.find(value_marker, idx)
    if vi == -1:
        return ""
    start = vi + len(value_marker)
    end = html.find('"', start)
    return html[start:end] if end != -1 else ""
