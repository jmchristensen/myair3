"""Device registry for MyAir3 integration."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN


async def async_get_device_info(hass: HomeAssistant, entry_id: str) -> dict:
    """Get device info for MyAir3 system."""
    coordinator = hass.data[DOMAIN][entry_id]

    return {
        "identifiers": {(DOMAIN, coordinator.host)},
        "name": "MyAir3 System",
        "manufacturer": "Advantage Air",
        "model": "MyAir3",
        "sw_version": "Legacy XML",
    }


async def async_setup_device_registry(hass: HomeAssistant, entry_id: str) -> None:
    """Set up device registry entry."""
    device_registry = dr.async_get(hass)
    coordinator = hass.data[DOMAIN][entry_id]

    device_registry.async_get_or_create(
        config_entry_id=entry_id,
        identifiers={(DOMAIN, coordinator.host)},
        name="MyAir3 System",
        manufacturer="Advantage Air",
        model="MyAir3",
        sw_version="Legacy XML",
    )
