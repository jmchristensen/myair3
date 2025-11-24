"""Sensor platform for MyAir3."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
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

    entities = [
        MyAir3DamperSensor(coordinator, zone_id, config_entry.entry_id)
        for zone_id in coordinator.data["zones"]
    ]

    async_add_entities(entities)


class MyAir3DamperSensor(SensorEntity):
    """Zone damper position sensor."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:valve"

    def __init__(
        self, coordinator: MyAir3Coordinator, zone_id: int, entry_id: str
    ) -> None:
        """Initialize."""
        self.coordinator = coordinator
        self._zone_id = zone_id
        self._entry_id = entry_id
        zone_name = coordinator.data["zones"][zone_id]["name"]
        self._attr_name = f"{zone_name} Damper"
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
