"""Climate entity for Naturela BurnerTouch pellet stove."""
from __future__ import annotations
import logging
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import CONF_DEVICE_ID, DOMAIN, MANUFACTURER, MODEL, STATE_OFF, STATE_ON

_LOGGER = logging.getLogger(__name__)
HVAC_MODES = [HVACMode.OFF, HVACMode.HEAT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NaturelaClimate(coordinator=data["coordinator"], api=data["api"], device_id=entry.data.get(CONF_DEVICE_ID, 6548))])


class NaturelaClimate(CoordinatorEntity, ClimateEntity):
    """Represents the pellet stove as a HA climate entity."""
    _attr_hvac_modes = HVAC_MODES
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 30
    _attr_max_temp = 85
    _attr_target_temperature_step = 1.0
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator, api, device_id: int) -> None:
        super().__init__(coordinator)
        self._api = api
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{device_id}_climate"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, str(device_id))},
            "name": "Schuurkachel",
            "manufacturer": MANUFACTURER,
            "model": MODEL,
        }

    @property
    def hvac_mode(self) -> HVACMode:
        if not self.coordinator.data:
            return HVACMode.OFF
        return HVACMode.HEAT if self.coordinator.data.get("State", STATE_OFF) == STATE_ON else HVACMode.OFF

    @property
    def current_temperature(self):
        return self.coordinator.data.get("TempBoiler") if self.coordinator.data else None

    @property
    def target_temperature(self):
        return self.coordinator.data.get("SetTemp") if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict:
        if not self.coordinator.data:
            return {}
        d = self.coordinator.data
        return {
            "status": d.get("Status"), "flue_temp": d.get("TempFume"),
            "dhw_temp": d.get("TempDHW"), "fire_level": d.get("FireLevel"),
            "power_kw": d.get("FPower"), "output_power_pct": d.get("OutputPower"),
            "ch_pump": d.get("CHPump"), "dhw_pump": d.get("DHWPump"),
            "fuel_consumed_kg": d.get("FuelConsum"), "error_flag": d.get("ErrorFlag"),
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        state = STATE_ON if hvac_mode == HVACMode.HEAT else STATE_OFF
        if await self._api.set_state(state):
            await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs) -> None:
        temp = kwargs.get("temperature")
        if temp and await self._api.set_temperature(temp):
            await self.coordinator.async_request_refresh()
