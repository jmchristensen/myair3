"""Climate platform for MyAir3."""

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

from . import MyAir3Coordinator
from .const import DOMAIN, FAN_MODE_TO_MYAIR3, MODE_TO_MYAIR3

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate platform from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[ClimateEntity] = [MyAir3Climate(coordinator, config_entry.entry_id)]
    entities.extend(
        MyAir3Zone(coordinator, zone_id, config_entry.entry_id)
        for zone_id in coordinator.data["zones"]
    )

    async_add_entities(entities)


class MyAir3Climate(ClimateEntity):
    """Main system climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.FAN_MODE
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.FAN_ONLY]
    _attr_fan_modes = ["low", "medium", "high"]
    _attr_min_temp = 16.0
    _attr_max_temp = 32.0
    _attr_target_temperature_step = 0.5

    def __init__(self, coordinator: MyAir3Coordinator, entry_id: str) -> None:
        """Initialize."""
        self.coordinator = coordinator
        self._entry_id = entry_id
        self._attr_name = "System"
        self._attr_unique_id = f"{coordinator.host}_system"

    @property
    def should_poll(self) -> bool:
        """Return whether polling is needed.

        No polling needed, coordinator handles updates.
        """
        return False

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return self.coordinator.last_update_success

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        return self.coordinator.data["centralActualTemp"]

    @property
    def target_temperature(self) -> float:
        """Return the target temperature."""
        return self.coordinator.data["centralDesiredTemp"]

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        if self.coordinator.data["airconOnOff"] == 0:
            return HVACMode.OFF
        mode = self.coordinator.data["mode"]
        return {1: HVACMode.COOL, 2: HVACMode.HEAT, 3: HVACMode.FAN_ONLY}.get(
            mode, HVACMode.OFF
        )

    @property
    def fan_mode(self) -> str:
        """Return the current fan mode."""
        speed = self.coordinator.data["fanSpeed"]
        return {1: "low", 2: "medium", 3: "high"}.get(speed, "low")

    async def async_set_temperature(self, **kwargs):
        """Set target temperature."""
        temp = kwargs.get("temperature")
        if temp:
            await self.coordinator.set_system_temp(temp)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new target hvac mode."""

        # 1. Handle OFF mode (system power)
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.set_system_power(0)
            return

        # 2. Handle other modes (COOL, HEAT, FAN_ONLY)
        # First, ensure the power is ON if it was OFF
        current_power = self.coordinator.data.get("airconOnOff", 0)
        if current_power == 0:
            await self.coordinator.set_system_power(1)

        # Then, set the mode
        myair3_mode = MODE_TO_MYAIR3.get(hvac_mode)
        if myair3_mode is not None:
            await self.coordinator.set_hvac_mode(myair3_mode)

    async def async_set_fan_mode(self, fan_mode: str):
        """Set fan mode."""
        speed_map = FAN_MODE_TO_MYAIR3
        if fan_mode in speed_map:
            await self.coordinator.set_fan_speed(speed_map[fan_mode])

    async def async_added_to_hass(self):
        """Connect to coordinator."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class MyAir3Zone(ClimateEntity):
    """Zone climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.FAN_ONLY]
    _attr_min_temp = 16.0
    _attr_max_temp = 32.0
    _attr_target_temperature_step = 0.5

    def __init__(
        self, coordinator: MyAir3Coordinator, zone_id: int, entry_id: str
    ) -> None:
        """Initialize."""
        self.coordinator = coordinator
        self._zone_id = zone_id
        self._entry_id = entry_id
        zone_name = coordinator.data["zones"][zone_id]["name"]
        self._attr_name = zone_name
        self._attr_unique_id = f"{coordinator.host}_zone_{zone_id}"

    @property
    def should_poll(self) -> bool:
        """No polling needed, coordinator handles updates."""
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        zone = self.coordinator.data["zones"][self._zone_id]
        # If temp sensor unavailable, use damper % as proxy (0-100 maps to 15-30°C range)
        if not zone.get("tempSensorAvailable", True):
            damper = zone["userPercentSetting"]
            return 15 + (damper / 100 * 15)  # Maps 0% to 15°C, 100% to 30°C
        return zone["actualTemp"]

    @property
    def target_temperature(self) -> float:
        """Return the target temperature."""
        zone = self.coordinator.data["zones"][self._zone_id]
        # If temp sensor unavailable, show damper % mapped to temp range
        if not zone.get("tempSensorAvailable", True):
            damper = zone["userPercentSetting"]
            return 15 + (damper / 100 * 15)
        return zone["desiredTemp"]

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        setting = self.coordinator.data["zones"][self._zone_id]["setting"]
        return HVACMode.OFF if setting == 0 else HVACMode.FAN_ONLY

    async def async_set_temperature(self, **kwargs):
        """Set target temperature."""
        temp = kwargs.get("temperature")
        if temp:
            await self.coordinator.set_zone_temp(self._zone_id, temp)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Turn zone on/off."""
        power = 1 if hvac_mode != HVACMode.OFF else 0
        await self.coordinator.set_zone_power(self._zone_id, power)

    async def async_added_to_hass(self):
        """Connect to coordinator."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
