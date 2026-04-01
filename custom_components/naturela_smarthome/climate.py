"""Climate entity for Naturela BurnerTouch pellet stove."""
from __future__ import annotations

import datetime
import logging

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, DOMAIN, MANUFACTURER, MODEL, STATE_OFF, STATE_ON, STATUS_NAMES

_LOGGER = logging.getLogger(__name__)

HVAC_MODES = [HVACMode.OFF, HVACMode.HEAT]

# Status codes where the stove is actively running / starting up
# 0=Stand-by, 1=Ontsteking, 2=Werkt, 3=Ontsteking(Igniter=True), 4=Fout, 5=Wachten, 6=Reinigen
# String values: older firmware may return "Firing" (ignition) or "keeping" (on temp), "Burning" (heating up)
ACTIVE_STATUSES = {1, 2, 3, 5, 6, 8, "Firing", "keeping", "Burning"}  # 3=Ontsteking(Igniter=True), 8=normaal werken

# Max time to wait for stove to enter an active status after an ON command
_COMMAND_TIMEOUT = datetime.timedelta(minutes=5)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Naturela climate entity."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            NaturelaClimate(
                coordinator=data["coordinator"],
                api=data["api"],
                device_id=entry.data.get(CONF_DEVICE_ID, 6548),
            )
        ]
    )


class NaturelaClimate(CoordinatorEntity, ClimateEntity):
    """Represents the pellet stove as a HA climate entity.

    Supports:
      - HVAC modes : OFF / HEAT
      - Target temperature control

    Uses optimistic state after a user command (_command_pending=True) so the
    UI shows \"Verwarmen\" immediately.  The coordinator is blocked from
    resetting the mode to OFF until the stove is confirmed running
    (Status in ACTIVE_STATUSES) or the user explicitly turns it off.
    """

    _attr_hvac_modes = HVAC_MODES
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 30
    _attr_max_temp = 85
    _attr_target_temperature_step = 1.0
    _attr_has_entity_name = True
    _attr_name = None  # use device name

    def __init__(self, coordinator, api, device_id: int) -> None:
        super().__init__(coordinator)
        self._api = api
        self._device_id = device_id
        self._command_pending = False  # True while waiting for stove to start
        self._command_pending_since: datetime.datetime | None = None
        self._attr_unique_id = f"{DOMAIN}_{device_id}_climate"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(device_id))},
            "name": "Schuurkachel",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }
        # Initialise _attr_* from current coordinator data (no async_write_ha_state)
        self._update_from_data(coordinator.data or {})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_from_data(self, data: dict) -> None:
        """Update _attr_* from a data dict.  Safe to call from __init__."""
        status = data.get("Status", 0)
        state = data.get("State", STATE_OFF)

        if status in ACTIVE_STATUSES or state == STATE_ON:
            self._attr_hvac_mode = HVACMode.HEAT
        else:
            self._attr_hvac_mode = HVACMode.OFF

        self._attr_current_temperature = data.get("TempBoiler")
        self._attr_target_temperature = data.get("SetTemp")

    def _handle_coordinator_update(self) -> None:
        """Called by the coordinator after every poll.

        When _command_pending is True (user just pressed \"heat\") we only
        switch to OFF if the API still reports stand-by AND the state field
        is also 0.  Once the stove enters an active status we clear the flag.
        """
        data = self.coordinator.data or {}
        status = data.get("Status", 0)
        state = data.get("State", STATE_OFF)

        if status in ACTIVE_STATUSES:
            # Stove is genuinely running — clear the pending flag and set HEAT
            self._command_pending = False
            self._command_pending_since = None
            self._attr_hvac_mode = HVACMode.HEAT
        elif self._command_pending:
            # Still waiting for the stove to start — keep optimistic HEAT state
            _LOGGER.debug(
                "Command pending, ignoring coordinator OFF (status=%s state=%s)",
                status,
                state,
            )
            # Timeout: give up if stove never started within 5 minutes
            if (
                self._command_pending_since is not None
                and (
                    datetime.datetime.now(datetime.timezone.utc)
                    - self._command_pending_since
                    > _COMMAND_TIMEOUT
                )
            ):
                _LOGGER.warning(
                    "Command timeout: stove did not start within %s, resetting pending flag",
                    _COMMAND_TIMEOUT,
                )
                self._command_pending = False
                self._command_pending_since = None
        else:
            # No pending command — follow the API faithfully
            if state == STATE_ON:
                self._attr_hvac_mode = HVACMode.HEAT
            else:
                self._attr_hvac_mode = HVACMode.OFF

        # Always update temperatures
        self._attr_current_temperature = data.get("TempBoiler")
        self._attr_target_temperature = data.get("SetTemp")

        if self.hass is not None:
            self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Extra attributes
    # ------------------------------------------------------------------

    @property
    def extra_state_attributes(self) -> dict:
        """Expose extra stove data as attributes."""
        if not self.coordinator.data:
            return {}
        d = self.coordinator.data
        return {
            "status": d.get("Status"),
            "flue_temp": d.get("TempFume"),
            "dhw_temp": d.get("TempDHW"),
            "fire_level": d.get("FireLevel"),
            "power_kw": d.get("FPower"),
            "output_power_pct": d.get("OutputPower"),
            "ch_pump": d.get("CHPump"),
            "dhw_pump": d.get("DHWPump"),
            "fuel_consumed_kg": d.get("FuelConsum"),
            "error_flag": d.get("ErrorFlag"),
            "command_pending": self._command_pending,
            "status_name": STATUS_NAMES.get(d.get("Status", 0), f"Status {d.get('Status')}"),
        }

    # ------------------------------------------------------------------
    # Service calls
    # ------------------------------------------------------------------

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Turn stove on or off."""
        if hvac_mode == HVACMode.HEAT:
            self._command_pending = True
            self._command_pending_since = datetime.datetime.now(datetime.timezone.utc)
        else:
            self._command_pending = False

        # Optimistic update so UI reflects the change immediately
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

        state = STATE_ON if hvac_mode == HVACMode.HEAT else STATE_OFF
        try:
            success = await self._api.set_state(state)
            if success:
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to set HVAC mode to %s", hvac_mode)
                self._command_pending = False
                await self.coordinator.async_request_refresh()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Error setting HVAC mode to %s: %s", hvac_mode, err)
            self._command_pending = False
            await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs) -> None:
        """Set a new target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return
        try:
            success = await self._api.set_temperature(temperature)
            if success:
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.error("Failed to set temperature to %s", temperature)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Error setting temperature to %s: %s", temperature, err)
