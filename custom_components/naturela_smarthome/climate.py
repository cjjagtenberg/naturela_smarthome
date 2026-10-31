"""Climate entity for Naturela BurnerTouch pellet stove."""
from __future__ import annotations

import logging
import math

import voluptuous as vol

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .verify import CommandVerifier
from .const import CONF_DEVICE_ID, DOMAIN, MANUFACTURER, MODEL, STATE_OFF, STATE_ON, STATUS_NAMES

_LOGGER = logging.getLogger(__name__)


def _safe_temp(value):
    """Convert API temperature value to float, returning None for NaN/Inf/None."""
    if value is None:
        return None
    try:
        f = float(value)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


HVAC_MODES = [HVACMode.OFF, HVACMode.HEAT]

SERVICE_TURN_OFF_IN = "turn_off_in"
SERVICE_TURN_ON_FOR = "turn_on_for"
SERVICE_TURN_ON_AT = "turn_on_at"
SERVICE_TURN_OFF_AT = "turn_off_at"
SERVICE_CANCEL_SCHEDULE = "cancel_schedule"
SERVICE_START_TIMER = "start_timer"
ATTR_DELAY = "delay"
ATTR_DURATION = "duration"
ATTR_DATETIME = "datetime"

# Status codes where the stove is actively running / starting up
# 0=Stand-by, 1=Cleaning, 2=Burning, 3=Cool down, 4=Fault, 5=Suspend, 6=Cleaning
# String values: older firmware may return "Firing" (ignition) or "keeping" (on temp)
ACTIVE_STATUSES = {1, 2, 5, 6, 8, "Firing", "keeping"}
# 8 = normal operation (observed in the field)


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
                scheduler=data["scheduler"],
            )
        ]
    )

    platform = entity_platform.async_get_current_platform()
    duration_schema = {
        vol.Required(ATTR_DURATION): vol.All(
            cv.time_period, cv.positive_timedelta
        )
    }
    datetime_schema = {vol.Required(ATTR_DATETIME): cv.datetime}
    platform.async_register_entity_service(
        SERVICE_TURN_OFF_IN, duration_schema, "async_service_turn_off_in"
    )
    platform.async_register_entity_service(
        SERVICE_TURN_ON_FOR, duration_schema, "async_service_turn_on_for"
    )
    platform.async_register_entity_service(
        SERVICE_TURN_ON_AT, datetime_schema, "async_service_turn_on_at"
    )
    platform.async_register_entity_service(
        SERVICE_TURN_OFF_AT, datetime_schema, "async_service_turn_off_at"
    )
    platform.async_register_entity_service(
        SERVICE_CANCEL_SCHEDULE, {}, "async_service_cancel_schedule"
    )
    platform.async_register_entity_service(
        SERVICE_START_TIMER,
        {
            vol.Required(ATTR_DELAY): cv.time_period,
            **duration_schema,
        },
        "async_service_start_timer",
    )


class NaturelaClimate(CoordinatorEntity, ClimateEntity):
    """Represents the pellet stove as a HA climate entity.

    Supports:
      - HVAC modes        : OFF / HEAT
      - Target temperature control

    Uses optimistic state after a user command (_command_pending=True) so the
    UI shows "Heating" immediately.  The coordinator is blocked from resetting
    the mode to OFF until the stove is confirmed running (Status in
    ACTIVE_STATUSES) or the user explicitly turns it off.
    """

    _attr_hvac_modes = HVAC_MODES
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 30
    _attr_max_temp = 85
    _attr_target_temperature_step = 1.0
    _attr_has_entity_name = True
    _attr_name = None  # use device name

    def __init__(self, coordinator, api, device_id: int, scheduler) -> None:
        super().__init__(coordinator)
        self._api = api
        self._scheduler = scheduler
        self._verifier = CommandVerifier(
            coordinator.hass, api, coordinator,
            lambda: self.entity_id,
            lambda: self.async_write_ha_state() if self.hass else None,
        )
        self._device_id = device_id
        self._command_pending = False  # True while waiting for stove to start
        self._attr_unique_id = f"{DOMAIN}_{device_id}_climate"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(device_id))},
            "name": "Pellet Stove",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }
        # Initialise _attr_* from current coordinator data (no async_write_ha_state)
        self._update_from_data(coordinator.data or {})

    async def async_added_to_hass(self) -> None:
        """Hook the scheduler up to this entity."""
        await super().async_added_to_hass()
        self._scheduler.attach_handler(self._async_switch_from_schedule)
        self.async_on_remove(lambda: self._scheduler.attach_handler(None))
        self.async_on_remove(
            self._scheduler.async_add_listener(self.async_write_ha_state)
        )
        self.async_on_remove(self._verifier.cancel)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_from_data(self, data: dict) -> None:
        """Update _attr_* from a data dict. Safe to call from __init__."""
        status = data.get("Status", 0)
        state  = data.get("State", STATE_OFF)
        if status in ACTIVE_STATUSES or state == STATE_ON:
            self._attr_hvac_mode = HVACMode.HEAT
        else:
            self._attr_hvac_mode = HVACMode.OFF
        self._attr_current_temperature = _safe_temp(data.get("TempBoiler"))
        self._attr_target_temperature  = _safe_temp(data.get("SetTemp"))

    def _handle_coordinator_update(self) -> None:
        """Called by the coordinator after every poll.

        When _command_pending is True (user just pressed "heat") we only switch
        to OFF if the API still reports stand-by AND the state field is also 0.
        Once the stove enters an active status we clear the flag.
        """
        data   = self.coordinator.data or {}
        status = data.get("Status", 0)
        state  = data.get("State", STATE_OFF)

        if status in ACTIVE_STATUSES:
            # Stove is genuinely running -- clear the pending flag and set HEAT
            self._command_pending = False
            self._attr_hvac_mode  = HVACMode.HEAT
        elif self._command_pending:
            # Still waiting for the stove to start -- keep optimistic HEAT state
            _LOGGER.debug(
                "Command pending, ignoring coordinator OFF (status=%s state=%s)",
                status, state,
            )
        else:
            # No pending command -- follow the API faithfully
            if state == STATE_ON:
                self._attr_hvac_mode = HVACMode.HEAT
            else:
                self._attr_hvac_mode = HVACMode.OFF

        # Always update temperatures
        self._attr_current_temperature = _safe_temp(data.get("TempBoiler"))
        self._attr_target_temperature  = _safe_temp(data.get("SetTemp"))
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
            "status":           d.get("Status"),
            "flue_temp":        d.get("TempFume"),
            "dhw_temp":         d.get("TempDHW"),
            "fire_level":       d.get("FireLevel"),
            "power_kw":         d.get("FPower"),
            "output_power_pct": d.get("OutputPower"),
            "ch_pump":          d.get("CHPump"),
            "dhw_pump":         d.get("DHWPump"),
            "fuel_consumed_kg": d.get("FuelConsum"),
            "error_flag":       d.get("ErrorFlag"),
            "command_pending":  self._command_pending,
            "status_name": STATUS_NAMES.get(d.get("Status", 0), f"Status {d.get('Status')}"),
            "scheduled_on": self._scheduler.on_at.isoformat() if self._scheduler.on_at else None,
            "scheduled_off": self._scheduler.off_at.isoformat() if self._scheduler.off_at else None,
            "command_check": self._verifier.state,
            "last_command": self._api.last_command,
        }

    # ------------------------------------------------------------------
    # Service calls
    # ------------------------------------------------------------------

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Turn stove on or off (user action)."""
        await self._async_apply_hvac_mode(hvac_mode)
        if hvac_mode == HVACMode.OFF:
            await self._scheduler.async_manual_off()

    async def _async_switch_from_schedule(self, turn_on: bool) -> None:
        """Called by the scheduler; does not touch the schedule itself."""
        await self._async_apply_hvac_mode(HVACMode.HEAT if turn_on else HVACMode.OFF)

    async def _async_apply_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Send the on/off command to the stove."""
        if hvac_mode == HVACMode.HEAT:
            self._command_pending = True
        else:
            self._command_pending = False

        # Optimistic update so UI reflects the change immediately
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

        state = STATE_ON if hvac_mode == HVACMode.HEAT else STATE_OFF
        try:
            success = await self._api.set_state(state)
            if success:
                self._verifier.start(hvac_mode == HVACMode.HEAT)
            if not success:
                _LOGGER.error("Failed to set HVAC mode to %s", hvac_mode)
                self._command_pending = False
                await self.coordinator.async_request_refresh()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Error setting HVAC mode to %s: %s", hvac_mode, err)
            self._command_pending = False
            await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn the stove on (shortcut used by climate.turn_on service)."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        """Turn the stove off (shortcut used by climate.turn_off service)."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    # Timer / schedule entity services (v1.4.0)
    async def async_service_turn_off_in(self, duration) -> None:
        await self._scheduler.async_turn_off_in(duration)

    async def async_service_turn_on_for(self, duration) -> None:
        await self._scheduler.async_turn_on_for(duration)

    async def async_service_turn_on_at(self, datetime) -> None:  # noqa: A002
        await self._scheduler.async_set_on_at(datetime)

    async def async_service_turn_off_at(self, datetime) -> None:  # noqa: A002
        await self._scheduler.async_set_off_at(datetime)

    async def async_service_start_timer(self, delay, duration) -> None:
        await self._scheduler.async_start_timer(delay, duration)

    async def async_service_cancel_schedule(self) -> None:
        await self._scheduler.async_cancel()

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
