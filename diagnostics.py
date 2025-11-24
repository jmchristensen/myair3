"""Diagnostics support for MyAir3 integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import MyAir3Coordinator
from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: MyAir3Coordinator = hass.data[DOMAIN][entry.entry_id]

    return {
        "entry_data": {
            "host": entry.data.get("host"),
        },
        "coordinator_last_update_success": coordinator.last_update_success,
        "coordinator_last_update": coordinator.last_update_success,
        "system_data": {
            "power": "on" if coordinator.data["airconOnOff"] == 1 else "off",
            "mode": {1: "cool", 2: "heat", 3: "fan"}.get(
                coordinator.data["mode"], "unknown"
            ),
            "fan_speed": {1: "low", 2: "medium", 3: "high"}.get(
                coordinator.data["fanSpeed"], "unknown"
            ),
            "current_temp": coordinator.data["centralActualTemp"],
            "target_temp": coordinator.data["centralDesiredTemp"],
            "num_zones": len(coordinator.data["zones"]),
        },
        "zones": {
            zone_id: {
                "name": zone_data["name"],
                "power": "on" if zone_data["setting"] == 1 else "off",
                "current_temp": zone_data["actualTemp"],
                "target_temp": zone_data["desiredTemp"],
                "damper_position": zone_data["userPercentSetting"],
                "temp_sensor_available": zone_data["tempSensorAvailable"],
            }
            for zone_id, zone_data in coordinator.data["zones"].items()
        },
    }
