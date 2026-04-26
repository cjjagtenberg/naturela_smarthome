"""Naturela Smarthome API client."""
from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

from .const import API_URL, LOGIN_URL, SET_STATE_URL, SET_TEMP_URL

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
        self._device_serial: str | None = None  # populated from DeviceID in API response
        self._session: aiohttp.ClientSession | None = None
        self._logged_in = False

    async def _get_session(self) -> aiohttp.ClientSession:
        """Return or create an aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def login(self) -> bool:
        """Log in to iot.naturela-bg.com and store session cookie.

        The site uses ASP.NET anti-forgery tokens, so we first do a GET to
        retrieve the token, then POST the credentials.
        """
        session = await self._get_session()
        try:
            # Step 1 – fetch login page to grab the CSRF token
            async with session.get(LOGIN_URL) as resp:
                html = await resp.text()

            csrf_token = _extract_csrf_token(html)
            if not csrf_token:
                _LOGGER.warning("Could not extract CSRF token from login page")

            # Step 2 – POST credentials
            form_data = {
                "Email": self._username,
                "Password": self._password,
                "rememberMe": "true",
                "__RequestVerificationToken": csrf_token,
            }
            async with session.post(
                LOGIN_URL,
                data=form_data,
                allow_redirects=True,
            ) as resp:
                final_url = str(resp.url)
                self._logged_in = "login" not in final_url.lower()
                _LOGGER.debug(
                    "Login result: status=%s, final_url=%s, success=%s",
                    resp.status,
                    final_url,
                    self._logged_in,
                )
                if not self._logged_in:
                    raise NaturelaAuthError(
                        f"Login failed – ended up at {final_url}"
                    )
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
                    _LOGGER.debug("Session expired, re-logging in")
                    self._logged_in = False
                    await self.login()
                    async with session.get(url) as resp2:
                        raw = await resp2.json(content_type=None)
                else:
                    raw = await resp.json(content_type=None)

            object_json = raw.get("objectJson")
            if not object_json:
                _LOGGER.warning("Empty objectJson in API response")
                return None

            parsed = json.loads(object_json)
            # Cache the device serial number for use in setState commands
            if parsed.get("DeviceID"):
                self._device_serial = str(parsed["DeviceID"])
            return parsed

        except (NaturelaAuthError, NaturelaConnectionError):
            raise
        except Exception as exc:
            raise NaturelaConnectionError(
                f"Failed to fetch device data: {exc}"
            ) from exc

    async def set_state(self, state: int) -> bool:
        """Set device state. 0 = OFF, 128 = ON."""
        # Ensure we have the serial number (populated by get_device_data)
        if self._device_serial is None:
            _LOGGER.debug("Serial not yet cached, fetching device data first")
            await self.get_device_data()
        device_id = self._device_serial or str(self._device_id)
        return await self._post_command(
            {"deviceId": device_id, "state": state},
            url=SET_STATE_URL,
        )

    async def set_temperature(self, temperature: float) -> bool:
        """Set target boiler temperature (degrees C)."""
        if self._device_serial is None:
            await self.get_device_data()
        device_id = self._device_serial or str(self._device_id)
        _LOGGER.debug(
            "set_temperature: sending %s to %s for device %s",
            int(temperature), SET_TEMP_URL, device_id,
        )
        return await self._post_command(
            {"deviceId": device_id, "temperature": int(temperature)},
            url=SET_TEMP_URL,
        )

    async def _post_command(self, payload: dict, url: str = SET_STATE_URL) -> bool:
        """POST a command; re-login once if the session has expired."""
        if not self._logged_in:
            await self.login()
        session = await self._get_session()

        def _do_post():
            return session.post(
                url,
                json=payload,
                allow_redirects=False,
                headers={
                    "Content-Type": "application/json",
                    "Origin": "https://iot.naturela-bg.com",
                    "Referer": "https://iot.naturela-bg.com/",
                },
            )

        try:
            async with _do_post() as resp:
                if resp.status in (301, 302, 401, 403):
                    # Session cookie expired — re-login and retry once
                    _LOGGER.debug(
                        "Session expired during command (status=%s), re-logging in",
                        resp.status,
                    )
                    self._logged_in = False
                    await self.login()
                    async with _do_post() as resp2:
                        success = resp2.status == 200
                        if not success:
                            _LOGGER.error(
                                "Command failed after re-login: status=%s payload=%s",
                                resp2.status, payload,
                            )
                        return success
                success = resp.status == 200
                if not success:
                    _LOGGER.error(
                        "Command failed: status=%s payload=%s",
                        resp.status, payload,
                    )
                return success
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
    # Search for value="..." after the marker
    value_marker = 'value="'
    vi = html.find(value_marker, idx)
    if vi == -1:
        return ""
    start = vi + len(value_marker)
    end = html.find('"', start)
    return html[start:end] if end != -1 else ""
