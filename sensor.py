"""Sensor platform for MyAir3."""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MyAir3Coordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor platform from config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[SensorEntity] = []

    # System sensors
    entities.append(
        MyAir3SystemTempSensor(
            coordinator, config_entry.entry_id, "Actual", "centralActualTemp"
        )
    )
    entities.append(
        MyAir3SystemTempSensor(
            coordinator, config_entry.entry_id, "Target", "centralDesiredTemp"
        )
    )

    # Zone sensors
    for zone_id in coordinator.data["zones"]:
        entities.append(MyAir3DamperSensor(coordinator, zone_id, config_entry.entry_id))
        entities.append(
            MyAir3ZoneTempSensor(
                coordinator, zone_id, config_entry.entry_id, "Actual", "actualTemp"
            )
        )
        entities.append(
            MyAir3ZoneTempSensor(
                coordinator, zone_id, config_entry.entry_id, "Target", "desiredTemp"
            )
        )

    async_add_entities(entities)


class MyAir3TempSensorBase(SensorEntity):
    """Base class for MyAir3 temperature sensors."""

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: MyAir3Coordinator,
        entry_id: str,
        name_suffix: str,
        data_key: str,
    ) -> None:
        """Initialize."""
        self.coordinator = coordinator
        self._entry_id = entry_id
        self._data_key = data_key
        self._name_suffix = name_suffix

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_added_to_hass(self):
        """Connect to coordinator."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )


class MyAir3SystemTempSensor(MyAir3TempSensorBase):
    """System temperature sensor."""

    def __init__(
        self,
        coordinator: MyAir3Coordinator,
        entry_id: str,
        name_suffix: str,
        data_key: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry_id, name_suffix, data_key)
        self.translation_key = f"system_{name_suffix.lower()}_temp"
        self._attr_unique_id = f"{coordinator.host}_system_{data_key}"

    @property
    def native_value(self) -> float | None:
        """Return the system temperature."""
        return self.coordinator.data.get(self._data_key)


class MyAir3ZoneTempSensor(MyAir3TempSensorBase):
    """Zone temperature sensor."""

    def __init__(
        self,
        coordinator: MyAir3Coordinator,
        zone_id: int,
        entry_id: str,
        name_suffix: str,
        data_key: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry_id, name_suffix, data_key)
        self._zone_id = zone_id
        self.translation_key = f"zone_{name_suffix.lower()}_temp"
        self._attr_translation_placeholders = {
            "zone_name": coordinator.data["zones"][zone_id]["name"]
        }
        self._attr_unique_id = f"{coordinator.host}_zone_{zone_id}_{data_key}"

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False

        zone = self.coordinator.data["zones"].get(self._zone_id)
        if not zone:
            return False

        # Actual temperature sensor is only available if the hardware sensor is working
        if self._data_key == "actualTemp" and not zone.get("tempSensorAvailable", True):
            return False

        return True

    @property
    def native_value(self) -> float | None:
        """Return the zone temperature."""
        zone = self.coordinator.data["zones"].get(self._zone_id)
        if not zone:
            return None

        # If it's the actual temp sensor and it's unavailable, we already return False for available.
        # However, for consistency with climate.py, we could return the fallback value here if we wanted.
        # But for a sensor named "Actual Temperature", it's better to stay unavailable.
        return zone.get(self._data_key)


class MyAir3DamperSensor(SensorEntity):
    """Zone damper position sensor."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:valve"
    translation_key = "damper"

    def __init__(
        self, coordinator: MyAir3Coordinator, zone_id: int, entry_id: str
    ) -> None:
        """Initialize."""
        self.coordinator = coordinator
        self._zone_id = zone_id
        self._entry_id = entry_id
        self._attr_translation_placeholders = {
            "zone_name": coordinator.data["zones"][zone_id]["name"]
        }
        self._attr_unique_id = f"{coordinator.host}_zone_{zone_id}_damper"

    @property
    def should_poll(self) -> bool:
        """No polling needed, coordinator handles updates."""
        return False

    @property
    def available(self) -> bool:
        """Sensor is only available when temperature sensor has low/no battery."""
        zone = self.coordinator.data["zones"][self._zone_id]
        # Only show damper sensor when temp sensor is unavailable
        return self.coordinator.last_update_success and not zone.get(
            "tempSensorAvailable", True
        )

    @property
    def native_value(self) -> int | None:
        """Return the damper position percentage."""
        return self.coordinator.data["zones"][self._zone_id]["userPercentSetting"]

    async def async_added_to_hass(self):
        """Connect to coordinator."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )
